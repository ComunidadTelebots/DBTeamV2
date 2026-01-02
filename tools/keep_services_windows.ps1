<#
Keeps selected services running on Windows by restarting them when they exit.

Usage:
  powershell -ExecutionPolicy Bypass -File tools\keep_services_windows.ps1

Edit the `$services` array below to add or remove entries.
#>

param(
    [int]$RestartDelay = 5
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir 'service_monitor.log'

function Log {
    param($msg)
    $ts = (Get-Date).ToString('s')
    $line = "$ts $msg"
    Add-Content -Path $logFile -Value $line
    Write-Output $line
}

function Start-ServiceProc($svc) {
    Log ("Starting {0}: {1} {2} (cwd={3})" -f $svc.Name, $svc.Exe, $svc.Args, $svc.Cwd)
    try {
        $proc = Start-Process -FilePath $svc.Exe -ArgumentList $svc.Args -WorkingDirectory $svc.Cwd -PassThru -WindowStyle Hidden
        Start-Sleep -Milliseconds 500
        return $proc
    } catch {
        Log ("Failed to start {0}: {1}" -f $svc.Name, $_)
        return $null
    }
}

# Define the services to run and monitor. Edit as needed.
$services = @(
    @{ Name = 'StaticWeb'; Exe = 'py'; Args = '-3 -m http.server 8000 --directory web'; Cwd = $repoRoot },
    @{ Name = 'AIServer'; Exe = 'py'; Args = '-3 python_api\ai_server.py --host 127.0.0.1 --port 8081'; Cwd = $repoRoot }
    # Example additional service:
    # @{ Name = 'BotBackend'; Exe = 'py'; Args = '-3 python_bot\bot.py'; Cwd = $repoRoot }
)

$procs = @{}

Log ("Service monitor starting. RestartDelay={0}s" -f $RestartDelay)

foreach ($svc in $services) {
    $procs[$svc.Name] = Start-ServiceProc $svc
}

$stopping = $false
$null = Register-EngineEvent PowerShell.Exiting -Action { $global:stopping = $true } | Out-Null

try {
    while (-not $stopping) {
        foreach ($svc in $services) {
            $p = $procs[$svc.Name]
            if ($p -eq $null -or $p.HasExited) {
                Log ("Process {0} not running. Restarting..." -f $svc.Name)
                $procs[$svc.Name] = Start-ServiceProc $svc
            }
        }
        Start-Sleep -Seconds $RestartDelay
    }
} finally {
    Log "Shutting down service monitor..."
    foreach ($k in $procs.Keys) {
        $p = $procs[$k]
        if ($p -and -not $p.HasExited) {
            try {
                Log ("Stopping {0} (PID {1})" -f $k, $p.Id)
                $p.Kill()
                $p.WaitForExit(5000)
            } catch {
                Log ("Error stopping {0}: {1}" -f $k, $_)
            }
        }
    }
    Log "Service monitor stopped."
}
<#
Keeps selected services running on Windows by restarting them when they exit.

Usage:
  powershell -ExecutionPolicy Bypass -File tools\keep_services_windows.ps1

Edit the `$services` array below to add or remove entries.
#>

param(
    [int]$RestartDelay = 5
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir 'service_monitor.log'

function Log {
    param($msg)
    $ts = (Get-Date).ToString('s')
    $line = "$ts $msg"
    Add-Content -Path $logFile -Value $line
    Write-Output $line
}

function Start-ServiceProc($svc) {
    Log ("Starting {0}: {1} {2} (cwd={3})" -f $svc.Name, $svc.Exe, $svc.Args, $svc.Cwd)
    try {
        $proc = Start-Process -FilePath $svc.Exe -ArgumentList $svc.Args -WorkingDirectory $svc.Cwd -PassThru -WindowStyle Hidden
        Start-Sleep -Milliseconds 500
        return $proc
    } catch {
        Log ("Failed to start {0}: {1}" -f $svc.Name, $_)
        return $null
    }
}

# Define the services to run and monitor. Edit as needed.
$services = @(
    @{ Name = 'StaticWeb'; Exe = 'py'; Args = '-3 -m http.server 8000 --directory web'; Cwd = $repoRoot },
    @{ Name = 'AIServer'; Exe = 'py'; Args = '-3 python_api\ai_server.py --host 127.0.0.1 --port 8081'; Cwd = $repoRoot }
    # Example additional service:
    # @{ Name = 'BotBackend'; Exe = 'py'; Args = '-3 python_bot\bot.py'; Cwd = $repoRoot }
)

$procs = @{}

Log ("Service monitor starting. RestartDelay={0}s" -f $RestartDelay)

foreach ($svc in $services) {
    $procs[$svc.Name] = Start-ServiceProc $svc
}

$stopping = $false
$null = Register-EngineEvent PowerShell.Exiting -Action { $global:stopping = $true } | Out-Null

try {
    while (-not $stopping) {
        foreach ($svc in $services) {
            $p = $procs[$svc.Name]
            if ($p -eq $null -or $p.HasExited) {
                Log ("Process {0} not running. Restarting..." -f $svc.Name)
                $procs[$svc.Name] = Start-ServiceProc $svc
            }
        }
        Start-Sleep -Seconds $RestartDelay
    }
} finally {
    Log "Shutting down service monitor..."
    foreach ($k in $procs.Keys) {
        $p = $procs[$k]
        if ($p -and -not $p.HasExited) {
            try {
                Log ("Stopping {0} (PID {1})" -f $k, $p.Id)
                $p.Kill()
                $p.WaitForExit(5000)
            } catch {
                Log ("Error stopping {0}: {1}" -f $k, $_)
            }
        }
    }
    Log "Service monitor stopped."
}
<#
Keeps selected services running on Windows by restarting them when they exit.

Usage:
  powershell -ExecutionPolicy Bypass -File tools\keep_services_windows.ps1

Edit the `$services` array below to add or remove entries.
#>

param(
    [int]$RestartDelay = 5
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir 'service_monitor.log'

function Log {
    param($msg)
    $ts = (Get-Date).ToString('s')
    $line = "$ts $msg"
    Add-Content -Path $logFile -Value $line
    Write-Output $line
}

function Start-ServiceProc($svc) {
    Log "Starting $($svc.Name): $($svc.Exe) $($svc.Args) (cwd=$($svc.Cwd))"
    try {
        $proc = Start-Process -FilePath $svc.Exe -ArgumentList $svc.Args -WorkingDirectory $svc.Cwd -PassThru -WindowStyle Hidden
        Start-Sleep -Milliseconds 500
        return $proc
    } catch {
        Log "Failed to start $($svc.Name): $_"
        return $null
    }
}

# Define the services to run and monitor. Edit as needed.
$services = @(
    @{ Name = 'StaticWeb'; Exe = 'py'; Args = '-3 -m http.server 8000 --directory web'; Cwd = $repoRoot },
    @{ Name = 'AIServer'; Exe = 'py'; Args = '-3 python_api\ai_server.py --host 127.0.0.1 --port 8081'; Cwd = $repoRoot }
    # Example additional service:
    # @{ Name = 'BotBackend'; Exe = 'py'; Args = '-3 python_bot\bot.py'; Cwd = $repoRoot }
)

$procs = @{}

Log "Service monitor starting. RestartDelay=${RestartDelay}s"

foreach ($svc in $services) {
    $procs[$svc.Name] = Start-ServiceProc $svc
}

$stopping = $false
$null = Register-EngineEvent PowerShell.Exiting -Action { $global:stopping = $true } | Out-Null

try {
    while (-not $stopping) {
        foreach ($svc in $services) {
            $p = $procs[$svc.Name]
            if ($p -eq $null -or $p.HasExited) {
                Log "Process $($svc.Name) not running. Restarting..."
                $procs[$svc.Name] = Start-ServiceProc $svc
            }
        }
        Start-Sleep -Seconds $RestartDelay
    }
} finally {
    Log "Shutting down service monitor..."
    foreach ($k in $procs.Keys) {
        $p = $procs[$k]
        if ($p -and -not $p.HasExited) {
            try {
                Log "Stopping $k (PID $($p.Id))"
                $p.Kill()
                $p.WaitForExit(5000)
            } catch {
                Log "Error stopping $k: $_"
            }
        }
    }
    Log "Service monitor stopped."
}
