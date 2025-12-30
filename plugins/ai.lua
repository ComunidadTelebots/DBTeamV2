local json = require('JSON')

local ai_client = loadfile('./plugins/ai_client.lua')()

local function run(msg, matches)
    local prompt = matches[2]
    local cfg_ok, cfg = pcall(function() return loadfile('./data/ai_config.lua')() end)
    if not cfg_ok or not cfg then
        return '⚠️ Configuración de AI no encontrada en data/ai_config.lua'
    end
    local ok, res_or_err = ai_client.call(prompt, cfg)
    if not ok then
        return '❌ Error al contactar la API de IA: ' .. tostring(res_or_err)
    end
    -- Ensure response is a string
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
        "^[!/#](ask) (.+)$",
        "^[!/#](ia) (.+)$"
    },
    run = run
}
