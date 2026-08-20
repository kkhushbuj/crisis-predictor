"""
graph/state.py — CrisisPredictor
Shared state schema for the LangGraph pipeline.
"""

from typing import TypedDict, Optional, Dict


class CrisisState(TypedDict, total=False):
    # Raw live-value descriptions per factor (display text, like GoldBot's factor fields)
    yield_curve: str
    hy_spread: str
    bank_rel: str
    repo_stress: str
    m2_growth: str
    vix: str
    drawdown: str
    gold_momentum: str
    dxy: str
    jobless: str
    cpi: str
    oil: str
    tariff_sanctions: str
    geopolitical_risk: str

    # Scores dict: factor_key -> int (-10 to +10)
    scores: Dict[str, int]

    # Reasoning per factor: factor_key -> str
    reasoning: Dict[str, str]

    # Final output
    prediction: str  # formatted STATUS/STRENGTH/REASONING/CONFIDENCE/BULLISH/BEARISH text block
    category_scores: Dict[str, float]
    composite: float
    regime: str
    pattern_match: str