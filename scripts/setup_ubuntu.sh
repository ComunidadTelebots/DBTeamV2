#!/usr/bin/env bash
set -euo pipefail

echo "Setting up DBTeamV2 on Ubuntu..."

# Ensure python3 and venv are available
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl wget aria2

# create virtualenv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
pip install --upgrade pip setuptools wheel

# install requirements for bot and python_api (if present)
if [ -f projects/bot/python_bot/requirements.txt ]; then
  pip install -r projects/bot/python_bot/requirements.txt
fi
if [ -f projects/python_api/python_api/requirements.txt ]; then
  pip install -r projects/python_api/python_api/requirements.txt
fi

echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Run the bot with: python projects/bot/python_bot/main.py"
