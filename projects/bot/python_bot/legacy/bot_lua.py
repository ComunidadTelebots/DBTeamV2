"""Lightweight port of `bot/bot.lua` main helpers to Python.

This module provides compatibility helpers used during migration. It does
not aim for full TDLib parity; instead it provides configuration loading,
plugin discovery and language loading utilities.
"""
import json
import os
from pathlib import Path
import importlib
import pkgutil

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
CONFIG_PATH = DATA_DIR / 'config.json'

def create_config():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        'enabled_plugins': [
            'settings','id','promote','moderation','commands','plugins','stats','gbans','extra','langs','private'
        ],
        'enabled_lang': ['english_lang'],
        'our_id': [0],
        'sudo_users': [0]
    }
    with open(CONFIG_PATH, 'w', encoding='utf-8') as fh:
        json.dump(config, fh, indent=2)
    return config

def load_config():
    if not CONFIG_PATH.exists():
        return create_config()
    try:
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception:
        return create_config()

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, indent=2)

def load_plugins(config):
    plugins = {}
    package_name = 'python_bot.plugins'
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return plugins
    if not hasattr(pkg, '__path__'):
        return plugins
    for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__):
        try:
            mod = importlib.import_module(f'{package_name}.{name}')
            plugins[name] = mod
            setup = getattr(mod, 'setup', None)
            if callable(setup):
                try:
                    setup()
                except Exception:
                    pass
        except Exception:
            continue
    return plugins

def load_langs(enabled_langs):
    # Attempt to import language modules under python_bot.lang
    langs = {}
    for name in enabled_langs:
        code = name.split('_')[0]
        try:
            mod = importlib.import_module(f'python_bot.lang.{code}')
            langs[code] = mod
        except Exception:
            continue
    return langs
