#!/usr/bin/env bash
set -euo pipefail

# Installer for Ubuntu/Linux to set up a virtualenv, install requirements,
# download GPT-2 into a local models directory and launch the AI server.
# Usage: sudo apt install python3-venv -y  # if python3-venv missing
# ./python_api/install_ai_ubuntu.sh [MODEL_DIR]

MODEL_DIR="${1:-$(pwd)/models}"
PYTHON=${PYTHON:-python3}
VENV_DIR=".venv_ai"

echo "Using python: $PYTHON"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python not found. Install python3 first." >&2
  exit 1
fi

echo "Creating virtualenv in $VENV_DIR..."
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
echo "Installing Python packages from python_api/requirements_ai.txt..."
pip install -r python_api/requirements_ai.txt

echo "Ensuring model directory exists: $MODEL_DIR"
mkdir -p "$MODEL_DIR"

echo "Downloading 'gpt2' model into $MODEL_DIR (this may take a while)..."
python - <<PY
from transformers import AutoTokenizer, AutoModelForCausalLM
from pathlib import Path
cache_dir = Path(r"$MODEL_DIR")
cache_dir.mkdir(parents=True, exist_ok=True)
AutoTokenizer.from_pretrained('gpt2', cache_dir=str(cache_dir))
AutoModelForCausalLM.from_pretrained('gpt2', cache_dir=str(cache_dir))
print('Downloaded gpt2 to', cache_dir)
PY

echo "Starting AI server in background (logs: python_api/ai_server.log)..."
PYMODEL_DIR="$MODEL_DIR" nohup "$VENV_DIR/bin/python" python_api/ai_server.py --host 127.0.0.1 --port 8081 --model-dir "$MODEL_DIR" > python_api/ai_server.log 2>&1 &
echo "AI server launched. Check python_api/ai_server.log for progress." 
