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
