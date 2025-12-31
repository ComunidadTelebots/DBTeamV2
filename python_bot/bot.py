"""Minimal Bot skeleton with plugin loader.
This is a lightweight scaffold to start porting Lua functionality to Python.
"""
import importlib
import pkgutil
from types import ModuleType


class Bot:
    def __init__(self):
        self.plugins = {}

    def start(self):
        print('Starting python_bot skeleton...')
        self.load_plugins()
        print(f'Loaded plugins: {list(self.plugins.keys())}')

    def load_plugins(self):
        # discover plugins in python_bot.plugins
        package = 'python_bot.plugins'
        for finder, name, ispkg in pkgutil.iter_modules(importlib.import_module(package).__path__):
            try:
                mod = importlib.import_module(f'{package}.{name}')
                self.plugins[name] = mod
            except Exception as e:
                print(f'Failed to load plugin {name}: {e}')
