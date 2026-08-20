"""
cache_utils.py — CrisisPredictor
Shared disk-based caching layer with TTL, matching SemiBot's cache_utils.py pattern.
"""

import hashlib
import pandas as pd
from diskcache import Cache

CACHE_DIR = "./cache"
cache = Cache(CACHE_DIR)

TTL_SLOW = 24 * 60 * 60   # 24h — FRED/macro series
TTL_FAST = 15 * 60        # 15min — market data (yfinance)
TTL_NEWS = 60 * 60        # 1h — LLM news sentiment


def make_cache_key(*parts) -> str:
    """Build a stable cache key from arbitrary parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(key: str):
    """Return cached value or None if missing/expired."""
    return cache.get(key)


def set_cached(key: str, value, ttl: int = TTL_FAST):
    """Store a value in the cache with a TTL (seconds)."""
    cache.set(key, value, expire=ttl)


def normalize_index(s: pd.Series) -> pd.Series:
    """Normalize a Series' datetime index to midnight, no timezone — fixes
    dtype mismatches between FRED (datetime64[us]) and yfinance (datetime64[s])."""
    s = s.copy()
    s.index = pd.to_datetime(s.index).normalize()
    return s


def clear_all_cache():
    """Wipe the entire cache — useful during development/debugging."""
    cache.clear()
    print("Cache cleared.")


if __name__ == "__main__":
    # quick self-test
    set_cached("test_key", "hello", ttl=60)
    print("Cached value:", get_cached("test_key"))
    print("Missing key:", get_cached("nonexistent_key"))