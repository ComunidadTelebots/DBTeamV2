FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and common tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    ca-certificates \
    curl \
    wget \
    aria2 \
    git \
 && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m appuser
WORKDIR /home/appuser/app

# Copy project files (dockerignore will filter large assets)
COPY . /home/appuser/app
RUN chown -R appuser:appuser /home/appuser/app

USER appuser

# Create and activate venv, install requirements (if present)
RUN python3 -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip setuptools wheel || true

# Install requirements if files exist
RUN if [ -f projects/bot/python_bot/requirements.txt ]; then . .venv/bin/activate && pip install -r projects/bot/python_bot/requirements.txt; fi
RUN if [ -f projects/python_api/python_api/requirements.txt ]; then . .venv/bin/activate && pip install -r projects/python_api/python_api/requirements.txt; fi

ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Expose ports used by web UI and stats API
EXPOSE 8000 8081

# Default command: run bot runner
CMD ["/bin/bash", "-lc", "python3 projects/bot/python_bot/main.py"]
