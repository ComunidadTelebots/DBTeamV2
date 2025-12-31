<#
start_dev.ps1
Script para arrancar el backend (uvicorn) y servir la carpeta `web` con Python HTTP server.
Uso: abre PowerShell en la raíz del repo y ejecuta:
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
  .\start_dev.ps1
#>

function Get-PythonExe {
    $candidates = @('python','py','python3')
    foreach ($name in $candidates) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Path }
    }
    return $null
}

$pythonExe = Get-PythonExe
if (-not $pythonExe) {
    Write-Host "No se ha encontrado Python en PATH. Instala Python 3.10+ y marca 'Add to PATH' durante la instalación."
    Write-Host "Alternativa: descarga desde https://www.python.org/downloads/ o instala el lanzador 'py'."
    exit 1
}

Write-Host "Usando Python en: $pythonExe"

if (-Not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv..."
    & $pythonExe -m venv .venv
    $venvPython = Join-Path ".venv\Scripts" "python.exe"
    if (Test-Path $venvPython) {
        & $venvPython -m pip install --upgrade pip
        if (Test-Path "python_api/requirements.txt") {
            & $venvPython -m pip install -r projects/python_api/python_api/requirements.txt
        }
    } else {
        Write-Host "No se pudo crear el entorno virtual en .venv; usando el python del sistema.";
        $venvPython = $pythonExe
    }
} else {
    $venvPython = Join-Path ".venv\Scripts" "python.exe"
}

if (-Not (Test-Path $venvPython)) {
    Write-Host "Python ejecutable no encontrado en el entorno virtual ni en el sistema. Abortando.";
    exit 1
}

Write-Host "Iniciando backend (uvicorn) en http://localhost:8081 ..."
Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "projects.python_api.python_api.app.main:app", "--host", "0.0.0.0", "--port", "8081", "--reload"

Write-Host "Sirviendo carpeta web en http://localhost:5500 ..."
Start-Process -FilePath $venvPython -ArgumentList "-m", "http.server", "5500", "--directory", "web"

try { Start-Process "http://127.0.0.1:5500" } catch { }
Write-Host "Hecho. Abre http://127.0.0.1:5500 en tu navegador si no se abre automáticamente."
