import os
from typing import Optional

BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
WEB_API_KEY: str = os.getenv('WEB_API_KEY', '')
WEB_API_SECRET: str = os.getenv('WEB_API_SECRET', '')
WEB_API_ORIGIN: str = os.getenv('WEB_API_ORIGIN', '*')
WEB_API_PORT: int = int(os.getenv('WEB_API_PORT', '8081'))

REDIS_URL: str = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
