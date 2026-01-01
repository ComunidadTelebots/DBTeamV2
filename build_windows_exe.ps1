<#
build_windows_exe.ps1
Build a Windows executable bundle for the bot using PyInstaller.
Usage (PowerShell):
  ./build_windows_exe.ps1            # uses .venv\Scripts\python.exe if exists
  ./build_windows_exe.ps1 -OneFile   # create single-file executable
#>

param(
  [switch]$OneFile
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

# choose python executable from venv if available
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPy) {
  $py = $venvPy
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $py = (Get-Command python).Source
} else {
  Write-Error 'Python not found. Install Python or create .venv first.'
  exit 1
}

Write-Host "Using Python: $py"

# ensure PyInstaller exists
& $py -m pip install --upgrade pip
& $py -m pip install pyinstaller

$entry = 'projects\\bot\\python_bot\\main.py'
$name = 'DBTeamV2_bot'

# include the whole projects tree and the example env
$adddata = @(
  'projects;projects',
  '.env.example;.'
)

$onedirArg = if ($OneFile) { '--onefile' } else { '--onedir' }

# build argument array
$args = @('PyInstaller','--clean',$onedirArg,'--name',$name)
foreach ($d in $adddata) { $args += '--add-data'; $args += $d }
$args += $entry

Write-Host 'Running PyInstaller with args:'
Write-Host $args -Join ' '

& $py -m @args

if (Test-Path (Join-Path 'dist' $name)) {
  Write-Host "Build complete: dist\$name"
} else {
  Write-Error 'Build failed or output not found.'
}

Write-Host 'Note: External dependencies (Redis, aria2c, libtorrent) are NOT bundled and must be installed separately.'
Pop-Location
