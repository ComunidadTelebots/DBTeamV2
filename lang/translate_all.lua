-- translate_all.lua
-- Traduce las entradas encontradas en lang/english_lang.lua a todos los códigos de idioma disponibles

local translator = require('lang.translator')
local lfs_ok, lfs = pcall(require, 'lfs')

local SOURCE = 'lang/english_lang.lua'
local OUT_DIR = 'lang'
local provider = os.getenv('TRANSLATE_PROVIDER') or 'libre'
local api_key = os.getenv('TRANSLATE_API_KEY') or nil
local delay = tonumber(os.getenv('TRANSLATE_DELAY') or '1')
local dry = os.getenv('TRANSLATE_DRY') == '1'

local function read_file(path)
  local fh, err = io.open(path, 'r')
  if not fh then return nil, err end
  local data = fh:read('*a')
  fh:close()
  return data
end

local function escape_lua_string(s)
  s = s:gsub('\\', '\\\\')
  s = s:gsub('\"', '\\"')
  s = s:gsub("\'","\\'")
  s = s:gsub('\n', '\\n')
  return s
end

local function parse_set_texts(content)
  local texts = {}
  for k, q, v in content:gmatch("set_text%s*%(%s*LANG%s*,%s*['\"]([^'\"]+)['\"]%s*,%s*(['\"])(.-)%2%s*%)") do
    texts[k] = v
  end
  -- capture numeric values (e.g., set_text(LANG, 'commands:0', 2))
  for k, v in content:gmatch("set_text%s*%(%s*LANG%s*,%s*['\"]([^'\"]+)['\"]%s*,%s*([0-9]+)%)") do
    texts[k] = tonumber(v)
  end
  return texts
end

local function list_targets()
  local targets = {}
  for file in io.popen('dir /b "'..OUT_DIR..'\*_lang.lua" 2>nul'):lines() do
    local code = file:match('([%w_%-]+)_lang%.lua')
    if code and code ~= 'english' then table.insert(targets, code) end
  end
  if #targets == 0 then
    if lfs_ok then
      for f in lfs.dir(OUT_DIR) do
        if f:match('([%w_%-]+)_lang%.lua') then
          local code = f:match('([%w_%-]+)_lang%.lua')
          if code and code ~= 'english' then table.insert(targets, code) end
        end
      end
    end
  end
  return targets
end

local src, err = read_file(SOURCE)
if not src then
  print('Error reading source:', tostring(err))
  os.exit(1)
end

local texts = parse_set_texts(src)
if not texts or next(texts) == nil then
  print('No set_text entries found in', SOURCE)
  os.exit(1)
end

local targets = list_targets()
if #targets == 0 then
  targets = { 'es','fr','de','it','pt','ru','zh','ja','ko','ar','fa','tr','nl','pl','sv','no','da','fi','he','hi' }
end

print('Translating', tostring(#texts), 'entries to', tostring(#targets), 'targets (provider='..provider..')')

for _, code in ipairs(targets) do
  if code == 'english' or code == 'en' then goto continue end
  print('->', code)
  local out_path = OUT_DIR..'/'..code..'_lang.lua'
  if dry then
    print('DRY RUN: would create', out_path)
  else
    local fh, ferr = io.open(out_path, 'w')
    if not fh then print('Error opening', out_path, ferr); goto continue end
    fh:write('-- Generated translations for '..code.."\n\n")
    fh:write("local LANG = '"..code.."'\n\n")
    fh:write('local function run(msg, matches)\n')
    fh:write("\tif permissions(msg.from.id, msg.to.id, \"lang_install\") then\n")
    for k, v in pairs(texts) do
      if type(v) == 'number' then
        fh:write('\t\tset_text(LANG, '..string.format('%q', k)..', '..tostring(v)..')\n')
      else
        local ok, translated = translator.translate_text(v, { provider = provider, api_key = api_key, source = 'en', target = code })
        if not ok then translated = v end
        translated = escape_lua_string(translated)
        fh:write('\t\tset_text(LANG, '..string.format('%q', k)..', ' .. '"'..translated..'"' .. ')\n')
      end
    end
    fh:write('\t\tif matches[1] == \'install\' then\n')
    fh:write('\t\t\treturn \"`>` '..code..' installed on your bot.`\"\n')
    fh:write('\t\telseif matches[1] == \'update\' then\n')
    fh:write('\t\t\treturn \"`>` '..code..' updated on your bot.`\"\n')
    fh:write('\t\tend\n')
    fh:write('\telse\n\t\treturn \"`>` This plugin *requires sudo* privileged user.\"\n\tend\nend\n\n')
    fh:write('return { patterns = {\n\t\'[!/#](install) ('..code..'_lang)$\',\n\t\'[!/#](update) ('..code..'_lang)$\'\n}, run = run }\n')
    fh:close()
    print('Wrote', out_path)
    if delay and delay > 0 then os.execute('sleep '..tostring(delay)) end
  end
  ::continue::
end

print('All done')
