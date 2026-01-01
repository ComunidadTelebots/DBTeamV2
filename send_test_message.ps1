param(
    [string]$Token,
    [string]$Chat,
    [string]$Text = "[DBTeamV2] Test message"
)

# Try to read BOT_TOKEN from .env if not provided
if (-not $Token) {
    if (Test-Path .env) {
        $line = Get-Content .env | Where-Object { $_ -match '^\s*BOT_TOKEN\s*=' } | Select-Object -First 1
        if ($line) { $Token = ($line -split '=')[1].Trim().Trim('"') }
    }
}

if (-not $Token) { $Token = Read-Host 'Enter BOT_TOKEN' }
if (-not $Chat) { $Chat = Read-Host 'Enter chat id (numeric) or @username' }
if (-not $Text) { $Text = Read-Host 'Enter message text (leave empty for default)'; if (-not $Text) { $Text = "[DBTeamV2] Test message" } }

$body = @{ chat_id = $Chat; text = $Text } | ConvertTo-Json

try {
    $resp = Invoke-RestMethod -Uri "https://api.telegram.org/bot$Token/sendMessage" -Method Post -ContentType 'application/json' -Body $body -ErrorAction Stop
    Write-Host "Message sent. Telegram response:"
    $resp | ConvertTo-Json -Depth 4 | Write-Host
    exit 0
} catch {
    Write-Host "Error sending message:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    if ($_.Exception.Response -and $_.Exception.Response.Content) {
        try { $_.Exception.Response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 4 | Write-Host } catch { Write-Host $_.Exception.Response.Content }
    }
    exit 1
}
