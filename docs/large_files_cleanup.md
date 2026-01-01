# Limpieza de archivos grandes (>100MB)

Este documento describe pasos seguros para eliminar archivos pesados del repositorio y alternativas para mantener datos grandes fuera del control de versiones.

1) Archivos detectados en este repo
- `.venv/` — entorno virtual local (no debe versionarse)
- `projects/bot/python_bot/data/ai_index.pkl` — índice grande (~210MB)

2) Añadidos en el repo por este cambio
- `.gitignore` actualizado para ignorar `*.pkl` y `projects/bot/python_bot/data/ai_index.pkl`
- `.gitattributes` que marca `*.pkl` para Git LFS
- `scripts/download_ai_index.ps1` para descargar el `ai_index.pkl` desde un almacenamiento externo

3) Pasos sugeridos (ejecutar en tu máquina local con `git` instalado)

- Retirar archivos grandes del índice (no borrar localmente):
```powershell
git rm -r --cached .venv
git rm --cached projects/bot/python_bot/data/ai_index.pkl
git add .gitignore .gitattributes scripts/download_ai_index.ps1
git commit -m "Remove large files from repo; add .gitignore and download script"
git push
```

- Usar Git LFS (opcional, si quieres versionar pkl sin inflar el repo):
```powershell
git lfs install
git lfs track "*.pkl"
git add .gitattributes
git add projects/bot/python_bot/data/ai_index.pkl
git commit -m "Track ai_index.pkl with Git LFS"
git push
```

- Purgar historial (ADVERTENCIA: reescribe historial; coordinar con colaboradores):
  - Usar `git-filter-repo` o `bfg-repo-cleaner`. Ejemplo con `git-filter-repo`:
```bash
pip install git-filter-repo
git clone --mirror <repo-url> repo.git
cd repo.git
git filter-repo --path projects/bot/python_bot/data/ai_index.pkl --invert-paths
git filter-repo --path .venv/ --invert-paths
git push --force --mirror
```

4) Alternativas para `ai_index.pkl`
- Subir a S3/Drive y usar `scripts/download_ai_index.ps1` antes de ejecutar el bot.
- Comprimir o serializar con compresión: `joblib.dump(obj, 'ai_index.pkl', compress=3)`.
- Utilizar backend más compacto (FAISS, SQLite, etc.).

5) Notas y advertencias
- No ejecutar la purga de historial sin coordinar con todo el equipo.
- Hacer backup del repositorio antes de operaciones que reescriban historial.
