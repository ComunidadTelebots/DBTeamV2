import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'projects', 'bot'))
from python_bot import storage
print(json.dumps(storage.get_pending_torrents(163103382), ensure_ascii=False))
