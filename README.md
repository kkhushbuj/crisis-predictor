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

Run `python backtest/analyze_300_random.py` to reproduce these from the saved scores. It makes no API calls, but it needs the `.env` keys set (see "Run it") because the scoring code loads them when it starts.

| | Result |
|---|---|
| Right overall | 220 of 300 (73%) |
| Stress dates caught | 80 of 150 (53%) |
| False alarms on calm dates | 10 of 150 (7%) |
| AUC (ranking stress above calm) | 0.87 |

All 300 dates were drawn by a computer using a fixed random rule (three batches: seeds 42, 7 and 2026; 150 stress days and 150 calm days). The rule picks days at random, but only from stress and calm periods that were chosen by hand in advance, such as 2000 to 2002, 2007 to 2009 and 2022. The weights and alarm line were fixed before these dates were scored, and no hand-picked dates are included.

## What it cannot do

- **It detects stress. It has not been shown to predict it.** In monthly tests of 2008 and 2020 the score reached the alarm line in the same month the official recession began, not before. Walk-forward tests of leading signals did not show reliable crash prediction either.
- **It misses many stress days.** 70 of 150 stress dates stayed below the alarm line, and most of them scored within 5 points of it.
- **The news text for past dates was written from history**, because a live search cannot look back. That part of the tests is less independent than the market data.
- **The sample is modest.** The dates were drawn from known stress and calm periods, and the level boundaries are working values.
- **News scoring is the least stable part.** The AI's reading of headlines can move a few points between runs.

An alternative setup was also tested: score from the 12 market and economic factors only, with the alarm at 52. It got 76% right (103 of 150 stress dates caught, 24 of 150 false alarms, AUC 0.89) on the same 300 dates. It is not used in the live app yet.

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

## The website

- **Landing page:** the backtest evidence, with all 300 test dates plotted on the risk scale, and an explanation of how the score is built.
- **Analysis page:** runs a live analysis with progress, shows the score, the four category bars and all 14 signals with the reason for each, and a chat assistant that streams its answers.
- **History:** analyses from the current browser tab are listed in a History panel on the home page and on the analysis page. They are kept only for that visit and cleared when the tab closes. Nothing is stored on the server.

Details on how the test numbers were produced are in [backtest/README.md](backtest/README.md).

## Technology

Python, LangGraph, FAISS retrieval, GPT-4o-mini, FastAPI, and a plain JavaScript front end with GSAP animations.
