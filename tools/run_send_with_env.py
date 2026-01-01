#!/usr/bin/env python3
import os, runpy
here = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(here, '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            print('LINE:', repr(line))
            if '=' not in line:
                continue
            k,v = line.strip().split('=',1)
            print('PARSED:', k, '->', repr(v))
            os.environ.setdefault(k, v)
# debug
print('ENV_LOADED:', os.path.exists(env_path))
bt = os.environ.get('BOT_TOKEN')
if bt:
    print('BOT_TOKEN present len=', len(bt))
else:
    print('BOT_TOKEN missing')
# execute the send script
runpy.run_path(os.path.join(here, 'send_torrent_via_bot.py'), run_name='__main__')
