# tdlib_client.py - TDLib integration for backend
# Requires python-tdlib and native TDLib library (libtdjson)
# Set env vars: TD_API_ID, TD_API_HASH, TD_PHONE, TD_DB_DIR (optional)

import os
try:
    from tdclient import TDClient
except ImportError:
    TDClient = None

class TDLibNotAvailable(Exception):
    pass

def get_client(prefer_dummy=False, api_id=None, api_hash=None):
    if TDClient is None:
        raise TDLibNotAvailable("python-tdlib is not installed or TDLib native library is missing.")
    # Permitir pasar api_id y api_hash por parámetro o usar env vars
    api_id = api_id or os.environ.get('TD_API_ID')
    api_hash = api_hash or os.environ.get('TD_API_HASH')
    phone = os.environ.get('TD_PHONE')
    db_dir = os.environ.get('TD_DB_DIR', './tdlib_data')
    if not (api_id and api_hash and phone):
        raise TDLibNotAvailable("Set TD_API_ID, TD_API_HASH, and TD_PHONE environment variables, o pásalos por parámetro.")
    client = TDClient(api_id=api_id, api_hash=api_hash, phone=phone, database_directory=db_dir)
    return client

# To use:
# 1. Set env vars: TD_API_ID, TD_API_HASH, TD_PHONE
# 2. Ensure libtdjson is installed on the system (see python-tdlib docs)
# 3. Use get_client() to obtain a TDLib client instance
