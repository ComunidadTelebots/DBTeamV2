"""Abuse protection helpers: rate counting, IP/country blocking using Redis.

This module provides simple request counting and blacklist management
backed by Redis. It attempts to resolve IP -> country using `geoip2`
if available; otherwise country lookup is skipped.

Config via env vars:
- REDIS_URL (default redis://127.0.0.1:6379/0)
- ABUSE_IP_THRESHOLD (requests within window to trigger block, default 100)
- ABUSE_WINDOW (seconds window for counting, default 60)
- ABUSE_BLOCK_TTL (seconds to block IP by default, default 3600)
"""
import os
import time
import json
try:
    import redis
except Exception:
    redis = None

try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except Exception:
    GEOIP_AVAILABLE = False
try:
    from . import alerts as alerts_module
except Exception:
    try:
        import alerts as alerts_module
    except Exception:
        alerts_module = None

REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
IP_THRESHOLD = int(os.environ.get('ABUSE_IP_THRESHOLD', '100'))
WINDOW = int(os.environ.get('ABUSE_WINDOW', '60'))
BLOCK_TTL = int(os.environ.get('ABUSE_BLOCK_TTL', '3600'))

# behavior flags
AUTO_BLOCK = os.environ.get('ABUSE_AUTO_BLOCK', '1') in ('1', 'true', 'True')
AUTO_ESCALATE = os.environ.get('ABUSE_AUTO_ESCALATE', '1') in ('1', 'true', 'True')

_r = None
if redis:
    try:
        _r = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        _r = None

GEOIP_DB = os.environ.get('GEOIP_DB')
_geo_reader = None
if GEOIP_AVAILABLE and GEOIP_DB:
    try:
        _geo_reader = geoip2.database.Reader(GEOIP_DB)
    except Exception:
        _geo_reader = None


def _now():
    return int(time.time())


def ip_to_country(ip: str):
    if not _geo_reader:
        return None
    try:
        rec = _geo_reader.country(ip)
        return rec.country.iso_code
    except Exception:
        return None


def ip_to_geo(ip: str):
    """Return geo dict with country, region (subdivision), city when available."""
    if not _geo_reader:
        return {}
    try:
        rec = _geo_reader.city(ip)
        country = rec.country.iso_code if rec.country and rec.country.iso_code else None
        city = rec.city.name if rec.city and rec.city.name else None
        region = None
        if rec.subdivisions and len(rec.subdivisions) > 0:
            region = rec.subdivisions.most_specific.name if hasattr(rec.subdivisions, 'most_specific') else rec.subdivisions[0].name
        return {'country': country, 'region': region, 'city': city}
    except Exception:
        return {}


def is_blocked_ip(ip: str) -> bool:
    if not _r:
        return False
    try:
        return _r.sismember('abuse:blacklist:ip', ip)
    except Exception:
        return False


def is_blocked_country(cc: str) -> bool:
    if not _r or not cc:
        return False
    try:
        return _r.sismember('abuse:blacklist:country', cc.upper())
    except Exception:
        return False


def is_blocked_region(region: str) -> bool:
    if not _r or not region:
        return False
    try:
        return _r.sismember('abuse:blacklist:region', region.upper())
    except Exception:
        return False


def is_blocked_city(city: str) -> bool:
    if not _r or not city:
        return False
    try:
        return _r.sismember('abuse:blacklist:city', city)
    except Exception:
        return False


def is_blocked_medium(medium: str) -> bool:
    if not _r or not medium:
        return False
    try:
        return _r.sismember('abuse:blacklist:medium', medium.lower())
    except Exception:
        return False


def block_ip(ip: str, reason: str = None, ttl: int = None):
    if not _r:
        return False
    try:
        _r.sadd('abuse:blacklist:ip', ip)
        info = {'ip': ip, 'reason': reason or 'auto', 'ts': _now()}
        _r.set(f'abuse:black:ip:{ip}', json.dumps(info), ex=(ttl or BLOCK_TTL))
        # also notify admins / moderation queue
        try:
            note = {'title': 'Auto-block IP', 'text': f'IP {ip} blocked ({reason})', 'ip': ip, 'reason': reason, 'ts': _now()}
            _r.rpush('web:notifications', json.dumps(note))
            _r.ltrim('web:notifications', -200, -1)
            action = {'type': 'block_ip', 'ip': ip, 'reason': reason or 'auto', 'ts': _now()}
            _r.rpush('moderation:actions', json.dumps(action))
        except Exception:
            pass
        return True
    except Exception:
        return False


def unblock_ip(ip: str):
    if not _r:
        return False
    try:
        _r.srem('abuse:blacklist:ip', ip)
        _r.delete(f'abuse:black:ip:{ip}')
        return True
    except Exception:
        return False


def block_country(cc: str, reason: str = None):
    if not _r or not cc:
        return False
    try:
        cc = cc.upper()
        _r.sadd('abuse:blacklist:country', cc)
        info = {'country': cc, 'reason': reason or 'auto', 'ts': _now()}
        _r.hset('abuse:black:country', cc, json.dumps(info))
        # notify admins
        try:
            note = {'title': 'Auto-block Country', 'text': f'Country {cc} blocked ({reason})', 'country': cc, 'reason': reason, 'ts': _now()}
            _r.rpush('web:notifications', json.dumps(note))
            _r.ltrim('web:notifications', -200, -1)
            action = {'type': 'block_country', 'country': cc, 'reason': reason or 'auto', 'ts': _now()}
            _r.rpush('moderation:actions', json.dumps(action))
        except Exception:
            pass
        return True
    except Exception:
        return False


def block_region(region: str, reason: str = None):
    if not _r or not region:
        return False
    try:
        rkey = region.upper()
        _r.sadd('abuse:blacklist:region', rkey)
        _r.hset('abuse:black:region', rkey, json.dumps({'region': rkey, 'reason': reason or 'admin', 'ts': _now()}))
        try:
            note = {'title': 'Auto-block Region', 'text': f'Region {rkey} blocked ({reason})', 'region': rkey, 'reason': reason, 'ts': _now()}
            _r.rpush('web:notifications', json.dumps(note))
            _r.ltrim('web:notifications', -200, -1)
            _r.rpush('moderation:actions', json.dumps({'type':'block_region','region':rkey,'reason':reason or 'auto','ts':_now()}))
        except Exception:
            pass
        return True
    except Exception:
        return False


def unblock_region(region: str):
    if not _r or not region:
        return False
    try:
        rkey = region.upper()
        _r.srem('abuse:blacklist:region', rkey)
        _r.hdel('abuse:black:region', rkey)
        return True
    except Exception:
        return False


def block_city(city: str, reason: str = None):
    if not _r or not city:
        return False
    try:
        _r.sadd('abuse:blacklist:city', city)
        _r.hset('abuse:black:city', city, json.dumps({'city': city, 'reason': reason or 'admin', 'ts': _now()}))
        try:
            note = {'title': 'Auto-block City', 'text': f'City {city} blocked ({reason})', 'city': city, 'reason': reason, 'ts': _now()}
            _r.rpush('web:notifications', json.dumps(note))
            _r.ltrim('web:notifications', -200, -1)
            _r.rpush('moderation:actions', json.dumps({'type':'block_city','city':city,'reason':reason or 'auto','ts':_now()}))
        except Exception:
            pass
        return True
    except Exception:
        return False


def unblock_city(city: str):
    if not _r or not city:
        return False
    try:
        _r.srem('abuse:blacklist:city', city)
        _r.hdel('abuse:black:city', city)
        return True
    except Exception:
        return False


def block_medium(medium: str, reason: str = None):
    if not _r or not medium:
        return False
    try:
        m = medium.lower()
        _r.sadd('abuse:blacklist:medium', m)
        _r.hset('abuse:black:medium', m, json.dumps({'medium': m, 'reason': reason or 'admin', 'ts': _now()}))
        try:
            note = {'title': 'Auto-block Medium', 'text': f'Medium {m} blocked ({reason})', 'medium': m, 'reason': reason, 'ts': _now()}
            _r.rpush('web:notifications', json.dumps(note))
            _r.ltrim('web:notifications', -200, -1)
            _r.rpush('moderation:actions', json.dumps({'type':'block_medium','medium':m,'reason':reason or 'auto','ts':_now()}))
        except Exception:
            pass
        return True
    except Exception:
        return False


def unblock_medium(medium: str):
    if not _r or not medium:
        return False
    try:
        m = medium.lower()
        _r.srem('abuse:blacklist:medium', m)
        _r.hdel('abuse:black:medium', m)
        return True
    except Exception:
        return False


def unblock_country(cc: str):
    if not _r or not cc:
        return False
    try:
        cc = cc.upper()
        _r.srem('abuse:blacklist:country', cc)
        _r.hdel('abuse:black:country', cc)
        return True
    except Exception:
        return False


def record_request(ip: str, meta: dict = None) -> dict:
    """Record a request from an IP. Returns dict with status and actions.

    If the IP exceeds threshold within the window, it will be blocked and
    an entry added to Redis blacklist. If GeoIP is available and many IPs
    from the same country trigger blocks, the country may be blocked too.
    """
    if not _r or not ip:
        return {'ok': False}
    now = _now()
    try:
        key = f'abuse:count:ip:{ip}'
        c = _r.incr(key)
        _r.expire(key, WINDOW)
        res = {'count': int(c)}
        # enrich with geo and medium info
        geo = ip_to_geo(ip) or {}
        medium = None
        if meta and isinstance(meta, dict):
            headers = meta.get('headers') or {}
            # header keys may be case-sensitive depending on source
            if isinstance(headers, dict):
                medium = headers.get('X-Medium') or headers.get('x-medium') or headers.get('X-Forwarded-Proto')
                ua = headers.get('User-Agent') or headers.get('user-agent') or ''
                if not medium and ua and 'telegram' in ua.lower():
                    medium = 'telegram'
            else:
                ua = ''
        if not medium:
            medium = 'web'
        res.update({'geo': geo, 'medium': medium})
        if int(c) >= IP_THRESHOLD:
            # block IP (auto) depending on config
            res['blocked'] = False
            if AUTO_BLOCK:
                ok = block_ip(ip, reason='rate')
                res['blocked'] = bool(ok)
            else:
                # escalate to admins if configured
                if AUTO_ESCALATE:
                    try:
                        note = {'title': 'Suspicious IP', 'text': f'IP {ip} exceeded rate ({c} reqs)', 'ip': ip, 'count': int(c), 'ts': _now(), 'suggestion': 'block_ip'}
                        _r.rpush('web:notifications', json.dumps(note))
                        _r.ltrim('web:notifications', -200, -1)
                        _r.rpush('moderation:actions', json.dumps({'type':'suggest_block_ip','ip':ip,'count':int(c),'ts':_now()}))
                        # notify via alerts module if available
                        if alerts_module:
                            try:
                                alerts_module.notify_admin('Suspicious IP', f"IP {ip} exceeded rate ({c} reqs)")
                            except Exception:
                                pass
                    except Exception:
                        pass
            # try country block: increment per-country blocked IPs
            cc = geo.get('country') or ip_to_country(ip)
            if cc:
                _r.incr(f'abuse:country:blockcount:{cc}')
                _r.expire(f'abuse:country:blockcount:{cc}', 24*3600)
                cnt = int(_r.get(f'abuse:country:blockcount:{cc}') or 0)
                # if many IPs from same country blocked, block country
                if cnt >= int(os.environ.get('ABUSE_COUNTRY_THRESHOLD', '10')):
                    if AUTO_BLOCK:
                        block_country(cc, reason='many_ips')
                        res['country_blocked'] = cc
                    else:
                        if AUTO_ESCALATE:
                            try:
                                note = {'title': 'Suspicious Country', 'text': f'Country {cc} has many blocked IPs', 'country': cc, 'ts': _now(), 'suggestion': 'block_country'}
                                _r.rpush('web:notifications', json.dumps(note))
                                _r.ltrim('web:notifications', -200, -1)
                                _r.rpush('moderation:actions', json.dumps({'type':'suggest_block_country','country':cc,'ts':_now()}))
                                if alerts_module:
                                    try:
                                        alerts_module.notify_admin('Suspicious Country', f'Country {cc} has many blocked IPs')
                                    except Exception:
                                        pass
                            except Exception:
                                pass
        # detect and optionally block by region/city/medium
        try:
            region = geo.get('region')
            city = geo.get('city')
            if region and is_blocked_region(region):
                res['blocked_region'] = region
            if city and is_blocked_city(city):
                res['blocked_city'] = city
            if medium and is_blocked_medium(medium):
                res['blocked_medium'] = medium
        except Exception:
            pass
        return res
    except Exception:
        return {'ok': False}


def list_blocked(limit=200):
    if not _r:
        return {'ips': [], 'countries': [], 'regions': [], 'cities': [], 'mediums': []}
    try:
        ips = list(_r.smembers('abuse:blacklist:ip') or [])
        countries = list(_r.smembers('abuse:blacklist:country') or [])
        regions = list(_r.smembers('abuse:blacklist:region') or [])
        cities = list(_r.smembers('abuse:blacklist:city') or [])
        mediums = list(_r.smembers('abuse:blacklist:medium') or [])
        return {'ips': ips[:limit], 'countries': countries[:limit], 'regions': regions[:limit], 'cities': cities[:limit], 'mediums': mediums[:limit]}
    except Exception:
        return {'ips': [], 'countries': [], 'regions': [], 'cities': [], 'mediums': []}
