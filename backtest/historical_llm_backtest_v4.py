"""
backtest/historical_llm_backtest_v4.py — CrisisPredictor
Fourth check: 120 NEW dates (60 stress, 60 normal) picked by a fixed random rule, not by hand.

How the dates are chosen (fixed before any scoring):
  * Stress dates are drawn at random from known stress windows (listed below); normal dates from known calm windows.
    The windows come from market history, not from the model's scores.
  * Seed 42; at least 5 days between new dates; no date within 10 days of any date used in v1-v3.
Scoring: the 12 numeric factors only (real historical data, same method as before). The 2 news factors are left out,
because writing 240 history texts by hand is error-prone; the score uses the remaining weights rescaled.
The alarm cutoff stays 55 (locked).

    python backtest/historical_llm_backtest_v4.py
Then:
    python backtest/analyze_v4.py
"""

import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from historical_llm_backtest import build_historical_descriptions  # noqa: E402
from historical_llm_backtest_v2 import _score_one  # noqa: E402

STRESS_WINDOWS = [
    ("2000-09-01", "2002-10-31"), ("2007-08-01", "2009-03-31"), ("2010-04-20", "2010-07-10"),
    ("2011-07-25", "2011-10-10"), ("2015-08-15", "2016-02-15"), ("2018-10-05", "2018-12-31"),
    ("2020-02-20", "2020-04-15"), ("2022-01-05", "2022-10-20"), ("2025-03-05", "2025-04-20"),
]
CALM_WINDOWS = [
    ("2003-07-01", "2007-01-31"), ("2012-02-01", "2015-06-30"), ("2016-07-01", "2018-01-15"),
    ("2019-01-15", "2020-01-31"), ("2020-12-01", "2021-12-15"), ("2023-11-15", "2024-07-01"),
    ("2024-11-01", "2025-01-31"),
]
PER_LABEL, SEED, GAP, KEEP_AWAY = 60, 42, 5, 10
NUMERIC = ["yield_curve", "hy_spread", "bank_rel", "repo_stress", "m2_growth", "vix", "drawdown",
           "gold_momentum", "dxy", "jobless", "cpi", "oil"]

DESC_PATH = os.path.join(HERE, "backtest_v4_descriptions.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v4_results.json")
DATES_PATH = os.path.join(HERE, "backtest_v4_dates.json")


def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def used_dates():
    out = [r["date"] for r in load_json(os.path.join(HERE, "rerun41_results.json"), {}).values()]
    out += [r["date"] for r in load_json(os.path.join(HERE, "backtest_v3_results.json"), {}).values()]
    return [pd.Timestamp(d) for d in out]


def pick_dates():
    existing = load_json(DATES_PATH, None)
    if existing:
        return existing
    rng, used = random.Random(SEED), used_dates()
    chosen = []
    for label, windows in (("stress", STRESS_WINDOWS), ("normal", CALM_WINDOWS)):
        pool = sorted({d for a, b in windows for d in pd.bdate_range(a, b)})
        pool = [d for d in pool if all(abs((d - u).days) > KEEP_AWAY for u in used)]
        rng.shuffle(pool)
        picked = []
        for d in pool:
            if all(abs((d - p).days) >= GAP for p in picked):
                picked.append(d)
            if len(picked) == PER_LABEL:
                break
        chosen += [{"date": d.strftime("%Y-%m-%d"), "label": label} for d in sorted(picked)]
    save_json(DATES_PATH, chosen)
    return chosen


def main():
    t0 = time.time()
    dates = pick_dates()
    print(f"{len(dates)} dates ({sum(d['label'] == 'stress' for d in dates)} stress)", flush=True)
    descs, results = load_json(DESC_PATH, {}), load_json(RESULTS_PATH, {})
    for i, item in enumerate(dates, 1):
        date, label = item["date"], item["label"]
        if date in results:
            continue
        if date not in descs:
            try:
                d = build_historical_descriptions(date)
            except Exception as e:
                print(f"[{i}] {date}: FAILED to fetch data: {str(e)[:100]}", flush=True)
                continue
            descs[date] = {"label": label, "descriptions": {k: d[k] for k in NUMERIC}}
            save_json(DESC_PATH, descs)
        with ThreadPoolExecutor(max_workers=7) as ex:
            pairs = list(ex.map(_score_one, descs[date]["descriptions"].items()))
        results[date] = {"date": date, "label": label, "factor_scores": dict(pairs)}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs if v is None]
        print(f"[{len(results)}/{len(dates)}] {date} {label} scored ({time.time() - t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    print(f"DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
