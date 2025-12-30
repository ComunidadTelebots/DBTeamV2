local socket = require('socket')
local json = require('libs.JSON')

local PORT = tonumber(os.getenv('WEBHOOK_PORT') or '8080')
local BOT_TOKEN = os.getenv('BOT_TOKEN') or ''
if BOT_TOKEN == '' then
  print('BOT_TOKEN not set. Set BOT_TOKEN env var to use webhook adapter.')
  return
end

local function handle_update(obj)
  if not obj then return end
  -- similar mapping as bot_api_adapter
  local u = obj
  local data = { ID = 'UpdateNewMessage', message_ = {} }
  local m = data.message_
  local msg = u.message or u.edited_message or u.channel_post or u.edited_channel_post
  if not msg then return end
  m.chat_id_ = (msg.chat and msg.chat.id) or 0
  m.id_ = msg.message_id or 0
  m.date_ = msg.date or os.time()
  if msg.from then m.sender_user_id_ = msg.from.id else m.sender_user_id_ = 0 end
  if msg.text then
    m.content_ = { ID = 'MessageText', text_ = msg.text }
  elseif msg.caption then
    m.content_ = { ID = 'MessageText', text_ = msg.caption }
  else
    m.content_ = { ID = 'MessageUnsupported' }
  end
  if msg.reply_to_message then
    m.reply_to_message_id_ = msg.reply_to_message.message_id
  else
    m.reply_to_message_id_ = 0
  end
  -- call existing handler
  if tdcli_update_callback then
    tdcli_update_callback(data)
  else
    print('tdcli_update_callback not defined; ensure bot is loaded')
  end
end

local function start_server()
  local server = assert(socket.bind('*', PORT))
  server:settimeout(nil)
  print('Webhook adapter listening on port ' .. PORT)
  while true do
    local client = server:accept()
    client:settimeout(5)
    -- read request line
    local ok, line = pcall(function() return client:receive('*l') end)
    if not ok or not line then client:close(); goto continue end
    -- read headers
    local content_length = 0
    while true do
      local hdr = client:receive('*l')
      if not hdr or hdr == '' then break end
      local name, val = hdr:match('^(.-):%s*(.*)')
      if name and name:lower() == 'content-length' then
        content_length = tonumber(val) or 0
      end
    end
    local body = ''
    if content_length > 0 then
      body = client:receive(content_length)
    else
      -- attempt to read rest
      body = client:receive('*a') or ''
    end
    -- try parse json
    local ok, obj = pcall(json.decode, body)
    if ok and obj then
      pcall(handle_update, obj)
    end
    -- respond 200 OK
    local resp = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK'
    client:send(resp)
    client:close()
    ::continue::
  end
end

start_server()
