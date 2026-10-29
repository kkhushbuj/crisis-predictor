"""
backtest/analyze_300.py — CrisisPredictor
The 300-date backtest of the live app setup: all 14 factors, alarm line 55, levels 30 / 55 / 75. No API calls.
Dates: 41 hand-picked + 39 fresh + 120 random-rule + 100 new random-rule (152 stress, 148 normal).
    python backtest/analyze_300.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from analyze_v2 import auc, crisis_score, regime  # noqa: E402
from tools.scoring_tools import CATEGORY_WEIGHTS  # noqa: E402

THRESHOLD = 55
GROUPS = [
    ("41 hand-picked", "rerun41_results.json"),
    ("39 fresh", "backtest_v3_results.json"),
    ("120 random", "backtest_v5_results.json"),
    ("100 new random", "backtest_v6_results.json"),
]


def load(name):
    res = json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    return [{"date": v.get("date", k), "label": v["label"], "score": crisis_score(v["factor_scores"], CATEGORY_WEIGHTS)}
            for k, v in res.items()]


def summary(rows):
    pos = [r for r in rows if r["label"] == "stress"]
    neg = [r for r in rows if r["label"] == "normal"]
    hits = sum(r["score"] >= THRESHOLD for r in pos)
    fas = sum(r["score"] >= THRESHOLD for r in neg)
    right = hits + len(neg) - fas
    return pos, neg, hits, fas, right


def main():
    all_rows = []
    print(f"Alarm line {THRESHOLD}, all 14 factors\n")
    for name, path in GROUPS:
        rows = load(path)
        all_rows += rows
        pos, neg, hits, fas, right = summary(rows)
        print(f"{name:15} right {right}/{len(rows)} ({right / len(rows):.0%}) | stress caught {hits}/{len(pos)} | false alarms {fas}/{len(neg)}")
    pos, neg, hits, fas, right = summary(all_rows)
    print(f"{'ALL':15} right {right}/{len(all_rows)} ({right / len(all_rows):.0%}) | stress caught {hits}/{len(pos)} | false alarms {fas}/{len(neg)}")
    print(f"AUC {auc([r['score'] for r in pos], [r['score'] for r in neg]):.3f} (1.00 = perfect ranking, 0.50 = coin flip)")
    print("\nDates in each level (stress / normal):")
    for label in ("Calm", "Elevated", "Stress", "Crisis"):
        p = sum(regime(r["score"]) == label for r in pos)
        n = sum(regime(r["score"]) == label for r in neg)
        print(f"  {label:9} stress {p:3}   normal {n:3}")


if __name__ == "__main__":
    main()
