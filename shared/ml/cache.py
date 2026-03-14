"""
Unified caching layer.
  - If USE_REDIS=true and redis is reachable  → uses Redis (survives restarts, shared across workers)
  - Otherwise                                 → in-process dict with TTL (dev / fallback)

Usage:
    from shared.ml.cache import cache
    cache.set("key", value, ttl=300)
    value = cache.get("key")          # None on miss
    cache.delete("key")
"""
import json
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process fallback cache
# ---------------------------------------------------------------------------
class _LocalCache:
    def __init__(self):
        self._store: dict = {}   # key → (expires_at, value_json)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value_json = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return json.loads(value_json)

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            self._store[key] = (time.time() + ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"LocalCache.set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def flush_pattern(self, prefix: str):
        keys = [k for k in list(self._store.keys()) if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)


# ---------------------------------------------------------------------------
# Redis-backed cache
# ---------------------------------------------------------------------------
class _RedisCache:
    def __init__(self, url: str):
        import redis as redis_lib
        self._client = redis_lib.from_url(url, decode_responses=True, socket_connect_timeout=3)
        self._client.ping()   # fail fast if misconfigured
        logger.info("[Cache] Connected to Redis")

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self._client.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as e:
            logger.warning(f"Redis.get({key}) failed: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            self._client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning(f"Redis.set({key}) failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self._client.delete(key))
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    def flush_pattern(self, prefix: str) -> int:
        try:
            keys = self._client.keys(f"{prefix}*")
            if keys:
                self._client.delete(*keys)
            return len(keys)
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Factory — picks Redis or local based on config
# ---------------------------------------------------------------------------
def _build_cache():
    from shared.core.config import settings
    if settings.USE_REDIS:
        try:
            return _RedisCache(settings.REDIS_URL)
        except Exception as e:
            logger.warning(f"[Cache] Redis unavailable ({e}), falling back to in-process cache")
    return _LocalCache()


# Singleton
_cache_instance = None
_global_cache = None   # populated lazily on first import — avoids import-time side effects

def _lazy_init():
    global _global_cache
    if _global_cache is None:
        from shared.ml.cache import _build_cache
        _global_cache = _build_cache()
    return _global_cache

class _LazyCacheProxy:
    """Proxy that initialises the real cache on first call."""
    def get(self, *a, **kw):   return _lazy_init().get(*a, **kw)
    def set(self, *a, **kw):   return _lazy_init().set(*a, **kw)
    def delete(self, *a, **kw):return _lazy_init().delete(*a, **kw)
    def exists(self, *a, **kw):return _lazy_init().exists(*a, **kw)
    def flush_pattern(self, *a, **kw): return _lazy_init().flush_pattern(*a, **kw)

cache = _LazyCacheProxy()
