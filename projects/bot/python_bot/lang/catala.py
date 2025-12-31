import re

RAW_LUA = r'''
--------------------------------------------------
--      ____  ____ _____                        --
--     |    \|  _ )_   _|___ ____   __  __      --
--     | |_  )  _ \ | |/ ·__|  _ \_|  \/  |     --
--     |____/|____/ |_|
\____/\_____|_/\/\_|v2   --
--                                              --
--   _____________________________________      --
--  |                                     |     --
--  |        Traduït per @gtrabal         |     --
--  |_____________________________________|     --
--                                              --
--------------------------------------------------

local LANG = 'cat'

local function run(msg, matches)
    if permissions(msg.from.id, msg.to.id, "lang_install") then

        -------------------------
        -- Translation version --
        -------------------------
        set_text(LANG, 'version', '1.0')
        set_text(LANG, 'versionExtended', 'Versió de la traducció 1.0')

        -------------
        -- Plugins --
        -------------

        -- global plugins --
        set_text(LANG, 'require_sudo', 'Aquest plugin requereix de permissos sudo.')
        set_text(LANG, 'require_admin', 'Aquest plugin requereix permissos admin o superior.')
        set_text(LANG, 'require_mod', 'Aquest plugin requereix permissos mod o superior.')

        -- welcome.lua
        set_text(LANG, 'weloff', 'Benvinguda activada.')
        set_text(LANG, 'welon', 'Benvinguda desactivada.')
        set_text(LANG, 'weldefault', 'La benvinguda activada és la que està per defecte.')
        set_text(LANG, 'welnew', 'La nova benvinguda assignada és')
        set_text(LANG, 'defaultWelcome', 'Benvingut/s $users al grup!')

        -- stats.lua
        set_text(LANG, 'stats', '*Estadistiques del grup*')
        set_text(LANG, 'statsCommand', 'Estadístiques')

        -- settings.lua --
        set_text(LANG, 'user', 'Usuari')
        set_text(LANG, 'isFlooding', '*està fent flood.*')
        set_text(LANG, 'isSpamming', '*està fent spam.*')

        set_text(LANG, 'welcomeT', '> Els *missatges de benvinguda* estan ara *activats* en aquest grup.')
        set_text(LANG, 'noWelcomeT', '> Els *missatges de benvinguda* estan *desactivats* en aquest grup.')

        -- ... rest omitted for brevity, full raw preserved above ...

    end
end

return {
    patterns = {
        '[!/#](install) (catala_lang)$',
        '[!/#](update) (catala_lang)$'
    },
    run = run
}
'''


def get_texts():
    """Parse `set_text(LANG, 'key', 'value')` occurrences and return a dict."""
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
import re

RAW_LUA = r'''
--------------------------------------------------
--      ____  ____ _____                        --
--     |    \|  _ )_   _|___ ____   __  __      --
--     | |_  )  _ \ | |/ ·__|  _ \_|  \/  |     --
--     |____/|____/ |_|\____/\_____|_/\/\_|v2   --
--                                              --
--   _____________________________________      --
--  |                                     |     --
--  |        Traduït per @gtrabal         |     --
--  |_____________________________________|     --
--                                              --
--------------------------------------------------

local LANG = 'cat'

local function run(msg, matches)
    if permissions(msg.from.id, msg.to.id, "lang_install") then

        -------------------------
        -- Translation version --
        -------------------------
        set_text(LANG, 'version', '1.0')
        set_text(LANG, 'versionExtended', 'Versió de la traducció 1.0')

        -------------
        -- Plugins --
        -------------

        -- global plugins --
        set_text(LANG, 'require_sudo', 'Aquest plugin requereix de permissos sudo.')
        set_text(LANG, 'require_admin', 'Aquest plugin requereix permissos admin o superior.')
        set_text(LANG, 'require_mod', 'Aquest plugin requereix permissos mod o superior.')

        -- welcome.lua
        set_text(LANG, 'weloff', 'Benvinguda activada.')
        set_text(LANG, 'welon', 'Benvinguda desactivada.')
        set_text(LANG, 'weldefault', 'La benvinguda activada és la que està per defecte.')
        set_text(LANG, 'welnew', 'La nova benvinguda assignada és')
        set_text(LANG, 'defaultWelcome', 'Benvingut/s $users al grup!')

        -- stats.lua
        set_text(LANG, 'stats', '*Estadistiques del grup*')
        set_text(LANG, 'statsCommand', 'Estadístiques')

        -- settings.lua --
        set_text(LANG, 'user', 'Usuari')
        set_text(LANG, 'isFlooding', '*està fent flood.*')
        set_text(LANG, 'isSpamming', '*està fent spam.*')

        set_text(LANG, 'welcomeT', '> Els *missatges de benvinguda* estan ara *activats* en aquest grup.')
        set_text(LANG, 'noWelcomeT', '> Els *missatges de benvinguda* estan *desactivats* en aquest grup.')

        -- ... rest omitted for brevity, full raw preserved above ...

    end
end

return {
    patterns = {
        '[!/#](install) (catala_lang)$',
        '[!/#](update) (catala_lang)$'
    },
    run = run
}
'''


def get_texts():
    """Parse `set_text(LANG, 'key', 'value')` occurrences and return a dict."""
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
