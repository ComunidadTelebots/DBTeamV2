local json = require('libs.JSON')
local has_https, https = pcall(require, 'ssl.https')
local has_socket, socket_http = pcall(require, 'socket.http')
local ltn12 = require('ltn12')

local BOT_TOKEN = os.getenv('BOT_TOKEN') or ''
if BOT_TOKEN == '' then
  print('BOT_TOKEN not set. Set BOT_TOKEN env var to use Bot API adapter.')
  return
end

local API_BASE = 'https://api.telegram.org/bot' .. BOT_TOKEN

local function http_post(url, body, headers)
  local resp = {}
  local req = { url = url, method = 'POST', source = ltn12.source.string(body or ''), sink = ltn12.sink.table(resp) }
  req.headers = headers or {}
  if not req.headers['Content-Type'] then req.headers['Content-Type'] = 'application/json' end
  if not req.headers['Content-Length'] then req.headers['Content-Length'] = tostring(#(body or '')) end
  if has_https then
    local r, code, h = https.request(req)
    return table.concat(resp), code, h
  elseif has_socket then
    local r, code, h = socket_http.request(req)
    return table.concat(resp), code, h
  else
    return nil, 'no-http'
  end
end

local function bot_api_request(method, payload)
  local url = API_BASE .. '/' .. method
  local body = json:encode(payload or {})
  local resp, code = http_post(url, body, { ['Content-Type'] = 'application/json' })
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok then return obj end
  return nil, resp
end

-- Override tdcli_function to map basic methods to Bot API
tdcli_function = function(call, cb, extra)
  if not call or not call.ID then return end
  local id = call.ID
  if id == 'SendMessage' then
    local chat_id = call.chat_id_
    local text = ''
    if call.input_message_content_ and call.input_message_content_.text_ then text = call.input_message_content_.text_ end
    local parse_mode = nil
    if call.input_message_content_ and call.input_message_content_.parse_mode_ then
      if call.input_message_content_.parse_mode_.ID == 'TextParseModeMarkdown' then parse_mode = 'Markdown' end
      if call.input_message_content_.parse_mode_.ID == 'TextParseModeHTML' then parse_mode = 'HTML' end
    end
    local payload = { chat_id = chat_id, text = text }
    if parse_mode then payload.parse_mode = parse_mode end
    local res, err = bot_api_request('sendMessage', payload)
    if cb then cb(extra, res) end
    return res
  elseif id == 'DeleteMessages' or id == 'DeleteMessage' then
    local chat_id = call.chat_id_
    local message_ids = call.message_ids_ or call.message_id_
    local mid = nil
    if type(message_ids) == 'table' then mid = message_ids[0] end
    if not mid and type(message_ids) == 'number' then mid = message_ids end
    if mid then
      local res, err = bot_api_request('deleteMessage', { chat_id = chat_id, message_id = mid })
      if cb then cb(extra, res) end
      return res
    end
  elseif id == 'SearchPublicChat' then
    local username = call.username_
    local res, err = bot_api_request('getChat', { chat_id = '@'..username })
    if cb then cb(extra, res) end
    return res
  else
    -- unsupported method in adapter; return empty
    if cb then cb(extra, {}) end
    return {}
  end
end

-- Polling loop: getUpdates and forward to tdcli_update_callback
local offset = 0
local function poll()
  while true do
    local ok, res = bot_api_request('getUpdates', { offset = offset, timeout = 20 })
    if ok and ok.result then
      for _, u in ipairs(ok.result) do
        offset = (u.update_id or 0) + 1
        if u.message then
          local msg = u.message
          local data = { ID = 'UpdateNewMessage', message_ = {} }
          local m = data.message_
          m.chat_id_ = msg.chat.id
          m.id_ = msg.message_id
          m.date_ = msg.date
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
          tdcli_update_callback(data)
        end
      end
    else
      -- wait before retry
      os.execute('sleep 1')
    end
  end
end

print('Starting Bot API adapter polling loop (BOT_TOKEN set).')
poll()
