FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    ffmpeg \
    ca-certificates \
    curl \
    wget \
    aria2 \
    git \
 && rm -rf /var/lib/apt/lists/*


# Create app user
RUN useradd -m appuser
ARG ENV=appuser
ENV ENV=${ENV}
WORKDIR /home/$ENV/app

# Copy project files (dockerignore will filter large assets)
COPY . /home/$ENV/app
RUN chown -R $ENV:$ENV /home/$ENV/app

USER $ENV

# Create and activate venv, install requirements from unified file
RUN python3 -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    if [ -f /home/$ENV/app/requirements.docker.txt ]; then \
        pip install -r /home/$ENV/app/requirements.docker.txt; \
    else \
        pip install -r /home/$ENV/app/requirements.txt; \
    fi

ENV PATH="/home/$ENV/app/.venv/bin:$PATH"

# Expose ports used by web UI and stats API
EXPOSE 8000 8081

# Default command: run bot runner
CMD ["/bin/bash", "-lc", "python3 projects/bot/python_bot/main.py"]


# --- Node.js, build tools y node-pre-gyp para webtorrent-hybrid (pyratebye) ---
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    python3 \
    python3-pip \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g node-pre-gyp \
    && npm install -g webtorrent-hybrid \
    && rm -rf /var/lib/apt/lists/*
USER appuser
