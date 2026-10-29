# Backtest

How the numbers on the website were produced. Nothing here is needed to run the app.

## The 300 test dates

All 300 dates were drawn by a computer with a fixed random rule from stress and calm periods chosen by hand in advance
(2000 to 2002, 2007 to 2009, 2022 and so on). Three batches, 150 stress days and 150 calm days, each scored with all 14 factors:

| Script | Seed | Dates | Saved results |
|---|---|---|---|
| `historical_llm_backtest_v4.py` (dates) and `historical_llm_backtest_v5.py` (scores, with news) | 42 | 120 | `backtest_v5_results.json` |
| `historical_llm_backtest_v6.py` | 7 | 100 | `backtest_v6_results.json` |
| `historical_llm_backtest_v7.py` | 2026 | 80 | `backtest_v7_results.json` |

The date lists are saved before anything is scored (`backtest_v4_dates.json`, `backtest_v6_dates.json`, `backtest_v7_dates.json`),
so they cannot be changed after seeing results. The news text for past dates was written from the historical record, because a live search
cannot look back.

## Reproduce the numbers (no API calls)

```bash
python backtest/analyze_300_random.py     # prints the results table
python backtest/build_web_evidence.py     # rebuilds web/data/evidence.json for the landing page
```

Scores are recomputed from the saved per-factor scores with the current weights in `tools/scoring_tools.py`.
Both scripts import the scoring code, so they need the `.env` keys set (see the main README).

## Older scripts

`historical_llm_backtest.py` holds the shared data fetching. `historical_llm_backtest_v2.py` and `_v3.py`, `rerun_41.py` and `analyze_v2.py`
belong to the first 80 hand-picked dates, which are no longer part of the reported results. They stay because the random-date
scripts import their helpers.
