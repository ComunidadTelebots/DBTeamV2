"""Stream-upload files into a chat by splitting them into parts and sending sequentially.

Commands:
- /stream_file (reply to a file) : split the replied file and upload parts
- /stream_file_url <url> : download the URL and upload parts

Notes:
- This sends multiple documents named with .partN suffix; receivers must reassemble.
- Be mindful of Telegram upload limits and rate limits; choose chunk_size accordingly.
"""
import asyncio
import io
import hashlib
import math
import os
import tempfile
from typing import Any

import requests
from python_bot.storage import storage
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None


def setup(bot):
    bot.register_command('stream_file', stream_file_cmd, 'Stream upload of a replied file', plugin='stream_file')
    bot.register_command('stream_file_url', stream_file_url_cmd, 'Stream upload from URL', plugin='stream_file')
    bot.register_command('stream_start', stream_start_cmd, 'Open a streaming session for this chat', plugin='stream_file')
    bot.register_command('stream_stop', stream_stop_cmd, 'Close/abort a streaming session', plugin='stream_file')
    # auto-detect uploaded files and start retransmission
    bot.register_message_handler('document|video|audio|photo', auto_file_handler, plugin='stream_file')


async def _download_url(url: str, path: str):
    loop = asyncio.get_running_loop()

    def _download():
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)

    await loop.run_in_executor(None, _download)


async def _download_telegram_file(bot_obj, file_id: str, path: str):
    # bot_obj is PTB Bot instance
    f = await bot_obj.get_file(file_id)
    await f.download_to_drive(path)


async def _send_parts(context, chat_id: int, filepath: str, orig_name: str, chunk_size: int = 10 * 1024 * 1024):
    file_size = os.path.getsize(filepath)
    parts = math.ceil(file_size / chunk_size)
    status_msg = await context.bot.send_message(chat_id=chat_id, text=f'Uploading {orig_name} in {parts} parts...')
    with open(filepath, 'rb') as fh:
        idx = 1
        while True:
            # check for abort flag on each chunk
            sess = storage.get_stream_session(chat_id)
            if sess and sess.get('abort') == '1':
                try:
                    await status_msg.edit_text(f'Upload aborted at part {idx}/{parts}')
                except Exception:
                    pass
                return
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            bio = io.BytesIO(chunk)
            bio.name = f'{orig_name}.part{idx}'
            try:
                await context.bot.send_document(chat_id=chat_id, document=bio, filename=bio.name, caption=f'Part {idx}/{parts}')
            except Exception:
                # fallback: send via requests (rare)
                try:
                    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                    files = {'document': (bio.name, bio)}
                    requests.post(f'https://api.telegram.org/bot{token}/sendDocument', data={'chat_id': chat_id, 'caption': f'Part {idx}/{parts}'}, files=files, timeout=30)
                except Exception:
                    pass
            idx += 1
            # update status
            try:
                await status_msg.edit_text(f'Uploaded part {idx-1}/{parts}')
            except Exception:
                pass
    try:
        await status_msg.edit_text(f'Upload complete: {orig_name} ({parts} parts)')
    except Exception:
        pass


async def stream_start_cmd(update: Any, context: Any):
    chat_id = update.effective_chat.id
    args = context.args or []
    name = args[0] if args else None
    storage.start_stream_session(chat_id, name)
    await update.message.reply_text(f'Streaming session started{f" ({name})" if name else ""}. Use /stream_stop to end or abort.')


async def stream_stop_cmd(update: Any, context: Any):
    chat_id = update.effective_chat.id
    # stop (set abort to 1 and remove session)
    storage.abort_stream_session(chat_id)
    storage.stop_stream_session(chat_id)
    await update.message.reply_text('Streaming session stopped/aborted.')


async def stream_file_cmd(update: Any, context: Any):
    # reply-to-message expected with document, audio, video
    args = context.args or []
    # allow optional target: 'private'|'me' to send to requester privately, or @username/chat_id
    target_arg = args[0] if args else None
    if not update.message.reply_to_message:
        await update.message.reply_text('Reply to a message containing a file (document, audio, or video) and run /stream_file [target]')
        return
    msg = update.message.reply_to_message
    file_field = None
    filename = 'file'
    if getattr(msg, 'document', None):
        file_field = msg.document.file_id
        filename = getattr(msg.document, 'file_name', filename)
    elif getattr(msg, 'audio', None):
        file_field = msg.audio.file_id
        filename = getattr(msg.audio, 'file_name', filename)
    elif getattr(msg, 'video', None):
        file_field = msg.video.file_id
        filename = getattr(msg.video, 'file_name', filename)
    else:
        await update.message.reply_text('Replied message does not contain a supported file type')
        return

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    # determine destination chat id
    dest_chat = update.effective_chat.id
    if target_arg:
        targ = target_arg.strip()
        if targ.lower() in ('private', 'me'):
            dest_chat = update.effective_user.id
        else:
            # try username (@name) or numeric id
            if targ.startswith('@'):
                try:
                    user = await context.bot.get_chat(targ)
                    dest_chat = user.id
                except Exception:
                    pass
            else:
                try:
                    dest_chat = int(targ)
                except Exception:
                    pass

    try:
        await _download_telegram_file(context.bot, file_field, tmp.name)
        await _send_parts(context, dest_chat, tmp.name, filename)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


async def stream_file_url_cmd(update: Any, context: Any):
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /stream_file_url <url> [target]')
        return
    url = args[0]
    target_arg = args[1] if len(args) > 1 else None
    orig_name = os.path.basename(url.split('?')[0]) or 'file'
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    # determine destination
    dest_chat = update.effective_chat.id
    if target_arg:
        targ = target_arg.strip()
        if targ.lower() in ('private', 'me'):
            dest_chat = update.effective_user.id
        else:
            if targ.startswith('@'):
                try:
                    user = await context.bot.get_chat(targ)
                    dest_chat = user.id
                except Exception:
                    pass
            else:
                try:
                    dest_chat = int(targ)
                except Exception:
                    pass

    try:
        await update.message.reply_text(f'Downloading {url}...')
        await _download_url(url, tmp.name)
        await _send_parts(context, dest_chat, tmp.name, orig_name)
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


async def auto_file_handler(update: Any, context: Any):
    """Automatic handler for incoming files: start a streaming session and retransmit parts.

    Uses `update.effective_message` so it works for `message`, `edited_message` and `channel_post`.
    """
    msg = getattr(update, 'effective_message', None)
    chat = getattr(update, 'effective_chat', None)
    user = getattr(update, 'effective_user', None)
    if msg is None or chat is None:
        return
    chat_id = chat.id
    # mark session
    storage.start_stream_session(chat_id, name='auto')
    storage.inc_stream_downloaders(chat_id)
    file_field = None
    filename = 'file'
    if getattr(msg, 'document', None):
        file_field = msg.document.file_id
        filename = getattr(msg.document, 'file_name', filename)
    elif getattr(msg, 'audio', None):
        file_field = msg.audio.file_id
        filename = getattr(msg.audio, 'file_name', filename)
    elif getattr(msg, 'video', None):
        file_field = msg.video.file_id
        filename = getattr(msg.video, 'file_name', filename)
    elif getattr(msg, 'photo', None):
        # photos: pick largest size
        sizes = msg.photo
        if sizes:
            file_field = sizes[-1].file_id
            # use message id if available, else thread id
            mid = getattr(msg, 'message_id', None) or getattr(msg, 'message_thread_id', None) or ''
            filename = f'photo_{mid}.jpg'
    else:
        try:
            await (msg.reply_text if hasattr(msg, 'reply_text') else context.bot.send_message)(chat_id=chat_id, text='Unsupported file type for auto-stream')
        except Exception:
            pass
        storage.stop_stream_session(chat_id)
        return

    # if torrent file, delegate to torrent plugin if available
    if filename and filename.lower().endswith('.torrent'):
        # decide whether to auto-start streaming: if uploaded in a group and
        # the uploader is the chat creator (owner), start automatically.
        try:
            should_auto = False
            ctype = chat.type if chat else None
            sender = getattr(msg, 'from_user', None) or user
            # chat creator in groups/supergroups
            if ctype in ('group', 'supergroup') and sender is not None:
                try:
                    cm = await context.bot.get_chat_member(chat.id, sender.id)
                    if getattr(cm, 'status', None) == 'creator':
                        should_auto = True
                except Exception:
                    # if we cannot determine membership, default to not auto-start
                    should_auto = False
            else:
                # in private chats, auto-start for the uploader (owner account behavior)
                should_auto = True

            # additionally allow explicit owner by environment variable or storage role
            try:
                import os
                owner_env = os.getenv('BOT_OWNER_ID') or os.getenv('OWNER_ID')
                if owner_env and sender is not None:
                    try:
                        if int(owner_env) == getattr(sender, 'id', None):
                            should_auto = True
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if sender is not None and storage.get_role(getattr(sender, 'id', None)) == 'owner':
                    should_auto = True
            except Exception:
                pass

            import python_bot.plugins.stream_torrent as st
            if should_auto:
                await st.stream_torrent_file_cmd(update, context)
                return
            # otherwise, do not auto-start; fall through to normal cover+send behavior
        except Exception:
            pass

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        await _download_telegram_file(context.bot, file_field, tmp.name)
        # compute file hash to track forwards
        try:
            h = hashlib.sha256()
            with open(tmp.name, 'rb') as _f:
                for chunk in iter(lambda: _f.read(8192), b''):
                    if not chunk:
                        break
                    h.update(chunk)
            file_hash = h.hexdigest()
        except Exception:
            file_hash = None

        # send cover image with counters
        counters = storage.get_stream_counters(chat_id)
        # attempt to create a small cover image
        if Image is not None:
            try:
                W, H = 400, 120
                im = Image.new('RGB', (W, H), color=(30, 30, 30))
                draw = ImageDraw.Draw(im)
                title = filename[:40]
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                draw.text((10, 10), f'Detected: {title}', fill=(255,255,255), font=font)
                draw.text((10, 40), f'Downloaders: {counters.get("downloaders",0)}', fill=(200,200,255), font=font)
                draw.text((10, 65), f'Uploaders: {counters.get("uploaders",0)}', fill=(200,255,200), font=font)
                bio = io.BytesIO()
                im.save(bio, format='PNG')
                bio.seek(0)
                await context.bot.send_photo(chat_id=chat_id, photo=bio, caption=f'Streaming: {title}')
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=f'Streaming: {filename} — dl={counters.get("downloaders",0)} up={counters.get("uploaders",0)}')
        else:
            await context.bot.send_message(chat_id=chat_id, text=f'Streaming: {filename} — dl={counters.get("downloaders",0)} up={counters.get("uploaders",0)}')

        storage.inc_stream_uploaders(chat_id)
        await _send_parts(context, chat_id, tmp.name, filename)
        # mark as forwarded to origin
        try:
            if file_hash:
                storage.record_forward(file_hash, chat_id)
        except Exception:
            pass
        storage.dec_stream_uploaders(chat_id)

        # Re-send to registered chats (if any). Skip origin and banned chats.
        try:
            registered = storage.list_chats() or []
            for dest in registered:
                try:
                    if dest == chat_id:
                        continue
                    if storage.is_banned(dest):
                        continue
                    # skip if we've already forwarded this file to dest
                    if file_hash and storage.has_been_forwarded(file_hash, dest):
                        continue
                    # mark session for dest
                    storage.start_stream_session(dest, name='auto-forward')
                    storage.inc_stream_uploaders(dest)
                    # send a small cover to destination
                    try:
                        if Image is not None:
                            W, H = 360, 100
                            im2 = Image.new('RGB', (W, H), color=(28, 28, 28))
                            draw2 = ImageDraw.Draw(im2)
                            draw2.text((8, 8), f'Reenviando: {filename[:30]}', fill=(230,230,230))
                            draw2.text((8, 36), f'From chat: {chat_id}', fill=(180,180,240))
                            bio2 = io.BytesIO()
                            im2.save(bio2, format='PNG')
                            bio2.seek(0)
                            await context.bot.send_photo(chat_id=dest, photo=bio2, caption=f'Forwarded: {filename}')
                        else:
                            await context.bot.send_message(chat_id=dest, text=f'Forwarded: {filename} (from {chat_id})')
                    except Exception:
                        pass
                    await _send_parts(context, dest, tmp.name, filename)
                    # record forwarded
                    try:
                        if file_hash:
                            storage.record_forward(file_hash, dest)
                    except Exception:
                        pass
                except Exception:
                    # continue with other destinations
                    pass
                finally:
                    try:
                        storage.dec_stream_uploaders(dest)
                    except Exception:
                        pass
                    try:
                        storage.stop_stream_session(dest)
                    except Exception:
                        pass
        except Exception:
            pass
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        storage.dec_stream_downloaders(chat_id)
        storage.stop_stream_session(chat_id)
