-- Rotate device tokens from OLD_WEB_API_SECRET to NEW_WEB_API_SECRET
local redis = require('redis')
local json = require('libs.JSON')
local os = require('os')

local OLD = os.getenv('OLD_WEB_API_SECRET') or os.getenv('WEB_API_SECRET') or ''
local NEW = os.getenv('NEW_WEB_API_SECRET') or ''
if NEW == '' then
  print('Set NEW_WEB_API_SECRET to the new secret (env)')
  os.exit(1)
end

local conn = redis.connect('127.0.0.1', 6379)

local function shell_escape_single(s)
  if not s then return '' end
  return s:gsub("'", "'\\''")
end

local function decrypt_with_secret(cipher, secret)
  if secret == '' or not cipher then return nil, 'no-secret' end
  local c = shell_escape_single(cipher)
  local sec = shell_escape_single(secret)
  local cmd = "printf '%s' '" .. c .. "' | openssl enc -d -aes-256-cbc -a -pass pass:'" .. sec .. "' 2>/dev/null"
  local fh = io.popen(cmd, 'r')
  if not fh then return nil, 'no-openssl' end
  local out = fh:read('*a')
  fh:close()
  if not out or out == '' then return nil, 'decrypt-failed' end
  out = out:gsub('%s+$','')
  return out, nil
end

local function encrypt_with_secret(plain, secret)
  if secret == '' or not plain then return plain end
  local p = shell_escape_single(plain)
  local sec = shell_escape_single(secret)
  local cmd = "printf '%s' '" .. p .. "' | openssl enc -aes-256-cbc -a -salt -pbkdf2 -pass pass:'" .. sec .. "'"
  local fh = io.popen(cmd, 'r')
  if not fh then return nil, 'no-openssl' end
  local out = fh:read('*a')
  fh:close()
  if not out or out == '' then return nil, 'encrypt-failed' end
  out = out:gsub('%s+$','')
  return out, nil
end

local items = conn:lrange('web:devices', 0, -1) or {}
print('Devices to process:', #items)
local new_list = {}
for i,v in ipairs(items) do
  local ok, obj = pcall(function() return json:decode(v) end)
  if not ok or not obj then
    print('Skipping invalid JSON at index', i)
  else
    local token = obj.token
    local plain = nil
    if token then
      local dec, derr = decrypt_with_secret(token, OLD)
      if not dec then
        -- maybe token is in plaintext already
        print('Warning: cannot decrypt token for', obj.id, 'assuming plaintext')
        dec = token
      end
      local enc, err = encrypt_with_secret(dec, NEW)
      if not enc then print('Failed to encrypt for', obj.id, err); enc = dec end
      obj.token = enc
    end
    table.insert(new_list, json:encode(obj))
  end
end

-- replace list atomically
conn:del('web:devices')
for i,v in ipairs(new_list) do conn:rpush('web:devices', v) end
print('Rotation complete. Replaced', #new_list, 'devices')
