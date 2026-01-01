#!/usr/bin/env python3
"""Scan repository for known vulnerabilities (dependencies) and risky code patterns.

Features:
- Parse `requirements.txt` and common dependency files and query OSV API for vulnerabilities.
- Perform static pattern scans on Python source to find risky usage (eval, pickle.load, shell=True, etc.).
- Output a JSON report and a human-readable summary.

Usage:
    python scripts/scan_cves.py --path . --output report.json

Note: OSV queries require network access. If offline, dependency checks will be skipped.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

OSV_URL = 'https://api.osv.dev/v1/query'

PATTERNS = [
    (r"\beval\s*\(", "Use of eval()"),
    (r"\bexec\s*\(", "Use of exec()"),
    (r"subprocess\.Popen\s*\(.*shell\s*=\s*True", "subprocess with shell=True"),
    (r"subprocess\.call\s*\(.*shell\s*=\s*True", "subprocess.call with shell=True"),
    (r"pickle\.load\s*\(", "Untrusted pickle.load()"),
    (r"pickle\.loads\s*\(", "Untrusted pickle.loads()"),
    (r"yaml\.load\s*\(", "yaml.load() without SafeLoader"),
    (r"requests\.get\s*\(.*verify\s*=\s*False", "requests.get verify=False"),
    (r"open\s*\(.*\,\s*\'w\'\s*\)", "File opened for write (check path)"),
]


def find_dependency_files(root: Path) -> List[Path]:
    candidates = []
    for name in ('requirements.txt', 'requirements-dev.txt', 'pyproject.toml', 'Pipfile'):
        p = root / name
        if p.exists():
            candidates.append(p)
    # also check common project dirs
    proj_req = root / 'projects' / 'bot' / 'python_bot' / 'requirements.txt'
    if proj_req.exists():
        candidates.append(proj_req)
    return candidates


def parse_requirements(path: Path) -> List[Dict[str, str]]:
    deps = []
    text = path.read_text(encoding='utf-8', errors='ignore')
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # simple parse: pkg==version or pkg>=version
        m = re.match(r"^([^=<>!~\[\]\s]+)\s*([=<>!~]+)\s*([\w\d\.\-\+]+)", line)
        if m:
            name = m.group(1)
            ver = m.group(3)
            deps.append({'name': name, 'version': ver})
        else:
            # attempt to parse bare package
            if 'git+' in line or line.startswith('-e '):
                continue
            pkg = re.split(r'[<>=!~\s]', line)[0]
            deps.append({'name': pkg, 'version': ''})
    return deps


def query_osv(name: str, version: str) -> Optional[Dict[str, Any]]:
    import requests

    payload = {'package': {'name': name, 'ecosystem': 'PyPI'}}
    if version:
        payload['version'] = version
    try:
        resp = requests.post(OSV_URL, json=payload, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def scan_dependencies(root: Path) -> Dict[str, Any]:
    files = find_dependency_files(root)
    results = {'files': [], 'vulnerabilities': []}
    for f in files:
        deps = parse_requirements(f)
        results['files'].append({'path': str(f), 'count': len(deps)})
        for d in deps:
            name = d.get('name')
            ver = d.get('version')
            osv = query_osv(name, ver) if name else None
            if osv and osv.get('vulns'):
                for v in osv.get('vulns', []):
                    results['vulnerabilities'].append({'package': name, 'version': ver, 'vuln': v})
    return results


def scan_code_patterns(root: Path) -> Dict[str, Any]:
    findings = []
    for p in root.rglob('*.py'):
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for pattern, note in PATTERNS:
            for m in re.finditer(pattern, text):
                # compute line number
                lineno = text.count('\n', 0, m.start()) + 1
                snippet = text.splitlines()[lineno-1].strip() if lineno-1 < len(text.splitlines()) else ''
                findings.append({'file': str(p), 'line': lineno, 'pattern': pattern, 'note': note, 'snippet': snippet})
    return {'findings': findings}


def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description='Scan repo for CVEs and risky patterns')
    parser.add_argument('--path', '-p', default='.', help='Repository root to scan')
    parser.add_argument('--output', '-o', default='scan_report.json', help='JSON output path')
    parser.add_argument('--skip-deps', action='store_true', help='Skip dependency CVE queries')
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    out = {'root': str(root)}

    if not args.skip_deps:
        print('Scanning dependencies...')
        dep_res = scan_dependencies(root)
        out['dependencies'] = dep_res
        print(f"Found {len(dep_res.get('vulnerabilities', []))} vulnerability items (raw)")
    else:
        out['dependencies'] = {'files': [], 'vulnerabilities': []}

    print('Scanning source for risky patterns...')
    code_res = scan_code_patterns(root)
    out['code'] = code_res
    print(f"Found {len(code_res.get('findings', []))} pattern findings")

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print('Report written to', args.output)


if __name__ == '__main__':
    main()
