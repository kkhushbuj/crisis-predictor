"""
tools/market_tools.py — CrisisPredictor
Cached yfinance market data fetchers.
"""

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


def fetch_yf_series(ticker: str, start: str = "1996-01-01", end: str = None, field: str = "Close", ttl: int = TTL_FAST):
    """Fetch a single yfinance series with caching."""
    key = make_cache_key("yf", ticker, start, end, field)
    cached = get_cached(key)
    if cached is not None:
        return cached

    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        s = df[field][ticker]
    else:
        s = df[field]
    s = normalize_index(s.rename(ticker))
    set_cached(key, s, ttl=ttl)
    return s


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