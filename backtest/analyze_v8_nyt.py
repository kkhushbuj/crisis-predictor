"""
backtest/analyze_v8_nyt.py — CrisisPredictor
Compares the 300-date backtest with AI-written news (v5+v6+v7) against the same dates scored with REAL New York Times
headlines (v8). All 14 factors, alarm line 55, levels 30 / 55 / 75. No API calls.
    python backtest/analyze_v8_nyt.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from analyze_300_random import GROUPS, line, load, summary  # noqa: E402
from analyze_v2 import regime  # noqa: E402

NEWS_KEYS = ["tariff_sanctions", "geopolitical_risk"]


def main():
    old = [r for _, path in GROUPS for r in load(path)]
    new = load("backtest_v8_results.json")
    print(f"Old (AI-written news): {len(old)} dates | New (real NYT news): {len(new)} dates\n")
    line("AI-written news", old)
    line("REAL NYT news", new)
    print()
    line("numbers only (55)", new, "numbers_only", 55)

    pos, neg, *_ = summary(new)
    print("\nREAL NYT news: dates in each level (stress / normal):")
    for label in ("Calm", "Elevated", "Stress", "Crisis"):
        p = sum(regime(r["score"]) == label for r in pos)
        n = sum(regime(r["score"]) == label for r in neg)
        print(f"  {label:9} stress {p:3}   normal {n:3}")
    avg = lambda xs: sum(xs) / len(xs)
    print(f"\nAverage score: stress {avg([r['score'] for r in pos]):.1f}, normal {avg([r['score'] for r in neg]):.1f}")

    res_new = json.load(open(os.path.join(HERE, "backtest_v8_results.json"), encoding="utf-8"))
    res_old = {}
    for _, path in GROUPS:
        res_old.update(json.load(open(os.path.join(HERE, path), encoding="utf-8")))
    print("\nAverage news-factor score (stress dates / normal dates):")
    for k in NEWS_KEYS:
        for name, res in (("AI-written", res_old), ("real NYT", res_new)):
            s = [v["factor_scores"][k] for v in res.values() if v["label"] == "stress" and v["factor_scores"].get(k) is not None]
            n = [v["factor_scores"][k] for v in res.values() if v["label"] == "normal" and v["factor_scores"].get(k) is not None]
            print(f"  {k:17} {name:10} stress {avg(s):5.1f} | normal {avg(n):5.1f}")


if __name__ == "__main__":
    main()
