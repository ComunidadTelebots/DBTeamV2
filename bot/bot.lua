-- Moved: legacy Lua implementation has been ported to python_bot/legacy
-- See: python_bot/legacy/bot_lua.py and related modules under
-- python_bot/legacy/ for the Python equivalents.
        local chat = chats[msgb.chat_id_]

        if ((not d) and chat) then
            if msgb.content_.ID == "MessageText" then
                do_notify(chat.title_, msgb.content_.text_)
            else
                do_notify(chat.title_, msgb.content_.ID)
            end
        end
		
		if redis:sismember("start", "settings") then
			redis:srem("start", "settings")
			changeAbout("DBTeamV2 Tg-cli administration Bot\nChannels: @DBTeamEn @DBTeamEs", ok_cb)
			getMe(getMeCb)
		elseif redis:sismember("load", "settings") then
			redis:srem("load", "settings")
			-- This loads to cache most of users, chats, channels .. that are removed in every reboot
			getChats(2^63 - 1, 0, 20, ok_cb)
			-- This opens all chats and channels in order to receive updates
			for k, chat in pairs (redis:smembers('chats:ids')) do
				 openChat(chat, ok_cb)
			end
		end

        msg = oldtg(data)
        tdcli_function ({
            ID = "GetUser",
            user_id_ = data.message_.sender_user_id_
        }, user_callback, msg)
    end
end

function msg_valid(msg)
    -- Don't process outgoing messages
    if msg.from.id == 0 then
        print('\27[36mNot valid: msg from us\27[39m')
        return false
    end

    -- Before bot was started
    if msg.date < now then
        print('\27[36mNot valid: old msg\27[39m')
        return false
    end

    if msg.unread == 0 then
        print('\27[36mNot valid: readed\27[39m')
        return false
    end

    if not msg.to.id then
        print('\27[36mNot valid: To id not provided\27[39m')
        return false
    end

    if not msg.from.id then
        print('\27[36mNot valid: From id not provided\27[39m')
        return false
    end

    if msg.from.id == 777000 then
        print('\27[36mNot valid: Telegram message\27[39m')
        return false
    end

    return true
end

-- Apply plugin.pre_process function
function pre_process_msg(msg)
    for name,plugin in pairs(plugins) do
        if plugin.pre_process and msg then
            print('Preprocess', name)
            msg = plugin.pre_process(msg)
        end
    end
    return msg
end

-- Go over enabled plugins patterns.
function match_plugins(msg)
    for name, plugin in pairs(plugins) do
        match_plugin(plugin, name, msg)
    end
end

-- Check if plugin is on _config.disabled_plugin_on_chat table
local function is_plugin_disabled_on_chat(plugin_name, receiver)
    local disabled_chats = _config.disabled_plugin_on_chat
    -- Table exists and chat has disabled plugins
    if disabled_chats and disabled_chats[receiver] then
        -- Checks if plugin is disabled on this chat
        for disabled_plugin,disabled in pairs(disabled_chats[receiver]) do
            if disabled_plugin == plugin_name and disabled then
                local warning = 'Plugin '..disabled_plugin..' is disabled on this chat'
                return true
            end
        end
    end
    return false
end

function match_plugin(plugin, plugin_name, msg)
    local receiver = get_receiver(msg)
    -- Go over patterns. If one matches it's enough.
    for k, pattern in pairs(plugin.patterns) do
        local matches = match_pattern(pattern, msg.text)
        if matches then
            -- Function exists
            if plugin.run then
                -- If plugin is for privileged users only
                local result = plugin.run(msg, matches)
                if result then
                    send_msg(receiver, result, "md")
                end
            end
            -- One patterns matches
            return
        end
    end
end

now = os.time()
math.randomseed(now)
