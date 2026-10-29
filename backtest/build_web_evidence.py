"""
backtest/build_web_evidence.py — CrisisPredictor
Builds web/data/evidence.json, the real backtest numbers shown on the landing page.
No API calls. Re-run it whenever the weights or cutoffs change:

    python backtest/build_web_evidence.py

Sources (all saved results already in this folder):
  - rerun41_results.json, backtest_v3_results.json, backtest_v5_results.json, backtest_v6_results.json
                                        the 300 test dates (152 stress, 148 calm), all 14 factors
  - monthly_backtest_results.csv        monthly scores for 2008 GFC and COVID, with NBER recession flags
Scores are recomputed from the saved per-factor scores with the CURRENT weights in
tools/scoring_tools.py, so the page always matches the live model.
"""

import csv
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from analyze_v2 import auc, crisis_score  # noqa: E402
from tools.scoring_tools import CATEGORY_WEIGHTS, REGIMES  # noqa: E402

THRESHOLD = next(lo for lo, _, label, _c in REGIMES if label == "Stress")

NAMES = {
    "S01_Aug2007_credit_crunch": "Aug 2007, credit crunch",
    "S02_Bear_Stearns_2008": "Mar 2008, Bear Stearns",
    "S03_Post_Lehman_2008": "Sep 2008, after Lehman",
    "S04_GFC_low_2009": "Mar 2009, financial crisis low",
    "S05_Euro_scare_2010": "May 2010, euro debt scare",
    "S06_US_downgrade_2011": "Aug 2011, US downgrade",
    "S07_China_shock_2015": "Aug 2015, China shock",
    "S08_Oil_China_selloff_2016": "Feb 2016, oil and China selloff",
    "S09_Volmageddon_2018": "Feb 2018, volatility spike",
    "S10_Q4_2018_low": "Dec 2018, trade-war low",
    "S11_COVID_VIX_peak_2020": "Mar 2020, COVID panic",
    "S12_Rate_shock_bear_2022": "Jun 2022, rate-shock bear market",
    "S13_Oct2022_low": "Oct 2022, bear market low",
    "S14_Tariff_selloff_2025": "Apr 2025, tariff selloff",
    "S15_Yen_carry_spike_2024": "Aug 2024, yen carry spike",
}


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RESULT_FILES = ["rerun41_results.json", "backtest_v3_results.json", "backtest_v5_results.json", "backtest_v6_results.json"]
DESC_FILES = ["backtest_v2_descriptions.json", "backtest_v3_descriptions.json", "backtest_v4_descriptions.json", "backtest_v6_descriptions.json"]


def date_name(d, label):
    kind = "stress period" if label == "stress" else "calm period"
    return f"{int(d[8:10])} {MONTHS[int(d[5:7]) - 1]} {d[:4]}, {kind}"


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


def month_index(d):
    return int(d[:4]) * 12 + int(d[5:7])


def monthly_block(rows, title):
    pts = [{"date": r["date"], "score": round(r["score"], 1), "recession": r["recession"]} for r in rows]
    first_cross = next((p["date"] for p in pts if p["score"] >= THRESHOLD), None)
    rec_start = next((p["date"] for p in pts if p["recession"]), None)
    lead = (month_index(rec_start) - month_index(first_cross)) if first_cross and rec_start else None
    back_under = [p["date"][:7] for p in pts if first_cross and p["date"] > first_cross and p["recession"] and p["score"] < THRESHOLD]
    peak = max(pts, key=lambda p: p["score"])
    return {"title": title, "points": pts, "first_cross": first_cross, "recession_start": rec_start,
            "lead_months": lead, "back_under_during_recession": back_under, "peak": peak}


def main():
    descs = {}
    for f in DESC_FILES:
        descs.update(load(f))
    points = []
    for f in RESULT_FILES:
        for ev, r in load(f).items():
            score = round(crisis_score(r["factor_scores"], CATEGORY_WEIGHTS), 1)
            label = r["label"]
            name = NAMES.get(ev) or date_name(r["date"], label)
            d = descs.get(ev, descs.get(r["date"], {})).get("descriptions", {})
            vix = re.search(r"VIX was ([\d.]+)", d.get("vix", ""))
            dd = re.search(r"was (-?[\d.]+)% from", d.get("drawdown", ""))
            points.append({"event": ev, "date": r["date"], "label": label, "name": name, "score": score,
                           "flagged": score >= THRESHOLD,
                           "vix": float(vix.group(1)) if vix else None, "drawdown": float(dd.group(1)) if dd else None})
    points.sort(key=lambda p: p["score"])
    stress = [p for p in points if p["label"] == "stress"]
    normal = [p for p in points if p["label"] == "normal"]
    shown = [p for p in points if p["vix"] is not None and p["drawdown"] is not None]  # compare view needs both
    missed = [p for p in stress if not p["flagged"]]

    monthly = {"gfc": [], "covid": []}
    with open(os.path.join(HERE, "monthly_backtest_results.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            factors = {k: int(v) for k, v in r.items() if k not in
                       ("period", "date", "composite", "regime", "status", "nber_recession", "missing_factors")}
            row = {"date": r["date"], "score": crisis_score(factors, CATEGORY_WEIGHTS), "recession": r["nber_recession"] == "1"}
            monthly["gfc" if r["period"].startswith("2008") else "covid"].append(row)

    out = {
        "generated": date.today().isoformat(),
        "weights": CATEGORY_WEIGHTS,
        "threshold": THRESHOLD,
        "out_of_sample": points,
        "compare": {
            "calm": min((p for p in shown if p["label"] == "normal"), key=lambda p: p["score"]),
            "panic": max((p for p in shown if p["label"] == "stress"), key=lambda p: p["score"]),
        },
        "summary": {
            "stress_total": len(stress), "stress_flagged": sum(p["flagged"] for p in stress),
            "normal_total": len(normal), "false_alarms": sum(p["flagged"] for p in normal),
            "avg_stress": round(sum(p["score"] for p in stress) / len(stress), 1),
            "avg_normal": round(sum(p["score"] for p in normal) / len(normal), 1),
            "total": len(points),
            "right": sum(p["flagged"] for p in stress) + len(normal) - sum(p["flagged"] for p in normal),
            "auc": round(auc([p["score"] for p in stress], [p["score"] for p in normal]), 2),
            "missed_near_line": sum(p["score"] >= THRESHOLD - 5 for p in missed),
        },
        "monthly": {
            "gfc": monthly_block(monthly["gfc"], "2008 financial crisis"),
            "covid": monthly_block(monthly["covid"], "COVID-19, 2020"),
        },
    }
    os.makedirs(os.path.join(ROOT, "web", "data"), exist_ok=True)
    path = os.path.join(ROOT, "web", "data", "evidence.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", path)
    print(json.dumps(out["summary"]))
    for k in ("gfc", "covid"):
        m = out["monthly"][k]
        print(k, {x: m[x] for x in ("first_cross", "recession_start", "lead_months", "back_under_during_recession", "peak")})


if __name__ == "__main__":
    main()
