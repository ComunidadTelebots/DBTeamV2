$repo = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projPath = Join-Path $repo 'projects\bot'
$logPath = Join-Path $repo 'bot.log'
$py = Join-Path $repo '.venv\Scripts\python.exe'
$main = Join-Path $repo 'projects\bot\python_bot\main.py'
# Load BOT_TOKEN from .env if present
$tokLine = Get-Content (Join-Path $repo '.env') | Where-Object {$_ -match '^BOT_TOKEN'}
if ($tokLine) { $env:BOT_TOKEN = ($tokLine -replace '^BOT_TOKEN=','' -replace '"','').Trim() }
$env:PYTHONPATH = $projPath
& $py -u $main 2>&1 | Out-File -FilePath $logPath -Encoding utf8 -Append
