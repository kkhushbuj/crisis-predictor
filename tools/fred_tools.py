"""
tools/fred_tools.py — CrisisPredictor
Cached FRED series fetchers.
"""

import os
from fredapi import Fred
from dotenv import load_dotenv

from cache_utils import make_cache_key, get_cached, set_cached, normalize_index, TTL_SLOW

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

# Validated series IDs (BAA10Y replaces BAMLH0A0HYM2 — ICE discontinued pre-2023 history)
FRED_SERIES = {
    "yield_curve": "T10Y2Y",
    "hy_spread": "BAA10Y",
    "jobless": "ICSA",
    "cpi": "CPIAUCSL",
}


def fetch_fred_series(series_id: str, obs_start: str = "1996-01-01", obs_end: str = None, ttl: int = TTL_SLOW):
    """Fetch a single FRED series with caching."""
    key = make_cache_key("fred", series_id, obs_start, obs_end)
    cached = get_cached(key)
    if cached is not None:
        return cached

    s = fred.get_series(series_id, observation_start=obs_start, observation_end=obs_end)
    s = normalize_index(s.rename(series_id))
    set_cached(key, s, ttl=ttl)
    return s


def fetch_all_fred_series(start: str = "2006-01-01", end: str = None) -> dict:
    """Fetch every FRED series needed for the credit/macro pillars."""
    data = {}
    for name, series_id in FRED_SERIES.items():
        obs_start = "1996-01-01" if name == "hy_spread" else start
        data[name] = fetch_fred_series(series_id, obs_start=obs_start, obs_end=end)
    return data


if __name__ == "__main__":
    import time
    t0 = time.time()
    data = fetch_all_fred_series()
    print(f"Fetched {len(data)} FRED series in {time.time()-t0:.1f}s")
    for name, s in data.items():
        print(f"{name:15s} | rows={len(s):6d} | range={s.index.min().date()} to {s.index.max().date()}")