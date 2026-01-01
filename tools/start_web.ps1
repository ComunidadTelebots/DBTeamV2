$repo = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$venvPython = Join-Path $repo '.venv\Scripts\python.exe'
$webdir = Join-Path $repo 'projects\web\web'

if (-not (Test-Path $venvPython)) {
    Write-Host "venv python not found: $venvPython" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $webdir)) {
    Write-Host "Web dir not found: $webdir" -ForegroundColor Red
    exit 1
}
Write-Host "Starting static server from $webdir on port 8000 using $venvPython..."
Start-Process -FilePath $venvPython -ArgumentList '-m','http.server','8000' -WorkingDirectory $webdir -WindowStyle Minimized
Start-Sleep -Seconds 1
try {
    $r = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000
    if ($r.TcpTestSucceeded) { Write-Host 'Started web server on port 8000' -ForegroundColor Green; exit 0 }
    else { Write-Host 'Failed to open port 8000' -ForegroundColor Red; $r | Format-List; exit 2 }
} catch {
    Write-Host ('Test failed: ' + $_.Exception.Message) -ForegroundColor Red
    exit 3
}