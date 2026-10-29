"""
backtest/analyze_v2.py — CrisisPredictor
Turns backtest_v2_results.json (factor scores per date) into 0-100 Crisis Scores
and accuracy metrics. No API calls. Run from anywhere:
    python backtest/analyze_v2.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))

from tools.scoring_tools import CATEGORY_FACTORS, CATEGORY_WEIGHTS  # noqa: E402

THRESHOLD = 55
OLD_WEIGHTS = {"credit_systemic": 30, "liquidity_shock": 30, "macro": 20, "geopolitical": 20}


def category_means(fs, include_news=True):
    out = {}
    for cat, keys in CATEGORY_FACTORS.items():
        if cat == "geopolitical" and not include_news:
            continue
        vals = [fs[k] for k in keys if fs.get(k) is not None]
        out[cat] = sum(vals) / len(vals) if vals else 0.0
    return out


def crisis_score(fs, weights, include_news=True):
    means = category_means(fs, include_news)
    used = {c: w for c, w in weights.items() if c in means}
    total_w = sum(used.values())
    return sum((w / total_w) * ((-means[c]) + 10) / 20 * 100 for c, w in used.items())


def regime(x):
    return "Calm" if x < 30 else "Elevated" if x < 55 else "Stress" if x < 75 else "Crisis"


def auc(pos, neg):
    """Probability a random stress date scores higher than a random normal date."""
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def metrics(rows, key):
    pos = [r[key] for r in rows if r["label"] == "stress"]
    neg = [r[key] for r in rows if r["label"] == "normal"]
    hits = sum(s >= THRESHOLD for s in pos)
    fas = sum(s >= THRESHOLD for s in neg)
    return {
        "hit": f"{hits}/{len(pos)}", "false_alarm": f"{fas}/{len(neg)}",
        "accuracy": f"{(hits + len(neg) - fas)}/{len(pos) + len(neg)}",
        "avg_stress": round(sum(pos) / len(pos), 1), "avg_normal": round(sum(neg) / len(neg), 1),
        "auc": round(auc(pos, neg), 2),
    }


def main():
    res = json.load(open(os.path.join(HERE, "backtest_v2_results.json"), encoding="utf-8"))
    desc = json.load(open(os.path.join(HERE, "backtest_v2_descriptions.json"), encoding="utf-8"))
    rows = []
    for ev, r in res.items():
        fs = r["factor_scores"]
        vix = re.search(r"VIX was ([\d.]+)", desc[ev]["descriptions"]["vix"])
        dd = re.search(r"was (-?[\d.]+)% from", desc[ev]["descriptions"]["drawdown"])
        rows.append({
            "event": ev, "date": r["date"], "label": r["label"],
            "full15": crisis_score(fs, CATEGORY_WEIGHTS), "num_only": crisis_score(fs, CATEGORY_WEIGHTS, include_news=False),
            "full20": crisis_score(fs, OLD_WEIGHTS),
            "news": (fs["tariff_sanctions"] + fs["geopolitical_risk"]) / 2,
            "vix": float(vix.group(1)) if vix else None, "dd": float(dd.group(1)) if dd else None,
            "missing": [k for k, v in fs.items() if v is None],
        })
    rows.sort(key=lambda r: (r["label"], r["date"]))

    print(f"{'event':28}{'date':12}{'label':8}{'VIX':>6}{'DD%':>7}{'news':>6}{'15%':>7}{'numOnly':>8}{'20%':>7}  call")
    for r in rows:
        on = r["full15"] >= THRESHOLD
        ok = on if r["label"] == "stress" else not on
        print(f"{r['event']:28}{r['date']:12}{r['label']:8}{r['vix'] or 0:6.1f}{r['dd'] or 0:7.1f}{r['news']:6.1f}"
              f"{r['full15']:7.1f}{r['num_only']:8.1f}{r['full20']:7.1f}  {'OK' if ok else 'WRONG'} ({regime(r['full15'])})")
    print()
    for name, key in [("Full model, news 15% (current)", "full15"), ("Numeric factors only (no news)", "num_only"),
                      ("Full model, news 20% (old)", "full20")]:
        print(f"{name:34}", metrics(rows, key))
    miss = [r["event"] for r in rows if r["missing"]]
    print("\nDates with failed factors:", miss or "none")


if __name__ == "__main__":
    main()
