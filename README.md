DBTeam-bot
============

Installation
------------

Debian/Ubuntu and derivatives:
```bash
# Tested on Ubuntu 16.04. (please use release "stable", isn't working on stretch/testing)
sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y && sudo apt-get update && sudo apt-get upgrade -y && sudo apt-get autoremove && sudo apt-get autoclean && sudo apt-get install git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 make libstdc++6 -y
```

Arch:
```bash
sudo yaourt -S git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0
```

Fedora:
```bash
sudo dnf install git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0
```

After those dependencies, lets install the bot
```bash
 git clone https://github.com/Josepdal/DBTeamV2.git
 cd DBTeamV2
 chmod +x launch.sh
 ./launch.sh install
 ./launch.sh # Will ask you for a phone number & confirmation code.
```

Docker
------

Un `Dockerfile` y `.dockerignore` están incluidos para ejecutar el bot en un contenedor basado en Ubuntu con `lua5.2` y `luarocks`.

Construir la imagen:

```bash
docker build -t dbteamv2 .
```

Ejecutar (ejemplo, usando LibreTranslate por defecto):

```bash
docker run -e TRANSLATE_PROVIDER=libre -v $(pwd):/app -it dbteamv2
```

Para usar DeepL dentro del contenedor:

```bash
docker run -e TRANSLATE_PROVIDER=deepl -e TRANSLATE_API_KEY=your_key_here -v $(pwd):/app -it dbteamv2
```

Traducciones (uso)
-------------------

Se ha añadido un módulo `lang/translator.lua` que soporta LibreTranslate (por defecto) y DeepL.

- Para generar una versión traducida del archivo base `lang/english_lang.lua`, envía el comando al bot:

	/translate <from> <to>

	Ejemplo: `/translate en es` generará `lang/es_lang.lua` (archivo de salida: `lang/es_lang.lua`).

- El proveedor por defecto es `libre`. Para cambiarlo usa la variable de entorno `TRANSLATE_PROVIDER` (`libre` o `deepl`). Para DeepL define `TRANSLATE_API_KEY`.

- Si prefieres traducir varios archivos o usar otro archivo base, modifica el comando en `plugins/commands.lua` o ejecuta el traductor directamente:

```lua
local t = require('lang.translator')
t.translate_file('lang/english_lang.lua', 'lang/es_lang.lua', { provider = 'libre', source = 'en', target = 'es' })
```

Notas
-----
- LibreTranslate públicos pueden tener límites; considera desplegar tu propia instancia de LibreTranslate o usar DeepL para mayor robustez.
- Archivos generados por traducción sobrescriben/crean `lang/<target>_lang.lua`.

Bot API adapter
---------------

Además del cliente TDLib/telegram-cli, este proyecto incluye un adaptador mínimo para la Telegram Bot API (`bot/bot_api_adapter.lua`). Es útil para pruebas rápidas con un Bot token (no requiere TDLib ni sesión telefónica).

- Para usarlo, exporta `BOT_TOKEN` y ejecuta `launch.sh` (el script arranca el adaptador automáticamente si detecta `BOT_TOKEN`):

```bash
export BOT_TOKEN=123456:ABC-DEF...
./launch.sh
```

- También puedes ejecutar el adaptador directamente:

```bash
BOT_TOKEN=123456:ABC-DEF... lua bot/bot_api_adapter.lua
```

- Notas sobre el adaptador:
	- Implementa long-polling con `getUpdates` y convierte cada `message` en la estructura interna usada por el bot, llamando `tdcli_update_callback`.
	- Reemplaza `tdcli_function` por una versión adaptada que soporta al menos `SendMessage`, `DeleteMessage` y `SearchPublicChat` a través de la Bot API. No cubre todas las llamadas de TDLib; si tus plugins usan otras funciones deberás ampliar el mapeo.
	- El adaptador es para pruebas y desarrollo; para producción se recomienda TDLib o un diseño con webhooks.

Webhook (API Bot web)
---------------------

También se incluye un adaptador webhook en Lua (`bot/webhook_adapter.lua`) que expone un servidor HTTP simple para recibir webhooks de Telegram y convertirlos en actualizaciones internas del bot. Uso recomendado para entornos donde puedas exponer HTTPS (por ejemplo mediante `ngrok` o un proxy con certificado).

- Para usar el webhook adapter exporta `BOT_TOKEN` y `WEBHOOK=1` y (opcional) `WEBHOOK_PORT` antes de ejecutar `launch.sh`:

```bash
export BOT_TOKEN=123456:ABC-DEF...
export WEBHOOK=1
export WEBHOOK_PORT=8443  # opcional, por defecto 8080
./launch.sh
```

- Telegram exige HTTPS para webhooks. Si desarrollas localmente usa `ngrok` o similar para exponer `http://localhost:PORT` como `https://...` y luego registra el webhook con `setWebhook`:

```bash
curl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" -d "url=https://<your-ngrok-url>/" 
```

- El adaptador HTTP incluido es intencionalmente simple (desarrollos/test). Para producción se recomienda recibir webhooks detrás de un proxy HTTPS o usar un servidor más robusto.
