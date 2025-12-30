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
  if u.message then
    local data = { ID = 'UpdateNewMessage', message_ = {} }
    local m = data.message_
    local msg = u.message
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
    if tdcli_update_callback then tdcli_update_callback(data) end

  elseif u.edited_message then
    local msg = u.edited_message
    local data = { ID = 'UpdateMessageEdited', message_ = {} }
    local m = data.message_
    m.chat_id_ = (msg.chat and msg.chat.id) or 0
    m.id_ = msg.message_id or 0
    m.date_ = msg.edit_date or msg.date or os.time()
    if msg.from then m.sender_user_id_ = msg.from.id else m.sender_user_id_ = 0 end
    if msg.text then
      m.content_ = { ID = 'MessageText', text_ = msg.text }
    elseif msg.caption then
      m.content_ = { ID = 'MessageText', text_ = msg.caption }
    else
      m.content_ = { ID = 'MessageUnsupported' }
    end
    if tdcli_update_callback then tdcli_update_callback(data) end

  elseif u.callback_query then
    local cq = u.callback_query
    local data = { ID = 'UpdateNewCallbackQuery', callback_query_ = {} }
    local c = data.callback_query_
    c.id_ = cq.id
    c.from_ = cq.from and cq.from.id or 0
    c.data_ = cq.data
    c.inline_message_id_ = cq.inline_message_id
    if cq.message then
      c.message_ = { chat_id_ = cq.message.chat and cq.message.chat.id or 0, id_ = cq.message.message_id }
    end
    if tdcli_update_callback then tdcli_update_callback(data) end

  elseif u.inline_query then
    local iq = u.inline_query
    local data = { ID = 'UpdateNewInlineQuery', inline_query_ = {} }
    local q = data.inline_query_
    q.id_ = iq.id
    q.from_ = iq.from and iq.from.id or 0
    q.query_ = iq.query
    q.offset_ = iq.offset
    if tdcli_update_callback then tdcli_update_callback(data) end

  elseif u.channel_post then
    local msg = u.channel_post
    local data = { ID = 'UpdateNewChannelMessage', message_ = {} }
    local m = data.message_
    m.chat_id_ = (msg.chat and msg.chat.id) or 0
    m.id_ = msg.message_id or 0
    m.date_ = msg.date or os.time()
    if msg.text then
      m.content_ = { ID = 'MessageText', text_ = msg.text }
    elseif msg.caption then
      m.content_ = { ID = 'MessageText', text_ = msg.caption }
    else
      m.content_ = { ID = 'MessageUnsupported' }
    end
    if tdcli_update_callback then tdcli_update_callback(data) end
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
