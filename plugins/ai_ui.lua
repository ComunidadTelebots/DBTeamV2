local json = require('JSON')
local ai_client = loadfile('./plugins/ai_client.lua')()

local function help_text()
    return [[
Comandos de IA (interfaz simple):

- `!ai <prompt>`: usa el proveedor por defecto configurado en `data/ai_config.lua`.
- `!ai <proveedor> <prompt>`: fuerza el uso de un proveedor (openai, huggingface, azure, local, groq).
- `!aihelp`: muestra esta ayuda.

Ejemplos:
`!ai ¿Cuál es la capital de Francia?`
`!ai openai Resume este texto...`
`
Asegúrate de tener `data/ai_config.lua` correctamente configurado con las credenciales.
]]
end

local function run(msg, matches)
    local body = matches[2]
    if not body or body:match('^%s*$') then
        return help_text()
    end

    -- If the first word is a known provider, use it as override
    local provider, prompt = body:match('^(%w+)%s+(.+)$')
    local cfg_ok, cfg = pcall(function() return loadfile('./data/ai_config.lua')() end)
    if not cfg_ok or not cfg then
        return '⚠️ No se encontró `data/ai_config.lua` o contiene errores.'
    end

    local override = nil
    if provider and (provider == 'openai' or provider == 'huggingface' or provider == 'azure' or provider == 'local' or provider == 'groq') then
        override = provider
    else
        -- not a provider, treat entire body as prompt
        prompt = body
    end

    local call_cfg = cfg
    if override then
        -- shallow copy and set provider override
        call_cfg = {}
        for k,v in pairs(cfg) do call_cfg[k]=v end
        call_cfg.provider = override
    end

    local ok, res_or_err = ai_client.call(prompt, call_cfg)
    if not ok then
        return '❌ Error comunicando con el proveedor de IA: ' .. tostring(res_or_err)
    end

    -- Ensure string response
    if type(ok) == 'string' then
        return ok
    elseif type(res_or_err) == 'string' then
        return res_or_err
    else
        return '✅ Respuesta recibida.'
    end
end

return {
    patterns = {
        "^[!/#](aihelp)$",
        "^[!/#](ai) (.+)$"
    },
    run = function(msg, matches)
        if matches[1] == 'aihelp' then
            return help_text()
        end
        return run(msg, matches)
    end
}
