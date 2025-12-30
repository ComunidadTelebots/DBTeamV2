<#
Create a git branch `feature/tdlib` and add TDLib Docker support files.

Run this script from repository root in PowerShell. It requires `git` installed.
Usage: PowerShell -ExecutionPolicy Bypass -File .\tools\create_tdlib_branch.ps1
#>

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not in PATH. Install Git and re-run this script."
    exit 1
}

$branch = 'feature/tdlib'
Write-Host "Creating branch $branch"
git fetch --all
git checkout -b $branch

# Create Dockerfile.tdlib
$tdfile = 'docker/Dockerfile.tdlib'
if (-not (Test-Path (Split-Path $tdfile -Parent))) { New-Item -ItemType Directory -Path (Split-Path $tdfile -Parent) -Force | Out-Null }
@"
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential cmake git wget unzip \
  libssl-dev libsqlite3-dev libwebp-dev libopus-dev zlib1g-dev \
  liblua5.2-dev liblua5.2-0-dev pkg-config ca-certificates && rm -rf /var/lib/apt/lists/*

# Build TDLib
RUN git clone --depth 1 https://github.com/tdlib/td.git /tmp/td && mkdir -p /tmp/td/build && cd /tmp/td/build \
  && cmake -DCMAKE_BUILD_TYPE=Release .. \
  && cmake --build . --target install \
  && rm -rf /tmp/td

WORKDIR /app
COPY . /app

RUN luarocks install luasocket || true
RUN luarocks install luasec || true

EXPOSE 8080
CMD ["/bin/sh", "./launch.sh"]
"@ | Out-File -FilePath $tdfile -Encoding utf8 -Force

# Create docker-compose override for TDLib (optional)
$compose = 'docker/docker-compose-tdlib.yml'
if (-not (Test-Path (Split-Path $compose -Parent))) { New-Item -ItemType Directory -Path (Split-Path $compose -Parent) -Force | Out-Null }
@"
version: '3.8'
services:
  bot:
    build:
      context: ..
      dockerfile: Dockerfile.tdlib
    image: dbteamv2:tdlib
    volumes:
      - ..:/app
    environment:
      - TRANSLATE_PROVIDER=libre
    depends_on:
      - redis
  redis:
    image: redis:6
    restart: unless-stopped
"@ | Out-File -FilePath $compose -Encoding utf8 -Force

git add docker/Dockerfile.tdlib docker/docker-compose-tdlib.yml
git commit -m "feat(tdlib): add TDLib Dockerfile and compose override" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "No changes to commit or commit failed."
} else {
  Write-Host "Committed changes to branch $branch."
}

Write-Host "Branch $branch created and files added. Remember to push: git push -u origin $branch"
