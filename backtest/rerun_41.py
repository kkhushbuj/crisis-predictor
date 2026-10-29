"""
backtest/rerun_41.py — CrisisPredictor
Re-scores ALL 41 historical test dates from scratch with the AI (the 11 original dates plus the 30 newer ones),
using the same real historical data and the same factor descriptions as before. Results are saved to
backtest/rerun41_results.json, with the earlier saved scores kept alongside for comparison.

Run from the project root so the shared ./cache is used:
    python backtest/rerun_41.py
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from historical_llm_backtest import (  # noqa: E402
    GEOPOLITICAL_HISTORICAL_CONTEXT, TEST_DATES, build_historical_descriptions,
)
from historical_llm_backtest_v2 import _score_one  # noqa: E402

OUT = os.path.join(HERE, "rerun41_results.json")


def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def main():
    old_a = {r["event"]: r for r in load(os.path.join(HERE, "historical_llm_backtest_results.json"), [])}
    old_b = load(os.path.join(HERE, "backtest_v2_results.json"), {})
    desc_b = load(os.path.join(HERE, "backtest_v2_descriptions.json"), {})
    results = load(OUT, {})

    jobs = []  # (event, date, group, label, descriptions, previous factor scores)
    for event, date in TEST_DATES.items():
        prev = old_a.get(event)
        label = "normal" if event.startswith("Calm") else "stress"
        jobs.append((event, date, "original11", label, None, prev["factor_scores"] if prev else None))
    for event, r in old_b.items():
        jobs.append((event, r["date"], "newer30", r["label"], desc_b[event]["descriptions"], r["factor_scores"]))

    t0 = time.time()
    for event, date, group, label, descs, prev in jobs:
        if event in results:
            continue
        if descs is None:  # original dates: rebuild the same real-data descriptions
            descs = build_historical_descriptions(date)
            geo = GEOPOLITICAL_HISTORICAL_CONTEXT[event]
            descs["tariff_sanctions"] = geo["tariff_sanctions"]
            descs["geopolitical_risk"] = geo["geopolitical_risk"]
        with ThreadPoolExecutor(max_workers=7) as ex:
            scores = dict(ex.map(_score_one, descs.items()))
        results[event] = {"date": date, "group": group, "label": label, "factor_scores": scores, "previous_factor_scores": prev}
        json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1)
        print(f"[{len(results)}/41] {event} {date} done ({time.time() - t0:.0f}s)", flush=True)
    print(f"DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
