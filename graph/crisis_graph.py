"""
graph/crisis_graph.py — CrisisPredictor
LangGraph orchestration: 4 category-scoring nodes (parallel-style, streamed)
-> generate_prediction node that computes the deterministic composite score
and writes a GoldBot-style formatted prediction block.
"""

import threading

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from graph.state import CrisisState
from tools.llm_scoring import score_factor
from tools.fred_tools import fetch_all_fred_series
from tools.market_tools import fetch_all_market_series
from tools.repo_m2_tools import fetch_repo_m2_data, compute_repo_spread, compute_m2_yoy_growth
from tools.external_tools import get_tariff_sanctions_news, get_geopolitical_risk_news
from tools.scoring_tools import (
    CATEGORY_FACTORS, FACTOR_LABELS,
    compute_category_scores, compute_composite_score, classify_regime,
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

_cache = {}  # simple in-process cache so each node doesn't re-fetch raw data
_cache_lock = threading.Lock()  # one fetch at a time: the Yahoo download helper is not thread-safe


def _get_live_data():
    with _cache_lock:
        if "fred" not in _cache:
            _cache["fred"] = fetch_all_fred_series()
        if "market" not in _cache:
            _cache["market"] = fetch_all_market_series()
        if "repo_m2" not in _cache:
            _cache["repo_m2"] = fetch_repo_m2_data()
        return _cache["fred"], _cache["market"], _cache["repo_m2"]


def _build_descriptions():
    fred_data, market_data, repo_m2_data = _get_live_data()
    repo_spread = compute_repo_spread(repo_m2_data)
    m2_growth = compute_m2_yoy_growth(repo_m2_data)
    sp500 = market_data["sp500"]
    xlf = market_data["xlf"]

    return {
        "yield_curve": f"10Y-2Y spread is currently {fred_data['yield_curve'].dropna().iloc[-1]:.2f}%",
        "hy_spread": f"Baa-10Y credit spread is currently {fred_data['hy_spread'].dropna().iloc[-1]:.2f}%",
        "bank_rel": f"Bank sector (XLF) relative performance vs S&P 500 over the trailing 3 months is {((xlf/sp500).pct_change(63).dropna().iloc[-1]*100):+.1f}%",
        "repo_stress": f"SOFR minus Fed target upper bound is currently {repo_spread.dropna().iloc[-1]:+.3f}%",
        "m2_growth": f"M2 money supply YoY growth is currently {m2_growth.dropna().iloc[-1]:.2f}%",
        "vix": f"VIX is currently at {market_data['vix'].dropna().iloc[-1]:.1f}",
        "drawdown": f"S&P 500 is currently {((sp500.iloc[-1]-sp500.cummax().iloc[-1])/sp500.cummax().iloc[-1]*100):.1f}% from its all-time high",
        "gold_momentum": f"Gold's 20-day price change is {(market_data['gold'].pct_change(20).dropna().iloc[-1]*100):+.1f}%",
        "dxy": f"US Dollar Index's 20-day momentum is {(market_data['dxy'].pct_change(20).dropna().iloc[-1]*100):+.1f}%",
        "jobless": f"Initial jobless claims 4-week trend change is {(fred_data['jobless'].pct_change(4).dropna().iloc[-1]*100):+.1f}%",
        "cpi": f"CPI YoY deviation from its 6-month trend is {abs(fred_data['cpi'].pct_change(12).dropna().iloc[-1]*100 - fred_data['cpi'].pct_change(12).dropna().tail(6).mean()*100):.2f} percentage points",
        "oil": f"Oil price's 20-day absolute move is {abs(market_data['oil'].pct_change(20).dropna().iloc[-1]*100):.1f}%",
    }


def _score_factors(state: CrisisState, factor_keys: list, descriptions: dict) -> CrisisState:
    scores = dict(state.get("scores", {}))
    reasoning = dict(state.get("reasoning", {}))
    updates = {}
    for fk in factor_keys:
        live_desc = descriptions[fk]
        result = score_factor(fk, live_desc)
        scores[fk] = result.score
        reasoning[fk] = result.reasoning
        updates[fk] = live_desc
    updates["scores"] = scores
    updates["reasoning"] = reasoning
    return {**state, **updates}


def node_fetch_credit_systemic(state: CrisisState) -> CrisisState:
    print("[graph] Scoring Credit/Systemic factors...")
    descriptions = _build_descriptions()
    return _score_factors(state, CATEGORY_FACTORS["credit_systemic"], descriptions)


def node_fetch_liquidity_shock(state: CrisisState) -> CrisisState:
    print("[graph] Scoring Liquidity/Shock factors...")
    descriptions = _build_descriptions()
    return _score_factors(state, CATEGORY_FACTORS["liquidity_shock"], descriptions)


def node_fetch_macro(state: CrisisState) -> CrisisState:
    print("[graph] Scoring Macro factors...")
    descriptions = _build_descriptions()
    return _score_factors(state, CATEGORY_FACTORS["macro"], descriptions)


def _summarize_news(raw_text: str, topic: str) -> str:
    """Condense raw search results into a clean 1-2 sentence display summary."""
    prompt = f"""Summarize the key market-relevant facts from this news search about {topic}
in exactly 1-2 concise sentences. No markdown, no headers, no tables, just plain prose.

{raw_text[:2500]}"""
    response = llm.invoke(prompt)
    return response.content.strip()


def node_fetch_geopolitical(state: CrisisState) -> CrisisState:
    print("[graph] Fetching geopolitical news + scoring...")
    tariff_news_raw = get_tariff_sanctions_news()
    geo_news_raw = get_geopolitical_risk_news()

    tariff_summary = _summarize_news(tariff_news_raw, "tariffs and sanctions")
    geo_summary = _summarize_news(geo_news_raw, "geopolitical conflict risk")

    # Score using the FULL raw text (best signal for the LLM scorer)
    scoring_descriptions = {
        "tariff_sanctions": f"Recent news on tariffs/sanctions/trade war:\n{tariff_news_raw[:2000]}",
        "geopolitical_risk": f"Recent news on geopolitical conflict/risk:\n{geo_news_raw[:2000]}",
    }
    updated_state = _score_factors(state, CATEGORY_FACTORS["geopolitical"], scoring_descriptions)

    # But overwrite the DISPLAY text with the clean summary
    updated_state["tariff_sanctions"] = tariff_summary
    updated_state["geopolitical_risk"] = geo_summary
    return updated_state


def node_generate_prediction(state: CrisisState) -> CrisisState:
    print("[graph] Generating final prediction...")
    scores = state["scores"]
    reasoning = state["reasoning"]

    category_scores = compute_category_scores({fk: {"score": s} for fk, s in scores.items()})
    composite = compute_composite_score(category_scores)
    regime, _ = classify_regime(composite)
    status = "ON" if composite >= 55 else "OFF"

    # bullish = highest positive scores, bearish = lowest negative scores
    sorted_factors = sorted(scores.items(), key=lambda x: x[1])
    bearish = [FACTOR_LABELS[fk] for fk, s in sorted_factors if s < 0][:3]
    bullish = [FACTOR_LABELS[fk] for fk, s in reversed(sorted_factors) if s > 0][:3]

    confidence = "High" if abs(composite - 50) > 20 else ("Medium" if abs(composite - 50) > 8 else "Low")

    # LLM writes one reasoning paragraph + pattern match
    factor_summary = "\n".join(f"- {FACTOR_LABELS[fk]}: {s:+d} ({reasoning.get(fk, '')})" for fk, s in scores.items())
    prompt = f"""Given these 14 scored crisis-risk factors (-10 bearish/crisis to +10 bullish/stable),
write ONE concise paragraph (3-4 sentences) explaining the overall {composite}/100 Crisis Score
({regime} regime). Be calibrated — do not exaggerate. Mention which category is driving the score most.

{factor_summary}

Composite: {composite}/100 ({regime})"""
    narrative_response = llm.invoke(prompt)
    reasoning_text = narrative_response.content.strip()

    prediction_text = (
        f"CRISIS_STATUS: {status}\n"
        f"STRENGTH: {composite}%\n"
        f"REASONING: {reasoning_text}\n"
        f"CONFIDENCE: {confidence}\n"
        f"BULLISH_FACTORS: {' | '.join(bullish)}\n"
        f"BEARISH_FACTORS: {' | '.join(bearish)}"
    )

    return {
        **state,
        "category_scores": category_scores,
        "composite": composite,
        "regime": regime,
        "prediction": prediction_text,
    }


def build_graph():
    graph = StateGraph(CrisisState)
    graph.add_node("fetch_credit_systemic", node_fetch_credit_systemic)
    graph.add_node("fetch_liquidity_shock", node_fetch_liquidity_shock)
    graph.add_node("fetch_macro", node_fetch_macro)
    graph.add_node("fetch_geopolitical", node_fetch_geopolitical)
    graph.add_node("generate_prediction", node_generate_prediction)

    graph.set_entry_point("fetch_credit_systemic")
    graph.add_edge("fetch_credit_systemic", "fetch_liquidity_shock")
    graph.add_edge("fetch_liquidity_shock", "fetch_macro")
    graph.add_edge("fetch_macro", "fetch_geopolitical")
    graph.add_edge("fetch_geopolitical", "generate_prediction")
    graph.add_edge("generate_prediction", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


app = build_graph()


if __name__ == "__main__":
    import time
    t0 = time.time()

    for chunk in app.stream({}, config={"configurable": {"thread_id": "test_run"}}, stream_mode="updates"):
        for node_name, node_data in chunk.items():
            print(f"--- {node_name} done ---")

    final_state = app.get_state(config={"configurable": {"thread_id": "test_run"}}).values
    print(f"\nCompleted in {time.time()-t0:.1f}s\n")
    print(final_state["prediction"])