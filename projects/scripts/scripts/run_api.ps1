<#
run_api.ps1 - helper to start the python_api service on Windows (PowerShell)

Usage examples:
  # start redis (docker-compose), install deps, and run API on port 5500
  .\run_api.ps1 -StartRedis -InstallDeps -Port 5500

  # just run API (assumes .venv exists and env vars set externally)
  .\run_api.ps1

Options:
  -StartRedis   : attempt to start Redis using python_api\docker-compose.yml
  -InstallDeps  : run `pip install -r python_api\requirements.txt` inside the virtualenv
  -Port <n>     : port for uvicorn (default 5500)
#>
param(
  [switch]$StartRedis,
  [switch]$InstallDeps,
  [int]$Port = 5500
)

Set-StrictMode -Version Latest

# --- user-configurable defaults (edit here) ---
$env:REDIS_URL = $env:REDIS_URL -or 'redis://localhost:6379/0'
$env:WEB_API_KEY = $env:WEB_API_KEY -or 'mi_secreto_local'
$env:BOT_TOKEN = $env:BOT_TOKEN -or ''
$env:WEB_API_SECRET = $env:WEB_API_SECRET -or 'cambia_esto'
$env:WEB_API_ORIGIN = $env:WEB_API_ORIGIN -or '*'
# ---------------------------------------------

<#
run_api.ps1 - helper to start the python_api service on Windows (PowerShell)

Usage examples:
  # start redis (docker-compose), install deps, and run API on port 5500
  .\run_api.ps1 -StartRedis -InstallDeps -Port 5500

  # just run API (assumes .venv exists and env vars set externally)
  .\run_api.ps1

Options:
  -StartRedis   : attempt to start Redis using python_api\docker-compose.yml
  -InstallDeps  : run `pip install -r python_api\requirements.txt` inside the virtualenv
  -Port <n>     : port for uvicorn (default 5500)
#>
param(
  [switch]$StartRedis,
  [switch]$InstallDeps,
  [int]$Port = 5500
)

Set-StrictMode -Version Latest

# --- user-configurable defaults (edit here) ---
$env:REDIS_URL = $env:REDIS_URL -or 'redis://localhost:6379/0'
$env:WEB_API_KEY = $env:WEB_API_KEY -or 'mi_secreto_local'
$env:BOT_TOKEN = $env:BOT_TOKEN -or ''
$env:WEB_API_SECRET = $env:WEB_API_SECRET -or 'cambia_esto'
$env:WEB_API_ORIGIN = $env:WEB_API_ORIGIN -or '*'
# ---------------------------------------------

Write-Host "Using REDIS_URL=$($env:REDIS_URL) PORT=$Port"

# start redis via docker-compose if requested
if($StartRedis){
  if(Test-Path "python_api/docker-compose.yml"){
    Write-Host "Starting redis via docker-compose..."
    Push-Location python_api
    docker-compose up -d redis
    Pop-Location
  }else{
    Write-Warning "docker-compose.yml not found in python_api; skipping StartRedis"
  }
}

# ensure virtualenv exists
$venvPath = Join-Path -Path $PSScriptRoot -ChildPath ".venv"
$venvActivate = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
if(-not (Test-Path $venvPath)){
  Write-Host "Creating virtual environment at $venvPath..."
  python -m venv $venvPath
}

# Activate the venv in this session
if(Test-Path $venvActivate){
  Write-Host "Activating virtual environment..."
  & $venvActivate
} else {
  Write-Warning "Activation script not found at $venvActivate — continuing without activation."
}

# Resolve pip/uvicorn executables inside the venv (fallback to global)
$pipExe = Join-Path -Path $venvPath -ChildPath "Scripts\pip.exe"
if(-not (Test-Path $pipExe)){
  $pipExe = "pip"
}
$uvicornExe = Join-Path -Path $venvPath -ChildPath "Scripts\uvicorn.exe"
if(-not (Test-Path $uvicornExe)){
  $uvicornExe = ""
}

# install deps if requested
if($InstallDeps){
  if(Test-Path "python_api\requirements.txt"){
    Write-Host "Installing python dependencies..."
    & $pipExe install -r python_api\requirements.txt
  }else{
    Write-Warning "python_api\requirements.txt not found; skipping InstallDeps"
  }
}

# Start uvicorn using the venv binary if available
Write-Host "Starting uvicorn (python_api.app.main:app) on port $Port..."
if($uvicornExe -ne ""){
  & $uvicornExe projects.python_api.python_api.app.main:app --reload --host 0.0.0.0 --port $Port
}else{
  # fallback to module invocation
  python -m uvicorn projects.python_api.python_api.app.main:app --reload --host 0.0.0.0 --port $Port
}
# install deps if requested
if($InstallDeps){
  if(Test-Path "python_api\requirements.txt"){
    Write-Host "Installing python dependencies..."
    & $pipExe install -r python_api\requirements.txt
  }else{
    Write-Warning "python_api\requirements.txt not found; skipping InstallDeps"
  }
}

# Start uvicorn using the venv binary if available
Write-Host "Starting uvicorn (python_api.app.main:app) on port $Port..."
if($uvicornExe -ne ""){
  & $uvicornExe projects.python_api.python_api.app.main:app --reload --host 0.0.0.0 --port $Port
}else{
  # fallback to module invocation
  python -m uvicorn projects.python_api.python_api.app.main:app --reload --host 0.0.0.0 --port $Port
}
  & $venvActivate
} else {
  Write-Warning ".venv not found at $venvActivate — ensure your virtualenv is activated manually if needed."
}

# install deps if requested
if($InstallDeps){
  if(Test-Path "python_api\requirements.txt"){
    Write-Host "Installing python dependencies..."
    pip install -r python_api\requirements.txt
  }else{
    Write-Warning "python_api\requirements.txt not found; skipping InstallDeps"
  }
}

# Start uvicorn
Write-Host "Starting uvicorn (python_api.app.main:app) on port $Port..."
$cmd = "uvicorn projects.python_api.python_api.app.main:app --reload --host 0.0.0.0 --port $Port"
Write-Host $cmd
# Execute the command so logs stream to this console
iex $cmd
