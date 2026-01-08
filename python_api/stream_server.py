from flask import Flask, jsonify, request, send_from_directory
import os
import json
import subprocess
import signal
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
import json as _json
try:
    import redis
except Exception:
    redis = None
import base64
import hashlib
try:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except Exception:
    CRYPTO_AVAILABLE = False
try:
    import requests
except Exception:
    requests = None
import sys

app = Flask(__name__)

# CORS fallback: prefer flask_cors if available, otherwise set permissive headers
try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    from flask import make_response

    @app.after_request
    def _cors_fix(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    # respond to OPTIONS preflight for root and any path
    @app.route('/', methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def _options(path=None):
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp


    # ----------------- Moderation endpoints -----------------
    @app.route('/admin/moderation/actions', methods=['GET'])
    def admin_moderation_actions():
        if not redis:
            return jsonify({'error': 'redis not available on server'}), 500
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'), decode_responses=True)
        try:
            entries = r.lrange('moderation:actions', 0, -1)
            parsed = []
            for e in entries:
                try:
                    parsed.append(json.loads(e))
                except Exception:
                    parsed.append({'raw': e})
            return jsonify({'actions': parsed})
        except Exception as e:
            return jsonify({'error': 'redis error', 'detail': str(e)}), 500


    @app.route('/admin/moderation/apply', methods=['POST'])
    def admin_moderation_apply():
        data = request.get_json(force=True)
        idx = data.get('index')
        action = data.get('action')
        if idx is None or action is None:
            return jsonify({'error': 'index and action required'}), 400
        if not redis:
            return jsonify({'error': 'redis not available on server'}), 500
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'), decode_responses=True)
        try:
            entries = r.lrange('moderation:actions', idx, idx)
            if not entries:
                return jsonify({'error': 'not found'}), 404
            raw = entries[0]
            try:
                j = json.loads(raw)
            except Exception:
                j = {'raw': raw}
            applied = {
                'applied_by': request.headers.get('X-User-Id') or 0,
                'action': action,
                'original': j,
                'ts': int(time.time()),
            }
            r.rpush('moderation:applied', json.dumps(applied))
            r.lrem('moderation:actions', 1, raw)
            return jsonify({'ok': True})
        except Exception as e:
            return jsonify({'error': 'redis error', 'detail': str(e)}), 500


SCENES_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'streams', 'scenes')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
TORRENTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'torrents')
os.makedirs(SCENES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(TORRENTS_DIR, exist_ok=True)
NEXTCLOUD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'nextcloud')
os.makedirs(NEXTCLOUD_DIR, exist_ok=True)
PLEX_TORRENTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'media', 'torrents')
os.makedirs(PLEX_TORRENTS_DIR, exist_ok=True)
MEDIA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'media')
os.makedirs(MEDIA_DIR, exist_ok=True)
MEDIA_OWNERS_FILE = os.path.join(MEDIA_DIR, 'owners.json')

def _load_media_owners():
    try:
        if os.path.exists(MEDIA_OWNERS_FILE):
            with open(MEDIA_OWNERS_FILE, 'r', encoding='utf-8') as f:
                return _json.load(f)
    except Exception:
        pass
    return {}

def _save_media_owners(m):
    try:
        with open(MEDIA_OWNERS_FILE, 'w', encoding='utf-8') as f:
            _json.dump(m, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False



def scene_path(name):
    safe = name.replace('/', '_').replace('\\', '_')
    return os.path.join(SCENES_DIR, f"{safe}.json")


@app.route('/stream/scenes', methods=['GET'])
def list_scenes():
    scenes = []
    for fname in os.listdir(SCENES_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(SCENES_DIR, fname), 'r', encoding='utf-8') as f:
                try:
                    scenes.append(json.load(f))
                except Exception:
                    continue
    return jsonify({'scenes': scenes})


@app.route('/stream/scenes', methods=['POST'])
def save_scene():
    data = request.get_json(force=True)
    if not data or 'name' not in data:
        return jsonify({'error': 'missing name'}), 400
    path = scene_path(data['name'])
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({'ok': True})


@app.route('/stream/scene/<path:name>', methods=['GET'])
def get_scene(name):
    try:
        p = scene_path(name)
        if not os.path.exists(p):
            return jsonify({'error': 'not found'}), 404
        with open(p, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': 'read error', 'detail': str(e)}), 500


@app.route('/stream/scene/<path:name>', methods=['DELETE'])
def delete_scene(name):
    try:
        p = scene_path(name)
        if os.path.exists(p):
            os.remove(p)
            return jsonify({'ok': True})
        return jsonify({'error': 'not found'}), 404
    except Exception as e:
        return jsonify({'error': 'delete error', 'detail': str(e)}), 500


@app.route('/stream/import_obs', methods=['POST'])
def import_obs():
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    f = request.files['file']
    try:
        data = json.load(f)
    except Exception as e:
        return jsonify({'error': 'invalid json', 'detail': str(e)}), 400

    imported = []
    # OBS scene collections often have 'scenes' as a key
    scenes = data.get('scenes') or data.get('sources') or []
    for s in scenes:
        name = s.get('name') or s.get('scene-name') or ('scene-' + str(len(imported)))
        scene_obj = {'name': name, 'obs_raw': s}
        with open(scene_path(name), 'w', encoding='utf-8') as out:
            json.dump(scene_obj, out, ensure_ascii=False, indent=2)
        imported.append(name)

    return jsonify({'imported': imported})


@app.route('/stream/import_rss', methods=['POST'])
def import_rss():
    data = request.get_json(force=True)
    url = data.get('url') if data else None
    name = data.get('name') if data else None
    if not url:
        return jsonify({'error': 'url required'}), 400
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read()
        try:
            text = raw.decode('utf-8')
        except Exception:
            text = raw.decode('latin-1')
        # parse XML
        root = ET.fromstring(text)
        # support RSS and Atom
        items = []
        feed_title = None
        # RSS
        channel = root.find('channel')
        if channel is not None:
            t = channel.find('title')
            if t is not None and t.text:
                feed_title = t.text
            for it in channel.findall('item'):
                it_title = it.find('title')
                it_link = it.find('link')
                it_desc = it.find('description')
                items.append({'title': unescape(it_title.text) if it_title is not None and it_title.text else '',
                              'link': it_link.text if it_link is not None and it_link.text else '',
                              'summary': unescape(it_desc.text) if it_desc is not None and it_desc.text else ''})
        else:
            # Atom
            ns = ''
            title = root.find('{http://www.w3.org/2005/Atom}title')
            if title is not None and title.text:
                feed_title = title.text
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                etitle = entry.find('{http://www.w3.org/2005/Atom}title')
                link = ''
                l = entry.find('{http://www.w3.org/2005/Atom}link')
                if l is not None:
                    link = l.get('href') or ''
                summary = entry.find('{http://www.w3.org/2005/Atom}summary')
                if summary is None:
                    summary = entry.find('{http://www.w3.org/2005/Atom}content')
                items.append({'title': etitle.text if etitle is not None and etitle.text else '', 'link': link, 'summary': summary.text if summary is not None and summary.text else ''})

        scene_name = name or (feed_title or 'rss-feed')
        scene_obj = {'name': scene_name, 'obs_raw': {'feed': {'title': feed_title, 'url': url}, 'items': items}}
        with open(scene_path(scene_name), 'w', encoding='utf-8') as out:
            json.dump(scene_obj, out, ensure_ascii=False, indent=2)
        return jsonify({'imported': scene_name, 'count': len(items)})
    except Exception as e:
        return jsonify({'error': 'fetch or parse error', 'detail': str(e)}), 500


def pidfile_for(scene):
    safe = scene.replace('/', '_').replace('\\', '_')
    return os.path.join(LOGS_DIR, f'stream_{safe}.pid')


def is_running_pid(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@app.route('/stream/start', methods=['POST'])
def start_stream():
    data = request.get_json(force=True)
    name = data.get('scene')
    platform = data.get('platform', 'test')
    if not name:
        return jsonify({'error': 'scene required'}), 400

    pidfile = pidfile_for(name)
    if os.path.exists(pidfile):
        try:
            with open(pidfile, 'r', encoding='utf-8') as f:
                pid = int(f.read().strip())
                if is_running_pid(pid):
                    return jsonify({'ok': True, 'pid': pid, 'message': 'already running'})
        except Exception:
            pass

    # Try to launch a real ffmpeg process if settings indicate a real target
    settings = _read_settings()
    target = settings.get('target') if settings else None
    use_ffmpeg = False
    if platform != 'test' and target:
        use_ffmpeg = True

    if use_ffmpeg:
        # Build a simple ffmpeg command: background color + drawtext for text sources
        try:
            # load scene file
            scene_path_ = scene_path(name)
            scene_obj = {}
            if os.path.exists(scene_path_):
                with open(scene_path_, 'r', encoding='utf-8') as sf:
                    scene_obj = _json.load(sf)

            text_overlays = []
            images = []
            sources = scene_obj.get('sources') or (scene_obj.get('obs_raw') or {}).get('sources') or []
            for s in sources:
                if s.get('type') == 'text' or s.get('text'):
                    txt = s.get('text') or s.get('content') or s.get('name') or ''
                    # drawtext expression; position is roughly placed by x/y percent
                    x = s.get('x') if isinstance(s.get('x'), (int,float)) else s.get('left')
                    y = s.get('y') if isinstance(s.get('y'), (int,float)) else s.get('top')
                    text_overlays.append({'text': txt, 'x': x, 'y': y, 'size': s.get('size', 24), 'color': s.get('color', 'white')})
                if s.get('type') == 'image' or s.get('url'):
                    images.append(s)

            ff_cmd = ['ffmpeg', '-y']
            # input: color background
            ff_cmd += ['-f', 'lavfi', '-i', 'color=size=1280x720:rate=30:color=black']

            # if there is an image, add it as input (first image only for simplicity)
            overlay_filter_parts = []
            if images:
                img = images[0]
                img_url = img.get('url') or img.get('src') or img.get('value')
                img_path = img_url
                # if it's a remote url, try downloading into logs
                if img_url and str(img_url).startswith('http'):
                    try:
                        import urllib.request as _ur
                        img_data = _ur.urlopen(img_url, timeout=10).read()
                        img_name = os.path.join(LOGS_DIR, f'image_{name}.png')
                        with open(img_name, 'wb') as _f:
                            _f.write(img_data)
                        img_path = img_name
                    except Exception:
                        img_path = None
                if img_path:
                    ff_cmd += ['-loop', '1', '-i', img_path]
                    # overlay image on top of background
                    overlay_filter_parts.append('[0:v][1:v] overlay=10:10 [ov];')

            # build drawtext filters
            draw_exprs = []
            for idx, to in enumerate(text_overlays):
                txt_esc = str(to['text']).replace("'", "\\'")
                # position fallback
                xexpr = f"{int((to['x'] or 10))}" if to.get('x') is not None else '10'
                yexpr = f"{int((to['y'] or 10))}" if to.get('y') is not None else '30'
                draw = f"drawtext=fontfile=/Windows/Fonts/arial.ttf:text='{txt_esc}':x={xexpr}:y={yexpr}:fontsize={to.get('size',24)}:fontcolor={to.get('color','white')}"
                draw_exprs.append(draw)

            vf_parts = []
            if overlay_filter_parts:
                # remove trailing semicolon in join
                vf_parts += [p for p in overlay_filter_parts]
            if draw_exprs:
                vf_parts += draw_exprs

            if vf_parts:
                vf = ','.join(part.rstrip(';') for part in vf_parts)
                ff_cmd += ['-vf', vf]

            # output to target
            ff_cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-tune', 'zerolatency', '-f', 'flv', target]

            # start ffmpeg
            log_out = os.path.join(LOGS_DIR, f'stream_{name}.stdout.log')
            log_err = os.path.join(LOGS_DIR, f'stream_{name}.stderr.log')
            with open(log_out, 'ab') as out_f, open(log_err, 'ab') as err_f:
                proc = subprocess.Popen(ff_cmd, stdout=out_f, stderr=err_f)
            with open(pidfile, 'w', encoding='utf-8') as f:
                f.write(str(proc.pid))
            return jsonify({'ok': True, 'pid': proc.pid, 'cmd': ff_cmd})
        except Exception as e:
            # fallback to simulated process
            pass

    # fallback simulated process (keeps previous behavior)
    cmd = ["python", "-c", "import time,sys; print('stream starting'); sys.stdout.flush(); time.sleep(999999)"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(pidfile, 'w', encoding='utf-8') as f:
        f.write(str(proc.pid))

    return jsonify({'ok': True, 'pid': proc.pid})


@app.route('/stream/stop', methods=['POST'])
def stop_stream():
    data = request.get_json(force=True)
    name = data.get('scene')
    if not name:
        return jsonify({'error': 'scene required'}), 400
    pidfile = pidfile_for(name)
    if not os.path.exists(pidfile):
        return jsonify({'ok': True, 'message': 'not running'})
    try:
        with open(pidfile, 'r', encoding='utf-8') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        # best-effort
        pass
    try:
        os.remove(pidfile)
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/stream/status', methods=['GET'])
def stream_status():
    scenes = []
    for fname in os.listdir(SCENES_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(SCENES_DIR, fname), 'r', encoding='utf-8') as f:
                try:
                    sc = json.load(f)
                except Exception:
                    continue
            name = sc.get('name')
            pidfile = pidfile_for(name)
            running = False
            pid = None
            if os.path.exists(pidfile):
                try:
                    pid = int(open(pidfile, 'r', encoding='utf-8').read().strip())
                    running = is_running_pid(pid)
                except Exception:
                    running = False
            scenes.append({'name': name, 'running': running, 'pid': pid})
    return jsonify({'scenes': scenes})


def call_ai_server(prompt, max_length=128):
    # Call local AI server at 127.0.0.1:8081 -> /ai/gpt2
    try:
        url = 'http://127.0.0.1:8081/ai/gpt2'
        payload = _json.dumps({'prompt': prompt, 'max_length': max_length}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
            try:
                return _json.loads(raw)
            except Exception:
                return {'text': raw}
    except Exception as e:
        return {'error': str(e)}


@app.route('/stream/ai_generate', methods=['POST'])
def ai_generate():
    data = request.get_json(force=True)
    prompt = data.get('prompt') if data else None
    scene = data.get('scene') if data else None
    if not prompt:
        return jsonify({'error': 'prompt required'}), 400
    result = call_ai_server(prompt)
    text = None
    if isinstance(result, dict):
        # prefer common key names
        text = result.get('text') or result.get('generated_text') or result.get('output')
        if text is None:
            # stringify
            text = _json.dumps(result)
    else:
        text = str(result)

    # attach to scene file if provided
    if scene:
        try:
            p = scene_path(scene)
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    obj = _json.load(f)
            else:
                obj = {'name': scene}
            obj.setdefault('ai_generated', []).append({'prompt': prompt, 'text': text})
            with open(p, 'w', encoding='utf-8') as f:
                _json.dump(obj, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return jsonify({'ok': True, 'text': text})


@app.route('/stream/torrent_url', methods=['POST'])
def torrent_url():
    """Generate a user-friendly URL for a torrent file using the local torrent domain.
    POST JSON: { "name": "file.torrent", "hash": "optional-hash" }
    Returns: { "url": "http://<id>.<domain>/torrents/<name>" }
    """
    data = request.get_json(force=True)
    if not data or ('name' not in data and 'hash' not in data):
        return jsonify({'error': 'name or hash required'}), 400
    name = data.get('name')
    h = data.get('hash')
    # allow overriding domain via live settings
    settings = _read_settings() or {}
    domain = settings.get('torrent_domain') or 'torrents.local'
    identifier = h or (os.path.splitext(name)[0] if name else 'torrent')
    # safe filename
    safe_name = name.replace('/', '_') if name else f"{identifier}.torrent"
    url = f"http://{identifier}.{domain}/torrents/{safe_name}"
    return jsonify({'ok': True, 'url': url})


@app.route('/torrents/<path:name>', methods=['GET'])
def serve_torrent(name):
    """Serve torrent files from the `data/torrents` folder."""
    try:
        p = os.path.join(TORRENTS_DIR, name)
        if not os.path.exists(p):
            return jsonify({'error': 'not found'}), 404
        # use send_from_directory to set correct headers
        return send_from_directory(TORRENTS_DIR, name, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'serve error', 'detail': str(e)}), 500


@app.route('/stream/torrents', methods=['GET'])
def list_torrents():
    try:
        files = []
        for fname in os.listdir(TORRENTS_DIR):
            if not fname.lower().endswith('.torrent'):
                continue
            p = os.path.join(TORRENTS_DIR, fname)
            try:
                st = os.stat(p)
                files.append({
                    'name': fname,
                    'size': st.st_size,
                    'mtime': int(st.st_mtime),
                    'url': f'/torrents/{fname}'
                })
            except Exception:
                continue
        return jsonify({'torrents': files})
    except Exception as e:
        return jsonify({'error': 'list error', 'detail': str(e)}), 500


@app.route('/nextcloud/files', methods=['GET'])
def list_nextcloud_files():
    try:
        user = request.args.get('user')
        files = []
        if user:
            # list only this user's files
            udir = _nextcloud_user_dir(user)
            for fname in os.listdir(udir):
                p = os.path.join(udir, fname)
                if os.path.isdir(p):
                    continue
                try:
                    st = os.stat(p)
                    files.append({'name': fname, 'size': st.st_size, 'mtime': int(st.st_mtime), 'url': f'/nextcloud/download/{user}/{fname}', 'user': user})
                except Exception:
                    continue
            return jsonify({'files': files})

        # no user specified: list root files and user subfolders
        for entry in os.listdir(NEXTCLOUD_DIR):
            p = os.path.join(NEXTCLOUD_DIR, entry)
            if os.path.isdir(p):
                # treat as user folder
                user_folder = entry
                for fname in os.listdir(p):
                    sp = os.path.join(p, fname)
                    if os.path.isdir(sp):
                        continue
                    try:
                        st = os.stat(sp)
                        files.append({'name': fname, 'size': st.st_size, 'mtime': int(st.st_mtime), 'url': f'/nextcloud/download/{user_folder}/{fname}', 'user': user_folder})
                    except Exception:
                        continue
            else:
                try:
                    st = os.stat(p)
                    files.append({'name': entry, 'size': st.st_size, 'mtime': int(st.st_mtime), 'url': f'/nextcloud/download/{entry}', 'user': None})
                except Exception:
                    continue

        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': 'list error', 'detail': str(e)}), 500


@app.route('/nextcloud/upload', methods=['POST'])
def nextcloud_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    f = request.files['file']
    name = f.filename or 'upload.bin'
    safe = _safe_filename(name)
    # determine user: form/query/header
    user = None
    try:
        user = request.form.get('user') or request.args.get('user') or request.headers.get('X-User')
    except Exception:
        user = None
    if user:
        udir = _nextcloud_user_dir(user)
        dest = os.path.join(udir, safe)
        try:
            f.save(dest)
            user_safe = _safe_username(user)
            return jsonify({'ok': True, 'name': safe, 'path': f'/nextcloud/download/{user_safe}/{safe}', 'user': user_safe})
        except Exception as e:
            return jsonify({'error': 'save failed', 'detail': str(e)}), 500

    # fallback: save in root
    dest = os.path.join(NEXTCLOUD_DIR, safe)
    try:
        f.save(dest)
        return jsonify({'ok': True, 'name': safe, 'path': f'/nextcloud/download/{safe}'})
    except Exception as e:
        return jsonify({'error': 'save failed', 'detail': str(e)}), 500


@app.route('/nextcloud/download/<path:user>/<path:name>', methods=['GET'])
def nextcloud_download_user(user, name):
    try:
        user_safe = _safe_username(user)
        p = os.path.join(NEXTCLOUD_DIR, user_safe, name)
        if not os.path.exists(p):
            return jsonify({'error': 'not found'}), 404
        return send_from_directory(os.path.join(NEXTCLOUD_DIR, user_safe), name, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'download error', 'detail': str(e)}), 500


@app.route('/nextcloud/download/<path:name>', methods=['GET'])
def nextcloud_download(name):
    try:
        p = os.path.join(NEXTCLOUD_DIR, name)
        if not os.path.exists(p):
            return jsonify({'error': 'not found'}), 404
        return send_from_directory(NEXTCLOUD_DIR, name, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'download error', 'detail': str(e)}), 500


@app.route('/nextcloud/delete', methods=['POST'])
def nextcloud_delete():
    data = request.get_json(force=True)
    name = data.get('name') if data else None
    user = data.get('user') if data else None
    if not name:
        return jsonify({'error': 'name required'}), 400
    if user:
        udir = _nextcloud_user_dir(user)
        p = os.path.join(udir, name)
    else:
        p = os.path.join(NEXTCLOUD_DIR, name)
    try:
        if os.path.exists(p):
            os.remove(p)
            return jsonify({'ok': True})
        return jsonify({'error': 'not found'}), 404
    except Exception as e:
        return jsonify({'error': 'delete error', 'detail': str(e)}), 500


def _nextcloud_user_dir(user: str) -> str:
    user_safe = _safe_username(user)
    d = os.path.join(NEXTCLOUD_DIR, user_safe)
    os.makedirs(d, exist_ok=True)
    return d


def _safe_username(uname: str) -> str:
    if not uname:
        return 'public'
    uname = os.path.basename(str(uname))
    uname = uname.replace(' ', '_')
    return ''.join(c for c in uname if c.isalnum() or c in ('-', '_')) or 'public'


def _sync_torrent_to_plex(src_path: str, safe_name: str):
    """Copy the saved .torrent into the Plex media folder and create a small .strm file
    so the torrent shows up in Plex. Also remove any copy in the mini-Nextcloud folder.
    """
    try:
        # copy torrent file
        dest_torrent = os.path.join(PLEX_TORRENTS_DIR, safe_name)
        try:
            import shutil
            shutil.copy2(src_path, dest_torrent)
        except Exception:
            # best-effort copy
            with open(src_path, 'rb') as r, open(dest_torrent, 'wb') as w:
                w.write(r.read())

        # create a .strm file that points to the torrent download URL on the streamer
        base_url = os.getenv('STREAMER_PUBLIC_URL') or 'http://127.0.0.1:8082'
        torrent_url = f"{base_url}/torrents/{safe_name}"
        # .strm filename use same base name but with .strm extension
        strm_name = os.path.splitext(safe_name)[0] + '.strm'
        strm_path = os.path.join(PLEX_TORRENTS_DIR, strm_name)
        with open(strm_path, 'w', encoding='utf-8') as s:
            s.write(torrent_url + '\n')

        # remove from mini-Nextcloud if present
        nc_path = os.path.join(NEXTCLOUD_DIR, safe_name)
        if os.path.exists(nc_path):
            try:
                os.remove(nc_path)
            except Exception:
                pass

        # Mark the torrent and its .strm pointer as owned by 'plex' so the
        # Plex owner can filter/list these in the owner UI.
        try:
            owners = _load_media_owners() or {}
            rel_torrent = os.path.relpath(dest_torrent, MEDIA_DIR).replace('\\', '/')
            rel_strm = os.path.relpath(strm_path, MEDIA_DIR).replace('\\', '/')
            owners[rel_torrent] = 'plex'
            owners[rel_strm] = 'plex'
            _save_media_owners(owners)
        except Exception:
            pass

        return True
    except Exception:
        return False


@app.route('/media/files', methods=['GET'])
def list_media_files():
    try:
        user = request.args.get('user')
        # When querying a specific user's files require a valid Authorization
        # Bearer token that maps to that same user. This prevents clients from
        # listing other users' torrents. (No longer rely on X-User header.)
        if user:
            sess = _get_session_from_bearer()
            if not sess:
                return jsonify({'error': 'authorization required'}), 401
            sess_user = sess.get('user') or sess.get('username') or sess.get('name') or sess.get('id')
            if not sess_user or sess_user != user:
                return jsonify({'error': 'forbidden'}), 403
        owners = _load_media_owners()
        files = []
        for root, dirs, filenames in os.walk(MEDIA_DIR):
            for fn in filenames:
                # skip internal owners file
                if fn == os.path.basename(MEDIA_OWNERS_FILE):
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, MEDIA_DIR).replace('\\', '/')
                try:
                    st = os.stat(full)
                    owner = owners.get(rel)
                    entry = {'path': rel, 'name': fn, 'size': st.st_size, 'mtime': int(st.st_mtime), 'url': f'/media/download/{rel}', 'owner': owner}
                    files.append(entry)
                except Exception:
                    continue
        if user:
            files = [f for f in files if f.get('owner') == user]
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': 'list error', 'detail': str(e)}), 500


@app.route('/media/download/<path:name>', methods=['GET'])
def media_download(name):
    try:
        # safe join
        full = os.path.join(MEDIA_DIR, name)
        if not os.path.exists(full):
            return jsonify({'error': 'not found'}), 404
        # serve file
        return send_from_directory(MEDIA_DIR, name, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'download error', 'detail': str(e)}), 500


@app.route('/media/stream/<path:name>', methods=['GET'])
def media_stream(name):
    try:
        # safe join
        full = os.path.join(MEDIA_DIR, name)
        if not os.path.exists(full):
            return jsonify({'error': 'not found'}), 404
        # serve file without forcing attachment so browsers can play media
        return send_from_directory(MEDIA_DIR, name, as_attachment=False)
    except Exception as e:
        return jsonify({'error': 'stream error', 'detail': str(e)}), 500


@app.route('/media/assign', methods=['POST'])
def media_assign():
    data = request.get_json(force=True)
    path = data.get('path') if data else None
    user = data.get('user') if data else None
    if not path or not user:
        return jsonify({'error': 'path and user required'}), 400
    owners = _load_media_owners()
    owners[path] = user
    if _save_media_owners(owners):
        return jsonify({'ok': True, 'path': path, 'user': user})
    return jsonify({'error': 'save failed'}), 500


def _safe_filename(fname: str) -> str:
    fname = os.path.basename(fname)
    fname = fname.replace(' ', '_')
    return ''.join(c for c in fname if c.isalnum() or c in ('-', '_', '.'))


# Redis + decryption helpers (optional)
REDIS_URL = os.getenv('REDIS_URL') or os.getenv('REDIS') or 'redis://127.0.0.1:6379/0'
try:
    _redis = redis.from_url(REDIS_URL, decode_responses=False) if redis else None
except Exception:
    _redis = None

WEB_API_SECRET = os.getenv('WEB_API_SECRET') or os.getenv('API_SECRET') or None
def _derive_key(secret: str):
    if not secret or not CRYPTO_AVAILABLE:
        return None
    salt = b'dbteam-salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key

FERNET = None
if WEB_API_SECRET and CRYPTO_AVAILABLE:
    try:
        key = _derive_key(WEB_API_SECRET)
        if key:
            FERNET = Fernet(key)
    except Exception:
        FERNET = None

def _decrypt_value(cipher: str) -> str:
    if not cipher:
        return None
    if not FERNET:
        return cipher
    try:
        if isinstance(cipher, bytes):
            cipher = cipher.decode()
        return FERNET.decrypt(cipher.encode()).decode()
    except Exception:
        return None

def _get_registered_devices():
    # returns list of device dicts stored in Redis key 'web:devices'
    out = []
    if not _redis:
        return out
    try:
        items = _redis.lrange('web:devices', 0, -1) or []
        for it in items:
            try:
                if isinstance(it, bytes):
                    s = it.decode('utf-8')
                else:
                    s = str(it)
                obj = _json.loads(s)
                # decrypt token if present
                token_enc = obj.get('token')
                if token_enc:
                    dec = _decrypt_value(token_enc)
                    obj['_token_dec'] = dec or token_enc
                out.append(obj)
            except Exception:
                continue
    except Exception:
        return out
    return out


@app.route('/panels/upload', methods=['POST'])
def upload_panel():
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    f = request.files['file']
    name = request.form.get('name') or f.filename or 'panel.css'
    desc = request.form.get('description') or ''
    safe = _safe_filename(name)
    panels_dir = os.path.join(os.path.dirname(__file__), '..', 'web', 'panels')
    os.makedirs(panels_dir, exist_ok=True)
    dest_path = os.path.join(panels_dir, safe)
    try:
        f.save(dest_path)
    except Exception as e:
        return jsonify({'error': 'save failed', 'detail': str(e)}), 500

    # update panels.json
    panels_file = os.path.join(panels_dir, 'panels.json')
    try:
        if os.path.exists(panels_file):
            with open(panels_file, 'r', encoding='utf-8') as pf:
                catalog = _json.load(pf)
        else:
            catalog = []
    except Exception:
        catalog = []

    entry_id = os.path.splitext(safe)[0]
    entry = {'id': entry_id, 'name': os.path.splitext(safe)[0], 'css': f'/panels/{safe}', 'description': desc}
    # avoid duplicates
    if not any(e.get('css') == entry['css'] for e in catalog):
        catalog.append(entry)
        try:
            with open(panels_file, 'w', encoding='utf-8') as pf:
                _json.dump(catalog, pf, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return jsonify({'ok': True, 'css': entry['css'], 'name': entry['name']})


@app.route('/stream/upload_torrent', methods=['POST'])
def upload_torrent():
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    f = request.files['file']
    name = f.filename or 'uploaded.torrent'
    safe = _safe_filename(name)
    dest = os.path.join(TORRENTS_DIR, safe)
    try:
        f.save(dest)
        # --- AUTO-SEED WITH WEBTORRENT-HYBRID ---
        # Use a lock file to avoid duplicate seeders for the same torrent
        lockfile = os.path.join(LOGS_DIR, f'seed_{safe}.lock')
        if not os.path.exists(lockfile):
            try:
                # Create lock file
                with open(lockfile, 'w') as lf:
                    lf.write('seeding')
                # Launch webtorrent-hybrid as a background process
                # Log output to logs/seed_<torrent>.out.log and .err.log
                out_log = os.path.join(LOGS_DIR, f'seed_{safe}.out.log')
                err_log = os.path.join(LOGS_DIR, f'seed_{safe}.err.log')
                # Use --keep-seeding to persist
                subprocess.Popen([
                    'webtorrent-hybrid',
                    os.path.abspath(dest),
                    '--keep-seeding'
                ], stdout=open(out_log, 'ab'), stderr=open(err_log, 'ab'))
            except Exception as e:
                # Remove lockfile if failed
                try:
                    os.remove(lockfile)
                except Exception:
                    pass
                # Log error but do not block upload
                err_log = os.path.join(LOGS_DIR, f'seed_{safe}.err.log')
                with open(err_log, 'ab') as ef:
                    ef.write(f'Failed to launch webtorrent-hybrid: {str(e)}\n'.encode('utf-8'))
        # ensure torrent is also available in Plex media folder and remove from Nextcloud if present
        try:
            _sync_torrent_to_plex(dest, safe)
        except Exception:
            pass

        # support assigning this upload to a specific user so the torrent and its .strm
        # are copied into a user-specific media folder (so Plex can show it under that
        # user's section). The request can provide `assign_user` (form/query/header).
        assign_user = None
        try:
            assign_user = request.form.get('assign_user') or request.args.get('assign_user') or request.headers.get('X-Assign-User')
        except Exception:
            assign_user = None
        if assign_user:
            try:
                u_safe = _safe_username(assign_user)
                user_torrents_dir = os.path.join(MEDIA_DIR, u_safe, 'torrents')
                os.makedirs(user_torrents_dir, exist_ok=True)
                # copy torrent to user folder
                user_torrent_dest = os.path.join(user_torrents_dir, safe)
                try:
                    import shutil
                    shutil.copy2(dest, user_torrent_dest)
                except Exception:
                    with open(dest, 'rb') as r, open(user_torrent_dest, 'wb') as w:
                        w.write(r.read())

                # create .strm in user folder
                base_url = os.getenv('STREAMER_PUBLIC_URL') or 'http://127.0.0.1:8082'
                torrent_url = f"{base_url}/torrents/{safe}"
                user_strm_name = os.path.splitext(safe)[0] + '.strm'
                user_strm_path = os.path.join(user_torrents_dir, user_strm_name)
                with open(user_strm_path, 'w', encoding='utf-8') as s:
                    s.write(torrent_url + '\n')

                # register ownership entries for user-visible listing
                try:
                    owners = _load_media_owners() or {}
                    rel_t = os.path.relpath(user_torrent_dest, MEDIA_DIR).replace('\\', '/')
                    rel_s = os.path.relpath(user_strm_path, MEDIA_DIR).replace('\\', '/')
                    owners[rel_t] = u_safe
                    owners[rel_s] = u_safe
                    _save_media_owners(owners)
                except Exception:
                    pass
            except Exception:
                pass

        # if device_id provided and not 'local', attempt to forward
        device_id = request.form.get('device_id') or request.args.get('device_id')
        # special local test receiver shortcut
        if device_id == 'LOCAL_TEST_RECEIVER':
            try:
                with open(dest, 'rb') as fh:
                    files = {'file': (safe, fh)}
                    r = requests.post('http://127.0.0.1:8082/test/receive', files=files, timeout=10)
                if r.ok:
                    return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': True, 'forward_status': r.status_code, 'forward_response': r.text})
                else:
                    return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': False, 'forward_status': r.status_code, 'forward_response': r.text}), 502
            except Exception as e:
                return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': False, 'forward_error': str(e)}), 502
        if device_id and device_id != 'local':
            # find device in redis list
            devices = _get_registered_devices()
            match = None
            for d in devices:
                if d.get('id') == device_id or d.get('name') == device_id:
                    match = d
                    break
            if match:
                # build target URL
                target_base = match.get('id') or device_id
                if target_base.startswith('http://') or target_base.startswith('https://'):
                    base_url = target_base.rstrip('/')
                else:
                    base_url = 'http://' + target_base.rstrip('/')
                target_url = base_url + '/stream/upload_torrent'
                try:
                    with open(dest, 'rb') as fh:
                        headers = {}
                        tok = match.get('_token_dec') or match.get('token')
                        if tok:
                            headers['Authorization'] = 'Bearer ' + tok
                        files = {'file': (safe, fh)}
                        resp = requests.post(target_url, files=files, headers=headers, timeout=20)
                    if resp.ok:
                        return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': True, 'forward_status': resp.status_code, 'forward_response': resp.text})
                    else:
                        return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': False, 'forward_status': resp.status_code, 'forward_response': resp.text}), 502
                except Exception as e:
                    return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': False, 'forward_error': str(e)}), 502
            else:
                return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}', 'forwarded': False, 'error': 'device not found'}), 404

        return jsonify({'ok': True, 'name': safe, 'path': f'/torrents/{safe}'})
    except Exception as e:
        return jsonify({'error': 'save failed', 'detail': str(e)}), 500


# --- Live settings and API key management ---
SETTINGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'streams')
os.makedirs(SETTINGS_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'live_settings.json')
APIKEY_FILE = os.path.join(SETTINGS_DIR, 'live_api_key.txt')


def _read_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return _json.load(f)
    except Exception:
        pass
    return {}


def _write_settings(obj):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            _json.dump(obj, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _read_apikey():
    try:
        if os.path.exists(APIKEY_FILE):
            with open(APIKEY_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def _write_apikey(key):
    try:
        with open(APIKEY_FILE, 'w', encoding='utf-8') as f:
            f.write(key)
        return True
    except Exception:
        return False


def _generate_key():
    import secrets, base64
    return base64.urlsafe_b64encode(secrets.token_bytes(24)).decode('ascii').rstrip('=')


@app.route('/stream/settings', methods=['GET'])
def get_settings():
    return jsonify({'settings': _read_settings()})


@app.route('/stream/settings', methods=['POST'])
def post_settings():
    data = request.get_json(force=True)
    if not data:
        return jsonify({'error': 'no data'}), 400
    ok = _write_settings(data)
    if ok:
        return jsonify({'ok': True})
    return jsonify({'error': 'write failed'}), 500


@app.route('/stream/apikey', methods=['GET'])
def get_apikey():
    key = _read_apikey()
    if not key:
        key = _generate_key()
        _write_apikey(key)
    return jsonify({'key': key})


@app.route('/stream/apikey', methods=['POST'])
def regenerate_apikey():
    key = _generate_key()
    ok = _write_apikey(key)
    if ok:
        return jsonify({'ok': True, 'key': key})
    return jsonify({'error': 'write failed'}), 500


@app.route('/admin/send_torrent', methods=['POST'])
def admin_send_torrent():
    data = request.get_json(force=True)
    name = data.get('name') if data else None
    if not name:
        return jsonify({'error': 'name required'}), 400
    p = os.path.join(TORRENTS_DIR, name)
    if not os.path.exists(p):
        return jsonify({'error': 'not found'}), 404
    try:
        script = os.path.join(os.path.dirname(__file__), '..', 'tools', 'send_torrent_via_bot.py')
        env = os.environ.copy()
        env['SELECTED_TORRENT'] = os.path.abspath(p)
        # log files
        out_log = os.path.join(LOGS_DIR, f'send_torrent_{name}.stdout.log')
        err_log = os.path.join(LOGS_DIR, f'send_torrent_{name}.stderr.log')
        with open(out_log, 'ab') as out_f, open(err_log, 'ab') as err_f:
            proc = subprocess.Popen([sys.executable, script], env=env, stdout=out_f, stderr=err_f)
        return jsonify({'ok': True, 'pid': proc.pid})
    except Exception as e:
        return jsonify({'error': 'exec error', 'detail': str(e)}), 500


@app.route('/test/receive', methods=['POST'])
def test_receive():
    # simple receiver for testing forwarded uploads
    if 'file' not in request.files:
        return jsonify({'error': 'file required'}), 400
    f = request.files['file']
    name = f.filename or 'uploaded.torrent'
    # save to a temporary path
    tmp = os.path.join(TORRENTS_DIR, 'test_received_' + _safe_filename(name))
    try:
        f.save(tmp)
        return jsonify({'ok': True, 'received': True, 'saved': tmp})
    except Exception as e:
        return jsonify({'error': 'save failed', 'detail': str(e)}), 500


@app.route('/stream/test_forward', methods=['GET'])
def stream_test_forward():
    """Helper to trigger a forward from an existing example torrent file for testing.
       It POSTs the example file to `/stream/upload_torrent?device_id=LOCAL_TEST_RECEIVER` so
       the upload_torrent logic saves and then forwards to `/test/receive`.
    """
    sample = os.path.join(TORRENTS_DIR, 'example-sample.torrent')
    if not os.path.exists(sample):
        return jsonify({'error': 'sample torrent not found', 'path': sample}), 404
    try:
        with open(sample, 'rb') as fh:
            files = {'file': ('example-sample.torrent', fh)}
            resp = requests.post('http://127.0.0.1:8082/stream/upload_torrent?device_id=LOCAL_TEST_RECEIVER', files=files, timeout=20)
        return (resp.text, resp.status_code, {'Content-Type': 'application/json'})
    except Exception as e:
        return jsonify({'error': 'forward failed', 'detail': str(e)}), 500


@app.route('/stream/add_magnet', methods=['POST'])
def add_magnet():
    """Accept a magnet link and either forward it to a registered device or
    create a .strm in the Plex torrents folder so Plex can surface it.

    POST JSON: { "magnet": "magnet:?xt=...", "device_id": "optional" }
    Or form field `magnet` / header `X-User` may be used.
    """
    try:
        data = None
        try:
            if request.is_json:
                data = request.get_json(force=True)
        except Exception:
            data = None

        magnet = None
        if data:
            magnet = data.get('magnet')
        if not magnet:
            magnet = request.form.get('magnet') or request.args.get('magnet') or request.headers.get('X-Magnet')
        if not magnet:
            return jsonify({'error': 'magnet required'}), 400

        # determine user/device
        device_id = None
        if data:
            device_id = data.get('device_id')
        if not device_id:
            device_id = request.form.get('device_id') or request.args.get('device_id')

        user = None
        try:
            user = request.headers.get('X-User')
        except Exception:
            user = None

        # If device specified and not local, try to forward to that device
        if device_id and device_id != 'local':
            devices = _get_registered_devices()
            match = None
            for d in devices:
                if d.get('id') == device_id or d.get('name') == device_id:
                    match = d
                    break
            if match:
                target_base = match.get('id') or device_id
                if target_base.startswith('http://') or target_base.startswith('https://'):
                    base_url = target_base.rstrip('/')
                else:
                    base_url = 'http://' + target_base.rstrip('/')
                target_url = base_url + '/stream/add_magnet'
                try:
                    headers = {'Content-Type': 'application/json'}
                    tok = match.get('_token_dec') or match.get('token')
                    if tok:
                        headers['Authorization'] = 'Bearer ' + tok
                    resp = requests.post(target_url, json={'magnet': magnet}, headers=headers, timeout=20)
                    if resp.ok:
                        return jsonify({'ok': True, 'forwarded': True, 'status': resp.status_code, 'response': resp.text})
                    else:
                        return jsonify({'ok': True, 'forwarded': False, 'status': resp.status_code, 'response': resp.text}), 502
                except Exception as e:
                    return jsonify({'ok': True, 'forwarded': False, 'error': str(e)}), 502

        # fallback: create a .strm file in the Plex torrents dir that contains the magnet link
        try:
            # create deterministic name from magnet
            h = hashlib.sha1(magnet.encode('utf-8')).hexdigest()[:16]
            strm_name = f'magnet_{h}.strm'
            strm_path = os.path.join(PLEX_TORRENTS_DIR, strm_name)
            with open(strm_path, 'w', encoding='utf-8') as s:
                s.write(magnet + '\n')

            # mark owner as plex if header indicates plex user or user param is plex
            if (user and user.lower() == 'plex') or (request.args.get('user') == 'plex'):
                try:
                    owners = _load_media_owners() or {}
                    rel = os.path.relpath(strm_path, MEDIA_DIR).replace('\\', '/')
                    owners[rel] = 'plex'
                    _save_media_owners(owners)
                except Exception:
                    pass

            return jsonify({'ok': True, 'path': f'/media/download/torrents/{strm_name}', 'strm': strm_name})
        except Exception as e:
            return jsonify({'error': 'create failed', 'detail': str(e)}), 500

    except Exception as e:
        return jsonify({'error': 'internal', 'detail': str(e)}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8082)
