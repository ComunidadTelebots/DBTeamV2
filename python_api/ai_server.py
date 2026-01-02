#!/usr/bin/env python3
"""
Flask AI server that exposes endpoints used by `model_chat.js`.

Endpoints:
 - GET /models/list -> { models: [ 'gpt2' ] }
 - POST /models/run -> { model, prompt } -> proxies to GPT-2 generator
 - POST /ai/gpt2 -> { prompt, max_length }

Model files are stored under the directory specified by environment var `PYMODEL_DIR`
or `./models/gpt2` by default. That folder is added to .gitignore to avoid committing models.
"""
import os
import argparse
from pathlib import Path
from flask import Flask, request, jsonify
try:
    from flask_cors import CORS
except Exception:
    CORS = None
import subprocess
import sys
import platform
import signal
import time
import json

app = Flask(__name__)

try:
    import psutil
except Exception:
    psutil = None


def _collect_docker_info():
    # Try docker SDK first, fallback to CLI `docker stats`/`docker ps` parsing
    try:
        try:
            import docker as _docker
        except Exception:
            _docker = None
        out = []
        if _docker is not None:
            try:
                cli = _docker.from_env()
                for c in cli.containers.list(all=True):
                    try:
                        info = {'id': c.id, 'name': c.name, 'image': getattr(c, 'image', None).tags[0] if getattr(c, 'image', None) and getattr(c, 'image', None).tags else None, 'status': c.status}
                        # try to get stats via low-level API
                        try:
                            stats = cli.api.stats(c.id, stream=False)
                            # cpu percent calc best-effort: use precalculated field if present
                            cpu = None
                            try:
                                cpu = float(stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0))
                            except Exception:
                                cpu = None
                            info.update({'raw_stats': stats, 'cpu_percent': None, 'memory_rss': None})
                            try:
                                mem = stats.get('memory_stats', {}).get('usage')
                                info['memory_rss'] = int(mem) if mem is not None else None
                            except Exception:
                                pass
                        except Exception:
                            pass
                        out.append(info)
                    except Exception:
                        continue
            except Exception:
                out = []
        else:
            # fallback to CLI
            try:
                p = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True, timeout=5)
                if p.returncode == 0 and p.stdout:
                    for line in p.stdout.splitlines():
                        try:
                            j = json.loads(line)
                            # j contains fields like Name, CPUPerc, MemUsage, MemPerc, Container
                            name = j.get('Name')
                            cid = j.get('Container')
                            cpu = None
                            try:
                                cpu = float(str(j.get('CPUPerc','')).strip().strip('%'))
                            except Exception:
                                cpu = None
                            mem_usage = None
                            try:
                                mu = j.get('MemUsage','')
                                # format: "12.34MiB / 1.952GiB"
                                used = mu.split('/')[0].strip()
                                # best-effort parse size
                                def parse_size(s):
                                    s = s.strip()
                                    if s.endswith('KiB'):
                                        return float(s[:-3].strip())*1024
                                    if s.endswith('MiB'):
                                        return float(s[:-3].strip())*1024*1024
                                    if s.endswith('GiB'):
                                        return float(s[:-3].strip())*1024*1024*1024
                                    if s.endswith('B'):
                                        return float(s[:-1].strip())
                                    return None
                                mem_usage = parse_size(used)
                            except Exception:
                                mem_usage = None
                            out.append({'id': cid, 'name': name, 'cpu_percent': cpu, 'memory_rss': mem_usage})
            except Exception:
                out = []
        return out
    except Exception as e:
        return {'error': str(e)}


def _collect_k8s_info():
    # Try kubernetes python client; fallback to `kubectl` CLI top/get
    try:
        try:
            from kubernetes import client as kclient, config as kconfig
        except Exception:
            kclient = None
            kconfig = None
        pods_out = []
        metrics_map = {}
        # try kubectl top pods for simple metrics
        try:
            p = subprocess.run(['kubectl', 'top', 'pods', '--all-namespaces', '--no-headers'], capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout:
                for line in p.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 3:
                        ns = parts[0]; name = parts[1]; cpu = parts[2]; mem = parts[3] if len(parts) > 3 else None
                        metrics_map[f"{ns}/{name}"] = {'cpu': cpu, 'mem': mem}
        except Exception:
            pass

        if kclient is not None and kconfig is not None:
            try:
                try:
                    kconfig.load_kube_config()
                except Exception:
                    try:
                        kconfig.load_incluster_config()
                    except Exception:
                        pass
                v1 = kclient.CoreV1Api()
                pods = v1.list_pod_for_all_namespaces(watch=False)
                for p in pods.items:
                    try:
                        name = p.metadata.name
                        ns = p.metadata.namespace
                        status = p.status.phase
                        node = p.spec.node_name
                        start = p.status.start_time
                        age = None
                        if start:
                            try:
                                age = int(time.time() - start.timestamp())
                            except Exception:
                                age = None
                        key = f"{ns}/{name}"
                        met = metrics_map.get(key)
                        pods_out.append({'namespace': ns, 'name': name, 'node': node, 'status': status, 'restarts': sum([c.restart_count for c in (p.status.container_statuses or [])]) if p.status.container_statuses else 0, 'cpu': met.get('cpu') if met else None, 'mem': met.get('mem') if met else None, 'age_seconds': age})
                    except Exception:
                        continue
            except Exception:
                pods_out = []
        else:
            # fallback to kubectl get pods
            try:
                p = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json'], capture_output=True, text=True, timeout=5)
                if p.returncode == 0 and p.stdout:
                    j = json.loads(p.stdout)
                    for it in j.get('items', []):
                        md = it.get('metadata', {})
                        st = it.get('status', {})
                        ns = md.get('namespace')
                        name = md.get('name')
                        node = st.get('nodeName')
                        phase = st.get('phase')
                        start = st.get('startTime')
                        age = None
                        try:
                            if start:
                                # parse ISO time
                                from datetime import datetime
                                dt = datetime.fromisoformat(start.replace('Z','+00:00'))
                                age = int(time.time() - dt.timestamp())
                        except Exception:
                            age = None
                        key = f"{ns}/{name}"
                        met = metrics_map.get(key)
                        pods_out.append({'namespace': ns, 'name': name, 'node': node, 'status': phase, 'cpu': met.get('cpu') if met else None, 'mem': met.get('mem') if met else None, 'age_seconds': age})
            except Exception:
                pods_out = []
        return pods_out
    except Exception as e:
        return {'error': str(e)}


def load_generator(model_dir: str):
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    except Exception as e:
        raise RuntimeError("Install transformers and torch: see python_api/requirements_ai.txt") from e

    cache_dir = model_dir
    tokenizer = AutoTokenizer.from_pretrained("gpt2", cache_dir=cache_dir)
    model = AutoModelForCausalLM.from_pretrained("gpt2", cache_dir=cache_dir)
    gen = pipeline("text-generation", model=model, tokenizer=tokenizer, device=-1)
    return gen


def create_app(model_dir: str):
    # ensure model dir exists (but don't auto-download huge files without user knowledge)
    os.makedirs(model_dir, exist_ok=True)
    # Lazy load on first request to avoid startup delay
    generator = {"obj": None}

    def get_gen():
        if generator["obj"] is None:
            generator["obj"] = load_generator(model_dir)
        return generator["obj"]

    # Enable CORS: prefer flask_cors if available, otherwise add permissive headers
    if CORS:
        CORS(app)
    else:
        @app.after_request
        def _add_cors_headers(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
            return response

        # Generic OPTIONS handler to answer preflight requests
        @app.route('/<path:path>', methods=['OPTIONS'])
        @app.route('/', methods=['OPTIONS'])
        def _options(path=None):
            return ('', 200)

    @app.route('/models/list', methods=['GET'])
    def models_list():
        # detect installed models by presence in model_dir
        installed = []
        try:
            if Path(model_dir).exists():
                # simple heuristic: if tokenizer files present
                files = list(Path(model_dir).rglob('*token*'))
                if files:
                    installed.append('gpt2')
        except Exception:
            pass
        return jsonify({"models": installed})

    @app.route('/models/install', methods=['POST'])
    def models_install():
        data = request.get_json(force=True) or {}
        model = data.get('model')
        if not model:
            return jsonify({"error": "model required"}), 400
        # Only allow safe model names (basic check)
        if not isinstance(model, str) or '..' in model or model.startswith('/'):
            return jsonify({"error": "invalid model name"}), 400
        try:
            # Download tokenizer and model into cache_dir (model_dir)
            from transformers import AutoTokenizer, AutoModelForCausalLM
            tokenizer = AutoTokenizer.from_pretrained(model, cache_dir=model_dir)
            model_obj = AutoModelForCausalLM.from_pretrained(model, cache_dir=model_dir)
            return jsonify({"ok": True, "model": model})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/models/run', methods=['POST'])
    def models_run():
        data = request.get_json(force=True) or {}
        model = data.get('model')
        prompt = data.get('prompt')
        max_length = int(data.get('max_length', 150))
        if not model or not prompt:
            return jsonify({"error": "model and prompt required"}), 400
        if model != 'gpt2':
            return jsonify({"error": f"model {model} not supported by this server"}), 501
        try:
            gen = get_gen()
            out = gen(prompt, max_length=max_length, do_sample=True, top_k=50, num_return_sequences=1)
            return jsonify({"result": out})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/ai/gpt2', methods=['POST'])
    def ai_gpt2():
        data = request.get_json(force=True) or {}
        prompt = data.get('prompt')
        max_length = int(data.get('max_length', 150))
        if not prompt:
            return jsonify({"error": "prompt required"}), 400
        try:
            gen = get_gen()
            out = gen(prompt, max_length=max_length, do_sample=True, top_k=50, num_return_sequences=1)
            text = out[0].get('generated_text') if isinstance(out, list) and out else str(out)
            return jsonify({"reply": text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- Monitor control endpoints ---
    # The monitor script created in tools/keep_services_*.ps1|sh writes logs to ../logs/service_monitor.log

    monitor_proc = {"p": None}

    def monitor_log_path():
        # logs directory relative to project root
        return str(Path(app.root_path).parents[0] / 'logs' / 'service_monitor.log')

    def monitor_pid_path():
        return str(Path(app.root_path).parents[0] / 'logs' / 'service_monitor.pid')

    def process_exists(pid):
        try:
            if isinstance(pid, str):
                pid = pid.strip().lstrip('\ufeff')
            pid = int(pid)
        except Exception:
            return False
        if pid <= 0:
            return False
        try:
            if platform.system().lower().startswith('windows'):
                # use tasklist to check pid (use shell form for consistent quoting/encoding)
                cmd = f'tasklist /FI "PID eq {pid}"'
                out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True, shell=True)
                return str(pid) in out
            else:
                # POSIX ps
                out = subprocess.check_output(['ps', '-p', str(pid)], stderr=subprocess.DEVNULL, universal_newlines=True)
                return str(pid) in out
        except Exception:
            return False

    def is_monitor_running():
        p = monitor_proc.get("p")
        if (p is not None) and (p.poll() is None):
            return True
        # fallback: check pidfile
        try:
            pidf = monitor_pid_path()
            if Path(pidf).exists():
                pid = Path(pidf).read_text().strip()
                return process_exists(pid)
        except Exception:
            pass
        return False

    def start_monitor_process():
        if is_monitor_running():
            return monitor_proc["p"]
        repo_root = Path(app.root_path).parents[0]
        if platform.system().lower().startswith('windows'):
            # use the cleaned monitor script name
            script = repo_root / 'tools' / 'keep_services_windows_clean.ps1'
            cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
        else:
            script = repo_root / 'tools' / 'keep_services_linux.sh'
            cmd = ['bash', str(script)]
        logfile = repo_root / 'logs' / 'service_monitor_stdout.log'
        logfile.parent.mkdir(parents=True, exist_ok=True)
        f = open(str(logfile), 'a')
        # Start detached so it survives when this process exits if needed
        creationflags = 0
        # DETACHED_PROCESS on Windows (0x8) to avoid inheriting console
        if platform.system().lower().startswith('windows'):
            creationflags = 0x00000008
            p = subprocess.Popen(cmd, cwd=str(repo_root), stdout=f, stderr=subprocess.STDOUT, creationflags=creationflags)
        else:
            p = subprocess.Popen(cmd, cwd=str(repo_root), stdout=f, stderr=subprocess.STDOUT)
        monitor_proc["p"] = p
        # write pidfile so external monitor instances are detectable
        try:
            pidf = monitor_pid_path()
            Path(pidf).write_text(str(p.pid))
        except Exception:
            pass
        return p

    def stop_monitor_process():
        p = monitor_proc.get("p")
        stopped = False
        pidf = monitor_pid_path()
        if p is None:
            # try stopping via pidfile
            try:
                if Path(pidf).exists():
                    pid = int(Path(pidf).read_text().strip())
                    if platform.system().lower().startswith('windows'):
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    stopped = True
            except Exception:
                stopped = False
            try:
                if Path(pidf).exists():
                    Path(pidf).unlink()
            except Exception:
                pass
            return stopped
        try:
            if platform.system().lower().startswith('windows'):
                p.terminate()
            else:
                p.send_signal(signal.SIGTERM)
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        monitor_proc["p"] = None
        try:
            if Path(pidf).exists():
                Path(pidf).unlink()
        except Exception:
            pass
        return True

    @app.route('/monitor/status', methods=['GET'])
    def monitor_status():
        logp = monitor_log_path()
        tail = ''
        try:
            if Path(logp).exists():
                with open(logp, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = fh.readlines()
                    tail = ''.join(lines[-200:])
        except Exception:
            tail = ''
        return jsonify({
            'running': is_monitor_running(),
            'pid': monitor_proc.get('p').pid if monitor_proc.get('p') else None,
            'log_tail': tail
        })

    @app.route('/monitor/start', methods=['POST'])
    def monitor_start():
        if is_monitor_running():
            return jsonify({'ok': True, 'running': True}), 200
        try:
            p = start_monitor_process()
            return jsonify({'ok': True, 'pid': p.pid}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/monitor/stop', methods=['POST'])
    def monitor_stop():
        if not is_monitor_running():
            return jsonify({'ok': True, 'running': False}), 200
        try:
            stop_monitor_process()
            return jsonify({'ok': True}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/monitor/service/status', methods=['GET'])
    def monitor_service_status():
        # return list of configured services and pid/status if available
        repo_root = Path(app.root_path).parents[0]
        logdir = repo_root / 'logs'
        services = []
        # mirror the services defined in the windows script
        svc_defs = [
            {'name': 'StaticWeb', 'cmd': 'py -3 -m http.server 8000 --directory web'},
            {'name': 'AIServer', 'cmd': 'py -3 python_api\\ai_server.py --host 127.0.0.1 --port 8081'}
        ]
        for s in svc_defs:
            pidfile = logdir / f'service_{s["name"]}.pid'
            pid = None
            running = False
            cpu = None
            memory = None
            uptime = None
            try:
                if pidfile.exists():
                    pid = pidfile.read_text().strip()
                    running = process_exists(pid)
            except Exception:
                pid = None
                running = False
            # if running and psutil available, collect basic process metrics
            if running and pid and psutil is not None:
                try:
                    p = psutil.Process(int(pid))
                    # non-blocking cpu_percent: first call may be 0.0, try a short interval
                    try:
                        cpu = p.cpu_percent(interval=0.1)
                    except Exception:
                        cpu = None
                    try:
                        memory = int(p.memory_info().rss)
                    except Exception:
                        memory = None
                    try:
                        uptime = int(time.time() - p.create_time())
                    except Exception:
                        uptime = None
                except Exception:
                    cpu = None; memory = None; uptime = None

            services.append({'name': s['name'], 'cmd': s['cmd'], 'pid': pid, 'running': running, 'cpu_percent': cpu, 'memory_rss': memory, 'uptime_seconds': uptime})
        # attach docker and k8s info if available
        docker_info = _collect_docker_info()
        k8s_info = _collect_k8s_info()
        return jsonify({'services': services, 'docker': docker_info, 'k8s': k8s_info})

        def _collect_docker_info():
            # Try docker SDK first, fallback to CLI `docker stats`/`docker ps` parsing
            try:
                try:
                    import docker as _docker
                except Exception:
                    _docker = None
                out = []
                if _docker is not None:
                    try:
                        cli = _docker.from_env()
                        for c in cli.containers.list(all=True):
                            try:
                                info = {'id': c.id, 'name': c.name, 'image': getattr(c, 'image', None).tags[0] if getattr(c, 'image', None) and getattr(c, 'image', None).tags else None, 'status': c.status}
                                # try to get stats via low-level API
                                try:
                                    stats = cli.api.stats(c.id, stream=False)
                                    # cpu percent calc best-effort: use precalculated field if present
                                    cpu = None
                                    try:
                                        cpu = float(stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0))
                                    except Exception:
                                        cpu = None
                                    info.update({'raw_stats': stats, 'cpu_percent': None, 'memory_rss': None})
                                    try:
                                        mem = stats.get('memory_stats', {}).get('usage')
                                        info['memory_rss'] = int(mem) if mem is not None else None
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                                out.append(info)
                            except Exception:
                                continue
                    except Exception:
                        out = []
                else:
                    # fallback to CLI
                    try:
                        p = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True, timeout=5)
                        if p.returncode == 0 and p.stdout:
                            for line in p.stdout.splitlines():
                                try:
                                    j = json.loads(line)
                                    # j contains fields like Name, CPUPerc, MemUsage, MemPerc, Container
                                    name = j.get('Name')
                                    cid = j.get('Container')
                                    cpu = None
                                    try:
                                        cpu = float(str(j.get('CPUPerc','')).strip().strip('%'))
                                    except Exception:
                                        cpu = None
                                    mem_usage = None
                                    try:
                                        mu = j.get('MemUsage','')
                                        # format: "12.34MiB / 1.952GiB"
                                        used = mu.split('/')[0].strip()
                                        # best-effort parse size
                                        def parse_size(s):
                                            s = s.strip()
                                            if s.endswith('KiB'):
                                                return float(s[:-3].strip())*1024
                                            if s.endswith('MiB'):
                                                return float(s[:-3].strip())*1024*1024
                                            if s.endswith('GiB'):
                                                return float(s[:-3].strip())*1024*1024*1024
                                            if s.endswith('B'):
                                                return float(s[:-1].strip())
                                            return None
                                        mem_usage = parse_size(used)
                                    except Exception:
                                        mem_usage = None
                                    out.append({'id': cid, 'name': name, 'cpu_percent': cpu, 'memory_rss': mem_usage})
                    except Exception:
                        out = []
                return out
            except Exception as e:
                return {'error': str(e)}


        def _collect_k8s_info():
            # Try kubernetes python client; fallback to `kubectl` CLI top/get
            try:
                try:
                    from kubernetes import client as kclient, config as kconfig
                except Exception:
                    kclient = None
                    kconfig = None
                pods_out = []
                metrics_map = {}
                # try kubectl top pods for simple metrics
                try:
                    p = subprocess.run(['kubectl', 'top', 'pods', '--all-namespaces', '--no-headers'], capture_output=True, text=True, timeout=5)
                    if p.returncode == 0 and p.stdout:
                        for line in p.stdout.splitlines():
                            parts = line.split()
                            if len(parts) >= 3:
                                ns = parts[0]; name = parts[1]; cpu = parts[2]; mem = parts[3] if len(parts) > 3 else None
                                metrics_map[f"{ns}/{name}"] = {'cpu': cpu, 'mem': mem}
                except Exception:
                    pass

                if kclient is not None and kconfig is not None:
                    try:
                        try:
                            kconfig.load_kube_config()
                        except Exception:
                            try:
                                kconfig.load_incluster_config()
                            except Exception:
                                pass
                        v1 = kclient.CoreV1Api()
                        pods = v1.list_pod_for_all_namespaces(watch=False)
                        for p in pods.items:
                            try:
                                name = p.metadata.name
                                ns = p.metadata.namespace
                                status = p.status.phase
                                node = p.spec.node_name
                                start = p.status.start_time
                                age = None
                                if start:
                                    try:
                                        age = int(time.time() - start.timestamp())
                                    except Exception:
                                        age = None
                                key = f"{ns}/{name}"
                                met = metrics_map.get(key)
                                pods_out.append({'namespace': ns, 'name': name, 'node': node, 'status': status, 'restarts': sum([c.restart_count for c in (p.status.container_statuses or [])]) if p.status.container_statuses else 0, 'cpu': met.get('cpu') if met else None, 'mem': met.get('mem') if met else None, 'age_seconds': age})
                            except Exception:
                                continue
                    except Exception:
                        pods_out = []
                else:
                    # fallback to kubectl get pods
                    try:
                        p = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces', '-o', 'json'], capture_output=True, text=True, timeout=5)
                        if p.returncode == 0 and p.stdout:
                            j = json.loads(p.stdout)
                            for it in j.get('items', []):
                                md = it.get('metadata', {})
                                st = it.get('status', {})
                                ns = md.get('namespace')
                                name = md.get('name')
                                node = st.get('nodeName')
                                phase = st.get('phase')
                                start = st.get('startTime')
                                age = None
                                try:
                                    if start:
                                        # parse ISO time
                                        from datetime import datetime
                                        dt = datetime.fromisoformat(start.replace('Z','+00:00'))
                                        age = int(time.time() - dt.timestamp())
                                except Exception:
                                    age = None
                                key = f"{ns}/{name}"
                                met = metrics_map.get(key)
                                pods_out.append({'namespace': ns, 'name': name, 'node': node, 'status': phase, 'cpu': met.get('cpu') if met else None, 'mem': met.get('mem') if met else None, 'age_seconds': age})
                    except Exception:
                        pods_out = []
                return pods_out
            except Exception as e:
                return {'error': str(e)}
    @app.route('/monitor/service/restart', methods=['POST'])
    def monitor_service_restart():
        data = request.get_json(force=True) or {}
        svc = data.get('service')
        if not svc:
            return jsonify({'error': 'service required'}), 400
        repo_root = Path(app.root_path).parents[0]
        logdir = repo_root / 'logs'
        pidfile = logdir / f'service_{svc}.pid'
        try:
            if pidfile.exists():
                pid = int(pidfile.read_text().strip())
                if platform.system().lower().startswith('windows'):
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.kill(pid, signal.SIGTERM)
            else:
                # no pidfile - attempt graceful restart by touching monitor's restart behavior: try stop then start monitor
                pass
            return jsonify({'ok': True}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/monitor/service/restart_all', methods=['POST'])
    def monitor_service_restart_all():
        repo_root = Path(app.root_path).parents[0]
        logdir = repo_root / 'logs'
        svc_defs = [
            {'name': 'StaticWeb', 'cmd': 'py -3 -m http.server 8000 --directory web'},
            {'name': 'AIServer', 'cmd': 'py -3 python_api\\ai_server.py --host 127.0.0.1 --port 8081'}
        ]
        restarted = []
        errors = []
        for s in svc_defs:
            try:
                pidfile = logdir / f'service_{s["name"]}.pid'
                if pidfile.exists():
                    pid = int(pidfile.read_text().strip())
                    if platform.system().lower().startswith('windows'):
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        os.kill(pid, signal.SIGTERM)
                    restarted.append(s['name'])
                else:
                    # nothing to kill, still mark to let monitor start them if down
                    restarted.append(s['name'])
            except Exception as e:
                errors.append({'service': s['name'], 'error': str(e)})
        return jsonify({'ok': True, 'restarted': restarted, 'errors': errors}), 200

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8081)
    parser.add_argument('--model-dir', default=os.environ.get('PYMODEL_DIR', './models/gpt2'))
    args = parser.parse_args()

    model_dir = str(Path(args.model_dir).resolve())
    print(f'Using model dir: {model_dir}')
    app = create_app(model_dir)
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
