#!/usr/bin/env python3
"""Scan HTML files and report missing asset references (css/js/img).

Usage: python scripts/check_html_assets.py
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import argparse


def find_html_dirs(root: Path):
    candidates = [root / 'web']
    # include project web folders
    for p in root.glob('projects/**/web'):
        candidates.append(p)
    for p in root.glob('projects/**/python_api/web'):
        candidates.append(p)
    # include python_api/web
    candidates.append(root / 'python_api' / 'web')
    return [p for p in candidates if p.exists()]


def check_html_file(path: Path, root: Path):
    text = path.read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(text, 'html.parser')
    tags = []
    for t in soup.find_all(['link','script','img','source']):
        if t.name == 'link' and t.get('href'):
            tags.append(('link', t.get('href')))
        if t.name == 'script' and t.get('src'):
            tags.append(('script', t.get('src')))
        if t.name == 'img' and t.get('src'):
            tags.append(('img', t.get('src')))
        if t.name == 'source' and t.get('src'):
            tags.append(('source', t.get('src')))

    missing = []
    for kind, ref in tags:
        # ignore absolute URLs
        if ref.startswith('http://') or ref.startswith('https://') or ref.startswith('//'):
            continue
        # clean query/hash
        ref_clean = ref.split('?',1)[0].split('#',1)[0]
        # resolve: if starts with '/', treat as repo root static
        if ref_clean.startswith('/'):
            candidate = root / ref_clean.lstrip('/')
        else:
            candidate = (path.parent / ref_clean).resolve()
        if not candidate.exists():
            missing.append((kind, ref, str(candidate)))
    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.', help='repo root')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    dirs = find_html_dirs(root)
    all_html = []
    for d in dirs:
        all_html.extend(list(d.rglob('*.html')))
    report = {}
    for h in sorted(set(all_html)):
        miss = check_html_file(h, root)
        if miss:
            report[str(h.relative_to(root))] = miss

    out = Path('logs')
    out.mkdir(exist_ok=True)
    repf = out / 'html_asset_report.txt'
    with repf.open('w', encoding='utf-8') as fh:
        if not report:
            fh.write('No missing assets detected.\n')
            print('No missing assets detected.')
        else:
            for html, items in report.items():
                fh.write(f'File: {html}\n')
                print(f'File: {html}')
                for kind, ref, cand in items:
                    line = f'  {kind}: {ref} -> {cand}\n'
                    fh.write(line)
                    print(line, end='')
                fh.write('\n')
    print('Report saved to', repf)


if __name__ == '__main__':
    try:
        import bs4
    except Exception:
        print('Missing dependency: bs4 (beautifulsoup4). Install with pip install beautifulsoup4')
        sys.exit(1)
    main()
