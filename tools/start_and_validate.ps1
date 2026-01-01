# Start bot and run smoke test
param(
  [string]$Token = ''
)
# dot-source control functions
. .\tools\bot_control.ps1

if ($Token -ne '') {
  Start-Bot -Token $Token
} else {
  Start-Bot
}

Start-Sleep -Seconds 2
Write-Host 'Running smoke test...'
. .\tools\smoke_test.ps1
