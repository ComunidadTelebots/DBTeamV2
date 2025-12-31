#!/usr/bin/env python3
"""Generate python language modules from web/i18n/bot/*.json

Creates `python_bot/lang/<code>.py` with a `LANG` dict and `get_text(key, default=None)` helper.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / 'web' / 'i18n' / 'bot'
OUT_DIR = ROOT / 'python_bot' / 'lang'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def write_module(code, data):
    out = OUT_DIR / f"{code}.py"
    lines = [
        '"""Auto-generated language module',
        f'Language: {code}',
        '"""',
        '',
        'LANG = {'
    ]
    for k, v in sorted(data.items()):
        safe = v.replace('\\', '\\\\').replace("'", "\\'")
        lines.append(f"    '{k}': '{safe}',")
    lines.append('}')
    lines.append('')
    lines.append('def get_text(key, default=None):')
    lines.append('    return LANG.get(key, default)')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print('Wrote', out)


def main():
    if not JSON_DIR.exists():
        print('No bot json dir:', JSON_DIR)
        return
    files = [p for p in JSON_DIR.iterdir() if p.suffix == '.json']
    if not files:
        print('No json files in', JSON_DIR)
        return
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print('Failed to read', f, e)
            continue
        code = f.stem
        write_module(code, data)

if __name__ == '__main__':
    main()
