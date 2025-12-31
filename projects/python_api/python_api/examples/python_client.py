import os
import requests
import json

"""Ejemplo sencillo de cliente Python para el endpoint /ai.

Configura opcionalmente las variables de entorno:
- WEB_API_KEY: clave para la API (si está configurada)
- API_URL: URL completa del endpoint (por defecto http://localhost:8081/ai)
"""

API_URL = os.getenv('API_URL', 'http://localhost:8081/ai')
WEB_API_KEY = os.getenv('WEB_API_KEY', '')

headers = {'Content-Type': 'application/json'}
if WEB_API_KEY:
    headers['X-API-Key'] = WEB_API_KEY

payload = {
    'prompt': 'Escribe un breve saludo en español y una línea sobre buenas prácticas.',
    'provider': 'local',
    'model': 'gpt2',
    'max_length': 80,
}

resp = requests.post(API_URL, headers=headers, json=payload)
print('Status:', resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception:
    print(resp.text)
