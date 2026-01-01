<#
Script para ejecutar localmente: retira del índice los archivos grandes y hace commit.
NO se ejecuta en este entorno; ejecuta este script en tu máquina con git instalado.
#>

Write-Host "Removing large files from git index (cached) and committing changes"

$commands = @(
    'git rm -r --cached .venv',
    'git rm --cached projects/bot/python_bot/data/ai_index.pkl',
    'git add .gitignore .gitattributes scripts/download_ai_index.ps1',
    'git commit -m "Remove large files from repo; add .gitignore and download script"'
)

foreach ($c in $commands) {
    Write-Host "-> $c"
    cmd /c $c
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Command failed: $c"
        exit $LASTEXITCODE
    }
}

Write-Host "Done. Remember to push: git push"
