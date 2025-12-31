#!/usr/bin/env python3
"""Generate web/i18n/*.json from lang/*.lua files.

Usage: python scripts/generate_i18n.py
It will parse `lang/*.lua` for `set_text(LANG, 'key', 'value')` calls
and write `web/i18n/<langcode>.json` files.
"""
import re
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
LANG_DIR = os.path.join(ROOT, 'lang')
OUT_DIR = os.path.join(ROOT, 'web', 'i18n')
BOT_OUT = os.path.join(OUT_DIR, 'bot')
WEB_OUT = os.path.join(OUT_DIR, 'web')

PAT = re.compile(r"set_text\s*\(\s*LANG\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](.*?)['\"]\s*\)", re.DOTALL)

def unescape(s):
    return s.encode('utf-8').decode('unicode_escape')

def parse_file(path):
    data = {}
    with open(path, 'r', encoding='utf-8') as fh:
        txt = fh.read()
    for m in PAT.finditer(txt):
        key = m.group(1)
        val = m.group(2)
        # keep Lua escapes as-is by interpreting common ones
        val = val.replace('\\n', '\n').replace("\\'","'")
        data[key] = val
    return data

def detect_lang_code(path):
    # look for local LANG = 'xx' declaration
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            m = re.match(r"\s*local\s+LANG\s*=\s*['\"]([^'\"]+)['\"]", line)
            if m:
                return m.group(1)
    # fallback to filename
    name = os.path.basename(path)
    return name.split('_')[0]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(BOT_OUT, exist_ok=True)
    os.makedirs(WEB_OUT, exist_ok=True)

    lua_files = [os.path.join(LANG_DIR, f) for f in os.listdir(LANG_DIR) if f.endswith('.lua')]
    if not lua_files:
        print('No lang files found in', LANG_DIR)
        return

    # Generate bot translations (from Lua files) into web/i18n/bot/<code>.json
    for lf in lua_files:
        code = detect_lang_code(lf)
        data = parse_file(lf)
        outp = os.path.join(BOT_OUT, f"{code}.json")
        with open(outp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print('Wrote', outp, '({} keys)'.format(len(data)))

    # Move any existing root-level i18n JSONs (legacy UI translations) into web/i18n/web/
    # Files that already live in OUT_DIR (like zh.json, ru.json) are treated as web UI translations.
    for fname in os.listdir(OUT_DIR):
        fpath = os.path.join(OUT_DIR, fname)
        if not fname.lower().endswith('.json'):
            continue
        # skip files inside subfolders
        if os.path.isdir(fpath):
            continue
        # skip bot files we just wrote (we wrote into BOT_OUT)
        # move the file into WEB_OUT
        try:
            with open(fpath, 'r', encoding='utf-8') as fh:
                txt = fh.read()
            # simple sanity check for JSON
            _ = json.loads(txt)
            dest = os.path.join(WEB_OUT, fname)
            # only move if destination different
            if os.path.abspath(fpath) != os.path.abspath(dest):
                os.replace(fpath, dest)
                print('Moved', fpath, '->', dest)
        except Exception:
            continue

if __name__ == '__main__':
    main()
