"""
backtest/historical_llm_backtest_v6.py — CrisisPredictor
Sixth check: 100 NEW dates (50 stress, 50 normal) picked by a fixed random rule (seed 7), scored with ALL 14 factors.
Purpose: test, on dates never used before, the rule chosen on the first 200 dates:
    alarm = score from the 12 numeric factors >= 52 (news left out of the alarm), news shown as a separate warning.

Date rule: same stress/calm windows as v4; at least 5 days between new dates; no date within 10 days of any date
used in v1-v5. The 2 news texts per date come from the v5 timelines (written from history before any scoring).

    python backtest/historical_llm_backtest_v6.py
Then:
    python backtest/analyze_v6.py
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
from historical_llm_backtest_v4 import CALM_WINDOWS, GAP, KEEP_AWAY, NUMERIC, STRESS_WINDOWS, load_json, save_json  # noqa: E402
from historical_llm_backtest_v5 import GEO, TARIFF, pick  # noqa: E402

PER_LABEL, SEED = 50, 7
DESC_PATH = os.path.join(HERE, "backtest_v6_descriptions.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v6_results.json")
DATES_PATH = os.path.join(HERE, "backtest_v6_dates.json")


def used_dates():
    out = [r["date"] for r in load_json(os.path.join(HERE, "rerun41_results.json"), {}).values()]
    out += [r["date"] for r in load_json(os.path.join(HERE, "backtest_v3_results.json"), {}).values()]
    out += [d["date"] for d in load_json(os.path.join(HERE, "backtest_v4_dates.json"), [])]
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
        todo = dict(descs[date]["descriptions"])
        todo["tariff_sanctions"] = pick(TARIFF, date)
        todo["geopolitical_risk"] = pick(GEO, date)
        with ThreadPoolExecutor(max_workers=7) as ex:
            pairs = list(ex.map(_score_one, todo.items()))
        results[date] = {"date": date, "label": label, "factor_scores": dict(pairs)}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs if v is None]
        print(f"[{len(results)}/{len(dates)}] {date} {label} scored ({time.time() - t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    print(f"DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
