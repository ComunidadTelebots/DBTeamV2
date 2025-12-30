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
