Mini plugins
----------------

Place small demonstration or utility plugins in this folder. Each plugin
should expose a `setup(bot)` function that registers commands and handlers
using the `bot` API (`register_command`, `register_message_handler`,
`register_inline_handler`).

Miniapp example:

- `miniapp.py` — a tiny demo app providing `/miniapp`, `/mini_set`, `/mini_get`,
  and `/mini_echo` commands; responds to `ping` and offers an inline echo.

Web App:

- `miniapp_webapp.html` — a minimal Telegram Web App page placed under `projects/web/web`.
    Use the `/webapp` command to send a button that opens the Web App. Configure `WEBAPP_URL`
    to point to the hosted page (defaults to `http://127.0.0.1:8000/miniapp_webapp.html`).

Testing locally:

1. Start the bot runner (ensure `.venv` is active):

```powershell
.\.venv\Scripts\python.exe projects\bot\python_bot\main.py
```

2. Use a chat with the bot and call `/miniapp` to see available commands.
