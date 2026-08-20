"""
tools/external_tools.py — CrisisPredictor
Live news search for the Geopolitical pillar (Tariff/Sanctions, Geopolitical Risk).
Tavily primary, DDGS fallback — matches GoldBot's external_tools.py pattern.
"""

import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_tavily(query: str, max_results: int = 5) -> str:
    from tavily import TavilyClient
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query=query, max_results=max_results, search_depth="basic")
    results = response.get("results", [])
    combined = "\n\n".join(f"{r.get('title', '')}: {r.get('content', '')}" for r in results)
    return combined if combined else "No results found."


def search_ddgs(query: str, max_results: int = 5) -> str:
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    combined = "\n\n".join(f"{r.get('title', '')}: {r.get('body', '')}" for r in results)
    return combined if combined else "No results found."


def search_news(query: str, max_results: int = 5) -> str:
    """Tavily first, DDGS fallback on any failure."""
    if TAVILY_API_KEY:
        try:
            return search_tavily(query, max_results)
        except Exception as e:
            print(f"[external_tools] Tavily failed ({e}), falling back to DDGS")
    try:
        return search_ddgs(query, max_results)
    except Exception as e:
        print(f"[external_tools] DDGS also failed ({e})")
        return "Data unavailable — both search providers failed."


def get_tariff_sanctions_news() -> str:
    return search_news("tariffs sanctions trade war economic impact market 2026", max_results=5)


def get_geopolitical_risk_news() -> str:
    return search_news("geopolitical conflict war military escalation markets 2026", max_results=5)


if __name__ == "__main__":
    print("=== Tariff/Sanctions News ===")
    print(get_tariff_sanctions_news())
    print("\n=== Geopolitical Risk News ===")
    print(get_geopolitical_risk_news())