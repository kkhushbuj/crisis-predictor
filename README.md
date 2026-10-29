# CrisisPredictor

An AI-assisted financial stress monitor. It reads 14 live signals from credit markets, stock markets, the economy and the news, scores each one, and combines them into a single **Crisis Score from 0 to 100**, a risk level (Calm, Elevated, Stress, Crisis) and an alarm.

It is an academic project and not financial advice.

## How it works

1. **Live data.** FRED provides the yield curve, credit spread, jobless claims, CPI, repo stress and M2 money supply. Yahoo Finance provides the VIX, S&P 500 drawdown, gold, the US dollar, bank stocks and oil. A live news search covers tariffs, sanctions and geopolitical conflict.
2. **AI scoring.** For each signal, GPT-4o-mini is given the matching section of a reference document with historical thresholds (retrieval with FAISS) and scores the signal from -10 (danger) to +10 (calm).
3. **Fixed weights.** Plain Python averages the scores per category and applies fixed weights: Credit 32.5%, Liquidity 32.5%, Macro 20%, News 15%. The AI never sets the final number.
4. **Result.** The Crisis Score, a level and an alarm. The alarm switches on at a score of 55 or above.

| Level | Score |
|---|---|
| Calm | 0 to 30 |
| Elevated | 30 to 55 |
| Stress (alarm on) | 55 to 75 |
| Crisis | 75 and above |

## Backtest results (300 past dates, all 14 factors, alarm line 55)

Run `python backtest/analyze_300.py` to reproduce these from the saved scores. It makes no API calls, but it needs the `.env` keys set (see "Run it") because the scoring code loads them when it starts.

| | Result |
|---|---|
| Right overall | 228 of 300 (76%) |
| Stress dates caught | 86 of 152 (57%) |
| False alarms on calm dates | 6 of 148 (4%) |
| AUC (ranking stress above calm) | 0.89 |

The dates come from four sets: 41 hand-picked, 39 fresh, 120 drawn by a fixed random rule and 100 more drawn by a fixed random rule. The first 41 were used while building the model. The other 259 were scored afterwards with the weights and alarm line already fixed.

## What it cannot do

- **It detects stress. It has not been shown to predict it.** In monthly tests of 2008 and 2020 the score reached the alarm line in the same month the official recession began, not before. Walk-forward tests of leading signals did not show reliable crash prediction either.
- **It misses many stress days.** 66 of 152 stress dates stayed below the alarm line, and most of them scored within 5 points of it.
- **The news text for past dates was written from history**, because a live search cannot look back. That part of the tests is less independent than the market data.
- **The sample is modest.** The dates were drawn from known stress and calm periods, and the level boundaries are working values.
- **News scoring is the least stable part.** The AI's reading of headlines can move a few points between runs.

An alternative setup was also tested: score from the 12 market and economic factors only, with the alarm at 52. It got 78% right (104 of 152 stress dates caught, 17 of 148 false alarms, AUC 0.90) on the same 300 dates. It is not used in the live app yet.

## Run it

```bash
pip install -r requirements-web.txt
uvicorn api.main:app --port 8000
```

Open http://localhost:8000. You need a `.env` file in the project root:

```
OPENAI_API_KEY=...
FRED_API_KEY=...
TAVILY_API_KEY=...   # optional
```

See [DEPLOY.md](DEPLOY.md) for deploying on Render.

## Project layout

| Folder | What it holds |
|---|---|
| `api/` | FastAPI backend: streaming analysis, chat assistant, rate limits |
| `web/` | The website: landing page, analysis page, scripts and styles |
| `graph/` | The LangGraph pipeline that fetches data and scores it |
| `tools/` | Data fetchers, the scoring math, levels and weights (`scoring_tools.py`) |
| `rag/` | The reference document of historical thresholds and its retriever |
| `backtest/` | Historical backtest scripts and saved results |

## Technology

Python, LangGraph, FAISS retrieval, GPT-4o-mini, FastAPI, and a plain JavaScript front end with GSAP animations.
