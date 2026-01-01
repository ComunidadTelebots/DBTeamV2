# **DBTeamV2** #

[![Library](https://img.shields.io/badge/TDLib-beta-brightgreen.svg)](https://core.telegram.org/tdlib)
[![Telegram-cli](https://img.shields.io/badge/TDCli-Bitbucket-green.svg)](https://bitbucket.org/vysheng/tdcli)
[![Lua](https://img.shields.io/badge/Lua-5.2-blue.svg)](https://www.lua.org/)
[![Redis](https://img.shields.io/badge/Redis-3.2.8-red.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-GNU%20GPL--3-yellow.svg)](https://github.com/Josepdal/DBTeamV1/blob/master/LICENSE)


### An administration Telegram bot using Telegram-cli

DBTeamV2 is a powerful administration userbot with multiple components (bot, web UI, Python API).

This repository has been reorganized: active components live under the `projects/` folder:

- `projects/bot/python_bot` — Python bot, plugins and compatibility layers.
- `projects/web/web` — frontend (Telegram login + Telegram-like UI and i18n).
- `projects/python_api/python_api` — FastAPI backend (REST endpoints, TDLib client helpers).

Legacy Lua artifacts were ported or archived during migration; see `projects/bot/python_bot/legacy` for compatibility helpers.

The difference among the old [DBTeamV1](https://github.com/Josepdal/DBTeamV1) and [DBTeamV2](https://github.com/Josepdal/DBTeamV2) is that this one uses a much newer *Tg-Cli* with new stuff and also the bot has improved in usability, stability and has new functions.

# Summary

- Easy to setup and to update, no compilation needed.
- Uses a plugins system so you can easily configure or add what you need.
- Multilanguage and easy to add new languages.
- Has many funtions that normal bots are not able to do, e.g., remove messages.
- Advanced moderation system.
- Has privilege ranges (sudo, admin, mod, user).
- Simple and intuitive command usages.
- Compatible with most of recent added telegram additions.
- Really fast and stable.
- Up-to-date documentation at http://telegra.ph/DBTeamV2-Tutorial-English-02-26


# Installation

## Quick Installation (Recommended)

The easiest way to install DBTeamV2 with all dependencies is using the automated installation script:

```bash
git clone https://github.com/Josepdal/DBTeamV2.git
cd DBTeamV2
chmod +x install.sh
./install.sh
```

The script will automatically:
- Detect your Linux distribution (Debian/Ubuntu, Arch, Fedora)
- Install all system dependencies
- Install Lua dependencies via luarocks
- Download telegram-cli
- Optionally install Python API dependencies

After installation completes, you can start the bot:
```bash
./launch.sh # Will ask you for a phone number & confirmation code.
```

Quick start (scripts)
---------------------

There are convenience scripts to run the UI, API and bot for local testing.

1. Make the scripts executable:

```bash
chmod +x start_quick.sh stop_quick.sh
```

2. Create a minimal `.env` in the repo root with at least:

```bash
BOT_TOKEN="<your_bot_token>"
WEB_API_SECRET="change_me"
REDIS_HOST="127.0.0.1"
REDIS_PORT="6379"
```

3. Start services:

```bash
./start_quick.sh
```

Logs are written to `logs/` and PIDs to `pids/`. To stop everything:

```bash
./stop_quick.sh
```

Tip: copy the example env and edit it before running:

```bash
cp .env.example .env
# then edit .env and fill your BOT_TOKEN and secrets
```


## Manual Installation

If you prefer to install dependencies manually, follow the instructions for your distribution:

Debian/Ubuntu and derivatives:
```bash
# Tested on Ubuntu 16.04 and Debian 8.7.1 stable. (please use release "stable", isn't working on stretch/testing)
sudo apt-get install git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 make libstdc++6 g++-4.9 unzip tmux -y

# If you have errors (maybe you'll need this on Ubuntu)
sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y; sudo apt-get autoclean; sudo apt-get update
sudo apt-get install git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 make libstdc++6 g++-4.9 unzip libreadline-gplv2-dev libreadline5-dev tmux -y

# If your bot still not working, maybe you don't have installed gcc and openssl, check if you have both installed.
```

Arch:
```bash
sudo pacman -S yaourt
sudo yaourt -S git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 tmux
```

Fedora:
```bash
sudo dnf install git redis-server libconfig8-dev libjansson-dev lua5.2 liblua5.2-dev lua-lgi glib-2.0 libnotify-dev libssl-dev libssl1.0.0 tmux
```                   
---------------------------------

After installing the dependencies, lets install the bot:
```bash
 git clone https://github.com/Josepdal/DBTeamV2.git
 cd DBTeamV2
 chmod +x launch.sh
 ./launch.sh install # you can use the option --no-download and only configure DBTeam
 ./launch.sh # Will ask you for a phone number & confirmation code.
```

To update the bot, you must exit the Tg-Cli console:
```bash
quit
```
And execute the following command:
```bash
./launch.sh update
```
The code will be updated if there is something new.

You can also run the bot in a Tmux session if you want:
```bash
./launch.sh tmux # create a session tmux

./launch.sh attach # if you want back to tmux session

./launch.sh kill # close session tmux
```

DBTeamV2 Developers:
--------------------
[![https://telegram.me/Josepdal](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-Josepdal-blue.svg)](https://t.me/Josepdal)
[![https://telegram.me/Jarriz](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-Jarriz-blue.svg)](https://t.me/Jarriz)
[![https://telegram.me/iicc1](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-iicc1-blue.svg)](https://t.me/iicc1)

DBTeamV2 Channels:
--------------------
[![https://telegram.me/DBTeamEN](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-DBTeamEN-blue.svg)](https://t.me/DBTeamEN)
[![https://telegram.me/DBTeamES](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-DBTeamES-blue.svg)](https://t.me/DBTeamES)

Special thanks to:
==================
Yago Pérez and his telegram-bot
-------------------------------
[![https://telegram.me/Yago_Perez](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-Yago_Perez-blue.svg)](https://t.me/Yago_Perez)
[![https://github.com/yagop/telegram-bot](https://img.shields.io/badge/%F0%9F%92%AC_GitHub-Telegram_bot-green.svg)](https://github.com/yagop/telegram-bot)


Riccardo and his GroupButler
----------------------------
[![https://telegram.me/Riccardo](https://img.shields.io/badge/%F0%9F%92%AC_Telegram-bac0nnn-blue.svg)](https://t.me/bac0nnn)
[![https://github.com/RememberTheAir/GroupButler](https://img.shields.io/badge/%F0%9F%92%AC_GitHub-GroupButler-green.svg)](https://github.com/RememberTheAir/GroupButler)


vysheng and his new tg-cli
--------------------------
[![https://valtman.name/telegram-cli](https://img.shields.io/badge/%F0%9F%92%AC_WebPage-valtman.name-red.svg)](https://valtman.name/telegram-cli)
[![https://github.com/vysheng](https://img.shields.io/badge/%F0%9F%92%AC_GitHub-vysheng-green.svg)](https://github.com/vysheng)


rizaumami and his tdcli lib
---------------------------
[![https://github.com/rizaumami/tdcli.lua](https://img.shields.io/badge/%F0%9F%92%AC_GitHub-rizaumami-green.svg)](https://github.com/rizaumami/tdcli.lua)

Thanks to [@Reload_Life](https://t.me/Reload_Life) for [settings design](https://github.com/Reload-Life).

## Packaging for GitHub + Docker

This repository is prepared to avoid committing large binary assets. Large media files and `.torrent` files are excluded via `.gitignore`. If you need to preserve specific assets, upload them to GitHub Releases or an object storage bucket and use `scripts/fetch_assets.sh` to retrieve them.

Quick actions added by maintainers:

- `.gitignore` and `.gitattributes` — keep virtualenvs, caches and large assets out of the repo.
- `scripts/setup_ubuntu.sh` — create a Python virtualenv and install requirements on Ubuntu.
- `Dockerfile` and `scripts/build_docker.sh` — build an Ubuntu-based image for Docker Desktop.
- `scripts/fetch_assets.sh` — template for `curl`/`wget`/`aria2c` commands to download excluded assets.
- `.dockerignore` — keep Docker images small.

See `README_DOCKER.md` for Docker-specific instructions.

### Large files & setup

If you need to handle large model artifacts or serialized indexes, see `docs/large_files_cleanup.md` for safe, reversible steps to remove them from git history or keep them externally (S3/Drive). A helper script to download `ai_index.pkl` is available at `scripts/download_ai_index.ps1`.
