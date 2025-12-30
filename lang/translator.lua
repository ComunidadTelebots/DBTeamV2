local json = require('libs.JSON')

local _M = {}

local has_https, https = pcall(require, 'ssl.https')
local has_socket, socket_http = pcall(require, 'socket.http')

local function urlencode(str)
  if not str then return '' end
  str = tostring(str)
  str = str:gsub('\n', '\r\n')
  str = str:gsub('([^%w _%%%-%.~])', function(c)
    return string.format('%%%02X', string.byte(c))
  end)
  str = str:gsub(' ', '+')
  return str
end

local function http_post(url, body, headers)
  local ltn12 = require('ltn12')
  local resp = {}
  local req = { url = url, method = 'POST', source = ltn12.source.string(body or ''), sink = ltn12.sink.table(resp) }
  req.headers = headers or {}
  if not req.headers['Content-Length'] then req.headers['Content-Length'] = tostring(#(body or '')) end

  if has_https then
    local r, code, h = https.request(req)
    return table.concat(resp), code, h
  elseif has_socket then
    local r, code, h = socket_http.request(req)
    return table.concat(resp), code, h
  else
    return nil, nil, 'no-http'
  end
end

local function libre_translate(text, source, target, endpoint)
  endpoint = endpoint or 'https://libretranslate.de/translate'
  local payload = { q = text, source = source or 'auto', target = target, format = 'text' }
  local body = json:encode(payload)
  local headers = { ['Content-Type'] = 'application/json' }
  local resp, code = http_post(endpoint, body, headers)
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok and obj and obj.translatedText then return obj.translatedText end
  return nil, resp
end

local function google_translate(text, source, target, api_key)
  if not api_key then return nil, 'missing_api_key' end
  local endpoint = 'https://translation.googleapis.com/language/translate/v2?key='..urlencode(api_key)
  local payload = { q = text, source = source == 'auto' and nil or source, target = target, format = 'text' }
  local body = json:encode(payload)
  local headers = { ['Content-Type'] = 'application/json' }
  local resp, code = http_post(endpoint, body, headers)
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok and obj and obj.data and obj.data.translations and obj.data.translations[1] and obj.data.translations[1].translatedText then
    return obj.data.translations[1].translatedText
  end
  return nil, resp
end

local function microsoft_translate(text, source, target, api_key, region)
  if not api_key then return nil, 'missing_api_key' end
  local endpoint = 'https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to='..urlencode(target)
  if source and source ~= 'auto' then
    endpoint = endpoint .. '&from=' .. urlencode(source)
  end
  local body = json:encode({ { Text = text } })
  local headers = { ['Content-Type'] = 'application/json', ['Ocp-Apim-Subscription-Key'] = api_key }
  if region and region ~= '' then headers['Ocp-Apim-Subscription-Region'] = region end
  local resp, code = http_post(endpoint, body, headers)
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok and type(obj) == 'table' and obj[1] and obj[1].translations and obj[1].translations[1] and obj[1].translations[1].text then
    return obj[1].translations[1].text
  end
  return nil, resp
end

local function deepl_translate(text, _source, target, api_key, endpoint)
  if not api_key then return nil, 'missing_api_key' end
  endpoint = endpoint or 'https://api-free.deepl.com/v2/translate'
  local body = 'auth_key=' .. urlencode(api_key) .. '&text=' .. urlencode(text) .. '&target_lang=' .. urlencode(string.upper(target))
  local headers = { ['Content-Type'] = 'application/x-www-form-urlencoded' }
  local resp, code = http_post(endpoint, body, headers)
  if not resp then return nil, code end
  local ok, obj = pcall(json.decode, resp)
  if ok and obj and obj.translations and obj.translations[1] and obj.translations[1].text then
    return obj.translations[1].text
  end
  return nil, resp
end

local function translate_text(opts, text, source, target)
  opts = opts or {}
  local providers = {}
  if opts.providers and type(opts.providers) == 'table' and #opts.providers > 0 then
    providers = opts.providers
  else
    table.insert(providers, opts.provider or 'libre')
  end

  for _, provider in ipairs(providers) do
    local p = provider:lower()
    if p == 'libre' then
      local ok, res = libre_translate(text, source, target, opts.libre_endpoint or opts.endpoint)
      if ok then return ok end
    elseif p == 'deepl' then
      local key = (opts.api_keys and opts.api_keys.deepl) or opts.api_key
      local ok, res = deepl_translate(text, source, target, key, opts.deepl_endpoint or opts.endpoint)
      if ok then return ok end
    elseif p == 'google' or p == 'google_cloud' then
      local key = (opts.api_keys and opts.api_keys.google) or opts.google_api_key or opts.api_key
      local ok, res = google_translate(text, source, target, key)
      if ok then return ok end
    elseif p == 'microsoft' or p == 'azure' or p == 'bing' then
      local key = (opts.api_keys and opts.api_keys.microsoft) or opts.microsoft_key or opts.api_key
      local region = (opts.api_keys and opts.api_keys.microsoft_region) or opts.microsoft_region or opts.azure_region
      local ok, res = microsoft_translate(text, source, target, key, region)
      if ok then return ok end
    else
      -- unknown provider, skip
    end
    -- if translation failed for this provider, continue to next
  end
  return nil, 'no_translation'
end

local function translate_table_recursive(t, opts, source, target)
  local res = {}
  for k, v in pairs(t) do
    if type(v) == 'string' then
      local ok, err = translate_text(opts, v, source, target)
      if ok then res[k] = ok else res[k] = v end
    elseif type(v) == 'table' then
      res[k] = translate_table_recursive(v, opts, source, target)
    else
      res[k] = v
    end
  end
  return res
end

local function serialize_lua(tbl, indent)
  indent = indent or ''
  local next_indent = indent .. '  '
  if type(tbl) == 'string' then
    return string.format('%q', tbl)
  elseif type(tbl) ~= 'table' then
    return tostring(tbl)
  end
  local parts = { '{' }
  for k, v in pairs(tbl) do
    local key
    if type(k) == 'string' and k:match('^%a[%w_]*$') then
      key = k
    else
      key = '[' .. serialize_lua(k) .. ']'
    end
    table.insert(parts, '\n' .. next_indent .. key .. ' = ' .. serialize_lua(v, next_indent) .. ',')
  end
  table.insert(parts, '\n' .. indent .. '}')
  return table.concat(parts)
end

function _M.translate_table(tbl, options)
  options = options or {}
  local source = options.source or 'auto'
  local target = options.target or 'en'
  return translate_table_recursive(tbl, options, source, target)
end

function _M.translate_file(in_path, out_path, options)
  options = options or {}
  local ok, loaded = pcall(loadfile, in_path)
  if not ok or not loaded then return nil, 'load_failed' end
  local success, tbl = pcall(loaded)
  if not success then return nil, 'execute_failed' end
  local translated = translate_table_recursive(tbl, options, options.source or 'auto', options.target or 'en')
  local fh, err = io.open(out_path, 'w')
  if not fh then return nil, err end
  fh:write('return ' .. serialize_lua(translated) .. '\n')
  fh:close()
  return true
end

function _M.translate_text(text, options)
  options = options or {}
  return translate_text(options, text, options.source or 'auto', options.target or 'en')
end

return _M
