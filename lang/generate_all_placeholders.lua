-- Generator: create placeholder language files for many ISO 639-1 codes
local codes = {
  'aa','ab','ae','af','ak','am','an','ar','as','av','ay','az','ba','be','bg','bh','bi','bm','bn','bo','br','bs','ca','ce','ch','co','cr','cs','cu','cv','cy','da','de','dv','dz','ee','el','en','eo','es','et','eu','fa','ff','fi','fj','fo','fr','fy','ga','gd','gl','gn','gu','gv','ha','he','hi','ho','hr','ht','hu','hy','hz','ia','id','ie','ig','ii','ik','io','is','it','iu','ja','jv','ka','kg','ki','kj','kk','kl','km','kn','ko','kr','ks','ku','kv','kw','ky','la','lb','lg','li','ln','lo','lt','lu','lv','mg','mh','mi','mk','ml','mn','mr','ms','mt','my','na','nb','nd','ne','ng','nl','nn','no','nr','nv','ny','oc','oj','om','or','os','pa','pi','pl','ps','pt','qu','rm','rn','ro','ru','rw','sa','sc','sd','se','sg','si','sk','sl','sm','sn','so','sq','sr','ss','st','su','sv','sw','ta','te','tg','th','ti','tk','tl','tn','to','tr','ts','tt','tw','ty','ug','uk','ur','uz','ve','vi','vo','wa','wo','xh','yi','yo','za','zh','zu'
}

local template = [[
--------------------------------------------------
--  Placeholder language file - %s
--------------------------------------------------

local LANG = '%s'

local function run(msg, matches)
    if permissions(msg.from.id, msg.to.id, "lang_install") then
        if matches[1] == 'install' then
            return '`>` %s placeholder installed on your bot.`'
        elseif matches[1] == 'update' then
            return '`>` %s placeholder updated on your bot.`'
        end
    else
        return "`>` This plugin *requires sudo* privileged user."
    end
end

return {
    patterns = {
        '[!/#](install) (%s)$',
        '[!/#](update) (%s)$'
    },
    run = run
}
]]

local lfs = require('lfs')
local outdir = '.'
for _, code in ipairs(codes) do
    local name = code..'_lang'
    local path = outdir..'/'..name..'.lua'
    local fh, err = io.open(path, 'w')
    if fh then
        fh:write(string.format(template, code, code, code, code, name, name))
        fh:close()
        print('wrote', path)
    else
        io.stderr:write('error writing ' .. path .. ': ' .. tostring(err) .. '\n')
    end
end

print('Done: placeholder language files generated in current directory (lang/).')
