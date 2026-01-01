import asyncio
import os
import sys

# Ensure local package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from python_bot.plugins import stream_torrent as st

class DummyMessage:
    async def reply_text(self, text):
        print('reply_text ->', text)

class DummyUser:
    def __init__(self, id):
        self.id = id

class DummyChat:
    def __init__(self, id):
        self.id = id

class DummyUpdate:
    def __init__(self, chat_id=12345, user_id=0):
        self.effective_chat = DummyChat(chat_id)
        self.effective_user = DummyUser(user_id)
        self.message = DummyMessage()

class DummyContext:
    def __init__(self, args=None):
        self.args = args or []
        self.bot = None

async def main():
    # Example magnet / infohash. We expect plugin to reply that libtorrent is required if not installed.
    upd = DummyUpdate(chat_id=12345, user_id=163103382)
    ctx = DummyContext(args=["magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567"])
    await st.stream_torrent_stream_cmd(upd, ctx)

if __name__ == '__main__':
    asyncio.run(main())
