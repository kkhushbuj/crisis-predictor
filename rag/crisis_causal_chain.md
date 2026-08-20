# Crisis Causal Chain — Historical Grounding Document

This document grounds each of CrisisPredictor's 14 factors in their historical
causal relationship to financial crises. Each section is retrieved via RAG and
given to the LLM as context before it scores that factor from -10 (strongly
bearish / crisis-signaling) to +10 (strongly bullish / stability-signaling).

---

## FACTOR: Yield Curve (10Y-2Y Treasury Spread)

The yield curve is one of the most reliable recession leading indicators in
market history. When short-term yields rise above long-term yields (inversion),
it signals markets expect the Fed to cut rates due to future economic weakness.
Every US recession since 1955 was preceded by a 10Y-2Y inversion, with a lag of
6-24 months between inversion and recession onset. The 2019 inversion preceded
COVID-triggered recession; the 2006-2007 inversion preceded the 2008 GFC.

Scoring thresholds:
- Spread below -0.5%: -10 (deep inversion, strong recession signal)
- Spread -0.5% to 0%: -6 (inverted, moderate signal)
- Spread 0% to 0.5%: -2 (flat, mild concern)
- Spread 0.5% to 1.5%: 0 (normal, neutral)
- Spread above 1.5%: +5 (steep curve, healthy growth expectations)

---

## FACTOR: Credit Spread (Baa Corporate Bond Yield - 10Y Treasury)

Credit spreads widen when investors demand more compensation for holding
corporate debt over risk-free government debt — a direct measure of perceived
default risk. Sharp widening preceded and accompanied the 2008 GFC (spreads
exceeded 6%) and COVID (spreads spiked in March 2020). Historically, spreads
below 2% indicate calm credit markets; above 4% indicates genuine credit stress.

Scoring thresholds:
- Spread above 4%: -10 (severe credit stress, crisis-level)
- Spread 3-4%: -6 (elevated stress)
- Spread 2-3%: -2 (mild widening)
- Spread 1.5-2%: 0 (normal)
- Spread below 1.5%: +5 (very calm credit conditions)

---

## FACTOR: Bank Sector Relative Strength (Financials vs S&P 500)

Banks are the transmission mechanism of credit crises — they fail first and
worst when systemic stress builds, because they're leveraged and interconnected.
Bank stocks underperforming the broad market by a wide margin is a strong tell
that credit markets see problems the broad market hasn't priced in yet. This
was true in 2007-2008 (banks fell 6+ months before the broad market bottomed)
and again in March 2023 (regional bank stress preceded SVB's collapse).

Scoring thresholds:
- Banks underperforming market by >15% (trailing 3mo): -10
- Underperforming by 8-15%: -6
- Underperforming by 3-8%: -2
- Roughly in line (-3% to +3%): 0
- Outperforming by >3%: +5

---

## FACTOR: Repo Market Stress (SOFR Overnight Rate Spikes)

The repo market is the plumbing of the financial system — banks borrow
short-term cash against collateral here daily. When repo rates spike far above
the Fed's target range, it signals a genuine cash/collateral shortage among
major institutions. The September 2019 repo spike (rates briefly hit 10%) was
a real warning sign of funding market fragility, even though it didn't
immediately cascade into a full crisis. Persistent repo stress is a leading
indicator banks are hoarding cash, expecting trouble.

Scoring thresholds:
- SOFR spike >2% above Fed target: -10 (acute funding stress)
- Spike 1-2% above target: -6
- Spike 0.25-1% above target: -2
- Within normal band: 0
- Persistently below target (excess liquidity): +3

---

## FACTOR: M2 Money Supply Growth Rate

M2 growth reflects the pace of money creation in the economy, driven heavily
by Fed policy. Extremely rapid contraction in M2 (as seen in 2022-2023, the
sharpest M2 contraction since the 1930s) signals aggressive monetary tightening
that historically precedes credit stress and recessions, as liquidity is pulled
from the system faster than the economy can adjust. Conversely, runaway M2
growth (as in 2020-2021) can signal asset bubbles building.

Scoring thresholds:
- M2 YoY growth below -3% (sharp contraction): -8
- Growth -3% to 0%: -4
- Growth 0% to 4% (normal range): 0
- Growth 4% to 10%: -2 (bubble risk building)
- Growth above 10%: -5 (excessive, bubble/inflation risk)

---

## FACTOR: VIX (CBOE Volatility Index)

The VIX measures the market's expectation of 30-day forward volatility, derived
from S&P 500 options pricing. It's the most widely watched "fear gauge." VIX
above 30 typically coincides with acute market stress; above 40 with genuine
panic (2008 peaked near 80, COVID March 2020 peaked near 82). VIX below 15
reflects genuine complacency/calm.

Scoring thresholds:
- VIX above 40: -10 (panic)
- VIX 30-40: -7 (acute stress)
- VIX 20-30: -3 (elevated concern)
- VIX 15-20: 0 (normal)
- VIX below 15: +5 (calm, possibly complacent)

---

## FACTOR: S&P 500 Drawdown from All-Time High

Drawdown magnitude and velocity both matter. A slow -10% correction over months
is very different from a fast -20% crash over weeks — the latter reflects
panic-driven forced selling, margin calls, and liquidity withdrawal, which is
exactly the dynamic seen in both 2008 and COVID. Drawdowns beyond -20% are
technically defined as bear markets and historically correlate with broader
economic damage, not just sentiment.

Scoring thresholds:
- Drawdown beyond -30%: -10 (severe bear market)
- Drawdown -20% to -30%: -7 (bear market)
- Drawdown -10% to -20%: -3 (correction territory)
- Drawdown -5% to -10%: 0 (normal pullback)
- Drawdown less than -5% (near highs): +5

---

## FACTOR: Gold Momentum (20-day price change)

Gold's role as a flight-to-safety asset means sharp upward momentum often
confirms that "real" fear (not just noise) is driving markets — investors are
actively rotating into safe-haven assets. This is a confirming signal alongside
VIX and drawdown, not a standalone one; gold can also rise for unrelated
reasons (inflation hedging, central bank buying), so strong momentum alone is
a moderate signal, not a strong one on its own.

Scoring thresholds:
- 20-day gain above +8%: -6 (strong flight-to-safety signal)
- Gain +4% to +8%: -3
- Gain -2% to +4%: 0 (normal range)
- Decline -2% to -6%: +2 (risk-on rotation, mild positive)
- Decline beyond -6%: +4 (strong risk-on, or gold-specific weakness)

---

## FACTOR: US Dollar Index (DXY) — 20-day momentum

Rapid dollar strengthening during stress periods reflects a "dollar shortage"
dynamic — global investors and institutions scramble for dollar liquidity
during crises (as seen sharply in March 2020), which paradoxically strengthens
the dollar even as US markets fall. This is a classic liquidity-crisis fingerprint
distinct from ordinary currency moves.

Scoring thresholds:
- 20-day DXY gain above +5% (rapid strengthening): -8
- Gain +2% to +5%: -4
- Gain -2% to +2%: 0 (normal range)
- Decline beyond -2%: +3 (dollar weakening, generally risk-on)

---

## FACTOR: Jobless Claims Trend (4-week change)

Initial jobless claims are one of the most timely labor-market indicators
available (weekly data, minimal lag). A sustained rising trend — not just one
noisy week — reliably precedes recognized recessions, as employers cut staff
before broader economic data catches up. This was true ahead of both 2008 and
2020, and is one of the few real-time indicators of labor market cracking.

Scoring thresholds:
- 4-week claims trend rising >15%: -8 (labor market cracking)
- Rising 8-15%: -5
- Rising 0-8%: -1
- Flat to declining: +3 (healthy labor market)

---

## FACTOR: CPI Shock (YoY deviation from trend)

Both inflation shocks (2022) and deflation shocks (2008-2009) precede or
accompany financial stress — the direction matters less than the magnitude of
deviation from the recent trend. A sudden CPI shock in either direction signals
the economy is being hit by a real shock the Fed will have to react to, often
clumsily, adding further instability.

Scoring thresholds:
- CPI YoY deviation from 6mo trend beyond 2 percentage points (either direction): -6
- Deviation 1-2 points: -3
- Deviation under 1 point: 0 (stable, predictable inflation path)

---

## FACTOR: Oil Price Volatility (20-day absolute % change)

Oil shocks — both spikes (supply disruption, geopolitical conflict) and crashes
(demand collapse, as in April 2020's negative pricing) — are classic crisis
accelerants because energy costs ripple through the entire economy. Historically,
oil price shocks preceded or coincided with several recessions (1973, 1979,
1990, 2008, 2020).

Scoring thresholds:
- 20-day absolute move beyond 25%: -8 (severe shock, either direction)
- Move 15-25%: -5
- Move 8-15%: -2
- Move under 8%: 0 (normal volatility range)

---

## FACTOR: Tariff/Sanctions Sentiment (live news, LLM-scored)

Trade policy shocks — new tariffs, sanctions regimes, export controls — create
sudden, hard-to-hedge risk for markets because they change the rules of global
commerce overnight. The 2018-2019 US-China trade war caused sustained equity
volatility and supply chain disruption without a "normal" economic trigger.
Sanctions (e.g., against Russia in 2022) similarly cause sudden repricing of
entire sectors and countries. This factor is scored by an LLM reading live news
search results for escalation language, market-moving policy actions, and
explicit economic-impact framing.

Scoring guidance for the LLM:
- Major new tariffs/sanctions announced with explicit market disruption: -8 to -10
- Escalating trade tension, threats, negotiations breaking down: -4 to -7
- Routine trade policy news, no major escalation: -1 to 0
- De-escalation, trade deals, tariff rollbacks: +3 to +6

---

## FACTOR: Geopolitical Risk (conflict/war news density, LLM-scored)

Armed conflict, war escalation, and major geopolitical crises (invasions, coups,
terrorist attacks with market impact) drive flight-to-safety behavior and can
disrupt commodity supply chains (energy, grain) with global economic
consequences. The 2022 Russia-Ukraine invasion is the clearest recent example —
immediate market volatility, energy price spikes, and sustained elevated risk
premium. This factor is scored by an LLM reading live news for conflict
escalation, new military action, and explicit market-relevant framing.

Scoring guidance for the LLM:
- Active new conflict/invasion with clear market impact: -8 to -10
- Escalating tensions, troop movements, credible war risk: -4 to -7
- Routine geopolitical news, no acute escalation: -1 to 0
- De-escalation, ceasefires, diplomatic resolution: +3 to +6

---

## SCORING METHODOLOGY NOTE

All 14 factors are scored -10 to +10 by the LLM using the thresholds above as
grounding context (retrieved via RAG per-factor). Python then applies fixed,
backtested category weights (Credit/Systemic 30, Liquidity/Shock 30, Macro 20,
Geopolitical 20 — summing to 100) to compute the final deterministic Crisis
Score. The LLM never decides the final weighting — only the per-factor
qualitative score, exactly as in GoldBot's architecture.