import asyncio
import os
import sys
import importlib.util

# load module from path
path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'plugins', 'stream_torrent.py'))
spec = importlib.util.spec_from_file_location('st_safe', path)
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

# Patch _send_parts_bot to avoid Telegram API calls
async def fake_send_parts(context, chat_id, filepath, orig_name, chunk_size=10*1024*1024):
    size = os.path.getsize(filepath)
    print(f'fake_send_parts called: chat_id={chat_id}, file={orig_name}, size={size} bytes')

st._send_parts_bot = fake_send_parts

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
    url = 'https://httpbin.org/bytes/2048'
    upd = DummyUpdate(chat_id=99999, user_id=0)
    ctx = DummyContext(args=[url])
    await st.download_torrent_cmd(upd, ctx)

if __name__ == '__main__':
    asyncio.run(main())
