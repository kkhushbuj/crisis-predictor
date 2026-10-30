# CrisisPredictor

An AI-assisted financial stress monitor. It reads 14 live signals from credit markets, stock markets, the economy and the news, scores each one, and combines them into a single **Crisis Score from 0 to 100**, a risk level (Calm, Elevated, Stress, Crisis) and an alarm.

**Live site: https://145-241-213-220.sslip.io**

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

Run `python backtest/analyze_v8_nyt.py` to reproduce these from the saved scores. It makes no API calls, but it needs the `.env` keys set (see "Run it") because the scoring code loads them when it starts.

| | Result |
|---|---|
| Right overall | 219 of 300 (73%) |
| Stress dates caught | 89 of 150 (59%) |
| False alarms on calm dates | 20 of 150 (13%) |
| AUC (ranking stress above calm) | 0.86 |

All 300 dates were drawn by a computer using a fixed random rule (three batches: seeds 42, 7 and 2026; 150 stress days and 150 calm days). The rule picks days at random, but only from stress and calm periods that were chosen by hand in advance, such as 2000 to 2002, 2007 to 2009 and 2022. The weights and alarm line were fixed before these dates were scored, and no hand-picked dates are included.

## What it cannot do

- **It detects stress. It has not been shown to predict it.** In monthly tests of 2008 and 2020 the score reached the alarm line in the same month the official recession began, not before. Walk-forward tests of leading signals did not show reliable crash prediction either.
- **It misses many stress days.** 61 of 150 stress dates stayed below the alarm line, and most of them scored within 5 points of it.
- **The news adds little.** For past dates, the 2 news factors were scored from real New York Times headlines from the 30 days before each date (nothing from the date itself or later). The news scores were almost the same on stress dates and calm dates, so the 12 market and economic factors do most of the work.
- **The headlines were picked by a fixed keyword rule**, so some are a loose fit, and one newspaper gives one view of events. The AI model may also remember how past events ended, which is a known problem when testing AI on history.
- **The sample is modest.** The dates were drawn from known stress and calm periods, and the level boundaries are working values.
- **News scoring is the least stable part.** The AI's reading of headlines can move a few points between runs.

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

The live site runs on an Oracle Cloud ARM server (4 CPUs, 24 GB) behind Caddy with HTTPS. See [DEPLOY.md](DEPLOY.md) for how it is deployed there and on Render.

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
