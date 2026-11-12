"""
Tiny in-process TTL cache for read-heavy endpoints.

The dashboard polls /summary every 30s per open tab; this keeps those requests
off the database. The cache is cleared whenever a pipeline run finishes, so
users never see stale numbers after a refresh. For multi-instance deployments
swap this module for Redis — the interface (get_or_set / clear / stats) is small.
"""

import threading
import time
from typing import Any, Callable

from app.config import get_settings

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}
_hits = 0
_misses = 0


def get_or_set(key: str, producer: Callable[[], Any], ttl: int | None = None) -> tuple[Any, bool]:
    """Return (value, was_cache_hit)."""
    global _hits, _misses
    ttl = get_settings().cache_ttl_seconds if ttl is None else ttl
    now = time.monotonic()
    with _lock:
        entry = _store.get(key)
        if entry and entry[0] > now:
            _hits += 1
            return entry[1], True
    value = producer()
    with _lock:
        _store[key] = (now + ttl, value)
        _misses += 1
    return value, False


def clear() -> None:
    with _lock:
        _store.clear()


def stats() -> dict:
    with _lock:
        total = _hits + _misses
        return {
            "entries": len(_store),
            "hits": _hits,
            "misses": _misses,
            "hit_rate": round(_hits / total, 3) if total else None,
        }
