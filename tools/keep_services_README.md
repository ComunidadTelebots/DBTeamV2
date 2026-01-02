# keep_services helper

This folder contains helper scripts to keep the web UI and related services running continuously.

Files
- `keep_services_windows.ps1` — PowerShell monitor that starts and restarts configured processes (Windows).
- `keep_services_linux.sh` — Bash helper to run/restart processes (Linux).

Quick start (Windows)

1. From repo root, run:

```powershell
powershell -ExecutionPolicy Bypass -File tools\keep_services_windows.ps1
```

2. Logs are written to `logs/service_monitor.log`.

Run as Windows service / startup
- Use Task Scheduler to run the PowerShell script at logon or system start (set to run whether user is logged in).
- Or install a small service wrapper like NSSM (https://nssm.cc/) and point it to `powershell -ExecutionPolicy Bypass -File <path>\tools\keep_services_windows.ps1`.

Quick start (Linux)

```bash
chmod +x tools/keep_services_linux.sh
./tools/keep_services_linux.sh &
```

Run as systemd unit
- Create a systemd service that runs the script at boot and restarts on failure. Example unit:

```
[Unit]
Description=Repo service monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/repo
ExecStart=/path/to/repo/tools/keep_services_linux.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

Customization
- Edit the `services` array in the PowerShell script or `CMDS` array in the bash script to add/remove commands to monitor.
- Make sure `py`/`python3` is on PATH for the commands used.

Notes
- These scripts are simple monitors and do not replace a proper init/system service manager in production.
- For production, prefer systemd (Linux) or NSSM/Windows Service for robust management and logging.
