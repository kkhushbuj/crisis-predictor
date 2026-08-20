"""
tools/repo_m2_tools.py — CrisisPredictor
Repo Market Stress (SOFR spike vs Fed target) + M2 Money Supply Growth.
Both via FRED, cached like the other FRED series.
"""

import os
from fredapi import Fred
from dotenv import load_dotenv

from cache_utils import make_cache_key, get_cached, set_cached, normalize_index, TTL_SLOW

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

REPO_M2_SERIES = {
    "sofr": "SOFR",              # Secured Overnight Financing Rate
    "fed_target_upper": "DFEDTARU",  # Fed funds target range - upper bound
    "m2": "M2SL",                 # M2 Money Stock
}


def fetch_series(series_id: str, obs_start: str = "2006-01-01", obs_end: str = None, ttl: int = TTL_SLOW):
    key = make_cache_key("fred_repo_m2", series_id, obs_start, obs_end)
    cached = get_cached(key)
    if cached is not None:
        return cached

    s = fred.get_series(series_id, observation_start=obs_start, observation_end=obs_end)
    s = normalize_index(s.rename(series_id))
    set_cached(key, s, ttl=ttl)
    return s


def fetch_repo_m2_data(start: str = "2006-01-01", end: str = None) -> dict:
    """Fetch SOFR, Fed target upper bound, and M2 for repo stress + M2 growth factors."""
    data = {}
    for name, series_id in REPO_M2_SERIES.items():
        data[name] = fetch_series(series_id, obs_start=start, obs_end=end)
    return data


def compute_repo_spread(data: dict):
    """SOFR minus Fed target upper bound — spike above 0 signals funding stress."""
    sofr = data["sofr"]
    target = data["fed_target_upper"]
    combined = sofr.to_frame("sofr").join(target.to_frame("target"), how="inner")
    combined["spread"] = combined["sofr"] - combined["target"]
    return combined["spread"]


def compute_m2_yoy_growth(data: dict):
    """M2 year-over-year growth rate (%)."""
    m2 = data["m2"]
    return m2.pct_change(12) * 100  # M2SL is monthly, so 12 = YoY


if __name__ == "__main__":
    import time
    t0 = time.time()
    data = fetch_repo_m2_data()
    print(f"Fetched {len(data)} series in {time.time()-t0:.1f}s")
    for name, s in data.items():
        print(f"{name:20s} | rows={len(s):6d} | range={s.index.min().date()} to {s.index.max().date()}")

    repo_spread = compute_repo_spread(data)
    m2_growth = compute_m2_yoy_growth(data)

    print(f"\nLatest repo spread: {repo_spread.iloc[-1]:.3f}% (SOFR vs Fed target upper)")
    print(f"Latest M2 YoY growth: {m2_growth.dropna().iloc[-1]:.2f}%")