"""Plugin wrapper to run `scripts/scan_cves.py` at bot startup and expose commands.

Commands:
- /scan_report: show a short summary of the last scan
- /scan_now: trigger a new scan (runs in background)
"""
import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from typing import Any


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def _log(msg: str):
    try:
        repo = _repo_root()
        p = os.path.join(repo, 'bot.log')
        with open(p, 'a', encoding='utf-8') as f:
            f.write(f"[scan_plugin] {msg}\n")
    except Exception:
        pass


def _run_scan(repo: str, output_path: str):
    script = os.path.join(repo, 'scripts', 'scan_cves.py')
    if not os.path.exists(script):
        _log(f'script not found: {script}')
        return
    cmd = [sys.executable, script, '--path', repo, '--output', output_path]
    try:
        _log(f'Running scan: {cmd}')
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        _log(f'scan returncode={proc.returncode}')
        if proc.stdout:
            _log(f'scan stdout: {proc.stdout[:2000]}')
        if proc.stderr:
            _log(f'scan stderr: {proc.stderr[:2000]}')
    except Exception as e:
        _log(f'scan failed: {e}')


def _start_scan_background():
    repo = _repo_root()
    data_dir = os.path.join(repo, 'projects', 'bot', 'python_bot', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out = os.path.join(data_dir, 'scan_report.json')
    thread = threading.Thread(target=_run_scan, args=(repo, out), daemon=True)
    thread.start()
    return out


async def scan_report_cmd(update: Any, context: Any):
    repo = _repo_root()
    out = os.path.join(repo, 'projects', 'bot', 'python_bot', 'data', 'scan_report.json')
    if not os.path.exists(out):
        await update.message.reply_text('No scan report found yet. Trigger /scan_now to run a scan.')
        return
    try:
        with open(out, 'r', encoding='utf-8') as f:
            data = json.load(f)
        deps = data.get('dependencies', {})
        vuls = deps.get('vulnerabilities', []) if deps else []
        code_find = data.get('code', {}).get('findings', []) if data.get('code') else []
        msg = f"Scan summary:\nVulnerabilities (raw items): {len(vuls)}\nCode pattern findings: {len(code_find)}"
        await update.message.reply_text(msg)
    except Exception as e:
        try:
            await update.message.reply_text(f'Failed to read report: {e}')
        except Exception:
            pass


async def scan_now_cmd(update: Any, context: Any):
    repo = _repo_root()
    data_dir = os.path.join(repo, 'projects', 'bot', 'python_bot', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out = os.path.join(data_dir, 'scan_report.json')
    # start background thread
    thread = threading.Thread(target=_run_scan, args=(repo, out), daemon=True)
    thread.start()
    try:
        await update.message.reply_text('Scan started in background; use /scan_report when finished.')
    except Exception:
        pass


def setup(bot):
    # start initial scan in background
    try:
        _start_scan_background()
    except Exception as e:
        _log(f'startup scan failed: {e}')
    # register commands
    bot.register_command('scan_report', scan_report_cmd, 'Show last CVE scan summary', plugin='scan_cves')
    bot.register_command('scan_now', scan_now_cmd, 'Trigger CVE/code scan now', plugin='scan_cves')
