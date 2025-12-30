return {
    -- provider: 'openai' | 'huggingface' | 'azure' | 'local'
    provider = 'openai',

    openai = {
        api_key = "YOUR_OPENAI_API_KEY_HERE",
        model = "gpt-3.5-turbo",
        max_tokens = 400,
        temperature = 0.7
    },

    huggingface = {
        api_key = "",
        model = "gpt2"
    },

    azure = {
        endpoint = "", -- e.g. https://your-resource.openai.azure.com
        api_key = "",
        deployment_id = "", -- deployment or model name
        api_version = "2023-05-15"
    },

    local = {
        url = "http://127.0.0.1:8000/generate" -- example local LLM endpoint
    }
,

    groq = {
        -- Provide your Groq endpoint URL and API key. Example:
        -- url = "https://api.groq.com/v1/models/<model>/predict"
        url = "",
        api_key = "",
        -- optional: customize request payload key (default uses {input = prompt})
        input_key = "input"
    }
}
