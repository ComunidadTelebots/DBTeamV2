local socket = require('socket')
local ltn12_ok, ltn12 = pcall(require, 'ltn12')
local has_https, https = pcall(require, 'ssl.https')
local has_socket, socket_http = pcall(require, 'socket.http')
local json = require('libs.JSON')

local PORT = tonumber(os.getenv('WEB_API_PORT') or '8081')
local BOT_TOKEN = os.getenv('BOT_TOKEN') or ''
local API_KEY = os.getenv('WEB_API_KEY') or ''
local ORIGIN = os.getenv('WEB_API_ORIGIN') or '*'
local SECRET = os.getenv('WEB_API_SECRET') or ''
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

-- Minimal pure-Lua SHA256 / HMAC implementation (works with Lua 5.2 bit32)
local bit = bit32
local function str2bytes(s)
  local t = {}
  for i=1,#s do t[i]=string.byte(s,i) end
  return t
end
local function bytes2str(t)
  return string.char(unpack(t))
end
local function tohex(s)
  return (s:gsub('.', function(c) return string.format('%02x', string.byte(c)) end))
end

local function sha256(msg)
  local K = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
  }
  local function rotr(x,n) return bit.ror(x,n) end
  local function shr(x,n) return bit.rshift(x,n) end
  local function add(...) local s=0; for i=1,select('#',...) do s=(s + select(i,...) ) % 2^32 end; return s end

  local H = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19}

  local msg_bits = #msg * 8
  msg = msg .. string.char(0x80)
  local zero_pad = (56 - (#msg % 64)) % 64
  msg = msg .. string.rep(string.char(0), zero_pad)
  -- append 64-bit big-endian length
  local hi = math.floor(msg_bits / 2^32)
  local lo = msg_bits % 2^32
  local function int32_to_bytes(n)
    n = n % 2^32
    local b1 = math.floor(n / 16777216) % 256
    local b2 = math.floor(n / 65536) % 256
    local b3 = math.floor(n / 256) % 256
    local b4 = n % 256
    return string.char(b1, b2, b3, b4)
  end
  msg = msg .. int32_to_bytes(hi) .. int32_to_bytes(lo)

  for i=1,#msg,64 do
    local w = {}
    local chunk = msg:sub(i,i+63)
    for j=1,16 do
      local a,b,c,d = string.byte(chunk, (j-1)*4+1, (j-1)*4+4)
      w[j-1] = ((a*256 + b)*256 + c)*256 + d
    end
    for j=16,63 do
      local s0 = add( bit.bxor( bit.bxor(rotr(w[j-15],7), rotr(w[j-15],18)), shr(w[j-15],3) ) )
      local s1 = add( bit.bxor( bit.bxor(rotr(w[j-2],17), rotr(w[j-2],19)), shr(w[j-2],10) ) )
      w[j] = add(w[j-16], s0, w[j-7], s1)
    end
    local a,b,c,d,e,f,g,h = H[1],H[2],H[3],H[4],H[5],H[6],H[7],H[8]
    for j=0,63 do
      local S1 = bit.bxor( bit.bxor(rotr(e,6), rotr(e,11)), rotr(e,25) )
      local ch = bit.bxor(bit.band(e,f), bit.band(bit.bnot(e), g))
      local temp1 = add(h, S1, ch, K[j+1], w[j])
      local S0 = bit.bxor( bit.bxor(rotr(a,2), rotr(a,13)), rotr(a,22) )
      local maj = bit.bxor(bit.bxor(bit.band(a,b), bit.band(a,c)), bit.band(b,c))
      local temp2 = add(S0, maj)
      h = g; g = f; f = e; e = add(d, temp1)
      d = c; c = b; b = a; a = add(temp1, temp2)
    end
    H[1]=add(H[1],a); H[2]=add(H[2],b); H[3]=add(H[3],c); H[4]=add(H[4],d); H[5]=add(H[5],e); H[6]=add(H[6],f); H[7]=add(H[7],g); H[8]=add(H[8],h)
  end
  local out = ''
  for i=1,8 do
    out = out .. string.format('%08x', H[i])
  end
  return out
end

local function hmac_sha256(key, msg)
  -- key and msg are strings; produce hex digest
  if #key > 64 then
    local kh = sha256(key)
    key = kh:gsub('(..)', function(h) return string.char(tonumber(h,16)) end)
  end
  key = key .. string.rep(string.char(0), 64 - #key)
  local o_key_pad = {}
  local i_key_pad = {}
  for i=1,64 do
    local kb = string.byte(key,i)
    o_key_pad[i] = string.char(bit.bxor(kb, 0x5c))
    i_key_pad[i] = string.char(bit.bxor(kb, 0x36))
  end
  local i_msg = table.concat(i_key_pad) .. msg
  local inner = sha256(i_msg)
  -- inner is hex; convert hex to raw bytes
  local inner_raw = inner:gsub('(..)', function(h) return string.char(tonumber(h,16)) end)
  local o_msg = table.concat(o_key_pad) .. inner_raw
  local outer = sha256(o_msg)
  return outer
end

local function rand_token()
  -- Prefer OpenSSL RNG if available on system
  local ok, fh = pcall(function() return io.popen('openssl rand -hex 32', 'r') end)
  if ok and fh then
    local out = fh:read('*a')
    fh:close()
    if out and out:match('%x%x') then
      out = out:gsub('%s+', '')
      if #out >= 64 then return out end
    end
  end
  -- Fallback: strengthen entropy for SHA256 fallback
  math.randomseed((os.time() % 100000) + (socket.gettime and math.floor(socket.gettime()*1000) or 0))
  local r = tostring(os.time()) .. tostring(math.random()) .. tostring(socket.gettime and socket.gettime() or '') .. tostring({}) .. tostring({})
  return sha256(r)
end

local function shell_escape_single(s)
  if not s then return '' end
  return s:gsub("'", "'\\''")
end

local function encrypt_token(plain)
  if SECRET == '' or not plain then return plain end
  local p = shell_escape_single(plain)
  local sec = shell_escape_single(SECRET)
  local cmd = "printf '%s' '" .. p .. "' | openssl enc -aes-256-cbc -a -salt -pbkdf2 -pass pass:'" .. sec .. "'"
  local fh = io.popen(cmd, 'r')
  if not fh then return plain end
  local out = fh:read('*a')
  fh:close()
  if not out or out == '' then return plain end
  out = out:gsub('%s+$','')
  return out
end

local function decrypt_token(cipher)
  if SECRET == '' or not cipher then return cipher end
  local c = shell_escape_single(cipher)
  local sec = shell_escape_single(SECRET)
  local cmd = "printf '%s' '" .. c .. "' | openssl enc -d -aes-256-cbc -a -pass pass:'" .. sec .. "'"
  local fh = io.popen(cmd, 'r')
  if not fh then return cipher end
  local out = fh:read('*a')
  fh:close()
  if not out or out == '' then return cipher end
  out = out:gsub('%s+$','')
  return out
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
    resp = resp .. 'Access-Control-Allow-Origin: ' .. ORIGIN .. '\r\n'
    resp = resp .. 'Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n'
    resp = resp .. 'Access-Control-Allow-Headers: Content-Type, Authorization, X-API-Key\r\n'
    resp = resp .. 'Access-Control-Allow-Credentials: true\r\n'
    resp = resp .. 'Content-Type: ' .. content_type .. '\r\n'
    resp = resp .. 'Content-Length: ' .. tostring(#(body_text or '')) .. '\r\n\r\n'
    resp = resp .. (body_text or '')
    client:send(resp)
  end

  local function check_auth()
    if API_KEY == '' then return true end
    local auth = headers['authorization'] or headers['x-api-key']
    if not auth then return false end
    -- support "Bearer <token>" and raw x-api-key
    if headers['authorization'] then
      local t = auth:match('^%s*Bearer%s+(.+)%s*$')
      if t and t == API_KEY then return true end
      -- check session tokens in redis (decrypt and validate)
      if t then
        local v = redis:get('web:session:'..t)
        if v then
          local dec = decrypt_token(v) or v
          local okj, obj = pcall(json.decode, dec)
          if okj and obj then return true end
        end
      end
    end
    if headers['x-api-key'] and headers['x-api-key'] == API_KEY then return true end
    return false
  end

  if method == 'OPTIONS' then
    send_response(200, '')
    client:close()
    return
  end

  if method == 'POST' and path == '/auth' then
    if BOT_TOKEN == '' then send_response(500, json:encode({ error = 'BOT_TOKEN not set on server' })); client:close(); return end
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.hash then
      send_response(400, json:encode({ error = 'invalid auth payload' })); client:close(); return
    end
    -- build data_check_string from payload excluding hash
    local parts = {}
    for k,v in pairs(payload) do
      if k ~= 'hash' then table.insert(parts, k) end
    end
    table.sort(parts)
    local data_check = ''
    for i,k in ipairs(parts) do
      local v = payload[k]
      data_check = data_check .. k .. '=' .. tostring(v)
      if i < #parts then data_check = data_check .. '\n' end
    end
    -- secret is sha256(bot_token) raw
    local secret_hex = sha256(BOT_TOKEN)
    local secret_raw = secret_hex:gsub('(..)', function(h) return string.char(tonumber(h,16)) end)
    local calc = hmac_sha256(secret_raw, data_check)
    if calc ~= (payload.hash or '') then
      send_response(401, json:encode({ error = 'invalid signature' })); client:close(); return
    end
    -- signature valid: create session token
    local token = rand_token()
    local sess = { id = payload.id, first_name = payload.first_name, last_name = payload.last_name, username = payload.username }
    local sess_raw = json:encode(sess)
    local enc = encrypt_token(sess_raw)
    local okset = redis:setex('web:session:' .. token, 3600, enc)
    if not okset then send_response(500, json:encode({ error = 'redis error' })); client:close(); return end
    send_response(200, json:encode({ token = token, ttl = 3600 }))
    client:close()
    return
  end

  if method == 'GET' and path:match('^/messages') then
    if not check_auth() then send_response(401, json:encode({ error = 'unauthorized' })); client:close(); return end
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

  if method == 'GET' and path == '/devices' then
    if not check_auth() then send_response(401, json:encode({ error = 'unauthorized' })); client:close(); return end
    local items = redis:lrange('web:devices', 0, -1) or {}
    local out = {}
    for i,v in ipairs(items) do
      local ok, obj = pcall(json.decode, v)
      if ok and obj then
        table.insert(out, { id = obj.id, name = obj.name })
      end
    end
    send_response(200, json:encode(out))
    client:close()
    return
  end

  if method == 'POST' and path == '/devices/add' then
    if not check_auth() then send_response(401, json:encode({ error = 'unauthorized' })); client:close(); return end
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.id or not payload.token then
      send_response(400, json:encode({ error = 'invalid payload, require id and token' })); client:close(); return
    end
    local enc = encrypt_token(payload.token)
    local obj = { id = payload.id, name = payload.name or payload.id, token = enc }
    local pushed = redis:rpush('web:devices', json:encode(obj))
    if pushed then send_response(200, json:encode({ status = 'added' })) else send_response(500, json:encode({ error = 'redis error' })) end
    client:close()
    return
  end

  if method == 'POST' and path == '/send' then
    if not check_auth() then send_response(401, json:encode({ error = 'unauthorized' })); client:close(); return end
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.chat_id or not payload.text then
      send_response(400, json:encode({ error = 'invalid payload, require chat_id and text' }))
      client:close()
      return
    end

    local token_to_use = BOT_TOKEN
    if payload.device_id then
      local items = redis:lrange('web:devices', 0, -1) or {}
      for i,v in ipairs(items) do
        local ok2, obj2 = pcall(json.decode, v)
        if ok2 and obj2 and obj2.id == payload.device_id and obj2.token then
          token_to_use = decrypt_token(obj2.token) or obj2.token
          break
        end
      end
    end
    if token_to_use == '' then
      send_response(500, json:encode({ error = 'no BOT_TOKEN available (and device not found)' }))
      client:close()
      return
    end

    local url = 'https://api.telegram.org/bot' .. token_to_use .. '/sendMessage'
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
    if not check_auth() then send_response(401, json:encode({ error = 'unauthorized' })); client:close(); return end
    -- enqueue a send request to be processed by the userbot process
    local ok, payload = pcall(function() return json:decode(body) end)
    if not ok or not payload or not payload.chat_id or not payload.text then
      send_response(400, json:encode({ error = 'invalid payload, require chat_id and text' }))
      client:close()
      return
    end
    local outobj = { chat_id = payload.chat_id, text = payload.text }
    if payload.device_id then outobj.device_id = payload.device_id end
    local pushed = redis:rpush('web:outbox', json:encode(outobj))
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
