"""
tools/scoring_tools.py — CrisisPredictor
Full 14-factor RAG+LLM scoring pipeline. Matches GoldBot's architecture:
LLM scores each factor -10 to +10 (grounded via RAG), Python applies fixed
deterministic category weights to compute the final Crisis Score.
"""

from tools.llm_scoring import score_factor
from tools.fred_tools import fetch_all_fred_series
from tools.market_tools import fetch_all_market_series
from tools.repo_m2_tools import fetch_repo_m2_data, compute_repo_spread, compute_m2_yoy_growth
from tools.external_tools import get_tariff_sanctions_news, get_geopolitical_risk_news

# --- Category weights (locked, sum to 100) ---
CATEGORY_WEIGHTS = {
    "credit_systemic": 32.5,
    "liquidity_shock": 32.5,
    "macro": 20,
    "geopolitical": 15,
}

CATEGORY_FACTORS = {
    "credit_systemic": ["yield_curve", "hy_spread", "bank_rel", "repo_stress", "m2_growth"],
    "liquidity_shock": ["vix", "drawdown", "gold_momentum", "dxy"],
    "macro": ["jobless", "cpi", "oil"],
    "geopolitical": ["tariff_sanctions", "geopolitical_risk"],
}

FACTOR_LABELS = {
    "yield_curve": "Yield Curve (10Y-2Y)",
    "hy_spread": "Credit Spread (Baa-10Y)",
    "bank_rel": "Bank Sector Relative Strength",
    "repo_stress": "Repo Market Stress",
    "m2_growth": "M2 Money Supply Growth",
    "vix": "VIX (Volatility)",
    "drawdown": "S&P 500 Drawdown",
    "gold_momentum": "Gold Momentum",
    "dxy": "US Dollar Index",
    "jobless": "Jobless Claims Trend",
    "cpi": "CPI Shock",
    "oil": "Oil Volatility",
    "tariff_sanctions": "Tariff/Sanctions Sentiment",
    "geopolitical_risk": "Geopolitical Risk",
}

REGIMES = [
    (0, 30, "Calm", "#2ecc71"),
    (30, 55, "Elevated", "#f1c40f"),
    (55, 75, "Stress", "#e67e22"),
    (75, 101, "Crisis", "#e74c3c"),
]


def gather_live_values() -> dict:
    """Fetch all raw live data needed to build the live-value descriptions for each factor."""
    print("[scoring] Fetching FRED series...")
    fred_data = fetch_all_fred_series()
    print("[scoring] Fetching market data...")
    market_data = fetch_all_market_series()
    print("[scoring] Fetching repo/M2 data...")
    repo_m2_data = fetch_repo_m2_data()
    repo_spread = compute_repo_spread(repo_m2_data)
    m2_growth = compute_m2_yoy_growth(repo_m2_data)

    sp500 = market_data["sp500"]
    xlf = market_data["xlf"]

    latest = {
        "yield_curve": fred_data["yield_curve"].dropna().iloc[-1],
        "hy_spread": fred_data["hy_spread"].dropna().iloc[-1],
        "bank_rel_pct": ((xlf / sp500).pct_change(63).dropna().iloc[-1] * 100),  # ~3mo relative
        "repo_spread": repo_spread.dropna().iloc[-1],
        "m2_growth": m2_growth.dropna().iloc[-1],
        "vix": market_data["vix"].dropna().iloc[-1],
        "sp500_drawdown_pct": ((sp500.iloc[-1] - sp500.cummax().iloc[-1]) / sp500.cummax().iloc[-1] * 100),
        "gold_momentum_pct": (market_data["gold"].pct_change(20).dropna().iloc[-1] * 100),
        "dxy_momentum_pct": (market_data["dxy"].pct_change(20).dropna().iloc[-1] * 100),
        "jobless_trend_pct": (fred_data["jobless"].pct_change(4).dropna().iloc[-1] * 100),
        "cpi_deviation_pct": abs(fred_data["cpi"].pct_change(12).dropna().iloc[-1] * 100 -
                                   fred_data["cpi"].pct_change(12).dropna().tail(6).mean() * 100),
        "oil_move_pct": abs(market_data["oil"].pct_change(20).dropna().iloc[-1] * 100),
    }
    return latest


def build_live_descriptions(latest: dict, tariff_news: str, geo_news: str) -> dict:
    """Turn raw numbers into plain-English descriptions the LLM scorer can read."""
    return {
        "yield_curve": f"10Y-2Y spread is currently {latest['yield_curve']:.2f}%",
        "hy_spread": f"Baa-10Y credit spread is currently {latest['hy_spread']:.2f}%",
        "bank_rel": f"Bank sector (XLF) relative performance vs S&P 500 over the trailing 3 months is {latest['bank_rel_pct']:+.1f}%",
        "repo_stress": f"SOFR minus Fed target upper bound is currently {latest['repo_spread']:+.3f}%",
        "m2_growth": f"M2 money supply YoY growth is currently {latest['m2_growth']:.2f}%",
        "vix": f"VIX is currently at {latest['vix']:.1f}",
        "drawdown": f"S&P 500 is currently {latest['sp500_drawdown_pct']:.1f}% from its all-time high",
        "gold_momentum": f"Gold's 20-day price change is {latest['gold_momentum_pct']:+.1f}%",
        "dxy": f"US Dollar Index's 20-day momentum is {latest['dxy_momentum_pct']:+.1f}%",
        "jobless": f"Initial jobless claims 4-week trend change is {latest['jobless_trend_pct']:+.1f}%",
        "cpi": f"CPI YoY deviation from its 6-month trend is {latest['cpi_deviation_pct']:.2f} percentage points",
        "oil": f"Oil price's 20-day absolute move is {latest['oil_move_pct']:.1f}%",
        "tariff_sanctions": f"Recent news on tariffs/sanctions/trade war:\n{tariff_news[:2000]}",
        "geopolitical_risk": f"Recent news on geopolitical conflict/risk:\n{geo_news[:2000]}",
    }


def score_all_factors() -> dict:
    """Run the full pipeline: fetch live data, score every factor via LLM+RAG, return results."""
    latest = gather_live_values()

    print("[scoring] Fetching geopolitical news...")
    tariff_news = get_tariff_sanctions_news()
    geo_news = get_geopolitical_risk_news()

    descriptions = build_live_descriptions(latest, tariff_news, geo_news)

    print("[scoring] Scoring all 14 factors via LLM+RAG...")
    factor_results = {}
    for factor_key, live_desc in descriptions.items():
        result = score_factor(factor_key, live_desc)
        factor_results[factor_key] = {
            "score": result.score,
            "reasoning": result.reasoning,
            "label": FACTOR_LABELS[factor_key],
            "live_value": live_desc,
        }
        print(f"  {factor_key:20s} | score={result.score:+3d}")

    return factor_results


def compute_category_scores(factor_results: dict) -> dict:
    """Average the -10..+10 scores within each category (simple mean per category)."""
    category_scores = {}
    for category, factor_keys in CATEGORY_FACTORS.items():
        scores = [factor_results[fk]["score"] for fk in factor_keys if fk in factor_results]
        category_scores[category] = sum(scores) / len(scores) if scores else 0
    return category_scores


def compute_composite_score(category_scores: dict) -> float:
    """
    Convert category scores (-10..+10 avg) into a 0-100 Crisis Score using fixed weights.
    A category average of -10 (max bearish/crisis) maps to 100 crisis points for that category's weight share.
    A category average of +10 (max bullish/stable) maps to 0 crisis points.
    """
    total = 0.0
    for category, weight in CATEGORY_WEIGHTS.items():
        avg_score = category_scores.get(category, 0)
        # map -10..+10 to 100..0 (crisis-scale, inverted)
        crisis_pct_for_category = ((-avg_score) + 10) / 20 * 100
        total += (weight / 100) * crisis_pct_for_category
    return round(total, 1)


def classify_regime(score: float) -> tuple:
    for low, high, label, color in REGIMES:
        if low <= score < high:
            return label, color
    return "Unknown", "#95a5a6"


if __name__ == "__main__":
    import time
    t0 = time.time()

    factor_results = score_all_factors()
    category_scores = compute_category_scores(factor_results)
    composite = compute_composite_score(category_scores)
    regime, _ = classify_regime(composite)

    print(f"\nCompleted in {time.time()-t0:.1f}s")
    print(f"\nCategory scores (-10 to +10 avg):")
    for cat, score in category_scores.items():
        print(f"  {cat:20s} | {score:+.2f}")

    print(f"\nComposite Crisis Score: {composite}/100")
    print(f"Regime: {regime}")