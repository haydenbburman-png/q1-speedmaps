"""Polite HTTP fetching with a small on-disk cache."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests

from . import config

_session = requests.Session()
_session.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "en-AU,en;q=0.9"})
_last_request = 0.0


def _cache_path(url: str) -> Path:
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    return config.CACHE_DIR / f"{key}.html"


def get(url: str, *, max_age_min: float | None = None, fresh: bool = False) -> str:
    """Return page HTML. Uses cache younger than max_age_min unless fresh=True."""
    global _last_request
    max_age = config.CACHE_TTL_MIN if max_age_min is None else max_age_min
    path = _cache_path(url)
    if not fresh and path.exists() and (time.time() - path.stat().st_mtime) < max_age * 60:
        return path.read_text(encoding="utf-8")

    wait = config.REQUEST_DELAY_SEC - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)

    for attempt in range(3):
        try:
            resp = _session.get(url, timeout=30)
            _last_request = time.time()
            if resp.status_code == 200:
                config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_text(resp.text, encoding="utf-8")
                return resp.text
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(5 * (attempt + 1))
                continue
            resp.raise_for_status()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}")


def save_debug(name: str, html: str) -> Path:
    config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    p = config.DEBUG_DIR / name
    p.write_text(html, encoding="utf-8")
    return p
