param(
  [string]$ModelDir = "$PWD\models",
  [string]$VenvDir = ".venv_ai"
)

Write-Output "Using PowerShell installer"
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Error "Python launcher 'py' not found. Ensure Python 3 is installed and 'py' is on PATH.";
  exit 1
}

if (-not (Test-Path $VenvDir)){
  py -3 -m venv $VenvDir
}

$activate = Join-Path $VenvDir 'Scripts\Activate.ps1'
Write-Output "Activating virtualenv: $activate"
. $activate

python -m pip install --upgrade pip
python -m pip install -r python_api/requirements_ai.txt

if (-not (Test-Path $ModelDir)){
  New-Item -ItemType Directory -Path $ModelDir | Out-Null
}

Write-Output "Downloading gpt2 into $ModelDir (this may take a while)..."
$py = @"
from transformers import AutoTokenizer, AutoModelForCausalLM
from pathlib import Path
import os
cache_dir = Path(r"$ModelDir")
cache_dir.mkdir(parents=True, exist_ok=True)
AutoTokenizer.from_pretrained('gpt2', cache_dir=str(cache_dir))
AutoModelForCausalLM.from_pretrained('gpt2', cache_dir=str(cache_dir))
print('Downloaded gpt2 to', cache_dir)
"@
$scriptPath = Join-Path $env:TEMP ("download_gpt2_{0}.py" -f (Get-Random))
Set-Content -Path $scriptPath -Value $py -Encoding UTF8
python $scriptPath
Remove-Item $scriptPath -Force

Write-Output "Starting AI server..."
$env:PYMODEL_DIR = $ModelDir
Start-Process -FilePath (Join-Path $VenvDir 'Scripts\python.exe') -ArgumentList 'python_api/ai_server.py','--host','127.0.0.1','--port','8081','--model-dir',$ModelDir -NoNewWindow -PassThru
Write-Output "AI server started (check process list)."
