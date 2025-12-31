"""Integration helper to copy/move repository folders into `projects/` mother folders.

Usage:
  py projects/integrate.py --dry-run
  py projects/integrate.py --move   # to move (destructive)

This script is safe by default: it performs a dry-run and prints planned operations.
It supports copying folders such as `python_bot`, `web`, `python_api`, `tools`, `libs`, `data`, `scripts` into their respective `projects/*` destinations.
"""
from pathlib import Path
import shutil
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = {
    'python_bot': ROOT / 'projects' / 'bot' / 'python_bot',
    'web': ROOT / 'projects' / 'web' / 'web',
    'python_api': ROOT / 'projects' / 'python_api' / 'python_api',
    'tools': ROOT / 'projects' / 'tools' / 'tools',
    'libs': ROOT / 'projects' / 'libs' / 'libs',
    'data': ROOT / 'projects' / 'data' / 'data',
    'scripts': ROOT / 'projects' / 'scripts' / 'scripts',
}

def plan_actions():
    actions = []
    for src_name, dst in MAPPINGS.items():
        src = ROOT / src_name
        if not src.exists():
            actions.append((src, dst, 'missing'))
            continue
        if dst.exists():
            actions.append((src, dst, 'exists'))
        else:
            actions.append((src, dst, 'copy'))
    return actions


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--move', action='store_true', help='Move instead of copy (destructive)')
    p.add_argument('--dry-run', action='store_true', default=True, help='Show actions without performing them')
    p.add_argument('--yes', action='store_true', help='Auto-confirm operations (no interactive prompt)')
    args = p.parse_args()

    actions = plan_actions()
    print('Planned actions:')
    for src, dst, op in actions:
        print(f' - {src} -> {dst} : {op}')

    if args.dry_run and not args.move:
        print('\nDry-run mode: no files were modified. Re-run with --move to perform operations.')
        return

    # Confirm
    print('\nAbout to perform operations. This will modify files.')
    if not args.yes:
        ok = input('Type YES to continue: ')
        if ok != 'YES':
            print('Aborted.')
            return
    else:
        print('Auto-confirmed with --yes')

    for src, dst, op in actions:
        if op == 'missing':
            print(f'SKIP missing source {src}')
            continue
        if op == 'exists':
            print(f'SKIP existing destination {dst}')
            continue
        # perform copy or move
        dst.parent.mkdir(parents=True, exist_ok=True)
        if args.move:
            print(f'Moving {src} -> {dst}')
            shutil.move(str(src), str(dst))
        else:
            print(f'Copying {src} -> {dst}')
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))

    print('Operations completed.')

if __name__ == '__main__':
    main()
