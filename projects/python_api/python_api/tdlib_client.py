"""Light TDLib client wrapper scaffold.

This module provides a thin wrapper around TDLib bindings if available.
It purposely avoids hard dependencies so the repo can be used without TDLib.

To enable full functionality you must install TDLib and a Python binding
such as `python-tdlib` (see README_TDLIB.md for instructions).
"""
import threading
import time
import json
import logging

logger = logging.getLogger('tdlib_client')

class TDLibNotAvailable(Exception):
    pass

try:
    # try to import a common tdlib binding (may vary between systems)
    import tdlib as _tdlib_binding
    HAVE_TDLIB = True
except Exception:
    _tdlib_binding = None
    HAVE_TDLIB = False


class TDClient:
    def __init__(self, database_dir='tdlib', use_test_dc=False):
        if not HAVE_TDLIB:
            raise TDLibNotAvailable('TDLib Python binding not available')
        # Try to initialize a client for common bindings. The exact
        # initialization depends on the installed Python TDLib binding.
        self._event_handler = None
        self._running = False
        self._thread = None
        self._client = None
        try:
            # common binding shape: tdlib.Client()
            if hasattr(_tdlib_binding, 'Client'):
                try:
                    self._client = _tdlib_binding.Client(database_directory=database_dir)
                except Exception:
                    # fallback without args
                    self._client = _tdlib_binding.Client()
            elif hasattr(_tdlib_binding, 'TdJson'):
                # other bindings expose TdJson wrapper
                self._client = _tdlib_binding.TdJson()
            else:
                # last resort: try to use module directly
                self._client = _tdlib_binding
        except Exception as e:
            raise TDLibNotAvailable(f'Failed to initialize TDLib binding: {e}')
        self._running = False
        self._thread = None
        self._event_handler = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        while self._running:
            try:
                # receive updates from tdlib binding, adapt as needed
                upd = None
                # try a few common receive method names
                if hasattr(self._client, 'receive'):
                    upd = self._client.receive(1.0)
                elif hasattr(self._client, 'get_update'):
                    upd = self._client.get_update(timeout=1.0)
                elif hasattr(self._client, 'run'):
                    # some bindings use a callback-run approach; sleep briefly
                    time.sleep(0.5)
                    upd = None

                if upd:
                    logger.debug('TD update: %s', upd)
                    try:
                        if self._event_handler:
                            # try to normalize to a python dict
                            if isinstance(upd, (str, bytes)):
                                try:
                                    parsed = json.loads(upd)
                                except Exception:
                                    parsed = upd
                            else:
                                parsed = upd
                            self._event_handler(parsed)
                    except Exception:
                        logger.exception('event handler failed')
            except Exception:
                time.sleep(0.1)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def send_message(self, chat_id: int, text: str):
        if not HAVE_TDLIB:
            raise TDLibNotAvailable('TDLib not available')
        # attempt to call a send method on the binding; adapt to common names
        try:
            if hasattr(self._client, 'send_message'):
                return self._client.send_message(chat_id=chat_id, text=text)
            if hasattr(self._client, 'send'):
                return self._client.send({'@type': 'sendMessage', 'chat_id': chat_id, 'input_message_content': {'@type': 'inputMessageText', 'text': text}})
            if hasattr(self._client, 'execute'):
                return self._client.execute({'@type': 'sendMessage', 'chat_id': chat_id, 'input_message_content': {'@type': 'inputMessageText', 'text': text}})
        except Exception as e:
            logger.exception('send_message failed')
            raise
        raise TDLibNotAvailable('send_message not implemented for this TDLib binding')

    def get_chats(self, limit=100):
        if not HAVE_TDLIB:
            raise TDLibNotAvailable('TDLib not available')
        try:
            if hasattr(self._client, 'get_chats'):
                return self._client.get_chats(limit=limit)
            if hasattr(self._client, 'getDialogs'):
                return self._client.getDialogs(limit=limit)
        except Exception:
            logger.exception('get_chats failed')
        return []

    def set_event_handler(self, handler):
        self._event_handler = handler


# Fallback non-functional client for development without TDLib
class DummyTDClient:
    def __init__(self, *args, **kwargs):
        self._running = False
        self._event_handler = None
        self._thread = None

    def start(self):
        self._running = True
        # start a small thread to emit simulated events for UI testing
        def _emit():
            import time
            i = 0
            while self._running:
                time.sleep(5)
                i += 1
                ev = {'type': 'message', 'id': f'dummy-{i}', 'chat_id': 1, 'text': f'Simulated message {i}', 'ts': int(time.time())}
                try:
                    if self._event_handler:
                        self._event_handler(ev)
                except Exception:
                    pass
        self._thread = threading.Thread(target=_emit, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if getattr(self, '_thread', None):
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass

    def send_message(self, chat_id: int, text: str):
        # simulate success
        return {'ok': True, 'chat_id': chat_id, 'text': text}

    def get_chats(self, limit=100):
        return []

    def set_event_handler(self, handler):
        self._event_handler = handler


def get_client(prefer_dummy=False):
    """Return a `TDClient` when a binding is available, otherwise `DummyTDClient`.

    Set `prefer_dummy=True` to force the dummy client for testing.
    """
    if prefer_dummy or not HAVE_TDLIB:
        return DummyTDClient()
    try:
        return TDClient()
    except Exception:
        return DummyTDClient()
