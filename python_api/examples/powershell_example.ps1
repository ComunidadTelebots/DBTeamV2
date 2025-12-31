$headers = @{ "Content-Type" = "application/json" }
if ($env:WEB_API_KEY) { $headers["X-API-Key"] = $env:WEB_API_KEY }

$body = @{
    prompt = "Hola, da 3 consejos para escribir código limpio."
    provider = "local"
    model = "gpt2"
    max_length = 80
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8081/ai" -Method Post -Body $body -Headers $headers -ContentType "application/json"
