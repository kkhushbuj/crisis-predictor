"""
backtest/historical_llm_backtest_v8_nyt.py — CrisisPredictor
The SAME 300 random dates (v4/v5 120 + v6 100 + v7 80), but the 2 news factors are scored from REAL New York Times
headlines instead of the AI-written timeline texts.

What stays the same: the 12 numeric factor scores are copied from the v5/v6/v7 results (same data, same scores).
What changes: tariff_sanctions and geopolitical_risk are re-scored by the same AI scorer (score_factor) on real
NYT headlines published in the 30 days BEFORE each date (never on the date, never after).

Headline rule (fixed before any scoring; nothing is tuned afterwards):
  - window: pub_date from date-30 days up to date-1 day
  - skip sections that are not news (sports, arts, style, travel, food, books, movies, theater, real estate, magazine, obituaries)
  - keep headlines whose headline+abstract match the topic's keyword list (word-boundary match)
  - rank by number of distinct keywords matched (+2 if in the headline), then newest first; keep the top 5
  - text = "- headline. abstract" per line, no dates, cut at 2000 characters (as the live app does)

    python backtest/historical_llm_backtest_v8_nyt.py --fetch     # download needed NYT months (slow, resumable)
    python backtest/historical_llm_backtest_v8_nyt.py --score     # build texts + score (needs the cache)
Then:
    python backtest/analyze_v8_nyt.py
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.append(ROOT)
sys.path.append(HERE)

from historical_llm_backtest_v2 import _score_one  # noqa: E402

CACHE = os.path.join(HERE, "backtest_v8_nyt_cache")
TEXTS_PATH = os.path.join(HERE, "backtest_v8_news_texts.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v8_results.json")
SOURCES = [
    ("backtest_v4_dates.json", "backtest_v5_results.json"),
    ("backtest_v6_dates.json", "backtest_v6_results.json"),
    ("backtest_v7_dates.json", "backtest_v7_results.json"),
]
NEWS_KEYS = ["tariff_sanctions", "geopolitical_risk"]
WINDOW_DAYS, TOP_N, MAX_CHARS = 30, 5, 2000

SKIP_SECTIONS = {
    "sports", "arts", "style", "travel", "food", "books", "movies", "theater", "real estate", "magazine",
    "obituaries", "fashion & style", "dining", "t magazine", "crosswords & games", "home & garden", "weddings",
}
KEYWORDS = {
    "tariff_sanctions": ["tariff", "tariffs", "sanction", "sanctions", "trade war", "embargo", "trade deal", "trade talks",
                         "trade dispute", "import duty", "import duties", "export ban", "export controls", "quota",
                         "quotas", "protectionism", "retaliation", "retaliatory", "boycott"],
    "geopolitical_risk": ["war", "invasion", "invade", "invades", "invaded", "military", "missile", "missiles", "troops",
                          "attack", "attacks", "terror", "terrorist", "terrorism", "bomb", "bombing", "conflict",
                          "nuclear", "airstrike", "airstrikes", "coup", "hostage", "hostages", "ceasefire", "rebels",
                          "insurgents", "crisis"],
}
PREFIX = {
    "tariff_sanctions": "Recent news on tariffs/sanctions/trade war:\n",
    "geopolitical_risk": "Recent news on geopolitical conflict/risk:\n",
}


def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def all_dates():
    out = []
    for dpath, _ in SOURCES:
        out += load_json(os.path.join(HERE, dpath), [])
    return out


def months_needed(dates):
    need = set()
    for item in dates:
        d = pd.Timestamp(item["date"])
        for x in (d - pd.Timedelta(days=WINDOW_DAYS), d - pd.Timedelta(days=1)):
            need.add((x.year, x.month))
    return sorted(need)


def nyt_key():
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if line.startswith("NYT_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("NYT_API_KEY missing in .env")


def fetch_month(key, year, month):
    path = os.path.join(CACHE, f"{year}-{month:02d}.json")
    if os.path.exists(path):
        return
    url = f"https://api.nytimes.com/svc/archive/v1/{year}/{month}.json?api-key={key}"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                docs = json.load(r)["response"]["docs"]
            keep = [{"d": x.get("pub_date", "")[:10], "h": (x.get("headline") or {}).get("main") or "",
                     "a": x.get("abstract") or x.get("snippet") or "", "s": (x.get("section_name") or "")}
                    for x in docs if x.get("pub_date")]
            save_json(path, keep)
            print(f"  {year}-{month:02d}: {len(keep)} articles", flush=True)
            return
        except urllib.error.HTTPError as e:
            wait = 70 if e.code == 429 else 15
            print(f"  {year}-{month:02d}: HTTP {e.code}, waiting {wait}s", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"  {year}-{month:02d}: {str(e)[:80]}, retrying", flush=True)
            time.sleep(15)
    print(f"  {year}-{month:02d}: GAVE UP", flush=True)


def do_fetch():
    os.makedirs(CACHE, exist_ok=True)
    key, months = nyt_key(), months_needed(all_dates())
    todo = [m for m in months if not os.path.exists(os.path.join(CACHE, f"{m[0]}-{m[1]:02d}.json"))]
    print(f"{len(months)} months needed, {len(todo)} still to download", flush=True)
    for y, m in todo:
        fetch_month(key, y, m)
        time.sleep(13)  # NYT limit is about 5 calls a minute
    print("FETCH DONE", flush=True)


_patterns = {k: re.compile(r"\b(" + "|".join(re.escape(w) for w in sorted(ws, key=len, reverse=True)) + r")\b")
             for k, ws in KEYWORDS.items()}
_month_cache = {}


def month_articles(year, month):
    if (year, month) not in _month_cache:
        p = os.path.join(CACHE, f"{year}-{month:02d}.json")
        _month_cache[(year, month)] = load_json(p, None)
    return _month_cache[(year, month)]


def build_text(topic, date):
    d = pd.Timestamp(date)
    start, end = (d - pd.Timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d"), (d - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    pool = []
    for y, m in sorted({(start[:4], start[5:7]), (end[:4], end[5:7])}):
        arts = month_articles(int(y), int(m))
        if arts is None:
            raise RuntimeError(f"month {y}-{m} not downloaded")
        pool += arts
    scored, seen = [], set()
    for a in pool:
        if not (start <= a["d"] <= end) or a["s"].lower() in SKIP_SECTIONS or not a["h"] or a["h"] in seen:
            continue
        head, full = a["h"].lower(), (a["h"] + " " + a["a"]).lower()
        hits = set(_patterns[topic].findall(full))
        if not hits:
            continue
        score = len(hits) + 2 * bool(_patterns[topic].search(head))
        seen.add(a["h"])
        scored.append((score, a["d"], a))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    lines = [f"- {a['h']}. {a['a']}".strip() for _, _, a in scored[:TOP_N]]
    body = "\n".join(lines) if lines else "No relevant headlines found."
    return (PREFIX[topic] + body)[:MAX_CHARS + len(PREFIX[topic])]


def do_score():
    dates, texts, results = all_dates(), load_json(TEXTS_PATH, {}), load_json(RESULTS_PATH, {})
    old = {}
    for _, rpath in SOURCES:
        old.update(load_json(os.path.join(HERE, rpath), {}))
    t0 = time.time()
    for item in dates:
        date, label = item["date"], item["label"]
        texts[date] = {k: build_text(k, date) for k in NEWS_KEYS}
    save_json(TEXTS_PATH, texts)
    print(f"built news texts for {len(texts)} dates", flush=True)
    for i, item in enumerate(dates, 1):
        date, label = item["date"], item["label"]
        if date in results or date not in old:
            continue
        with ThreadPoolExecutor(max_workers=2) as ex:
            pairs = dict(ex.map(_score_one, texts[date].items()))
        scores = {k: v for k, v in old[date]["factor_scores"].items() if k not in NEWS_KEYS}
        scores.update(pairs)
        results[date] = {"date": date, "label": label, "factor_scores": scores}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs.items() if v is None]
        print(f"[{len(results)}/{len(dates)}] {date} {label} tariff={pairs['tariff_sanctions']} geo={pairs['geopolitical_risk']} "
              f"({time.time() - t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    print(f"SCORE DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        do_fetch()
    if a.score:
        do_score()
    if not (a.fetch or a.score):
        dates = all_dates()
        print(f"{len(dates)} dates, {len(months_needed(dates))} NYT months needed")
