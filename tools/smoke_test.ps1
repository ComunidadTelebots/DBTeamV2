# Simple smoke test for web server and stats API
param(
    [string]$WebUrl = 'http://127.0.0.1:8000/',
    [string]$StatsUrl = 'http://127.0.0.1:8081/stats'
)

function Get-EnvApiKey {
    if (Test-Path .env) {
        $k = (Get-Content .env | Where-Object { $_ -match '^WEB_API_SECRET=' }) -replace '^[^=]*=' , ''
        return $k.Trim('"')
    }
    return ''
}

Write-Host "Checking web URL: $WebUrl"
try {
    $r = Invoke-WebRequest -Uri $WebUrl -UseBasicParsing -TimeoutSec 5
    Write-Host "Web responded: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Web check failed: $_" -ForegroundColor Red
}

$k = Get-EnvApiKey
$headers = @{}
if ($k) { $headers['Authorization'] = "Bearer $k" }
Write-Host "Checking stats API: $StatsUrl"
try {
    $r = Invoke-RestMethod -Uri $StatsUrl -Headers $headers -TimeoutSec 5
    Write-Host "Stats OK:" -ForegroundColor Green
    $r | ConvertTo-Json -Depth 3
} catch {
    Write-Host "Stats check failed: $_" -ForegroundColor Red
}
