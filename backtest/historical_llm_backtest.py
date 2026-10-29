"""
backtest/historical_llm_backtest.py — CrisisPredictor
Validates the LLM+RAG scoring engine against known historical dates.
9 events (6 crises + 3 calm periods), 11 test dates, 14 factors each.
Results saved to backtest/historical_llm_backtest_results.json and .csv
"""

import sys
import os
import json
import csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.llm_scoring import score_factor
from tools.fred_tools import fetch_fred_series
from tools.market_tools import fetch_yf_series
from tools.repo_m2_tools import fetch_series as fetch_repo_m2_series

# ---------------------------------------------------------------------------
# TEST DATES (locked scope: 9 events, 11 dates)
# ---------------------------------------------------------------------------
TEST_DATES = {
    "2008_GFC_early":    "2008-06-15",
    "2008_GFC_peak":     "2008-10-15",
    "2011_Euro_Crisis":  "2011-09-01",
    "2018_Trade_War":    "2018-12-15",
    "COVID_early":       "2020-02-20",
    "COVID_peak":        "2020-03-23",
    "Ukraine_2022":      "2022-03-08",
    "SVB_2023":          "2023-03-13",
    "Calm_2017":         "2017-06-15",
    "Calm_2019_H1":      "2019-03-15",
    "Calm_2024":         "2024-06-15",
}

# Manually-written historical event summaries for the 2 geopolitical factors
# (can't search "the news as it was" historically, so this is illustrative
# ground-truth text standing in for what live news search would have shown)
GEOPOLITICAL_HISTORICAL_CONTEXT = {
    "2008_GFC_early": {
        "tariff_sanctions": "No major tariff or sanctions escalation reported.",
        "geopolitical_risk": "No major armed conflict escalation. Early signs of credit market stress dominating headlines instead.",
    },
    "2008_GFC_peak": {
        "tariff_sanctions": "No major tariff escalation. Trade policy overshadowed by financial crisis.",
        "geopolitical_risk": "No major new armed conflict. Global financial system in acute crisis following Lehman Brothers bankruptcy (Sept 2008).",
    },
    "2011_Euro_Crisis": {
        "tariff_sanctions": "No major new tariffs. Eurozone sovereign debt crisis is the dominant economic policy concern.",
        "geopolitical_risk": "European sovereign debt crisis escalating (Greece, Italy, Spain). No major armed conflict, but significant political/economic instability in the Eurozone.",
    },
    "2018_Trade_War": {
        "tariff_sanctions": "US-China trade war actively escalating. Major tariffs imposed on hundreds of billions in goods by both sides through 2018.",
        "geopolitical_risk": "Elevated US-China tensions but no armed conflict. Trade war is the dominant geopolitical/economic risk.",
    },
    "COVID_early": {
        "tariff_sanctions": "No major new tariff escalation reported.",
        "geopolitical_risk": "Early COVID-19 outbreak spreading beyond China. WHO has not yet declared a pandemic. Markets beginning to price in disruption risk.",
    },
    "COVID_peak": {
        "tariff_sanctions": "No major new tariff escalation. Trade policy overshadowed by pandemic.",
        "geopolitical_risk": "COVID-19 declared a global pandemic. Widespread lockdowns, travel bans, and economic shutdowns across major economies.",
    },
    "Ukraine_2022": {
        "tariff_sanctions": "Major Western sanctions imposed on Russia following invasion of Ukraine (Feb 24, 2022). SWIFT restrictions, asset freezes.",
        "geopolitical_risk": "Russia has invaded Ukraine. Active war in Europe. Global energy and grain supply chains disrupted.",
    },
    "SVB_2023": {
        "tariff_sanctions": "No major new tariff or sanctions escalation reported.",
        "geopolitical_risk": "No major armed conflict escalation. Banking sector stress (SVB, Signature Bank failures) is the dominant risk factor, not geopolitical.",
    },
    "Calm_2017": {
        "tariff_sanctions": "No major tariff escalation. Pre-trade-war period.",
        "geopolitical_risk": "No major armed conflict or acute geopolitical crisis. Relatively stable global backdrop.",
    },
    "Calm_2019_H1": {
        "tariff_sanctions": "US-China trade tensions present but not yet at peak escalation.",
        "geopolitical_risk": "No major armed conflict. Yield curve inversion beginning to raise recession concerns, but no acute geopolitical shock.",
    },
    "Calm_2024": {
        "tariff_sanctions": "No major new tariff escalation reported at this date.",
        "geopolitical_risk": "No major new armed conflict escalation reported at this date beyond ongoing existing conflicts.",
    },
}

EXPECTED_DIRECTION = {
    "2008_GFC_early": "bearish", "2008_GFC_peak": "bearish",
    "2011_Euro_Crisis": "bearish", "2018_Trade_War": "bearish",
    "COVID_early": "bearish", "COVID_peak": "bearish",
    "Ukraine_2022": "bearish", "SVB_2023": "bearish",
    "Calm_2017": "neutral", "Calm_2019_H1": "mixed", "Calm_2024": "neutral",
}


def get_historical_value(series, target_date):
    """Get the last available value at or before target_date."""
    target_ts = datetime.strptime(target_date, "%Y-%m-%d")
    filtered = series[series.index <= target_ts]
    return filtered.iloc[-1] if len(filtered) else None


def pct_change_asof(series, date_str, lookback):
    """% change over `lookback` periods, as of the last value at/before date_str."""
    filtered = series[series.index <= date_str]
    if len(filtered) < lookback + 1:
        return None
    return (filtered.iloc[-1] - filtered.iloc[-1 - lookback]) / filtered.iloc[-1 - lookback] * 100


def build_historical_descriptions(date_str):
    """Fetch historical values as-of the given date and build live-value descriptions,
    using the same derived-metric style (% moves, relative performance) as the live system."""
    yield_curve = fetch_fred_series("T10Y2Y", obs_start="1996-01-01", obs_end=date_str)
    hy_spread = fetch_fred_series("BAA10Y", obs_start="1996-01-01", obs_end=date_str)
    jobless = fetch_fred_series("ICSA", obs_start="1996-01-01", obs_end=date_str)
    cpi = fetch_fred_series("CPIAUCSL", obs_start="1996-01-01", obs_end=date_str)

    vix = fetch_yf_series("^VIX", start="1996-01-01", end=date_str)
    sp500 = fetch_yf_series("^GSPC", start="1996-01-01", end=date_str)
    gold = fetch_yf_series("GC=F", start="2000-01-01", end=date_str)
    dxy = fetch_yf_series("DX-Y.NYB", start="2000-01-01", end=date_str)
    xlf = fetch_yf_series("XLF", start="2000-01-01", end=date_str)
    oil = fetch_yf_series("CL=F", start="2000-01-01", end=date_str)

    yc_val = get_historical_value(yield_curve, date_str)
    hy_val = get_historical_value(hy_spread, date_str)
    vix_val = get_historical_value(vix, date_str)
    sp500_val = get_historical_value(sp500, date_str)
    sp500_filtered = sp500[sp500.index <= date_str]
    sp500_max = sp500_filtered.cummax().iloc[-1] if len(sp500_filtered) else sp500_val
    jobless_series = jobless[jobless.index <= date_str]
    cpi_series = cpi[cpi.index <= date_str]
    oil_series = oil[oil.index <= date_str]

    drawdown_pct = ((sp500_val - sp500_max) / sp500_max * 100) if sp500_max else 0

    bank_rel_series = (xlf / sp500).dropna()
    bank_rel_pct = pct_change_asof(bank_rel_series, date_str, lookback=63)  # ~3 months trading days
    gold_mom_pct = pct_change_asof(gold, date_str, lookback=20)
    dxy_mom_pct = pct_change_asof(dxy, date_str, lookback=20)
    oil_move_pct = pct_change_asof(oil, date_str, lookback=20)
    jobless_trend_pct = pct_change_asof(jobless_series, date_str, lookback=4)
    cpi_yoy = pct_change_asof(cpi_series, date_str, lookback=12)
    cpi_yoy_trend = cpi_series.pct_change(12).dropna().tail(6).mean() * 100 if len(cpi_series.pct_change(12).dropna()) >= 6 else cpi_yoy
    cpi_deviation = abs(cpi_yoy - cpi_yoy_trend) if (cpi_yoy is not None and cpi_yoy_trend is not None) else None

    # Real historical repo/M2 data
    try:
        sofr = fetch_repo_m2_series("SOFR", obs_start="2018-01-01", obs_end=date_str)
        fed_target = fetch_repo_m2_series("DFEDTARU", obs_start="2008-01-01", obs_end=date_str)
        combined = sofr.to_frame("sofr").join(fed_target.to_frame("target"), how="inner")
        repo_spread_val = (combined["sofr"] - combined["target"]).iloc[-1] if len(combined) else None
    except Exception:
        repo_spread_val = None

    try:
        m2 = fetch_repo_m2_series("M2SL", obs_start="1996-01-01", obs_end=date_str)
        m2_growth_val = pct_change_asof(m2, date_str, lookback=12)
    except Exception:
        m2_growth_val = None

    return {
        "yield_curve": f"As of {date_str}, the 10Y-2Y spread was {yc_val:.2f}%" if yc_val is not None else "Data unavailable",
        "hy_spread": f"As of {date_str}, the Baa-10Y credit spread was {hy_val:.2f}%" if hy_val is not None else "Data unavailable",
        "bank_rel": f"As of {date_str}, bank sector (XLF) relative performance vs S&P 500 over the trailing 3 months was {bank_rel_pct:+.1f}%" if bank_rel_pct is not None else "As of this date, insufficient history to compute 3-month relative bank performance — treat as neutral.",
        "repo_stress": f"As of {date_str}, SOFR minus Fed target upper bound was {repo_spread_val:+.3f}%" if repo_spread_val is not None else f"As of {date_str}, SOFR data does not exist yet (SOFR only began publishing in April 2018) — treat as unavailable/neutral for this historical date.",
        "m2_growth": f"As of {date_str}, M2 money supply YoY growth was {m2_growth_val:.2f}%" if m2_growth_val is not None else "As of this date, insufficient history to compute M2 YoY growth — treat as neutral.",
        "vix": f"As of {date_str}, the VIX was {vix_val:.1f}" if vix_val is not None else "Data unavailable",
        "drawdown": f"As of {date_str}, the S&P 500 was {drawdown_pct:.1f}% from its all-time high to that point" if sp500_val else "Data unavailable",
        "gold_momentum": f"As of {date_str}, gold's 20-day price change was {gold_mom_pct:+.1f}%" if gold_mom_pct is not None else "As of this date, insufficient gold price history to compute 20-day momentum — treat as neutral.",
        "dxy": f"As of {date_str}, US Dollar Index's 20-day momentum was {dxy_mom_pct:+.1f}%" if dxy_mom_pct is not None else "As of this date, insufficient DXY history to compute 20-day momentum — treat as neutral.",
        "jobless": f"As of {date_str}, initial jobless claims 4-week trend change was {jobless_trend_pct:+.1f}%" if jobless_trend_pct is not None else "Data unavailable",
        "cpi": f"As of {date_str}, CPI YoY deviation from its 6-month trend was {cpi_deviation:.2f} percentage points" if cpi_deviation is not None else "Data unavailable",
        "oil": f"As of {date_str}, oil price's 20-day absolute move was {abs(oil_move_pct):.1f}%" if oil_move_pct is not None else "Data unavailable",
    }


def run_historical_backtest():
    results = []

    for event_name, date_str in TEST_DATES.items():
        print(f"\n=== Testing {event_name} ({date_str}) ===")
        try:
            descriptions = build_historical_descriptions(date_str)
        except Exception as e:
            print(f"  Failed to fetch historical data: {e}")
            continue

        geo_context = GEOPOLITICAL_HISTORICAL_CONTEXT[event_name]
        descriptions["tariff_sanctions"] = geo_context["tariff_sanctions"]
        descriptions["geopolitical_risk"] = geo_context["geopolitical_risk"]

        event_scores = {}
        for factor_key, live_desc in descriptions.items():
            try:
                result = score_factor(factor_key, live_desc)
                event_scores[factor_key] = result.score
                print(f"  {factor_key:20s} | score={result.score:+3d}")
            except Exception as e:
                print(f"  {factor_key:20s} | FAILED: {e}")
                event_scores[factor_key] = None

        avg_score = sum(v for v in event_scores.values() if v is not None) / len([v for v in event_scores.values() if v is not None])
        results.append({
            "event": event_name,
            "date": date_str,
            "expected_direction": EXPECTED_DIRECTION[event_name],
            "factor_scores": event_scores,
            "average_score": round(avg_score, 2),
        })
        print(f"  --> Average score: {avg_score:+.2f} (expected: {EXPECTED_DIRECTION[event_name]})")

    return results


def save_results(results):
    out_dir = os.path.dirname(os.path.abspath(__file__))

    json_path = os.path.join(out_dir, "historical_llm_backtest_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved JSON to {json_path}")

    csv_path = os.path.join(out_dir, "historical_llm_backtest_results.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["event", "date", "expected_direction", "average_score"] + list(TEST_DATES.keys())[:1])
        for r in results:
            writer.writerow([r["event"], r["date"], r["expected_direction"], r["average_score"]])
    print(f"Saved CSV to {csv_path}")


if __name__ == "__main__":
    import time
    t0 = time.time()
    results = run_historical_backtest()
    save_results(results)
    print(f"\nTotal time: {time.time()-t0:.1f}s")
    print(f"\n=== SUMMARY ===")
    for r in results:
        print(f"{r['event']:20s} | avg={r['average_score']:+6.2f} | expected={r['expected_direction']}")