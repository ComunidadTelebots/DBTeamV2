FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system deps (Lua 5.2, build tools, redis server, luarocks and libs)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    git \
    redis-server \
    lua5.2 \
    lua5.2-dev \
    liblua5.2-dev \
    luarocks \
    libconfig-dev \
    libjansson-dev \
    lua-lgi \
    libnotify-dev \
    libssl-dev \
    build-essential \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install common Lua rocks used by the project
RUN luarocks install luasocket || true
RUN luarocks install luasec || true
RUN luarocks install redis-lua || true
RUN luarocks install serpent || true

WORKDIR /app

# Copy repository into image
COPY . /app

# Fetch upstream gwtweb frontend (if present) and copy into web/gwtweb
RUN git clone --depth 1 https://github.com/ComunidadTelebots/DBTeamV2 /tmp/gwtrepo || true \
 && if [ -d /tmp/gwtrepo/gwtweb ]; then mkdir -p /app/web/gwtweb && cp -r /tmp/gwtrepo/gwtweb/* /app/web/gwtweb; fi \
 && rm -rf /tmp/gwtrepo

# Add start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8081 8001

CMD ["/start.sh"]
# Dockerfile para DBTeamV2
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Lua 5.2 y dependencias comunes
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    bash \
    lua5.2 \
    luarocks \
    build-essential \
    libssl-dev \
    ca-certificates \
    curl \
    git \
  && rm -rf /var/lib/apt/lists/*

# Instalar módulos Lua necesarios
RUN luarocks install luasocket || true
RUN luarocks install luasec || true

WORKDIR /app
COPY . /app

# Ensure launch script is executable and uses bash
RUN chmod +x /app/launch.sh || true
RUN sed -i 's/\r$//' /app/launch.sh || true

# Exponer puertos si el bot web usa alguno (ajusta si es necesario)
EXPOSE 8080

# Ejecutar el script de lanzamiento (asegúrate de que launch.sh tenga permisos ejecutables)
CMD ["/bin/bash", "./launch.sh"]
