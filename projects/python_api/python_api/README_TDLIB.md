TDLib integration (scaffold)
=================================

This folder includes a minimal scaffold to integrate TDLib with the FastAPI backend.

What was added
- `python_api/tdlib_client.py`: wrapper scaffold that attempts to use a Python TDLib binding if installed, otherwise exposes a dummy client for development.
- `python_api/app/tdlib_router.py`: FastAPI router exposing `/tdlib/connect`, `/tdlib/disconnect`, `/tdlib/send`, `/tdlib/chats` and a WebSocket at `/tdlib/ws`.

Requirements and setup
1. Install TDLib (native C++ library). Follow the official TDLib build instructions: https://tdlib.github.io/td/build.html
2. Install a Python binding for TDLib. One option is `python-tdlib` (package name may vary). After installing TDLib, install the binding:

   pip install python-tdlib

3. Configure environment and run the API (example):

```powershell
cd python_api
$env:REDIS_URL='redis://localhost:6379/0'
$env:WEB_API_SECRET='change_me'
uvicorn python_api.app.main:app --reload --port 5500
```

Usage notes
- Start the TDLib client via POST `/tdlib/connect` (optionally `{"dummy": true}` to use a dummy client).
- Real-time events should be forwarded from your TDLib event loop into the WebSocket manager in `tdlib_router.py` (the scaffold currently echoes messages for testing).

Security
- TDLib handles authentication with phone numbers; ensure credentials and session files are stored securely.

Extending the scaffold
- Implement actual binding calls in `tdlib_client.TDClient` according to the Python binding you choose.
- Push TDLib updates into `tdlib_router.ws_mgr.broadcast()` so connected UIs receive events.

Quick test (dummy auth + dummy client)
-------------------------------------

1. Ensure Redis is running or the repo can write temporary files (the scaffold falls back to `tmp_tdlib_auth.json`).
2. Start the API (from repository root):

```powershell
cd python_api
python -m uvicorn python_api.app.main:app --reload --port 5500
```

3. Open `http://127.0.0.1:5500/telegram.html` in your browser.
4. In the "Iniciar sesión de Telegram" panel enter a phone (any string) and click "Enviar código".
5. Enter `12345` as the verification code and click "Verificar" — the UI will auto-connect the dummy TDLib client and open the WebSocket to receive simulated messages.

If you want me to adapt the login UI to match a specific design, provide the CSS variables or a screenshot and I'll update `web/telegram.html` and `web/telegram.js` accordingly.
