import re

RAW_LUA = r'''
```lua
--------------------------------------------------
--      ____  ____ _____                        --
--     |    \|  _ )_   _|___ ____   __  __      --
--     | |_  )  _ \ | |/ ·__|  _ \_|  \/  |     --
--     |____/|____/ |_|\____/\_____|_/\/\_|v2   --
--                                              --
--------------------------------------------------

local LANG = 'en'

local function run(msg, matches)
    if permissions(msg.from.id, msg.to.id, "lang_install") then

        -------------------------
        -- Translation version --
        -------------------------
        set_text(LANG, 'version', '2.0')
        set_text(LANG, 'versionExtended', 'Translation version 2.0')

        -------------
        -- Plugins --
        -------------

        -- global plugins --
        set_text(LANG, 'require_sudo', 'This plugin requires sudo privileges.')
        set_text(LANG, 'require_admin', 'This plugin requires admin privileges or higher.')
        set_text(LANG, 'require_mod', 'This plugin requires mod privileges or higher.')

        -- welcome.lua
        set_text(LANG, 'weloff', 'Welcome enabled.')
        set_text(LANG, 'welon', 'Welcome disabled.')
        set_text(LANG, 'weldefault', 'The welcome is the default.')
        set_text(LANG, 'welnew', 'Welcome saved! Actual welcome:\n')
        set_text(LANG, 'defaultWelcome', 'Welcome $users to the chat!')

        -- stats.lua
        set_text(LANG, 'stats', '*Chat stats*')

        -- settings.lua --
        set_text(LANG, 'user', 'User')
        set_text(LANG, 'isFlooding', '*is flooding.*')
        set_text(LANG, 'isSpamming', '*is spamming.*')

        set_text(LANG, 'welcomeT', '> *Welcome messages* are now *enabled* in this chat.')
        set_text(LANG, 'noWelcomeT', '> *Welcome messages* are *disabled* in this chat.')

        set_text(LANG, 'noStickersT', '`>` *Stickers* are *not allowed* in this chat.')
        set_text(LANG, 'stickersT', '`>` *Stickers* are now *allowed* in this chat.')

        set_text(LANG, 'noTgservicesT', '`>` *Telegram services disabled* in this chat.')
        set_text(LANG, 'tgservicesT', '`>` *Telegram services enabled* in this chat.')

        set_text(LANG, 'gifsT', '`>` *Gifs* are now *allowed* in this chat.')
        set_text(LANG, 'noGifsT', '`>` *Gifs* are *not allowed* in this chat.')

        set_text(LANG, 'photosT', '`>` *Photos* are now `allowed` in this chat.')
        set_text(LANG, 'noPhotosT', '`>` *Photos* are *not allowed* in this chat.')

        set_text(LANG, 'botsT', '`>` *Bots* are now allowed in this chat.')
        set_text(LANG, 'noBotsT', '`>` Bots are not allowed in this chat.')

        set_text(LANG, 'arabicT', '`>` *Arabic* is now *allowed* in this chat.')
        set_text(LANG, 'noArabicT', '`>` *Arabic* is *not allowed* in this chat.')

        set_text(LANG, 'audiosT', '`>` *Audios* are now *allowed* in this chat.')
        set_text(LANG, 'noAudiosT', '`>` *Audios* are *not allowed* in this chat.')

        set_text(LANG, 'documentsT', '`>` *Documents* are now *allowed* in this chat.')
        set_text(LANG, 'noDocumentsT', '`>` *Documents* are *not allowed* in this chat.')

        set_text(LANG, 'videosT', '`>` *Videos* are now *allowed* in this chat.')
        set_text(LANG, 'noVideosT', '`>` *Videos* are *not allowed* in this chat.')

        set_text(LANG, 'locationT', '`>` *Location* is now *allowed* in this chat.')
        set_text(LANG, 'noLocationT', '`>` *Location* is *not allowed* in this chat.')

        set_text(LANG, 'emojisT', '`>` *Emojis* are now *allowed* in this chat.')
        set_text(LANG, 'noEmojisT', '`>` *Emojis* are *not allowed* in this chat.')

        set_text(LANG, 'englishT', '`>` *English* is now *allowed* in this chat.')
        set_text(LANG, 'noEnglishT', '`>` *English* is *not allowed* in this chat.')

        set_text(LANG, 'inviteT', '`>` *Invite* is now *allowed* in this chat.')
        set_text(LANG, 'noInviteT', '`>` *Invite* is *not allowed* in this chat.')

        set_text(LANG, 'voiceT', '`>` *Voice messages* are now *allowed* in this chat.')
        set_text(LANG, 'noVoiceT', '`>` *Voice messages* are *not allowed* in this chat.')

        set_text(LANG, 'infoT', '`>` *Photo/title* can be changed in this chat.')
        set_text(LANG, 'noInfoT', '`>` *Photo/title* can\'t be changed in this chat.')

        set_text(LANG, 'gamesT', '`>` *Games* are now *allowed* in this chat.')
        set_text(LANG, 'noGamesT', '`>` *Games* are *not allowed* in this chat.')

        set_text(LANG, 'spamT', '`>` *Spam* is now *allowed* in this chat.')
        set_text(LANG, 'noSpamT', '`>` *Spam* is *not allowed* in this chat.')
        set_text(LANG, 'setSpam', '`>` Changed blacklist to ')

        set_text(LANG, 'forwardT', '`>` *Forward messages* is now *allowed* in this chat.')
        set_text(LANG, 'noForwardT', '`>` *Forward messages* is not *allowed* in this chat.')

        set_text(LANG, 'floodT', '`>` *Flood* is now *allowed* in this chat.')
        set_text(LANG, 'noFloodT', '`>` *Flood* is *not allowed* in this chat.')

        set_text(LANG, 'floodTime', '`>` *Flood time* check has been set to ')
        set_text(LANG, 'floodMax', '`>` *Max flood* messages have been set to ')

        set_text(LANG, 'gSettings', 'chat settings')

        set_text(LANG, 'allowed', 'allowed')
        set_text(LANG, 'noAllowed', 'not allowed')
        set_text(LANG, 'noSet', 'not set')

        set_text(LANG, 'stickers', 'Stickers')
        set_text(LANG, 'tgservices', 'Tg services')
        set_text(LANG, 'links', 'Links')
        set_text(LANG, 'arabic', 'Arabic')
        set_text(LANG, 'bots', 'Bots')
        set_text(LANG, 'gifs', 'Gifs')
        set_text(LANG, 'photos', 'Photos')
        set_text(LANG, 'audios', 'Audios')
        set_text(LANG, 'kickme', 'Kickme')
        set_text(LANG, 'spam', 'Spam')
        set_text(LANG, 'gName', 'Group Name')
        set_text(LANG, 'flood', 'Flood')
        set_text(LANG, 'language', 'Language')
        set_text(LANG, 'mFlood', 'Max flood')
        set_text(LANG, 'tFlood', 'Flood time')
        set_text(LANG, 'setphoto', 'Set photo')

        set_text(LANG, 'forward', 'Forward')
        set_text(LANG, 'videos', 'Videos')
        set_text(LANG, 'invite', 'Invite')
        set_text(LANG, 'games', 'Games')
        set_text(LANG, 'documents', 'Documents')
        set_text(LANG, 'location', 'Location')
        set_text(LANG, 'voice', 'Voice')
        set_text(LANG, 'icontitle', 'Change icon/title')
        set_text(LANG, 'english', 'English')
        set_text(LANG, 'emojis', 'Emojis')
        --Made with @TgTextBot by @iicc1
        set_text(LANG, 'groupSettings', 'G̲r̲o̲u̲p̲ s̲e̲t̲t̲i̲n̲g̲s̲')
        set_text(LANG, 'allowedMedia', 'A̲l̲l̲o̲w̲e̲d̲ m̲e̲d̲i̲a̲')
        set_text(LANG, 'settingsText', 'T̲e̲x̲t̲')

        set_text(LANG, 'langUpdated', 'Your language has been updated to: ')

        set_text(LANG, 'linkSet', '`>` *New link* has been *set*')
        set_text(LANG, 'linkError', '`>` Need *creator rights* to export chat invite link.')

        set_text(LANG, 'newRules', '`>` *New rules* have been *created.*')
        set_text(LANG, 'rulesDefault', '`>` Your previous *rules have been removed.*')
        set_text(LANG, 'noRules', '`>` *There are no visible rules* in this group.')

        set_text(LANG, 'defaultRules', '*Chat rules:*\n`>` No Flood.\n`>` No Spam.\n`>` Try to stay on topic.\n`>` Forbidden any racist, sexual, gore content...\n\n_Repeated failure to comply with these rules will cause ban._')

        set_text(LANG, 'delAll', '`>` All messages *cleared*.')

        -- export_gban.lua --
        set_text(LANG, 'accountsGban', 'accounts globally banned.')

        -- promote.lua --
        set_text(LANG, 'alreadyAdmin', 'This user is already *admin.*')
        set_text(LANG, 'alreadyMod', 'This user is already *mod.*')

        set_text(LANG, 'newAdmin', '<code>></code> <b>New admin</b>')
        set_text(LANG, 'newMod', '<code>></code> <b>New mod</b>')
        set_text(LANG, 'nowUser', ' <b>is now an user.</b>')

        -- ... (full file preserved) ...

    end
end

return {
    patterns = {
        '[!/#](install) (english_lang)$',
        '[!/#](update) (english_lang)$'
    },
    run = run
}
```
'''


def get_texts():
    """Parse `set_text(LANG, 'key', 'value')` occurrences and return a dict."""
    pattern = re.compile(r"set_text\(LANG,\s*'([^']+)',\s*'((?:\\'|[^'])*)'\)")
    texts = {}
    for k, v in pattern.findall(RAW_LUA):
        texts[k] = v.replace("\\'", "'")
    return texts
