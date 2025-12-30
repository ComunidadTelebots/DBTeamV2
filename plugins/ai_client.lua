local https_ok, https = pcall(require, 'ssl.https')
local ltn12_ok, ltn12 = pcall(require, 'ltn12')
local socket_http_ok, socket_http = pcall(require, 'socket.http')
local json = require('JSON')

local M = {}

local function http_post_json(url, body, headers)
    if not ltn12_ok then return nil, 'ltn12 missing' end
    local resp = {}
    local source, sink
    source = ltn12.source.string(body)
    sink = ltn12.sink.table(resp)

    local req_headers = headers or {}
    req_headers['Content-Length'] = tostring(#body)

    local ok, code, res_headers, status
    if https_ok and url:lower():match('^https') then
        ok, code, res_headers, status = https.request{
            url = url,
            method = 'POST',
            headers = req_headers,
            source = source,
            sink = sink
        }
    elseif socket_http_ok then
        ok, code, res_headers, status = socket_http.request{
            url = url,
            method = 'POST',
            headers = req_headers,
            source = source,
            sink = sink
        }
    else
        return nil, 'no http lib available (ssl.https or socket.http)'
    end

    if not ok then
        return nil, tostring(code)
    end
    return table.concat(resp), code
end

local function openai_chat(prompt, cfg)
    local c = cfg.openai or {}
    local payload = {
        model = c.model or 'gpt-3.5-turbo',
        messages = {{role = 'user', content = prompt}},
        max_tokens = c.max_tokens or 400,
        temperature = c.temperature or 0.7
    }
    local body = json:encode(payload)
    local url = 'https://api.openai.com/v1/chat/completions'
    local headers = {
        ['Content-Type'] = 'application/json',
        ['Authorization'] = 'Bearer ' .. (c.api_key or '')
    }
    local raw, code_or_err = http_post_json(url, body, headers)
    if not raw then return nil, code_or_err end
    local ok, decoded = pcall(json.decode, raw)
    if not ok then return nil, 'json decode error' end
    if decoded and decoded.choices and decoded.choices[1] and decoded.choices[1].message then
        return decoded.choices[1].message.content
    end
    return nil, 'no content in openai response'
end

local function huggingface_generate(prompt, cfg)
    local c = cfg.huggingface or {}
    if not c.model or c.model == '' then return nil, 'huggingface model not set' end
    local url = 'https://api-inference.huggingface.co/models/' .. c.model
    local body = json:encode({inputs = prompt})
    local headers = {
        ['Content-Type'] = 'application/json',
        ['Authorization'] = 'Bearer ' .. (c.api_key or '')
    }
    local raw, err = http_post_json(url, body, headers)
    if not raw then return nil, err end
    local ok, decoded = pcall(json.decode, raw)
    if ok and type(decoded) == 'table' then
        -- HuggingFace may return array of results or a single object
        if decoded[1] and decoded[1].generated_text then
            return decoded[1].generated_text
        elseif decoded.generated_text then
            return decoded.generated_text
        else
            return raw
        end
    end
    return raw
end

local function azure_openai(prompt, cfg)
    local c = cfg.azure or {}
    if not c.endpoint or c.endpoint == '' or not c.api_key or c.api_key == '' or not c.deployment_id then
        return nil, 'azure configuration incomplete'
    end
    local url = c.endpoint:gsub('/$','') .. '/openai/deployments/' .. c.deployment_id .. '/chat/completions?api-version=' .. (c.api_version or '2023-05-15')
    local payload = {
        messages = {{role = 'user', content = prompt}},
        max_tokens = c.max_tokens or 400,
        temperature = c.temperature or 0.7
    }
    local body = json:encode(payload)
    local headers = {
        ['Content-Type'] = 'application/json',
        ['api-key'] = c.api_key
    }
    local raw, err = http_post_json(url, body, headers)
    if not raw then return nil, err end
    local ok, decoded = pcall(json.decode, raw)
    if not ok then return nil, 'json decode error' end
    if decoded and decoded.choices and decoded.choices[1] and decoded.choices[1].message then
        return decoded.choices[1].message.content
    end
    return nil, 'no content in azure response'
end

local function local_generate(prompt, cfg)
    local c = cfg['local'] or {}
    if not c.url or c.url == '' then return nil, 'local url not set' end
    local body = json:encode({prompt = prompt})
    local headers = { ['Content-Type'] = 'application/json' }
    local raw, err = http_post_json(c.url, body, headers)
    if not raw then return nil, err end
    local ok, decoded = pcall(json.decode, raw)
    if ok and decoded then
        if type(decoded) == 'table' and decoded.text then return decoded.text end
        if type(decoded) == 'string' then return decoded end
    end
    return raw
end

local function groq_generate(prompt, cfg)
    local c = cfg.groq or {}
    if not c.url or c.url == '' or not c.api_key or c.api_key == '' then
        return nil, 'groq configuration incomplete (url and api_key required)'
    end
    local input_key = c.input_key or 'input'
    local payload = {}
    payload[input_key] = prompt
    local body = json:encode(payload)
    local headers = {
        ['Content-Type'] = 'application/json',
        ['Authorization'] = 'Bearer ' .. (c.api_key or '')
    }
    local raw, err = http_post_json(c.url, body, headers)
    if not raw then return nil, err end
    local ok, decoded = pcall(json.decode, raw)
    if ok and decoded then
        -- Attempt common response shapes
        if type(decoded) == 'table' then
            if decoded.output_text then return decoded.output_text end
            if decoded.output and decoded.output[1] and decoded.output[1].content then return decoded.output[1].content end
            if decoded.results and decoded.results[1] and decoded.results[1].text then return decoded.results[1].text end
        elseif type(decoded) == 'string' then
            return decoded
        end
        return raw
    end
    return raw
end

function M.call(prompt, cfg)
    local provider = cfg.provider or 'openai'
    if provider == 'openai' then
        return openai_chat(prompt, cfg)
    elseif provider == 'huggingface' then
        return huggingface_generate(prompt, cfg)
    elseif provider == 'azure' then
        return azure_openai(prompt, cfg)
    elseif provider == 'local' then
        return local_generate(prompt, cfg)
    elseif provider == 'groq' then
        return groq_generate(prompt, cfg)
    else
        return nil, 'unknown provider: ' .. tostring(provider)
    end
end

return M
