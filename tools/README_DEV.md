Development helper

This project includes a small dev proxy to serve the `web/` static files and proxy API calls to the backend to avoid CORS while developing locally.

Quick start (Windows PowerShell):

1) Install Python deps for the proxy:

```powershell
py -3 -m pip install --user flask requests
```

2) Start the streamer backend and the dev proxy (both in background processes):

```powershell
# from the repo root
.\tools\start_dev_env.ps1
```

3) Open the UI:

- http://127.0.0.1:8000/owner.html

Notes:
- If you prefer to run processes manually, you can start the backend and proxy in separate consoles:

```powershell
py -3 python_api\stream_server.py
py -3 tools\dev_proxy.py
```

- To stop the started services, use `Stop-Process -Id <pid>` where `<pid>` is in `logs/dev_streamer.pid` and `logs/dev_proxy.pid`.
