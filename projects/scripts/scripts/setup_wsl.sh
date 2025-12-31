#!/usr/bin/env bash
set -euo pipefail

# Minimal installer for WSL / Ubuntu to run DBTeamV2 python_api locally.
# Review before running.

echo "Starting DBTeamV2 WSL setup..."

# Update
sudo apt update
sudo apt upgrade -y

# Install core packages
sudo apt install -y python3 python3-venv python3-pip redis-server curl wget git openssl build-essential

# Start and enable Redis
sudo systemctl enable --now redis

# Optional: Docker (commented by default)
read -p "Install Docker (recommended for production)? [y/N]: " -r INSTALL_DOCKER
if [[ "$INSTALL_DOCKER" =~ ^[Yy]$ ]]; then
  sudo apt install -y ca-certificates curl gnupg lsb-release
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable\" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker $USER
  echo "Docker installed. You may need to re-login to use docker without sudo."
fi

# Clone repo if not present
REPO_DIR="$HOME/DBTeamV2"
if [ ! -d "$REPO_DIR" ]; then
  echo "Repo not found at $REPO_DIR. Cloning into $REPO_DIR"
  git clone https://github.com/<owner>/<repo>.git "$REPO_DIR" || true
fi

cd "$REPO_DIR" || exit 1

# Create venv and install requirements for python_api
if [ -d "python_api" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  if [ -f projects/python_api/python_api/requirements.txt ]; then
    pip install -r projects/python_api/python_api/requirements.txt
  fi
  echo "Virtualenv ready. To run the API:"
  echo "  cd $REPO_DIR/python_api && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
else
  echo "No python_api folder found. Please ensure the repo contains the python_api scaffold." >&2
fi

# Provide common env vars example
cat > .env.example <<'EOF'
REDIS_URL=redis://127.0.0.1:6379
WEB_API_SECRET=change_me
BOT_TOKEN=your-telegram-bot-token
WEB_API_KEY=optional_key
EOF

echo "Created .env.example. Copy to .env and set variables before running the API."

echo "Setup complete." 
