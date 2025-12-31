-- Verify encryption for web:devices and web:session keys in Redis
local redis = require('redis')
local json = require('libs.JSON')
local os = require('os')

local SECRET = os.getenv('WEB_API_SECRET') or ''
local conn = redis.connect('127.0.0.1', 6379)

local function shell_escape_single(s)
  if not s then return '' end
  return s:gsub("'", "'\\''")
end

local function decrypt_token(cipher)
  if SECRET == '' or not cipher then return cipher end
  local c = shell_escape_single(cipher)
  local sec = shell_escape_single(SECRET)
  local cmd = "printf '%s' '" .. c .. "' | openssl enc -d -aes-256-cbc -a -pass pass:'" .. sec .. "' 2>/dev/null"
  local fh = io.popen(cmd, 'r')
  if not fh then return nil, 'no-openssl' end
  local out = fh:read('*a')
  fh:close()
  if not out or out == '' then return nil, 'decrypt-failed' end
  out = out:gsub('%s+$','')
  return out, nil
end

print('WEB_API_SECRET present:', SECRET ~= '')

-- check devices
local devices = conn:lrange('web:devices', 0, -1) or {}
print('Found devices:', #devices)
for i,v in ipairs(devices) do
  local ok, obj = pcall(function() return json:decode(v) end)
  if not ok or not obj then
    print(i, 'invalid json')
  else
    if obj.token then
      local dec, err = decrypt_token(obj.token)
      if not dec then
        print('device', obj.id or ('index '..i), 'token decrypt error:', err)
      else
        print('device', obj.id or ('index '..i), 'token decrypt OK')
      end
    else
      print('device', obj.id or ('index '..i), 'no token field')
    end
  end
end

-- check sessions
local keys = conn:keys('web:session:*') or {}
print('Found sessions:', #keys)
for i,k in ipairs(keys) do
  local v = conn:get(k)
  if not v or v == '' then print(k, 'empty') else
    local dec, err = decrypt_token(v)
    if not dec then
      print(k, 'decrypt error:', err)
    else
      local ok, obj = pcall(function() return json:decode(dec) end)
      if not ok or not obj then print(k, 'invalid json after decrypt') else print(k, 'session decrypt OK') end
    end
  end
end

print('Done')
