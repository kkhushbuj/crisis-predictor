"""
tools/llm_scoring.py — CrisisPredictor
LLM-per-factor RAG-grounded scoring. Matches GoldBot's architecture:
the LLM reads retrieved causal-chain context + the live value and scores
-10 to +10. Python then applies fixed category weights — the LLM never
decides the final weighting.
"""

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

from rag.retriever import retrieve_factor_context

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)


class FactorScore(BaseModel):
    score: int = Field(description="Integer from -10 (strongly bearish/crisis-signaling) to +10 (strongly bullish/stable), based on the scoring thresholds provided", ge=-10, le=10)
    reasoning: str = Field(description="One concise sentence explaining the score, referencing the actual value and the threshold it falls into")


# Human-readable factor names used as RAG retrieval queries
FACTOR_QUERIES = {
    "yield_curve": "Yield Curve 10Y-2Y Treasury Spread",
    "hy_spread": "Credit Spread Baa Corporate Bond Yield",
    "bank_rel": "Bank Sector Relative Strength Financials",
    "repo_stress": "Repo Market Stress SOFR Overnight Rate",
    "m2_growth": "M2 Money Supply Growth Rate",
    "vix": "VIX CBOE Volatility Index",
    "drawdown": "S&P 500 Drawdown from All-Time High",
    "gold_momentum": "Gold Momentum flight to safety",
    "dxy": "US Dollar Index DXY momentum",
    "jobless": "Jobless Claims Trend labor market",
    "cpi": "CPI Shock inflation deviation",
    "oil": "Oil Price Volatility shock",
    "tariff_sanctions": "Tariff Sanctions Sentiment trade war",
    "geopolitical_risk": "Geopolitical Risk conflict war news",
}


def score_factor(factor_key: str, live_value_description: str) -> FactorScore:
    """
    factor_key: one of FACTOR_QUERIES keys
    live_value_description: plain-English description of the current live value,
        e.g. "10Y-2Y spread is currently 0.15%" or news search results for LLM-scored factors
    """
    query = FACTOR_QUERIES.get(factor_key, factor_key)
    context = retrieve_factor_context(query, k=1)

    prompt = f"""You are scoring a single financial crisis-risk factor using the grounding
context below. Apply the scoring thresholds exactly as given — do not invent your own scale.

GROUNDING CONTEXT:
{context}

CURRENT LIVE DATA:
{live_value_description}

Score this factor from -10 to +10 using the thresholds in the grounding context above.
Give one concise sentence of reasoning that references the actual value and threshold."""

    structured_llm = llm.with_structured_output(FactorScore)
    return structured_llm.invoke(prompt)


if __name__ == "__main__":
    # Quick standalone test with a few factors
    test_cases = [
        ("yield_curve", "10Y-2Y spread is currently 0.35%"),
        ("vix", "VIX is currently at 14.9"),
        ("hy_spread", "Baa-10Y credit spread is currently 1.8%"),
    ]
    for factor_key, live_desc in test_cases:
        result = score_factor(factor_key, live_desc)
        print(f"{factor_key:15s} | score={result.score:+3d} | {result.reasoning}")