"""
services/location_search.py
Hybrid location search:
  1. Offline DB (321 kota besar Sundaland) — instan
  2. Nominatim Online — agresif, hingga nama desa/kelurahan/kecamatan

Nominatim aggressive mode:
  - Limit 10 results (was 5)
  - addressdetails=1 untuk nama lengkap
  - namedetails=1 untuk nama alternatif/lokal
  - Tidak dibatasi wilayah (global search)
  - Timeout 8 detik

FIX #12: Rate limiting 1 req/detik sesuai syarat penggunaan Nominatim
  https://operations.osmfoundation.org/policies/nominatim/
"""

import time
import urllib.parse
import urllib.request
import json

from core.location_db import search_offline


# ── Sundaland bounding box untuk filter hasil online ─────────────────────────
# Sedikit diperluas agar mencakup seluruh wilayah lempeng
SUNDALAND_BOUNDS = {
    'lon_min': 60.0,
    'lon_max': 160.0,
    'lat_min': -25.0,
    'lat_max':  35.0,
}

# FIX #12: Timestamp request Nominatim terakhir — pastikan jeda minimal 1 detik
_last_nominatim_request: float = 0.0


def _in_sundaland(lat: float, lon: float) -> bool:
    b = SUNDALAND_BOUNDS
    return b['lat_min'] <= lat <= b['lat_max'] and \
           b['lon_min'] <= lon <= b['lon_max']


def _nominatim_search(query: str, limit: int = 10) -> list:
    """
    Search Nominatim OpenStreetMap.
    Returns list of (display_name, lat, lon, country, place_type)

    FIX #12: Menerapkan rate limiting 1 request/detik sesuai ToS Nominatim.
    Tanpa ini, pencarian cepat berulang bisa menyebabkan ban IP.
    """
    global _last_nominatim_request
    # Tunggu agar jeda antar request minimal 1.0 detik
    elapsed = time.monotonic() - _last_nominatim_request
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_nominatim_request = time.monotonic()

    params = urllib.parse.urlencode({
        'q'             : query,
        'format'        : 'json',
        'limit'         : limit,
        'addressdetails': 1,
        'namedetails'   : 1,
        'extratags'     : 1,
        'accept-language': 'id,en',   # Indonesian first, then English
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent'    : 'GeoPlateAnalyst/2.0 (sundaland-research)',
            'Accept'        : 'application/json',
            'Accept-Language': 'id,en',
        }
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    results = []
    for item in data:
        lat  = float(item['lat'])
        lon  = float(item['lon'])
        addr = item.get('address', {})

        # Build clean display name
        parts = []
        for key in ['village','hamlet','suburb','neighbourhood',
                    'town','city_district','city','county',
                    'state','country']:
            val = addr.get(key, '')
            if val and val not in parts:
                parts.append(val)
        name = ', '.join(parts[:4]) if parts else item.get('display_name','')[:80]

        country    = addr.get('country', '')
        place_type = item.get('type', item.get('class', ''))

        results.append((name, lat, lon, country, place_type))

    return results


def search_location(query: str) -> tuple:
    """
    Hybrid search.
    Returns (results, source) where:
      results = [(name, lat, lon, country), ...]
      source  = 'offline' | 'online' | 'not_found'
    """
    q = query.strip()

    # 1. Offline DB first (instan)
    offline = search_offline(q)
    if offline:
        return offline, 'offline'

    # 2. Nominatim online — agresif
    try:
        raw = _nominatim_search(q, limit=10)

        # Filter: prioritize Sundaland region but don't exclude others
        sundaland = [(n,la,lo,c) for n,la,lo,c,_ in raw if _in_sundaland(la,lo)]
        outside   = [(n,la,lo,c) for n,la,lo,c,_ in raw if not _in_sundaland(la,lo)]

        # Return Sundaland results first, then outside if no Sundaland match
        results = sundaland if sundaland else outside

        # Remove duplicates by coordinate proximity
        seen = []
        unique = []
        for r in results:
            lat, lon = r[1], r[2]
            duplicate = any(abs(lat - s[1]) < 0.001 and
                           abs(lon - s[2]) < 0.001 for s in seen)
            if not duplicate:
                unique.append(r)
                seen.append(r)

        if unique:
            return unique[:8], 'online'

    except Exception:
        pass   # No internet or timeout — silently fallback

    return [], 'not_found'


def search_location_online_only(query: str, limit: int = 10) -> tuple:
    """
    Force online-only search — skip offline DB.
    Useful for detailed village/hamlet level search.
    Returns (results, source).
    """
    try:
        raw     = _nominatim_search(query, limit=limit)
        results = [(n, la, lo, c) for n, la, lo, c, _ in raw]
        if results:
            return results, 'online'
    except Exception:
        pass
    return [], 'not_found'
