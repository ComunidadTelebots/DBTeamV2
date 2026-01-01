#!/usr/bin/env python3
"""Entrypoint wrapper used by the web API to start the backend bot.

This simply runs the existing runner located at
`projects/bot/python_bot/main.py` so we don't duplicate runner logic.
"""
import runpy
from pathlib import Path
import sys


def _repo_root() -> Path:
    # file is at <repo>/python_bot/backendbot.py -> parents[1] is repo root
    return Path(__file__).resolve().parents[1]


def main():
    repo = _repo_root()
    runner = repo / 'projects' / 'bot' / 'python_bot' / 'main.py'
    if not runner.exists():
        print('Runner not found at', runner)
        raise SystemExit(2)
    # Execute the runner as __main__ so it behaves like a script
    runpy.run_path(str(runner), run_name='__main__')


if __name__ == '__main__':
    main()
