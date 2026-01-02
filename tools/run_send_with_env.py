#!/usr/bin/env python3
import os
import runpy
here = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(here, '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '=' not in line:
                continue
            k, v = line.strip().split('=', 1)
            os.environ.setdefault(k, v)

print('ENV_LOADED:', os.path.exists(env_path))
bt = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
if bt:
    print('BOT_TOKEN present len=', len(bt))
else:
    print('BOT_TOKEN missing')

# Detect candidate torrent file to show to user
candidates = [
    os.path.join('projects', 'bot', 'tmp_downloaded.torrent'),
    os.path.join('data', 'torrents', 'tmp_downloaded.torrent'),
]
found = None
for p in candidates:
    if os.path.exists(p):
        found = os.path.abspath(p)
        break
if not found:
    d = os.path.join('data', 'torrents')
    if os.path.isdir(d):
        for fname in os.listdir(d):
            if fname.endswith('.torrent'):
                found = os.path.abspath(os.path.join(d, fname))
                break

if found:
    print('Found torrent file:', found)
    try:
        ans = input('Send this torrent? [Y/n]: ').strip().lower()
    except Exception:
        ans = 'y'
    if ans not in ('n', 'no'):
        os.environ['SELECTED_TORRENT'] = found
        print('Confirmed. Launching sender...')
    else:
        print('Aborted by user.')
        raise SystemExit(0)
else:
    print('No local torrent file detected. The sender will attempt to generate a URL via the stream server.')

# execute the send script
runpy.run_path(os.path.join(here, 'send_torrent_via_bot.py'), run_name='__main__')
