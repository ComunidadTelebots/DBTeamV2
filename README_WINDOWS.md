# Windows build & run (PyInstaller)

This document explains how to build a Windows executable for the Python bot using `build_windows_exe.ps1`.

Prerequisites
- Windows 10/11 with PowerShell
- Python 3.9+ or the project `.venv` created in repo root
- Git clone of this repository
- Install external tools separately: `redis` (service), `aria2c` (optional), `libtorrent` (optional)

Quick build
1. Open PowerShell as your user in the repo root.
2. (Optional) Create and populate `.env` from `.env.example`.

```powershell
cp .env.example .env
# edit .env with your BOT_TOKEN and secrets
```

3. Create venv and install deps (recommended):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r projects\bot\python_bot\requirements.txt
pip install -r projects\python_api\python_api\requirements.txt
```

4. Run build script (one-folder default):
```powershell
.\build_windows_exe.ps1
# or one-file exe: .\build_windows_exe.ps1 -OneFile
```

Output
- Folder: `dist\DBTeamV2_bot\` containing `DBTeamV2_bot.exe` (one-folder build).
- Use `run_bot.bat` to launch it:
```powershell
.\run_bot.bat
```

Notes & limitations
- The exe bundles the Python runtime and the `projects` tree, but external native dependencies (Redis server, aria2c, libtorrent native lib) are NOT bundled. Install them separately on Windows.
- `python-libtorrent` (if used) is a binary wheel tied to specific Python versions; building it on Windows can be difficult. Prefer running torrent downloads via `aria2c` if `libtorrent` isn't available.
- For production, run Redis as a Windows service or use a remote Redis instance.

If you want, I can also generate a packaged installer (NSIS) or a systemd/unit equivalent for Windows (service wrapper).