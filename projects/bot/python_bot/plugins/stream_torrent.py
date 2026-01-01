"""Torrent-compatible streaming: download torrent/magnet and upload parts to chat.

Commands:
- /stream_torrent <magnet_or_torrent_url>
- /stream_torrent_file (reply to a .torrent file)

Attempts to use python-libtorrent (preferred). If unavailable, falls back to calling
`aria2c` CLI to download the torrent.
"""
import asyncio
import io
import math
import os
import subprocess
import tempfile
import sys
from typing import Any
import hashlib

try:
    import libtorrent as lt
except Exception:
    lt = None

import requests
from python_bot.storage import storage
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None
import traceback
from datetime import datetime
import re
import time


def _log_exception(exc: Exception, note: str = ''):
    try:
        tb = traceback.format_exc()
        ts = datetime.utcnow().isoformat()
        # write log to repository root bot.log (robust when cwd differs)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        logpath = os.path.join(repo_root, 'bot.log')
        with open(logpath, 'a', encoding='utf-8') as lf:
            lf.write(f"[{ts}] stream_torrent exception {note}: {tb}\n")
    except Exception:
        pass


def _get_logpath() -> str:
    return os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')), 'bot.log')


# Active torrents registry for syncing with web UI (/torrents API)
# keys: id -> { 'id': id, 'chat_id': int, 'name': str, 'status': 'downloading'|'done'|'aborted'|'error', 'started_at': ts, 'path': path_or_empty }
ACTIVE_TORRENTS = {}


def _extract_infohash_from_magnet(s: str) -> str:
    m = re.search(r"xt=urn:btih:([A-Fa-f0-9]{40}|[A-Z2-7]{32})", s)
    if not m:
        return ''
    h = m.group(1)
    # normalize: if base32, return as-is; if hex, lowercase
    if len(h) == 40:
        return h.lower()
    return h.upper()


def _make_torrent_id(s: str) -> str:
    # prefer infohash when magnet; else fallback to sha1 of input
    ih = _extract_infohash_from_magnet(s)
    if ih:
        return ih
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def stop_torrent(tid: str) -> bool:
    """Mark a torrent as aborted/stopped. Returns True if found."""
    try:
        rec = ACTIVE_TORRENTS.get(tid)
        if not rec:
            return False
        rec['status'] = 'aborted'
        # signal stream session abort for related chat if present
        try:
            cid = rec.get('chat_id')
            if cid:
                storage.abort_stream_session(int(cid))
        except Exception:
            pass
        return True
    except Exception:
        return False


async def send_message(bot, chat_id: int, text: str, **kwargs):
    """Send message and log sending/sent status to repo bot.log."""
    ts = datetime.utcnow().isoformat()
    logpath = _get_logpath()
    try:
        with open(logpath, 'a', encoding='utf-8') as lf:
            lf.write(f"[{ts}] sending message to {chat_id}: {text[:200]}\n")
    except Exception:
        pass
    try:
        msg = await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        try:
            with open(logpath, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] sent message id={getattr(msg, 'message_id', None)} chat={chat_id}\n")
        except Exception:
            pass
        return msg
    except Exception as e:
        _log_exception(e, note=f'send_message chat={chat_id}')
        raise


async def send_document(bot, chat_id: int, document, filename: str = None, caption: str = None, **kwargs):
    ts = datetime.utcnow().isoformat()
    logpath = _get_logpath()
    try:
        with open(logpath, 'a', encoding='utf-8') as lf:
            lf.write(f"[{ts}] sending document to {chat_id}: {filename}\n")
    except Exception:
        pass
    try:
        msg = await bot.send_document(chat_id=chat_id, document=document, filename=filename, caption=caption, **kwargs)
        try:
            with open(logpath, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] sent document id={getattr(msg, 'message_id', None)} chat={chat_id}\n")
        except Exception:
            pass
        return msg
    except Exception as e:
        # fallback via HTTP will be attempted by caller; log and re-raise
        _log_exception(e, note=f'send_document chat={chat_id} filename={filename}')
        raise


async def send_photo(bot, chat_id: int, photo, caption: str = None, **kwargs):
    ts = datetime.utcnow().isoformat()
    logpath = _get_logpath()
    try:
        with open(logpath, 'a', encoding='utf-8') as lf:
            lf.write(f"[{ts}] sending photo to {chat_id}\n")
    except Exception:
        pass
    try:
        msg = await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, **kwargs)
        try:
            with open(logpath, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] sent photo id={getattr(msg, 'message_id', None)} chat={chat_id}\n")
        except Exception:
            pass
        return msg
    except Exception as e:
        _log_exception(e, note=f'send_photo chat={chat_id}')
        raise


async def send_video(bot, chat_id: int, video, caption: str = None, **kwargs):
    ts = datetime.utcnow().isoformat()
    logpath = _get_logpath()
    try:
        with open(logpath, 'a', encoding='utf-8') as lf:
            lf.write(f"[{ts}] sending video to {chat_id}\n")
    except Exception:
        pass
    try:
        msg = await bot.send_video(chat_id=chat_id, video=video, caption=caption, **kwargs)
        try:
            with open(logpath, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] sent video id={getattr(msg, 'message_id', None)} chat={chat_id}\n")
        except Exception:
            pass
        return msg
    except Exception as e:
        _log_exception(e, note=f'send_video chat={chat_id}')
        raise


def setup(bot):
    # write a small marker to bot.log so live-reload tests can detect setup runs
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
        with open(os.path.join(repo_root, 'bot.log'), 'a', encoding='utf-8') as lf:
            lf.write(f"[live_reload_test] stream_torrent.setup invoked at {int(time.time())}\n")
    except Exception:
        pass
    bot.register_command('stream_torrent', stream_torrent_cmd, 'Download torrent/magnet and stream parts', plugin='stream_torrent')
    bot.register_command('stream_torrent_file', stream_torrent_file_cmd, 'Reply to a .torrent file to stream it', plugin='stream_torrent')
    bot.register_command('stream_torrent_stream', stream_torrent_stream_cmd, 'Stream while downloading (requires libtorrent)', plugin='stream_torrent')
    bot.register_command('download_torrent', download_torrent_cmd, 'Download torrent/magnet and upload file parts', plugin='stream_torrent')
    bot.register_command('stream_torrent_stop', stream_torrent_stop_cmd, 'Stop/abort a streaming torrent session', plugin='stream_torrent')
    bot.register_command('cover', cover_cmd, 'Generate a cover for a magnet/infohash', plugin='stream_torrent')
    bot.register_command('allow_send', allow_send_cmd, 'Allow a user to let bot post origin messages in this chat (reply to user or pass user_id)', plugin='stream_torrent')
    bot.register_command('disallow_send', disallow_send_cmd, 'Remove allow to post origin messages (reply or user_id)', plugin='stream_torrent')
    # automatically handle uploaded .torrent files: start download when a .torrent is sent
    try:
        bot.register_message_handler('document', handle_torrent_document, plugin='stream_torrent')
    except Exception:
        # older runtimes may not support message handler registration
        pass
    # add user-facing commands to manage pending torrents sent in private
    async def mytorrents_cmd(update: Any, context: Any):
        user = update.effective_user
        if not user:
            return
        lst = storage.get_pending_torrents(user.id)
        if not lst:
            await update.message.reply_text('No tienes torrents pendientes.')
            return
        # build message with action buttons: Send to chat, Open in Web UI
        from urllib.parse import quote_plus
        mw_url = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000/multimedia.html'
        host_api = os.getenv('STATS_API_URL') or 'http://127.0.0.1:8081'
        reply_lines = []
        buttons = []
        for i, e in enumerate(lst):
            fn = e.get('filename') or os.path.basename(e.get('path') or '')
            ts = e.get('uploaded_at') or 0
            # direct pending file URL via stats API
            file_url = f"{host_api}/pending?user={user.id}&file={quote_plus(fn)}"
            web_ui_link = f"{mw_url}"
            reply_lines.append(f'{i}: {fn}')
            buttons.append((i, file_url, web_ui_link))
        # send a text summary
        await update.message.reply_text('Torrents pendientes:\n' + '\n'.join(reply_lines))
        # send one message per pending with inline buttons
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            for idx, furl, wlink in buttons:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton('Enviar a este chat', callback_data=f'sendpending:{idx}'), InlineKeyboardButton('Abrir en Web UI', url=f'{wlink}?torrent_url={quote_plus(furl)}')]])
                await update.message.reply_text(f'[{idx}]', reply_markup=kb)
        except Exception:
            # fallback: include URLs in plain text
            for idx, furl, wlink in buttons:
                await update.message.reply_text(f'[{idx}] {furl} — {wlink}')

    async def startpending_cmd(update: Any, context: Any):
        user = update.effective_user
        if not user:
            return
        args = context.args or []
        if not args:
            await update.message.reply_text('Usage: /startpending <index>')
            return
        try:
            idx = int(args[0])
        except Exception:
            await update.message.reply_text('Index must be a number')
            return
        lst = storage.get_pending_torrents(user.id)
        if idx < 0 or idx >= len(lst):
            await update.message.reply_text('Index out of range')
            return
        entry = lst[idx]
        path = entry.get('path')
        if not path or not os.path.exists(path):
            await update.message.reply_text('Torrent file not found on server')
            return
        # start download using existing code path: call stream_torrent_file_cmd flow by simulating a reply
        try:
            # remove from pending first
            ok = storage.remove_pending_torrent(user.id, idx)
            await update.message.reply_text(f'Iniciando descarga de {entry.get("filename")}...')
            # trigger download by calling download_torrent_cmd with args
            class CtxObj: pass
            obj = CtxObj()
            obj.args = [path]
            await download_torrent_cmd(update, obj)
        except Exception as e:
            _log_exception(e, note='startpending_cmd')
            await update.message.reply_text(f'Error iniciando descarga: {e}')

    try:
        bot.register_command('mytorrents', mytorrents_cmd, 'List your pending torrents (private messages)', plugin='stream_torrent')
        bot.register_command('startpending', startpending_cmd, 'Start a pending torrent by index', plugin='stream_torrent')
    except Exception:
        pass
    # inline: list active torrents and allow quick-stop via sending /stream_torrent_stop <id>
    async def inline_torrents_handler(update: Any, context: Any):
        iq = getattr(update, 'inline_query', None)
        if iq is None:
            return
        try:
            from telegram import InlineQueryResultArticle, InputTextMessageContent
            results = []
            # Add a helper entry to open multimedia web UI
            mw_url = os.getenv('WEBAPP_URL') or 'http://127.0.0.1:8000/multimedia.html'
            results.append(InlineQueryResultArticle(id='webui', title='Open multimedia web UI', input_message_content=InputTextMessageContent(f'Open multimedia: {mw_url}'), description='Open the multimedia web UI'))
            # list active torrents
            for t in list(ACTIVE_TORRENTS.values()):
                tid = t.get('id')
                name = (t.get('name') or '')[:80]
                desc = f"{t.get('status') or ''} — chat {t.get('chat_id') or ''}"
                content = InputTextMessageContent(f"/stream_torrent_stop {tid}")
                results.append(InlineQueryResultArticle(id=str(tid), title=name or tid, input_message_content=content, description=desc))
            await iq.answer(results, cache_time=3)
        except Exception:
            pass

    try:
        bot.register_inline_handler(inline_torrents_handler, plugin='stream_torrent')
    except Exception:
        pass


async def allow_send_cmd(update: Any, context: Any):
    """Allow a user to have the bot post origin/chat-visible messages triggered by their uploads.

    Usage: reply to a user with /allow_send or: /allow_send <user_id>
    Only `owner` or `admin` roles can grant this.
    """
    sender = update.effective_user
    if not sender:
        return
    role = storage.get_role(sender.id)
    if role not in ('owner', 'admin'):
        await update.message.reply_text('Permission denied')
        return
    # get target
    target_id = None
    if update.message.reply_to_message and getattr(update.message.reply_to_message, 'from', None):
        target_id = getattr(update.message.reply_to_message, 'from').id
    else:
        args = context.args or []
        if args:
            try:
                target_id = int(args[0])
            except Exception:
                await update.message.reply_text('Specify a numeric user_id or reply to a user')
                return
    if not target_id:
        await update.message.reply_text('No target user')
        return
    storage.add_allowed_sender(update.effective_chat.id, target_id)
    await update.message.reply_text(f'User {target_id} allowed to post origin messages in this chat')


async def disallow_send_cmd(update: Any, context: Any):
    """Revoke allow_send for a user. Usage like /allow_send."""
    sender = update.effective_user
    if not sender:
        return
    role = storage.get_role(sender.id)
    if role not in ('owner', 'admin'):
        await update.message.reply_text('Permission denied')
        return
    target_id = None
    if update.message.reply_to_message and getattr(update.message.reply_to_message, 'from', None):
        target_id = getattr(update.message.reply_to_message, 'from').id
    else:
        args = context.args or []
        if args:
            try:
                target_id = int(args[0])
            except Exception:
                await update.message.reply_text('Specify a numeric user_id or reply to a user')
                return
    if not target_id:
        await update.message.reply_text('No target user')
        return
    storage.remove_allowed_sender(update.effective_chat.id, target_id)
    await update.message.reply_text(f'User {target_id} disallowed to post origin messages in this chat')


async def _send_parts_bot(context, chat_id: int, filepath: str, orig_name: str, chunk_size: int = 10 * 1024 * 1024):
    file_size = os.path.getsize(filepath)
    parts = math.ceil(file_size / chunk_size)
    status_msg = await context.bot.send_message(chat_id=chat_id, text=f'Uploading {orig_name} in {parts} parts...')
    with open(filepath, 'rb') as fh:
        idx = 1
        while True:
            # check abort
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
                _log_exception(Exception('send_document_failed'), note=f'send_document chat={chat_id} part={idx}')
                # fallback via requests and log response/errors
                try:
                    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                    files = {'document': (bio.name, bio)}
                    resp = requests.post(f'https://api.telegram.org/bot{token}/sendDocument', data={'chat_id': chat_id, 'caption': f'Part {idx}/{parts}'}, files=files, timeout=30)
                    try:
                        with open(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')), 'bot.log'), 'a', encoding='utf-8') as lf:
                            lf.write(f"[send_document_fallback] status={resp.status_code} text={resp.text[:800]}\n")
                    except Exception:
                        pass
                except Exception as rexc:
                    _log_exception(rexc, note=f'send_document_fallback chat={chat_id} part={idx}')
            idx += 1
            try:
                await status_msg.edit_text(f'Uploaded part {idx-1}/{parts}')
            except Exception:
                pass
    try:
        await status_msg.edit_text(f'Upload complete: {orig_name} ({parts} parts)')
    except Exception:
        pass


async def _download_with_libtorrent(magnet_or_torrent: str, dest: str) -> str:
    ses = lt.session()
    ses.listen_on(6881, 6891)
    params = { 'save_path': dest }
    if magnet_or_torrent.startswith('magnet:'):
        handle = lt.add_magnet_uri(ses, magnet_or_torrent, params)
    else:
        info = lt.torrent_info(magnet_or_torrent)
        handle = ses.add_torrent({ 'ti': info, 'save_path': dest })
    # wait for metadata
    while not handle.has_metadata():
        await asyncio.sleep(1)
    ti = handle.get_torrent_info()
    # choose largest file
    files = ti.files()
    sizes = [(i, files.size(i)) for i in range(files.num_files())]
    idx, _ = max(sizes, key=lambda x: x[1])
    # enable sequential download for smoother single-file download
    handle.set_sequential_download(True)
    target_path = os.path.join(dest, files.file_path(idx))
    # wait until file appears and download completes
    while not os.path.exists(target_path) or os.path.getsize(target_path) < files.size(idx):
        await asyncio.sleep(2)
    return target_path


async def _download_with_aria2(url: str, dest: str) -> str:
    # requires aria2c installed
    cmd = ['aria2c', '--dir', dest, '--max-concurrent-downloads=1', '--enable-dht=true', '--enable-peer-exchange=true', url]
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
        out_text = (out or b'').decode('utf-8', errors='replace')
        err_text = (err or b'').decode('utf-8', errors='replace')
        combined = out_text + "\n" + err_text
        # find downloaded file in dest (newest)
        files = sorted([os.path.join(dest, f) for f in os.listdir(dest)], key=os.path.getmtime, reverse=True) if os.path.exists(dest) else []
        path = files[0] if files else ''
        # return tuple (path, aria2_output)
        return path, combined
    except Exception as e:
        _log_exception(e, note='_download_with_aria2')
        return '', str(e)


async def stream_torrent_cmd(update: Any, context: Any):
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /stream_torrent <magnet_or_torrent_url>')
        return
    url = args[0]
    # allow passing raw infohash (40 hex chars) or base32 (32 chars)
    def _maybe_to_magnet(s: str) -> str:
        ss = s.strip()
        # hex infohash (40 hex chars)
        import re
        if re.fullmatch(r"[A-Fa-f0-9]{40}", ss):
            return f"magnet:?xt=urn:btih:{ss}"
        # base32 (usually 32 chars A-Z2-7)
        if re.fullmatch(r"[A-Z2-7]{32}", ss.upper()):
            return f"magnet:?xt=urn:btih:{ss}"
        return ss

    url = _maybe_to_magnet(url)
    torrent_id = _make_torrent_id(url)
    tmpdir = tempfile.mkdtemp()
    # register active torrent
    ACTIVE_TORRENTS[torrent_id] = {'id': torrent_id, 'chat_id': update.effective_chat.id if update.effective_chat else None, 'name': url, 'status': 'downloading', 'started_at': int(time.time()), 'path': ''}
    await update.message.reply_text(f'Starting download to {tmpdir}...')
    try:
        if lt is not None:
                path = await _download_with_libtorrent(url, tmpdir)
                aria_out = None
        else:
                path, aria_out = await _download_with_aria2(url, tmpdir)
        if not path:
            msg = 'Download failed'
            if aria_out:
                msg += f" (aria2: {aria_out.splitlines()[-1][:300]})"
            await update.message.reply_text(msg)
            _log_exception(Exception('download_failed'), note=f'stream_torrent_cmd: {aria_out}')
            ACTIVE_TORRENTS[torrent_id]['status'] = 'error'
            return
        ACTIVE_TORRENTS[torrent_id]['path'] = path
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
        ACTIVE_TORRENTS[torrent_id]['status'] = 'done'
    except Exception as e:
        try:
            await update.message.reply_text(f'Error: {type(e).__name__}: {e}')
        except Exception:
            pass
        _log_exception(e, note='stream_torrent_cmd')
    finally:
        # cleanup
        try:
            for f in os.listdir(tmpdir):
                os.unlink(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
        except Exception:
            pass
        # ensure registry updated
        try:
            if torrent_id in ACTIVE_TORRENTS and ACTIVE_TORRENTS[torrent_id].get('status') == 'downloading':
                ACTIVE_TORRENTS[torrent_id]['status'] = 'done'
        except Exception:
            pass


async def download_torrent_cmd(update: Any, context: Any):
    """Download torrent or URL fully and upload file parts to the chat.

    Usage: /download_torrent <magnet_or_torrent_url>
    This command behaves like `/stream_torrent` but is explicit for full downloads/uploads.
    """
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /download_torrent <magnet_or_torrent_url>')
        return
    url = args[0]
    # reuse conversion helper
    def _maybe_to_magnet(s: str) -> str:
        ss = s.strip()
        import re
        if re.fullmatch(r"[A-Fa-f0-9]{40}", ss):
            return f"magnet:?xt=urn:btih:{ss}"
        if re.fullmatch(r"[A-Z2-7]{32}", ss.upper()):
            return f"magnet:?xt=urn:btih:{ss}"
        return ss

    url = _maybe_to_magnet(url)
    torrent_id = _make_torrent_id(url)
    tmpdir = tempfile.mkdtemp()
    # register active torrent
    try:
        ACTIVE_TORRENTS[torrent_id] = {'id': torrent_id, 'chat_id': update.effective_chat.id if update.effective_chat else None, 'name': url, 'status': 'downloading', 'started_at': int(time.time()), 'path': ''}
    except Exception:
        pass
    await update.message.reply_text(f'Starting download to {tmpdir}...')
    try:
        if lt is not None:
            path = await _download_with_libtorrent(url, tmpdir)
            aria_out = None
        else:
            path, aria_out = await _download_with_aria2(url, tmpdir)
        if not path:
            msg = 'Download failed'
            if aria_out:
                msg += f" (aria2: {aria_out.splitlines()[-1][:300]})"
            await update.message.reply_text(msg)
            _log_exception(Exception('download_failed'), note=f'download_torrent_cmd: {aria_out}')
            try:
                ACTIVE_TORRENTS[torrent_id]['status'] = 'error'
            except Exception:
                pass
            return
        try:
            ACTIVE_TORRENTS[torrent_id]['path'] = path
        except Exception:
            pass
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
        try:
            ACTIVE_TORRENTS[torrent_id]['status'] = 'done'
        except Exception:
            pass
    except Exception as e:
        try:
            await update.message.reply_text(f'Error: {type(e).__name__}: {e}')
        except Exception:
            pass
        _log_exception(e, note='download_torrent_cmd')
    finally:
        try:
            for f in os.listdir(tmpdir):
                os.unlink(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
        except Exception:
            pass
        # ensure registry updated
        try:
            if torrent_id in ACTIVE_TORRENTS and ACTIVE_TORRENTS[torrent_id].get('status') == 'downloading':
                ACTIVE_TORRENTS[torrent_id]['status'] = 'done'
        except Exception:
            pass


async def stream_torrent_file_cmd(update: Any, context: Any):
    if not update.message.reply_to_message or not getattr(update.message.reply_to_message, 'document', None):
        await update.message.reply_text('Reply to a .torrent file with /stream_torrent_file')
        return
    doc = update.message.reply_to_message.document
    if not doc.file_name.endswith('.torrent'):
        await update.message.reply_text('Replied file is not a .torrent')
        return
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        f = await context.bot.get_file(doc.file_id)
        await f.download_to_drive(tmp.name)
        # create and send a small cover/info image to the uploader (private) and origin chat
        try:
            size = os.path.getsize(tmp.name)
            h = hashlib.sha256()
            with open(tmp.name, 'rb') as tf:
                for chunk in iter(lambda: tf.read(8192), b''):
                    if not chunk:
                        break
                    h.update(chunk)
            hexsha = h.hexdigest()
            title = getattr(doc, 'file_name', 'torrent')
            if Image is not None:
                try:
                    W, H = 600, 140
                    im = Image.new('RGB', (W, H), color=(30, 30, 30))
                    draw = ImageDraw.Draw(im)
                    try:
                        font = ImageFont.truetype('arial.ttf', 14)
                    except Exception:
                        font = ImageFont.load_default()
                    draw.text((12, 12), f'Archivo: {title}', fill=(240,240,240), font=font)
                    draw.text((12, 38), f'Tamaño: {size} bytes ({size//1024} KB)', fill=(200,200,220), font=font)
                    draw.text((12, 64), f'SHA256: {hexsha[:20]}...', fill=(200,200,200), font=font)
                    draw.text((12, 92), f'Acción: /stream_torrent_file para iniciar streaming', fill=(180,180,250), font=font)
                    buf = io.BytesIO()
                    im.save(buf, format='PNG')
                    buf.seek(0)
                    # send privately to uploader
                    try:
                        await context.bot.send_photo(chat_id=update.effective_user.id, photo=buf, caption=f'{title} — {size//1024} KB')
                    except Exception:
                        pass
                    # also send to origin chat only if uploader allowed or is admin/owner
                    try:
                        sender = getattr(update, 'effective_user', None)
                        sender_id = getattr(sender, 'id', None)
                        can_post = False
                        if sender_id is not None:
                            role = storage.get_role(sender_id)
                            if role in ('owner', 'admin'):
                                can_post = True
                            elif storage.is_allowed_sender(update.effective_chat.id, sender_id):
                                can_post = True
                        if can_post:
                            buf.seek(0)
                            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf, caption=f'{title} — {size//1024} KB')
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(chat_id=update.effective_user.id, text=f'{title} — {size//1024} KB — SHA256 {hexsha[:20]}...')
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f'{title} — {size//1024} KB')
                except Exception:
                    pass
        except Exception:
            pass
        # create torrent folder structure using repository script
        try:
            # locate script relative to plugin file
            script_path = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'scripts', 'create_torrent_structure.py')))
            if os.path.exists(script_path):
                cmd = [sys.executable, script_path, '--torrent', tmp.name, '--title', title, '--outdir', os.path.join(os.getcwd(), 'torrents')]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if proc.returncode == 0:
                            out = proc.stdout.strip() or 'Estructura creada.'
                            # send to origin chat only if allowed
                            try:
                                sender = getattr(update, 'effective_user', None)
                                sender_id = getattr(sender, 'id', None)
                                can_post = False
                                if sender_id is not None:
                                    role = storage.get_role(sender_id)
                                    if role in ('owner', 'admin'):
                                        can_post = True
                                    elif storage.is_allowed_sender(update.effective_chat.id, sender_id):
                                        can_post = True
                                if can_post:
                                    try:
                                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Creada estructura: {out}')
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            # try to find metadata.json under ./torrents (newest)
                            try:
                                outdir = os.path.join(os.getcwd(), 'torrents')
                                meta_file = None
                                if os.path.exists(outdir):
                                    candidates = []
                                    for root, dirs, files in os.walk(outdir):
                                        if 'metadata.json' in files:
                                            candidates.append(os.path.join(root, 'metadata.json'))
                                    if candidates:
                                        meta_file = max(candidates, key=lambda p: os.path.getmtime(p))
                                if meta_file:
                                    try:
                                        import json
                                        with open(meta_file, 'r', encoding='utf-8') as mf:
                                            md = json.load(mf)
                                        infohash = md.get('infohash')
                                        if infohash:
                                            # store permanently (Redis or in-memory)
                                            storage.add_infohash(infohash)
                                            try:
                                                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Infohash almacenado: {infohash[:20]}...')
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    else:
                        try:
                            await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error creando estructura: {proc.stderr.strip()[:400]}')
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        tmpdir = tempfile.mkdtemp()
        aria_out = None
        if lt is not None:
            path = await _download_with_libtorrent(tmp.name, tmpdir)
        else:
            path, aria_out = await _download_with_aria2(tmp.name, tmpdir)
        if not path:
            await update.message.reply_text('Download failed')
            return
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
    except Exception as e:
        try:
            await update.message.reply_text(f'Error: {type(e).__name__}: {e}')
        except Exception:
            pass
        _log_exception(e, note='stream_torrent_file_cmd')
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


async def handle_torrent_document(update: Any, context: Any):
    """Handle incoming `.torrent` document uploads and start download automatically.

    If a user sends a `.torrent` file as a document, the bot will download the .torrent,
    start the torrent download (using libtorrent if available, otherwise aria2c),
    and upload the resulting file parts to the chat.
    """
    if not update.message or not getattr(update.message, 'document', None):
        return
    doc = update.message.document
    fname = getattr(doc, 'file_name', '') or ''
    if not fname.lower().endswith('.torrent'):
        return

    # download the uploaded .torrent file
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        f = await context.bot.get_file(doc.file_id)
        await f.download_to_drive(tmp.name)
    except Exception as e:
        try:
            await update.message.reply_text(f'Failed to download uploaded .torrent: {e}')
        except Exception:
            pass
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        return

    # If sent in private, add to user's pending torrents list instead of downloading immediately
    try:
        chat = update.effective_chat
        user = update.effective_user
        is_private = getattr(chat, 'type', '') == 'private' or (chat and str(chat.id).startswith('-') is False and chat.type == 'private')
    except Exception:
        is_private = False
    if is_private and getattr(user, 'id', None):
        # persist the .torrent file into pending folder and record in storage
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
            pending_dir = os.path.join(repo_root, 'pending_torrents', str(user.id))
            os.makedirs(pending_dir, exist_ok=True)
            dest = os.path.join(pending_dir, fname)
            # move temp file to pending location
            try:
                os.replace(tmp.name, dest)
            except Exception:
                os.rename(tmp.name, dest)
            entry = {'filename': fname, 'path': dest, 'uploaded_at': int(time.time())}
            try:
                storage.add_pending_torrent(int(user.id), entry)
                # Automatically generate and send a small cover/info image to the user (private)
                try:
                    size = os.path.getsize(dest)
                    h = hashlib.sha256()
                    with open(dest, 'rb') as tf:
                        for chunk in iter(lambda: tf.read(8192), b''):
                            if not chunk:
                                break
                            h.update(chunk)
                    hexsha = h.hexdigest()
                    title = fname
                    if Image is not None:
                        try:
                            W, H = 600, 140
                            im = Image.new('RGB', (W, H), color=(30, 30, 30))
                            draw = ImageDraw.Draw(im)
                            try:
                                font = ImageFont.truetype('arial.ttf', 14)
                            except Exception:
                                font = ImageFont.load_default()
                            draw.text((12, 12), f'Archivo: {title}', fill=(240,240,240), font=font)
                            draw.text((12, 38), f'Tamaño: {size} bytes ({size//1024} KB)', fill=(200,200,220), font=font)
                            draw.text((12, 64), f'SHA256: {hexsha[:20]}...', fill=(200,200,200), font=font)
                            draw.text((12, 92), f'Acción: enviado automáticamente', fill=(180,180,250), font=font)
                            buf = io.BytesIO()
                            im.save(buf, format='PNG')
                            buf.seek(0)
                            try:
                                await context.bot.send_photo(chat_id=user.id, photo=buf, caption=f'{title} — {size//1024} KB')
                            except Exception:
                                pass
                        except Exception:
                            pass
                    else:
                        try:
                            await context.bot.send_message(chat_id=user.id, text=f'{title} — {size//1024} KB — SHA256 {hexsha[:20]}...')
                        except Exception:
                            pass
                except Exception:
                    # ignore cover generation errors but keep torrent saved
                    pass
                # notify user the torrent was saved
                await context.bot.send_message(chat_id=user.id, text=f'Torrent recibido y añadido a tu lista pendiente. Hemos enviado la portada automáticamente. Usa /mytorrents para listar y /startpending <n> para iniciar.')
                # Start download immediately for private uploads: remove from pending and trigger download
                try:
                    lst = storage.get_pending_torrents(int(user.id))
                    # find the entry we just added
                    idx = None
                    for i, e in enumerate(lst):
                        p = e.get('path') or ''
                        fn = e.get('filename') or ''
                        if p == dest or fn == fname:
                            idx = i
                            break
                    if idx is not None:
                        # remove from pending before starting
                        try:
                            storage.remove_pending_torrent(int(user.id), idx)
                        except Exception:
                            pass
                    # trigger download using same code path as /startpending
                    class CtxObj: pass
                    obj = CtxObj()
                    obj.args = [dest]
                    await download_torrent_cmd(update, obj)
                except Exception:
                    # don't fail the whole handler if download trigger fails
                    pass
            except Exception:
                await context.bot.send_message(chat_id=user.id, text='Error al guardar el torrent pendiente.')
        except Exception as e:
            _log_exception(e, note='handle_torrent_document_pending')
        return

    # fallback: if not private, proceed with immediate download as before
    tmpdir = tempfile.mkdtemp()
    await update.message.reply_text(f'Starting download from uploaded torrent to {tmpdir}...')
    try:
        aria_out = None
        if lt is not None:
            path = await _download_with_libtorrent(tmp.name, tmpdir)
        else:
            path, aria_out = await _download_with_aria2(tmp.name, tmpdir)
        if not path:
            await update.message.reply_text('Download failed')
            return
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
    except Exception as e:
        try:
            await update.message.reply_text(f'Error: {type(e).__name__}: {e}')
        except Exception:
            pass
        _log_exception(e, note='handle_torrent_document')
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        try:
            for f in os.listdir(tmpdir):
                os.unlink(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
        except Exception:
            pass


async def stream_torrent_stream_cmd(update: Any, context: Any):
    """Start streaming the torrent file while downloading (incremental).

    Usage: /stream_torrent_stream <magnet_or_torrent_url>
    Requires `libtorrent` to be installed.
    """
    if lt is None:
        await update.message.reply_text('libtorrent is required for incremental streaming. Install python-libtorrent.')
        return
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /stream_torrent_stream <magnet_or_torrent_url>')
        return
    url = args[0]
    # accept raw infohash (hex or base32) and convert to magnet
    def _maybe_to_magnet(s: str) -> str:
        ss = s.strip()
        import re
        if re.fullmatch(r"[A-Fa-f0-9]{40}", ss):
            return f"magnet:?xt=urn:btih:{ss}"
        if re.fullmatch(r"[A-Z2-7]{32}", ss.upper()):
            return f"magnet:?xt=urn:btih:{ss}"
        return ss

    url = _maybe_to_magnet(url)
    chat_id = update.effective_chat.id
    storage.start_stream_session(chat_id, name='torrent')
    tmpdir = tempfile.mkdtemp()
    await update.message.reply_text(f'Starting incremental torrent download to {tmpdir}...')
    try:
        # start torrent session and get target file path
        ses = lt.session()
        ses.listen_on(6881, 6891)
        params = {'save_path': tmpdir}
        if url.startswith('magnet:'):
            handle = lt.add_magnet_uri(ses, url, params)
        else:
            ti = lt.torrent_info(url)
            handle = ses.add_torrent({'ti': ti, 'save_path': tmpdir})

        # wait for metadata
        while not handle.has_metadata():
            # check abort
            if storage.get_stream_session(chat_id) and storage.get_stream_session(chat_id).get('abort') == '1':
                storage.stop_stream_session(chat_id)
                await update.message.reply_text('Streaming aborted before metadata')
                return
            await asyncio.sleep(1)

        ti = handle.get_torrent_info()
        files = ti.files()
        # choose largest file
        sizes = [(i, files.size(i)) for i in range(files.num_files())]
        idx, _ = max(sizes, key=lambda x: x[1])
        relpath = files.file_path(idx)
        target_path = os.path.join(tmpdir, relpath)
        # enable sequential download
        handle.set_sequential_download(True)

        # stream while downloading
        await _stream_while_downloading(handle, target_path, context, chat_id, os.path.basename(relpath))
    except Exception as e:
        try:
            await update.message.reply_text(f'Error: {type(e).__name__}: {e}')
        except Exception:
            pass
        _log_exception(e, note='stream_torrent_stream_cmd')
    finally:
        storage.stop_stream_session(chat_id)
        try:
            for f in os.listdir(tmpdir):
                os.unlink(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
        except Exception:
            pass


async def _stream_while_downloading(handle, filepath: str, context, chat_id: int, orig_name: str, chunk_size: int = 5 * 1024 * 1024):
    """Read the target file while libtorrent downloads it, sending chunks as they become available."""
    sent = 0
    status_msg = await context.bot.send_message(chat_id=chat_id, text=f'Streaming {orig_name}...')
    try:
        while True:
            # abort check
            sess = storage.get_stream_session(chat_id)
            if sess and sess.get('abort') == '1':
                await status_msg.edit_text('Streaming aborted by user')
                return

            if os.path.exists(filepath):
                available = os.path.getsize(filepath)
            else:
                available = 0

            # include peer count in status if available
            try:
                st = handle.status()
                peers = getattr(st, 'num_peers', None)
            except Exception:
                peers = None

            # send all full chunks available
            while available - sent >= chunk_size:
                with open(filepath, 'rb') as fh:
                    fh.seek(sent)
                    chunk = fh.read(chunk_size)
                bio = io.BytesIO(chunk)
                bio.name = f'{orig_name}.part{(sent // chunk_size) + 1}'
                try:
                    await context.bot.send_document(chat_id=chat_id, document=bio, filename=bio.name, caption=f'Part {(sent // chunk_size) + 1}')
                except Exception:
                    pass
                sent += len(chunk)
                try:
                    if peers is not None:
                        await status_msg.edit_text(f'Streamed {(sent // chunk_size)} parts... | peers: {peers}')
                    else:
                        await status_msg.edit_text(f'Streamed {(sent // chunk_size)} parts...')
                except Exception:
                    pass

            # check if download finished
            if handle.is_seed():
                # send remaining
                if os.path.exists(filepath):
                    final_size = os.path.getsize(filepath)
                    if final_size > sent:
                        with open(filepath, 'rb') as fh:
                            fh.seek(sent)
                            tail = fh.read()
                        if tail:
                            bio = io.BytesIO(tail)
                            bio.name = f'{orig_name}.part{(sent // chunk_size) + 1}'
                            try:
                                await context.bot.send_document(chat_id=chat_id, document=bio, filename=bio.name, caption='Final part')
                            except Exception:
                                pass
                await status_msg.edit_text('Streaming complete')
                return

            await asyncio.sleep(1)
    except Exception:
        try:
            await status_msg.edit_text('Streaming stopped due to error')
        except Exception:
            pass


async def stream_torrent_stop_cmd(update: Any, context: Any):
    # If called with an id argument, stop that specific torrent id; otherwise abort current chat session
    args = getattr(context, 'args', []) or []
    if args:
        tid = args[0]
        ok = stop_torrent(tid)
        if ok:
            await update.message.reply_text(f'Torrent {tid} stop requested.')
        else:
            await update.message.reply_text(f'Torrent id {tid} not found.')
        return
    chat_id = update.effective_chat.id
    storage.abort_stream_session(chat_id)
    storage.stop_stream_session(chat_id)
    await update.message.reply_text('Torrent streaming stopped/aborted.')


async def cover_cmd(update: Any, context: Any):
    """Generate and send a small cover image for a magnet URI or raw infohash.

    Usage: /cover <magnet_or_infohash>
    If `libtorrent` is available the command will try to fetch metadata to show file/name/size.
    """
    args = context.args or []
    if not args:
        await update.message.reply_text('Usage: /cover <magnet_or_infohash>')
        return
    s = args[0].strip()
    import re

    def to_magnet(x: str) -> str:
        if x.startswith('magnet:'):
            return x
        if re.fullmatch(r'[A-Fa-f0-9]{40}', x):
            return f'magnet:?xt=urn:btih:{x}'
        if re.fullmatch(r'[A-Z2-7]{32}', x.upper()):
            return f'magnet:?xt=urn:btih:{x}'
        return x

    mag = to_magnet(s)
    title = mag
    size = None
    sha = None

    if lt is not None and mag.startswith('magnet:'):
        try:
            ses = lt.session()
            ses.listen_on(6881, 6891)
            handle = lt.add_magnet_uri(ses, mag, {'save_path': tempfile.gettempdir()})
            # wait short time for metadata
            for _ in range(15):
                if handle.has_metadata():
                    break
                await asyncio.sleep(1)
            if handle.has_metadata():
                ti = handle.get_torrent_info()
                files = ti.files()
                total = sum(files.size(i) for i in range(files.num_files()))
                sizes = [(i, files.size(i)) for i in range(files.num_files())]
                idx, _ = max(sizes, key=lambda x: x[1])
                title = files.file_path(idx)
                size = total
                sha = ti.info_hash().to_string() if hasattr(ti, 'info_hash') else None
        except Exception:
            pass

    # build image
    if Image is not None:
        try:
            W, H = 650, 160
            im = Image.new('RGB', (W, H), color=(28, 28, 30))
            d = ImageDraw.Draw(im)
            try:
                font = ImageFont.truetype('arial.ttf', 14)
            except Exception:
                font = ImageFont.load_default()
            d.text((12, 12), f'Title: {str(title)[:60]}', fill=(240,240,240), font=font)
            if size is not None:
                d.text((12, 40), f'Size: {size} bytes ({size//1024} KB)', fill=(200,200,220), font=font)
            if sha is not None:
                d.text((12, 68), f'InfoHash: {sha[:20]}...', fill=(200,200,200), font=font)
            d.text((12, 96), f'Source: {"magnet" if mag.startswith("magnet:") else "infohash"}', fill=(180,200,180), font=font)
            d.text((12, 124), 'Use /stream_torrent_stream <magnet> to stream while downloading', fill=(180,180,250), font=font)
            bio = io.BytesIO()
            im.save(bio, format='PNG')
            bio.seek(0)
            # check permission: allow if requester is admin/owner or allowed sender
            try:
                sender = getattr(update, 'effective_user', None)
                sender_id = getattr(sender, 'id', None)
                can_post = False
                if sender_id is not None:
                    role = storage.get_role(sender_id)
                    if role in ('owner', 'admin'):
                        can_post = True
                    elif storage.is_allowed_sender(update.effective_chat.id, sender_id):
                        can_post = True
                if can_post:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio, caption=f'Cover for {str(title)[:50]}')
                else:
                    # send privately to requester if not allowed to post in chat
                    await context.bot.send_photo(chat_id=update.effective_user.id, photo=bio, caption=f'Cover for {str(title)[:50]}')
                return
            except Exception:
                pass
            return
        except Exception:
            pass

    # fallback text message
    txt = f'Cover: {str(title)[:200]}'
    if size:
        txt += f' — size: {size} bytes'
    if sha:
        txt += f' — infohash: {sha[:20]}...'
    await update.message.reply_text(txt)
