# Instala TDLib (libtdjson) y python-tdlib en Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y git cmake gperf zlib1g-dev libssl-dev libcurl4-openssl-dev liblzma-dev

git clone --depth=1 --branch v1.8.27 https://github.com/tdlib/td.git
cd td
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --target install -j$(nproc)

# Esto instalará libtdjson.so en /usr/local/lib
# Puedes necesitar exportar LD_LIBRARY_PATH o mover la librería a /usr/lib

# Instala dependencias Python
cd ../../
pip install -r requirements.txt

# Variables de entorno necesarias para el backend
# Sustituye por tus valores reales
set TD_API_ID=TU_API_ID
set TD_API_HASH=TU_API_HASH
set TD_PHONE=+34123456789

# Inicia el backend normalmente
# uvicorn main:app --host 0.0.0.0 --port 8000
