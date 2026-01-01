import os

# Configuration loaded from environment variables. Set these in your shell or a .env file.
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEB_API_KEY = os.getenv('WEB_API_KEY')
WEB_API_SECRET = os.getenv('WEB_API_SECRET')
WEB_API_ORIGIN = os.getenv('WEB_API_ORIGIN')
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')
