#!/usr/bin/env python3
"""
Merge `set_text(LANG, 'key', value)` entries from `lang/*.lua` into
`web/i18n/en.json`.

Usage (run from repo root):
  python scripts/merge_langs.py

Behavior:
- Parse all files matching `lang/*_lang.lua`.
- Prefer values found in `lang/english_lang.lua` when available.
- Keep existing entries in `web/i18n/en.json` and only add missing keys.
- Write the merged file sorted by key.

This script is intended to be run locally where Python is available.
"""
import os
import re
import json

ROOT = os.path.dirname(os.path.dirname(__file__))
LANG_DIR = os.path.join(ROOT, 'lang')
EN_JSON = os.path.join(ROOT, 'web', 'i18n', 'en.json')

RE_STR = re.compile(r"set_text\(\s*LANG\s*,\s*'([^']+)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)")
RE_NUM = re.compile(r"set_text\(\s*LANG\s*,\s*'([^']+)'\s*,\s*([0-9]+)\s*\)")

def parse_file(path):
    content = open(path, 'r', encoding='utf-8').read()
    d = {}
    for m in RE_STR.finditer(content):
        k = m.group(1)
        v = m.group(2)
        # Unescape simple escaped sequences
        v = v.replace("\\n", "\\n").replace("\\'", "'")
        d[k] = v
    for m in RE_NUM.finditer(content):
        k = m.group(1)
        v = int(m.group(2))
        d[k] = v
    return d

def main():
    # load existing en.json if present
    if os.path.exists(EN_JSON):
        with open(EN_JSON, 'r', encoding='utf-8') as f:
            try:
                en = json.load(f)
            except Exception:
                en = {}
    else:
        en = {}

    # parse english first (priority)
    english_path = os.path.join(LANG_DIR, 'english_lang.lua')
    english_map = parse_file(english_path) if os.path.exists(english_path) else {}

    merged = dict(en)  # start from existing

    # ensure english keys are present
    for k, v in english_map.items():
        if k not in merged:
            merged[k] = v

    # parse other lang files and add missing keys (if not present in merged)
    for fname in os.listdir(LANG_DIR):
        if not fname.endswith('_lang.lua'):
            continue
        path = os.path.join(LANG_DIR, fname)
        try:
            if os.path.exists(english_path) and os.path.samefile(path, english_path):
                continue
        except Exception:
            # os.path.samefile may fail on some platforms for different reasons
            pass
        parsed = parse_file(path)
        for k, v in parsed.items():
            if k not in merged:
                merged[k] = v

    # sort keys and write back
    out_dir = os.path.dirname(EN_JSON)
    os.makedirs(out_dir, exist_ok=True)
    with open(EN_JSON, 'w', encoding='utf-8') as f:
        json.dump({k: merged[k] for k in sorted(merged)}, f, ensure_ascii=False, indent=2)
    print(f'Wrote {EN_JSON} ({len(merged)} keys)')

if __name__ == '__main__':
    main()
