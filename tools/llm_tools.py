"""
tools/llm_tools.py — CrisisPredictor
GPT-4o-mini narrative generation with structured output.
"""

import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

CRISIS_PATTERNS = {
    "2008_gfc": {
        "label": "2008-style Credit Crisis",
        "signature": ["hy_spread widening sharply", "bank_rel underperforming heavily",
                      "yield_curve inverted then steepening"],
    },
    "covid_2020": {
        "label": "COVID-style Liquidity Shock",
        "signature": ["vix spiking fast", "drawdown deep and rapid",
                      "gold_momentum up then volatile", "oil extreme move"],
    },
    "trade_war_tariffs": {
        "label": "Tariff/Trade War Shock",
        "signature": ["geopolitical sentiment sharply negative", "dxy volatile",
                      "sector-specific drawdown"],
    },
    "sanctions_geopolitical": {
        "label": "Sanctions/Geopolitical Shock",
        "signature": ["geopolitical risk elevated", "oil spike", "gold up", "dxy up"],
    },
}


class CrisisAnalysis(BaseModel):
    narrative: str = Field(description="3-4 sentence plain-English narrative explaining today's score, calibrated and precise, not exaggerated")
    pattern_match: Literal["none", "2008_gfc", "covid_2020", "trade_war_tariffs", "sanctions_geopolitical"] = Field(
        description="Which historical crisis pattern today's readings most resemble, or 'none' if no strong match"
    )
    pattern_confidence: Literal["low", "moderate", "high"] = Field(
        description="Confidence in the pattern match. Use 'low' liberally if the match is only partial."
    )
    watch_items: list[str] = Field(description="2-3 short specific things to monitor next")


def generate_crisis_narrative(score: float, regime: str, pillars: dict) -> CrisisAnalysis:
    """Generate a structured narrative analysis for the current crisis score."""
    pattern_descriptions = "\n".join(
        f"- {key}: {p['label']} — {', '.join(p['signature'])}" for key, p in CRISIS_PATTERNS.items()
    )

    prompt = f"""You are a financial risk analyst. Given today's crisis indicator readings, produce a structured analysis.

Composite crisis score: {score:.1f}/100 ({regime} regime)
Pillar breakdown:
- Credit/Systemic: {pillars['credit']:.1f}
- Liquidity/Shock: {pillars['liquidity']:.1f}
- Macro: {pillars['macro']:.1f}

Known historical crisis patterns for reference:
{pattern_descriptions}

Be calibrated and precise. Do not exaggerate an Elevated score into sounding like a Crisis. Only claim a pattern match if genuinely similar — default to pattern_match='none' with confidence 'low' when readings are mixed or moderate."""

    structured_llm = llm.with_structured_output(CrisisAnalysis)
    return structured_llm.invoke(prompt)


if __name__ == "__main__":
    # quick standalone test with dummy data
    dummy_pillars = {"credit": 53.2, "liquidity": 29.4, "macro": 53.4}
    result = generate_crisis_narrative(44.3, "Elevated", dummy_pillars)
    print(f"Pattern match: {result.pattern_match} (confidence: {result.pattern_confidence})")
    print(f"Watch items: {result.watch_items}")
    print(f"\nNarrative:\n{result.narrative}")