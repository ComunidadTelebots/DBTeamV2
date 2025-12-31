# Python API (python_api)

Esta carpeta contiene la pequeña API web usada por la aplicación web del proyecto. Aquí se explica cómo instalar, ejecutar y usar el nuevo endpoint `/ai` añadido para soportar generación de texto mediante distintos proveedores (local, Hugging Face o OpenAI).

**Resumen rápido**
- Endpoint principal: `POST /ai` (JSON: `prompt` requerido)
- Soporta `provider`: `local`, `huggingface`, `openai`

## Requisitos
- Python 3.10+ recomendado
- Redis (opcional, pero usado por la API para sesiones/colas)

Dependencias (ver `requirements.txt`):
- `fastapi`, `uvicorn`, `redis`, `cryptography`, `requests`, `python-dotenv`, `python-telegram-bot`, `uvloop`
- Para `provider: local` (opcional): `transformers`, `torch` — modelos locales necesitan recursos y pueden requerir GPU/CPU y espacio en disco.

## Variables de entorno importantes
- `WEB_API_KEY` — clave para proteger la API web (opcional: si no está, la API está abierta)
- `WEB_API_SECRET` — secreto usado para cifrar sesiones (opcional)
- `BOT_TOKEN` — token del bot Telegram (usado por endpoints de envío)
- `REDIS_URL` — URL de Redis (por defecto `redis://127.0.0.1:6379/0`)
- `HUGGINGFACE_API_KEY` — si usas `provider: huggingface`
- `OPENAI_API_KEY` — si usas `provider: openai`

## Instalar y ejecutar (PowerShell)
1. Crear entorno e instalar dependencias:
```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r python_api/requirements.txt
```

2. Setear variables necesarias y ejecutar la API (ejemplo PowerShell):
```powershell
setx WEB_API_KEY "tu_web_api_key"
setx BOT_TOKEN "tu_bot_token"
uvicorn python_api.app.main:app --host 0.0.0.0 --port 8081
```

Nota: en Linux/macOS usa `source .venv/bin/activate` y `export VAR=valor`.

## Endpoint `/ai`
POST `/ai` — cuerpo JSON mínimo:

- `prompt` (string) — texto a completar/generar (requerido)
- `provider` (string) — `local` (por defecto), `huggingface` o `openai`
- `model` (string) — nombre del modelo a usar (ej. `gpt2`, `gpt-2-large`, `EleutherAI/gpt-neo-125M`, etc.)
- Parámetros opcionales: `max_length`, `do_sample`, `top_k`, `num_return_sequences`, `parameters` (para HF)

Ejemplo: llamada básica usando `local` (curl):
```bash
curl -X POST http://localhost:8081/ai \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu_web_api_key" \
  -d '{"prompt":"Hola, ¿puedes resumir esto?","provider":"local","model":"gpt2","max_length":80}'
```

Proveedor `local`
- Usa `transformers.pipeline('text-generation', model=...)`. Recomendado usar modelos muy pequeños para pruebas (`gpt2`, `distilgpt2`) ya que los modelos grandes tardan en descargarse y requieren mucha memoria.
- Si `transformers` no está instalado el endpoint devolverá un error explicando que falta la dependencia.

Proveedor `huggingface`
- Reenvía la petición a `https://api-inference.huggingface.co/models/{model}` usando `HUGGINGFACE_API_KEY`.

Proveedor `openai`
- Reenvía a la ruta `v1/completions` de OpenAI usando `OPENAI_API_KEY`.

## Seguridad y límites
- La API usa `WEB_API_KEY` y/o sesiones cifradas para autorizar. Configura `WEB_API_KEY` para evitar exponer el endpoint públicamente.
- Si vas a permitir `provider: local` en producción, añade límites y controles para evitar que cualquier usuario descargue o cargue modelos pesados.

## Recomendaciones
- Para desarrollo: usar `provider: huggingface` con modelos pequeños o `provider: local` con `distilgpt2`/`gpt2`.
- Para producción: preferir un proveedor de inferencia gestionado (Hugging Face, OpenAI) o desplegar un servidor de inferencia controlado separado con límites.

## Problemas comunes
- Errores de memoria o tiempo de descarga al usar modelos locales: usa modelos más pequeños o una máquina con GPU/CPU adecuada.
- `transformers not installed`: instala `transformers` y `torch` o usa otro `provider`.

## Archivos relevantes
- `python_api/app/main.py` — lógica de la API web y endpoint `/ai`.
- `python_api/requirements.txt` — dependencias del servicio.

Si quieres, añado ejemplos adicionales con Python (requests) o una página web de prueba para llamar al endpoint desde la interfaz existente.

## Ejemplos de uso
He añadido ejemplos funcionales en `python_api/examples`:

- `python_api/examples/python_client.py` — script Python que llama a `/ai` usando la librería `requests`.
- `python_api/examples/powershell_example.ps1` — ejemplo PowerShell con `Invoke-RestMethod`.

Uso rápido (Python):
```powershell
setx WEB_API_KEY "tu_web_api_key"
python python_api/examples/python_client.py
```

Uso rápido (PowerShell):
```powershell
$env:WEB_API_KEY = "tu_web_api_key"
.\\python_api\\examples\\powershell_example.ps1
```

Estos ejemplos muestran llamadas básicas al endpoint `/ai`. Ajusta `provider` y `model` según tus necesidades.

# Python API scaffold for DBTeam

This folder contains a FastAPI-based scaffold implementing the web API endpoints from the Lua version:

- GET /messages
- GET /devices
- POST /devices/add
- POST /send
- POST /send_user
- POST /auth

Requirements: see `requirements.txt`.

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN='your_bot_token'
export WEB_API_SECRET='a_long_secret'
# optional: WEB_API_KEY, WEB_API_ORIGIN, WEB_API_PORT
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

Notes:
- Uses `cryptography` Fernet with key derived from `WEB_API_SECRET` to encrypt device tokens and sessions in Redis.
- Uses Redis keys compatible with the Lua version: `web:devices` (list), `web:outbox` (list), `web:messages` (list), `web:session:<token>`.
