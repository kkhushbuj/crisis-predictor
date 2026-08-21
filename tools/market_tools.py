"""
tools/market_tools.py — CrisisPredictor
Cached yfinance market data fetchers.
"""

import time

import pandas as pd
import yfinance as yf

from cache_utils import make_cache_key, get_cached, set_cached, normalize_index, TTL_FAST

# Validated tickers
YF_TICKERS = {
    "vix": "^VIX",
    "sp500": "^GSPC",
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "xlf": "XLF",
    "oil": "CL=F",
}

# Retry settings for transient Yahoo Finance rate limiting (common on shared
# cloud IPs like Streamlit Community Cloud).
YF_MAX_RETRIES = 3
YF_RETRY_BACKOFF_SECONDS = 3


def fetch_yf_series(ticker: str, start: str = "1996-01-01", end: str = None, field: str = "Close", ttl: int = TTL_FAST):
    """Fetch a single yfinance series with caching, retrying on transient
    rate-limit errors and falling back to the last known-good cached value
    (even if expired) if every retry fails."""
    key = make_cache_key("yf", ticker, start, end, field)
    stale_key = make_cache_key("yf-stale", ticker, start, end, field)

    cached = get_cached(key)
    if cached is not None:
        return cached

    last_error = None
    for attempt in range(YF_MAX_RETRIES):
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                s = df[field][ticker]
            else:
                s = df[field]
            if s.dropna().empty:
                raise ValueError(f"No data returned for {ticker}")
            s = normalize_index(s.rename(ticker))
            set_cached(key, s, ttl=ttl)
            set_cached(stale_key, s, ttl=None)  # never expires — last known-good fallback
            return s
        except Exception as e:
            last_error = e
            if attempt < YF_MAX_RETRIES - 1:
                time.sleep(YF_RETRY_BACKOFF_SECONDS * (attempt + 1))

    # All retries failed — fall back to the last known-good value if we have one.
    stale = get_cached(stale_key)
    if stale is not None:
        print(f"[market_tools] {ticker}: live fetch failed ({last_error}), using stale cached data")
        return stale

    raise RuntimeError(f"Failed to fetch {ticker} after {YF_MAX_RETRIES} attempts and no cached fallback exists: {last_error}")


def fetch_all_market_series(start: str = "2006-01-01", end: str = None) -> dict:
    """Fetch every yfinance series needed for the liquidity/credit pillars."""
    data = {}
    for name, ticker in YF_TICKERS.items():
        data[name] = fetch_yf_series(ticker, start=start, end=end)
    return data


if __name__ == "__main__":
    import time
    t0 = time.time()
    data = fetch_all_market_series()
    print(f"Fetched {len(data)} market series in {time.time()-t0:.1f}s")
    for name, s in data.items():
        print(f"{name:15s} | rows={len(s):6d} | range={s.index.min().date()} to {s.index.max().date()}")