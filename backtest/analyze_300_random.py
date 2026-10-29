"""
backtest/analyze_300_random.py — CrisisPredictor
The 300-date backtest where EVERY date came from a random draw (no hand-picked dates): all 14 factors, alarm line 55,
levels 30 / 55 / 75. No API calls.
Dates: 120 (seed 42) + 100 (seed 7) + 80 (seed 2026), drawn from the same stress and calm windows (150 stress, 150 normal).
    python backtest/analyze_300_random.py
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
    ("120 random (seed 42)", "backtest_v5_results.json"),
    ("100 random (seed 7)", "backtest_v6_results.json"),
    ("80 random (seed 2026)", "backtest_v7_results.json"),
]


def load(name):
    res = json.load(open(os.path.join(HERE, name), encoding="utf-8"))
    return [{"date": v.get("date", k), "label": v["label"], "score": crisis_score(v["factor_scores"], CATEGORY_WEIGHTS),
             "numbers_only": crisis_score(v["factor_scores"], CATEGORY_WEIGHTS, include_news=False)} for k, v in res.items()]


def summary(rows, key="score", line=THRESHOLD):
    pos = [r for r in rows if r["label"] == "stress"]
    neg = [r for r in rows if r["label"] == "normal"]
    hits = sum(r[key] >= line for r in pos)
    fas = sum(r[key] >= line for r in neg)
    return pos, neg, hits, fas, hits + len(neg) - fas


def line(name, rows, key="score", cut=THRESHOLD):
    pos, neg, hits, fas, right = summary(rows, key, cut)
    a = auc([r[key] for r in pos], [r[key] for r in neg])
    print(f"{name:22} right {right}/{len(rows)} ({right / len(rows):.0%}) | stress caught {hits}/{len(pos)} | false alarms {fas}/{len(neg)} | AUC {a:.3f}")


def main():
    all_rows = []
    print(f"All 14 factors, alarm line {THRESHOLD}\n")
    for name, path in GROUPS:
        rows = load(path)
        all_rows += rows
        line(name, rows)
    line("ALL RANDOM", all_rows)
    print("\nFor comparison, on the same dates:")
    line("numbers only, line 52", all_rows, "numbers_only", 52)
    line("numbers only, line 55", all_rows, "numbers_only", 55)
    pos, neg, *_ = summary(all_rows)
    print("\nDates in each level (stress / normal):")
    for label in ("Calm", "Elevated", "Stress", "Crisis"):
        p = sum(regime(r["score"]) == label for r in pos)
        n = sum(regime(r["score"]) == label for r in neg)
        print(f"  {label:9} stress {p:3}   normal {n:3}")
    avg = lambda xs: sum(xs) / len(xs)
    print(f"\nAverage score: stress {avg([r['score'] for r in pos]):.1f}, normal {avg([r['score'] for r in neg]):.1f}")


if __name__ == "__main__":
    main()
