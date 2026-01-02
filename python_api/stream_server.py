from flask import Flask, jsonify, request, send_from_directory
import os
import json
import subprocess
import signal
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
import json as _json

app = Flask(__name__)

# CORS fallback: prefer flask_cors if available, otherwise set permissive headers
try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    @app.after_request
    def _cors_fix(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    @app.route('/', methods=['OPTIONS'])
    def _options():
        return ('', 204)

SCENES_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'streams', 'scenes')
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
TORRENTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'torrents')
os.makedirs(SCENES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(TORRENTS_DIR, exist_ok=True)


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


def _safe_filename(fname: str) -> str:
    fname = os.path.basename(fname)
    fname = fname.replace(' ', '_')
    return ''.join(c for c in fname if c.isalnum() or c in ('-', '_', '.'))


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


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8082)
