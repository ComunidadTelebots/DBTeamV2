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


def setup(bot):
    bot.register_command('stream_torrent', stream_torrent_cmd, 'Download torrent/magnet and stream parts', plugin='stream_torrent')
    bot.register_command('stream_torrent_file', stream_torrent_file_cmd, 'Reply to a .torrent file to stream it', plugin='stream_torrent')
    bot.register_command('stream_torrent_stream', stream_torrent_stream_cmd, 'Stream while downloading (requires libtorrent)', plugin='stream_torrent')
    bot.register_command('stream_torrent_stop', stream_torrent_stop_cmd, 'Stop/abort a streaming torrent session', plugin='stream_torrent')
    bot.register_command('cover', cover_cmd, 'Generate a cover for a magnet/infohash', plugin='stream_torrent')
    bot.register_command('allow_send', allow_send_cmd, 'Allow a user to let bot post origin messages in this chat (reply to user or pass user_id)', plugin='stream_torrent')
    bot.register_command('disallow_send', disallow_send_cmd, 'Remove allow to post origin messages (reply or user_id)', plugin='stream_torrent')


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
        target_id = update.message.reply_to_message.from.id
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
        target_id = update.message.reply_to_message.from.id
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
                # fallback via requests
                try:
                    token = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
                    files = {'document': (bio.name, bio)}
                    requests.post(f'https://api.telegram.org/bot{token}/sendDocument', data={'chat_id': chat_id, 'caption': f'Part {idx}/{parts}'}, files=files, timeout=30)
                except Exception:
                    pass
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
    cmd = ['aria2c', '--dir', dest, '--max-concurrent-downloads=1', url]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.wait()
    # find downloaded file in dest (newest)
    files = sorted([os.path.join(dest, f) for f in os.listdir(dest)], key=os.path.getmtime, reverse=True)
    return files[0] if files else ''


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
    tmpdir = tempfile.mkdtemp()
    await update.message.reply_text(f'Starting download to {tmpdir}...')
    try:
        if lt is not None:
            path = await _download_with_libtorrent(url, tmpdir)
        else:
            # fallback to aria2c
            path = await _download_with_aria2(url, tmpdir)
        if not path:
            await update.message.reply_text('Download failed')
            return
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        # cleanup
        try:
            for f in os.listdir(tmpdir):
                os.unlink(os.path.join(tmpdir, f))
            os.rmdir(tmpdir)
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
        path = await _download_with_libtorrent(tmp.name, tmpdir) if lt is not None else await _download_with_aria2(tmp.name, tmpdir)
        if not path:
            await update.message.reply_text('Download failed')
            return
        await _send_parts_bot(context, update.effective_chat.id, path, os.path.basename(path))
    except Exception as e:
        await update.message.reply_text(f'Error: {e}')
    finally:
        try:
            os.unlink(tmp.name)
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
        await update.message.reply_text(f'Error: {e}')
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
