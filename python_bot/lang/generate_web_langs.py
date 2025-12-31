"""Generate language modules for the web UI strings.

This script extracts visible strings from `web/pages.json` and `web/index.html`
and generates per-language Python modules under `python_bot/lang/generated/`.

By default it will create modules for a set of common languages (50). Each
module contains `WEB_STRINGS` mapping keys -> translation (placeholder = English).

Run locally to regenerate or to create more language files.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'web'
OUT = Path(__file__).resolve().parents[0] / 'generated'
OUT.mkdir(parents=True, exist_ok=True)


def extract_strings():
    texts = []
    # pages.json labels
    pages_json = WEB / 'pages.json'
    if pages_json.exists():
        data = json.loads(pages_json.read_text(encoding='utf-8'))
        for item in data:
            label = item.get('label')
            if label:
                texts.append(label.strip())

    # index.html: extract text nodes naively (tags and visible text)
    index = WEB / 'index.html'
    if index.exists():
        html = index.read_text(encoding='utf-8')
        # remove scripts and styles
        html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.I)
        html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.I)
        # find text between angle-bracket tags
        parts = re.findall(r'>([^<>]+)<', html)
        for p in parts:
            s = p.strip()
            if not s:
                continue
            # ignore small punctuation-only strings
            if len(s) < 2:
                continue
            texts.append(s)

    # deduplicate preserving order
    seen = set()
    out = []
    for t in texts:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


COMMON_LANGS = [
    'en','es','fr','de','it','pt','ru','zh','ja','ko','ar','hi','bn','ur','vi','id',
    'ms','th','tr','nl','pl','sv','no','da','fi','cs','ro','hu','el','he','fa','sr',
    'hr','sk','uk','bg','lt','lv','et','sl','sq','mk','az','ka','hy','mn','am'
]


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    if not s:
        s = 'key'
    return s


def build_key_map(strings):
    mapping = {}
    for s in strings:
        key = slugify(s)
        # avoid collisions
        if key in mapping:
            i = 2
            while f"{key}_{i}" in mapping:
                i += 1
            key = f"{key}_{i}"
        mapping[key] = s
    return mapping


def write_lang(code, mapping):
    out_file = OUT / f'{code}.py'
    lines = [
        '"""Auto-generated language module for web strings.',
        f"Language: {code}",
        'Placeholder translations default to English source strings.',
        '"""',
        '',
        'WEB_STRINGS = {'
    ]
    for k, v in mapping.items():
        safe = v.replace('\\', '\\\\').replace("\'", "\\'")
        lines.append(f"    '{k}': '{safe}',")
    lines.append('}')
    out_file.write_text('\n'.join(lines), encoding='utf-8')


def main():
    strings = extract_strings()
    mapping = build_key_map(strings)
    for code in COMMON_LANGS:
        write_lang(code, mapping)
    print(f'Wrote {len(COMMON_LANGS)} language modules to {OUT}')


if __name__ == '__main__':
    main()
