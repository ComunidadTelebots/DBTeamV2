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
			end

        msg = oldtg(data)
        tdcli_function ({
            ID = "GetUser",
            user_id_ = data.message_.sender_user_id_
        }, user_callback, msg)
    end
end

function msg_valid(msg)
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

        print('\27[36mNot valid: From id not provided\27[39m')
        return false
    end

    if msg.from.id == 777000 then
        print('\27[36mNot valid: Telegram message\27[39m')
        return false
    end

    return true

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
    end
end

-- Check if plugin is on _config.disabled_plugin_on_chat table
local function is_plugin_disabled_on_chat(plugin_name, receiver)
    local disabled_chats = _config.disabled_plugin_on_chat
    -- Table exists and chat has disabled plugins
    if disabled_chats and disabled_chats[receiver] then
        -- Checks if plugin is disabled on this chat
        for disabled_plugin,disabled in pairs(disabled_chats[receiver]) do
                local warning = 'Plugin '..disabled_plugin..' is disabled on this chat'
                return true
            end
        end
    end
    return false
end

function match_plugin(plugin, plugin_name, msg)


            -- ================= INTEGRACIÓN CON COMANDOS DEL BOT =================

            function handle_command(msg)
                 local text = msg.text or ""
                 if text:match("^/alerta_critica") then
                      send_critical_alert(msg.chat_id, "¡Alerta crítica enviada!")
                      return "Alerta crítica enviada."
                 elseif text:match("^/resumen_diario") then
                      send_daily_summary(msg.chat_id)
                      return "Resumen diario solicitado."
                 elseif text:match("^/usuarios_activos") then
                      list_active_users(msg.chat_id)
                      return "Usuarios activos listados."
                 elseif text:match("^/estado_servicios") then
                      report_service_status(msg.chat_id)
                      return "Estado de servicios consultado."
                 elseif text:match("^/limpiar_temp") then
                      clean_temp_files()
                      return "Archivos temporales limpiados."
                 elseif text:match("^/backup_config") then
                      backup_config()
                      return "Backup de configuración realizado."
                 elseif text:match("^/ayuda_interactiva") then
                      interactive_help(msg.chat_id, msg.from.id)
                      return "Ayuda interactiva mostrada."
                 elseif text:match("^/estadisticas_bot") then
                      show_bot_stats(msg.chat_id)
                      return "Estadísticas del bot mostradas."
                 elseif text:match("^/monitor_sistema") then
                      system_resource_monitor(msg.chat_id)
                      return "Monitor de sistema ejecutado."
                 else
                      return nil -- Comando no reconocido
                 end
            end


            -- ================= INTEGRACIÓN WEB (ESQUEMA BÁSICO) =================

            -- Nota: Esto es un esquema genérico. Debes adaptar a tu framework web (por ejemplo, LuaSocket, OpenResty, etc.)

            -- function handle_http_request(path, params)
            --     if path == "/api/alerta_critica" then
            --         send_critical_alert(params.chat_id, params.message)
            --         return "{\"status\":\"ok\"}"
            --     elseif path == "/api/resumen_diario" then
            --         send_daily_summary(params.chat_id)
            --         return "{\"status\":\"ok\"}"
            --     elseif path == "/api/usuarios_activos" then
            --         list_active_users(params.chat_id)
            --         return "{\"status\":\"ok\"}"
            --     elseif path == "/api/estado_servicios" then
            --         report_service_status(params.chat_id)
            --         return "{\"status\":\"ok\"}"
            --     -- ...agrega más endpoints según funciones...
            --     else
            --         return "{\"error\":\"endpoint no encontrado\"}"
            --     end
            -- end

            -- Para exponer estas funciones realmente por web, debes integrar este esquema en tu servidor HTTP Lua.
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

-- ================= FUNCIONES SUGERIDAS =================

-- 1. Notificaciones avanzadas
function send_critical_alert(chat_id, message)
    -- Enviar alerta crítica a canal/grupo
    -- TODO: Implementar lógica de envío
end

function send_daily_summary(chat_id)
    -- Enviar resumen diario/semanal de actividad o logs
    -- TODO: Implementar lógica de resumen
end

-- 2. Gestión de usuarios y permisos
function list_active_users(chat_id)
    -- Listar usuarios activos y sus permisos
    -- TODO: Implementar lógica de listado
end

function audit_permission_changes()
    -- Auditar cambios de permisos/accesos
    -- TODO: Implementar lógica de auditoría
end

-- 3. Integración con servicios externos
function report_service_status(chat_id)
    -- Consultar y reportar estado de servicios externos (Nextcloud, Plex, torrents)
    -- TODO: Implementar lógica de consulta y reporte
end

function restart_service(service_name)
    -- Reiniciar servicio externo desde el bot
    -- TODO: Implementar lógica de reinicio
end

-- 4. Automatización y mantenimiento
function clean_temp_files()
    -- Limpieza automática de archivos temporales/logs antiguos
    -- TODO: Implementar lógica de limpieza
end

function update_dependencies()
    -- Comprobar y actualizar dependencias del sistema/bot
    -- TODO: Implementar lógica de actualización
end

-- 5. Utilidades para administradores
function backup_config()
    -- Hacer backup de configuraciones clave
    -- TODO: Implementar lógica de backup
end

function restore_config()
    -- Restaurar configuraciones clave
    -- TODO: Implementar lógica de restauración
end

function analyze_logs_for_errors()
    -- Analizar logs y detectar patrones de error frecuentes
    -- TODO: Implementar lógica de análisis
end

-- 6. Mejoras en la interacción
function interactive_help(chat_id, user_id)
    -- Ayuda interactiva según permisos del usuario
    -- TODO: Implementar lógica de ayuda
end

function suggest_commands(chat_id, user_input)
    -- Sugerir comandos/autocompletar
    -- TODO: Implementar lógica de sugerencia
end

-- 7. Monitorización y estadísticas
function show_bot_stats(chat_id)
    -- Mostrar estadísticas de uso del bot
    -- TODO: Implementar lógica de estadísticas
end

function system_resource_monitor(chat_id)
    -- Monitor de recursos del sistema accesible desde el bot
    -- TODO: Implementar lógica de monitorización
end
