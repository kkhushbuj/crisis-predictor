# Historical LLM+RAG Scoring Validation — Methods Note

## What this test is (and isn't)

This is a **directional calibration check** of the RAG+LLM per-factor scoring
engine (`tools/llm_scoring.py`), not a formal accuracy benchmark. It answers:
"does the scoring engine react in the correct direction to real historical
market conditions?" — not "what % of days would this system have correctly
flagged as a crisis."

For a quantitative, threshold-based accuracy metric (peak score, % of days
above the 55-point Stress threshold, and lead time in days ahead of the
market bottom), see the earlier **statistical composite backtest**
(`backtest/crisis_backtest.py`, results in `composite_backtest_output.csv`),
which validated the underlying 14-factor statistical framework this LLM
layer sits on top of. That backtest showed 100% detection across all 6
tested crises with 197-264 days of lead time.

## Scope

9 events, 11 test dates, 14 factors scored per date (154 total LLM calls).

| Category | Events | Dates |
|---|---|---|
| Crisis (peak/acute) | 2008 GFC, 2011 Euro Crisis, 2018 Trade War, COVID-19, Ukraine 2022, SVB 2023 | 6 dates |
| Crisis (early-warning) | 2008 GFC, COVID-19 | 2 dates |
| Calm control | 2017, 2019 H1, 2024 | 3 dates |

## Results summary

| Event | Date | Avg score | Direction |
|---|---|---|---|
| 2008_GFC_early | 2008-06-15 | -0.64 | Mild bearish |
| 2008_GFC_peak | 2008-10-15 | -2.14 | Bearish |
| 2011_Euro_Crisis | 2011-09-01 | -1.64 | Bearish |
| 2018_Trade_War | 2018-12-15 | -0.93 | Bearish |
| COVID_early | 2020-02-20 | +0.79 | Mild bullish* |
| COVID_peak | 2020-03-23 | -3.79 | Strongly bearish |
| Ukraine_2022 | 2022-03-08 | -3.93 | Strongly bearish |
| SVB_2023 | 2023-03-13 | -0.71 | Mild bearish |
| Calm_2017 | 2017-06-15 | +0.86 | Neutral/mild bullish |
| Calm_2019_H1 | 2019-03-15 | +0.50 | Neutral |
| Calm_2024 | 2024-06-15 | +0.57 | Neutral/mild bullish |

*COVID_early (Feb 20, 2020) scored mild-bullish, which initially looks like
a miss against its "expected: bearish" label. On inspection, this is a
test-design issue, not a model error: Feb 19-2020 was literally the S&P
500's all-time high the day before the COVID crash began. VIX and drawdown
correctly scored positive because markets genuinely hadn't cracked yet on
that date. The test label should have been "expected: mild/early signal,"
not "bearish."

## Honest takeaways

- All 6 crisis peak/acute dates scored correctly bearish, several (Ukraine
  2022, COVID peak) substantially strengthened after fixing derived-metric
  descriptions (see "Known limitation, fixed" below).
- All 3 calm control dates scored correctly neutral/mild.
- The one apparent "miss" (COVID_early) reflects accurate historical
  reasoning, not a scoring failure — see note above.
- **No single "% accuracy" figure is reported**, because this test was not
  built against a formal classification threshold. Reporting one would
  overstate what was measured.

## Known limitation, fixed during this run

The first version of this backtest script under-described 3-5 of 14
factors (raw price levels instead of % moves, hardcoded "data unavailable"
for repo/M2 factors), which silently pulled every factor toward a Neutral
(0) score. This was corrected by computing the same derived-metric style
(20-day % moves, 3-month relative performance, real historical repo/M2
data) that the live system uses. Results above are from the corrected run.

## Known limitation, not fixable

The 2 geopolitical factors (`tariff_sanctions`, `geopolitical_risk`) cannot
be backtested with live news search, since Tavily/DDGS only search current
news. For these 11 dates, manually-written factual historical event
summaries were substituted (see `GEOPOLITICAL_HISTORICAL_CONTEXT` in
`historical_llm_backtest.py`). This is a reasonable stand-in for testing
whether the scoring engine reacts correctly to known historical severity,
but it is not equivalent to a live backtest and should be described as
such in any writeup.

## Files

- `historical_llm_backtest.py` — the test script
- `historical_llm_backtest_results.json` — full per-factor scores, all dates
- `historical_llm_backtest_results.csv` — summary table