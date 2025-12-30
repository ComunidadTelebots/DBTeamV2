local socket = require('socket')
local ltn12_ok, ltn12 = pcall(require, 'ltn12')
local has_https, https = pcall(require, 'ssl.https')
local has_socket, socket_http = pcall(require, 'socket.http')
local json = require('libs.JSON')

local PORT = tonumber(os.getenv('WEB_API_PORT') or '8081')
local BOT_TOKEN = os.getenv('BOT_TOKEN') or ''
local redis = require('redis')
redis = redis.connect('127.0.0.1', 6379)

local function send_http_json(url, body, headers)
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

local function handle_request(client)
  client:settimeout(5)
  local ok, line = pcall(function() return client:receive('*l') end)
  if not ok or not line then client:close(); return end
  local method, path = line:match('^(%w+)%s+(.-)%s+HTTP')
  local headers = {}
  local content_length = 0
  while true do
    local hdr = client:receive('*l')
    if not hdr or hdr == '' then break end
    local name, val = hdr:match('^(.-):%s*(.*)')
    if name then headers[name:lower()] = val end
    if name and name:lower() == 'content-length' then content_length = tonumber(val) or 0 end
  end
  local body = ''
  if content_length > 0 then body = client:receive(content_length) end

  local function send_response(code, body_text, content_type)
    content_type = content_type or 'application/json'
    local resp = 'HTTP/1.1 ' .. tostring(code) .. '\r\n'
    resp = resp .. 'Access-Control-Allow-Origin: *\r\n'
    resp = resp .. 'Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n'
    resp = resp .. 'Access-Control-Allow-Headers: Content-Type\r\n'
    resp = resp .. 'Content-Type: ' .. content_type .. '\r\n'
    resp = resp .. 'Content-Length: ' .. tostring(#(body_text or '')) .. '\r\n\r\n'
    resp = resp .. (body_text or '')
    client:send(resp)
  end

  if method == 'OPTIONS' then
    send_response(200, '')
    client:close()
    return
  end

  if method == 'GET' and path:match('^/messages') then
    local qlimit = 20
    local q = path:match('limit=(%d+)')
    if q then qlimit = tonumber(q) end
    local items = redis:lrange('web:messages', 0, qlimit - 1) or {}
    local out = {}
    for i,v in ipairs(items) do
      local ok, obj = pcall(json.decode, v)
      if ok and obj then table.insert(out, obj) end
    end
    send_response(200, json:encode(out))
    client:close()
    return
  end

  if method == 'POST' and path == '/send' then
    if BOT_TOKEN == '' then
      send_response(500, json:encode({ error = 'BOT_TOKEN not set' }))
      client:close()
      return
    end
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.chat_id or not payload.text then
      send_response(400, json:encode({ error = 'invalid payload, require chat_id and text' }))
      client:close()
      return
    end
    local url = 'https://api.telegram.org/bot' .. BOT_TOKEN .. '/sendMessage'
    local b = json:encode({ chat_id = payload.chat_id, text = payload.text })
    local raw, code = send_http_json(url, b, { ['Content-Type'] = 'application/json' })
    if not raw then
      send_response(500, json:encode({ error = code }))
    else
      send_response(200, raw, 'application/json')
    end
    client:close()
    return
  end

  if method == 'POST' and path == '/send_user' then
    -- enqueue a send request to be processed by the userbot process
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.chat_id or not payload.text then
      send_response(400, json:encode({ error = 'invalid payload, require chat_id and text' }))
      client:close()
      return
    end
    local pushed = redis:rpush('web:outbox', json:encode({ chat_id = payload.chat_id, text = payload.text }))
    if pushed then
      send_response(200, json:encode({ status = 'queued' }))
    else
      send_response(500, json:encode({ error = 'redis error' }))
    end
    client:close()
    return
  end

  -- not found
  send_response(404, json:encode({ error = 'not found' }))
  client:close()
end

local function start_server()
  local server = assert(socket.bind('*', PORT))
  server:settimeout(nil)
  print('Web API listening on port ' .. PORT)
  while true do
    local client = server:accept()
    pcall(handle_request, client)
  end
end

start_server()
