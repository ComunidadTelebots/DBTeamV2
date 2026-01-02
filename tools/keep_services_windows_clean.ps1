<#
Windows monitor (clean). Starts and restarts configured processes and logs to logs/service_monitor.log
#>
param(
    [int]$RestartDelay = 5
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir 'service_monitor.log'
$pidFile = Join-Path $logDir 'service_monitor.pid'

function Log { param($msg); $ts=(Get-Date).ToString('s'); Add-Content -Path $logFile -Value "$ts $msg"; Write-Output "$ts $msg" }

function Start-ServiceProc($svc) {
    Log ("Starting {0}: {1} {2} (cwd={3})" -f $svc.Name, $svc.Exe, $svc.Args, $svc.Cwd)
  try {
    $p = Start-Process -FilePath $svc.Exe -ArgumentList $svc.Args -WorkingDirectory $svc.Cwd -PassThru -WindowStyle Hidden
    # write per-service pidfile
    try { $svcPidFile = Join-Path $logDir ("service_{0}.pid" -f $svc.Name); Set-Content -Path $svcPidFile -Value $p.Id -Encoding UTF8 } catch { Log ("Failed to write pidfile for {0}: {1}" -f $svc.Name, $_) }
    return $p
  } catch { Log ("Failed to start {0}: {1}" -f $svc.Name, $_); return $null }
}

$services=@(
    @{ Name='StaticWeb'; Exe='py'; Args='-3 -m http.server 8000 --directory web'; Cwd=$repoRoot },
    @{ Name='AIServer'; Exe='py'; Args='-3 python_api\ai_server.py --host 127.0.0.1 --port 8081'; Cwd=$repoRoot }
)

$procs=@{}
Log ("Service monitor starting. RestartDelay={0}s" -f $RestartDelay)
# write pidfile so external tools can detect this monitor
try { Set-Content -Path $pidFile -Value $PID -Encoding UTF8 } catch { Log ("Failed to write pidfile: {0}" -f $_) }
foreach($s in $services){ $procs[$s.Name]=Start-ServiceProc $s }

$stopping=$false
$null=Register-EngineEvent PowerShell.Exiting -Action { $global:stopping=$true } | Out-Null
try{
  while(-not $stopping){
    foreach($s in $services){
      $p=$procs[$s.Name]
      if($p -eq $null -or $p.HasExited){ Log ("Process {0} not running. Restarting..." -f $s.Name); $procs[$s.Name]=Start-ServiceProc $s }
    }
    Start-Sleep -Seconds $RestartDelay
  }
} finally {
  Log "Shutting down service monitor..."
  foreach($k in $procs.Keys){
    $p=$procs[$k]
    if($p -and -not $p.HasExited){
      try{
        Log ("Stopping {0} (PID {1})" -f $k,$p.Id);
        $p.Kill();
        $p.WaitForExit(5000)
      } catch { Log ("Error stopping {0}: {1}" -f $k,$_ ) }
    }
    # remove per-service pidfile
    try { $svcPidFile = Join-Path $logDir ("service_{0}.pid" -f $k); if (Test-Path $svcPidFile) { Remove-Item $svcPidFile -ErrorAction SilentlyContinue } } catch { }
  }
  try { if (Test-Path $pidFile) { Remove-Item $pidFile -ErrorAction SilentlyContinue } } catch { }
  Log "Service monitor stopped."
}
