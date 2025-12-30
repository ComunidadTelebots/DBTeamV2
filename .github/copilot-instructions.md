This repository is a Lua-based Telegram bot (DBTeam) implemented as a small plugin system.
The instructions below give an AI coding assistant the minimal, actionable knowledge to be productive.

1) Big picture
- **Language & runtime**: Lua 5.2. Files assume `lua` and common Lua networking libs (`ssl.https`, `socket.http`, `ltn12`). See [README.md](README.md) for install hints.
- **Main entry**: `launch.sh` runs the bot; core runtime loop and plugin loader live in [bot/bot.lua](bot/bot.lua).
- **Plugin architecture**: Plugins live in `plugins/*.lua`. Each plugin returns a table with keys like `patterns` (array of Lua regex strings), `run(msg, matches)` and optional `pre_process(msg)`.
- **Configuration**: Runtime configuration is in `data/config.lua` (created from `bot.create_config()` if missing). Enabled plugins are listed in `_config.enabled_plugins` and languages in `_config.enabled_lang`.

2) Key integration points (where to change behavior)
- Message processing flow: `tdcli_update_callback` -> `user_callback` -> `bot_init` -> `pre_process_msg` -> `match_plugins` in [bot/bot.lua](bot/bot.lua).
- Plugin matching: `plugin.patterns` are tested against `msg.text`; when matched, `plugin.run(msg, matches)` is invoked. See [plugins/commands.lua](plugins/commands.lua) and [plugins/ai.lua](plugins/ai.lua) for examples.
- AI integration: `plugins/ai.lua` calls `plugins/ai_client.lua` which supports multiple providers (OpenAI, HuggingFace, Azure, local, Groq). The user-facing prompt config is in [data/ai_config.lua](data/ai_config.lua).

3) Common conventions & patterns
- Loading: code uses `loadfile('./plugins/<name>.lua')()` to import plugin modules; plugins must return a Lua table.
- Plugin shape: at minimum return `{ patterns = {"regex"}, run = function(msg, matches) ... end }`.
- Responses: `run` may return a string (message body) — `bot.match_plugin` will `send_msg(receiver, result, "md")` when a result is returned.
- Pre-processing: implement `pre_process(msg)` in a plugin to mutate/validate messages before matching.

4) Developer workflows & tests
- Start locally (Linux/macOS): `chmod +x launch.sh && ./launch.sh install && ./launch.sh`. On Windows use a compatible Lua runtime and ensure dependencies (Redis, Lua libs) are available. See [README.md](README.md).
- To test an AI prompt flow: configure `data/ai_config.lua` with `provider` and credentials, then send chat commands like `!ask <your prompt>` or `/ask <prompt>` (see patterns in [plugins/ai.lua](plugins/ai.lua)).

5) Troubleshooting notes
- HTTP libraries: `ai_client.lua` tries `ssl.https` then `socket.http` — missing these will break remote LLM calls.
- JSON: project uses `libs/JSON.lua` (synchronous decode/encode). Keep payload sizes within provider limits (`max_tokens` in `data/ai_config.lua`).
- Errors loading plugins are printed (see `load_plugins()` in [bot/bot.lua](bot/bot.lua)); preserve that pattern when adding new plugin code.

6) How to add a new plugin (example)
- Create `plugins/myplugin.lua`:
```lua
return {
  patterns = {"^[!/#](hello)$"},
  run = function(msg, matches)
    return "Hello from myplugin" -- bot will send this
  end
}
```
- Add `"myplugin"` to `data/config.lua` under `enabled_plugins` or call `create_config()` to regenerate defaults.

7) Files to inspect for more patterns
- [bot/bot.lua](bot/bot.lua) — main loop and plugin dispatch
- [plugins/ai.lua](plugins/ai.lua) and [plugins/ai_client.lua](plugins/ai_client.lua) — AI integration
- [data/ai_config.lua](data/ai_config.lua) — provider credentials & options
- [plugins/commands.lua](plugins/commands.lua) — example of command patterns and replies

If any area is unclear or you want extra examples (e.g., adding a plugin that calls an external API, unit-test patterns, or a local dev setup for Windows), tell me which part to expand and I'll iterate.
