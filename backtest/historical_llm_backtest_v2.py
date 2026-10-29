"""
backtest/historical_llm_backtest_v2.py — CrisisPredictor
Second, out-of-sample historical check: 30 NEW dates (15 stress/crisis, 15 normal).

Labels (stress vs normal) were fixed BEFORE any scoring was run and are not changed
afterwards. The 12 numeric factors use real historical data, built by the same
build_historical_descriptions() as the first backtest. The 2 news factors use short
factual summaries written from general knowledge (the search tool cannot look up
old news); they contain only geopolitical/trade facts, no market-stress commentary.

Usage (run from the project root so the shared ./cache is used):
    python backtest/historical_llm_backtest_v2.py                 # all 30 dates
    python backtest/historical_llm_backtest_v2.py --dates 2018-02-08

Phase A fetches the real data and saves the factor descriptions (resumable).
Phase B scores the 14 factors per date in parallel and saves after every date.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from historical_llm_backtest import build_historical_descriptions  # noqa: E402
from tools.llm_scoring import score_factor  # noqa: E402

NO_TARIFF = "No major new tariff or sanctions escalation reported."

# (event, date, label, tariff_sanctions text, geopolitical_risk text)
DATES = [
    # ---------------- STRESS / CRISIS (15) ----------------
    ("S01_Aug2007_credit_crunch", "2007-08-16", "stress", NO_TARIFF,
     "US-led wars in Iraq and Afghanistan are ongoing; no new major conflict escalation reported."),
    ("S02_Bear_Stearns_2008", "2008-03-17", "stress", NO_TARIFF,
     "US-led wars in Iraq and Afghanistan are ongoing; no new major conflict escalation reported."),
    ("S03_Post_Lehman_2008", "2008-09-29", "stress", NO_TARIFF,
     "Iraq and Afghanistan wars continue. The Russia-Georgia conflict of August 2008 ended in a ceasefire but tensions remain."),
    ("S04_GFC_low_2009", "2009-03-09", "stress", NO_TARIFF,
     "Iraq and Afghanistan wars continue; no major new conflict escalation reported."),
    ("S05_Euro_scare_2010", "2010-05-20", "stress", NO_TARIFF,
     "Tensions on the Korean peninsula are elevated after an international investigation, announced on 20 May 2010, found North Korea responsible for sinking a South Korean navy ship in March."),
    ("S06_US_downgrade_2011", "2011-08-08", "stress", NO_TARIFF,
     "The NATO-led intervention in Libya is ongoing and Arab Spring unrest continues across the Middle East; no new major escalation reported on this date."),
    ("S07_China_shock_2015", "2015-08-24", "stress",
     "Western sanctions on Russia over Ukraine remain in place; the July 2015 Iran nuclear deal is due to ease sanctions on Iran.",
     "The Syrian civil war and the conflict in eastern Ukraine continue; no major new escalation reported."),
    ("S08_Oil_China_selloff_2016", "2016-02-11", "stress",
     "Western sanctions on Russia remain in place; sanctions on Iran were lifted in January 2016 under the nuclear deal.",
     "The Syrian civil war and the Ukraine conflict continue; North Korea conducted a nuclear test in January 2016 and a rocket launch in February 2016."),
    ("S09_Volmageddon_2018", "2018-02-08", "stress",
     "The US imposed safeguard tariffs on washing machines and solar panels in January 2018; broader trade tensions are rising, with steel and aluminum tariffs under review.",
     "The Syrian civil war continues and tensions with North Korea remain a concern."),
    ("S10_Q4_2018_low", "2018-12-24", "stress",
     "The US-China trade war is ongoing, with tariffs imposed on hundreds of billions of dollars of goods in 2018; a 90-day truce was agreed on 1 December 2018 and talks continue.",
     "The Syrian civil war continues and the US has announced plans to withdraw troops from Syria; the arrest of Huawei's CFO in Canada on 1 December 2018 has heightened US-China tensions."),
    ("S11_COVID_VIX_peak_2020", "2020-03-16", "stress",
     "The US-China Phase One trade deal was signed in January 2020; no major new tariff escalation reported.",
     "COVID-19 was declared a pandemic by the WHO on 11 March 2020; widespread travel bans and lockdowns are being imposed. An oil price war between Saudi Arabia and Russia began in early March 2020."),
    ("S12_Rate_shock_bear_2022", "2022-06-16", "stress",
     "Western sanctions on Russia imposed after the February 2022 invasion of Ukraine remain in place; US tariffs on Chinese goods from 2018-2019 remain.",
     "The Russia-Ukraine war, ongoing since 24 February 2022, continues with heavy fighting in eastern Ukraine; energy and grain supply disruptions continue."),
    ("S13_Oct2022_low", "2022-10-12", "stress",
     "Western sanctions on Russia remain in place; on 7 October 2022 the US announced new export controls on advanced chips to China.",
     "The Russia-Ukraine war is ongoing; Russia annexed four Ukrainian regions in late September 2022 and has made nuclear threats; the Nord Stream pipelines were damaged in late September 2022."),
    ("S14_Tariff_selloff_2025", "2025-04-08", "stress",
     "The US announced broad 'reciprocal' tariffs on imports from most countries on 2 April 2025, with tariffs on China escalating in early April; trading partners have announced or are considering retaliation.",
     "The Russia-Ukraine war and the Israel-Gaza conflict continue."),
    ("S15_Yen_carry_spike_2024", "2024-08-05", "stress",
     "US and EU tariffs on Chinese electric vehicles were announced in 2024; no other major new tariff escalation reported at this date.",
     "Tensions in the Middle East are escalating after the assassination of Hamas political leader Ismail Haniyeh in Tehran on 31 July 2024, with fears of an Iranian retaliation; the Russia-Ukraine war and Israel-Gaza war continue."),

    # ---------------- NORMAL (15) ----------------
    ("N01_Dec2006", "2006-12-15", "normal", NO_TARIFF,
     "The Iraq war continues; North Korea conducted a nuclear test in October 2006."),
    ("N02_May2007", "2007-05-15", "normal", NO_TARIFF,
     "The Iraq war continues with a US troop surge under way; no new major conflict escalation reported."),
    ("N03_Dec2010", "2010-12-15", "normal", NO_TARIFF,
     "North Korea shelled Yeonpyeong Island on 23 November 2010, raising tensions on the Korean peninsula; Iraq and Afghanistan wars continue."),
    ("N04_Jul2025", "2025-07-15", "normal",
     "The US has imposed or announced broad tariffs on many trading partners during 2025, with ongoing negotiations and deadline extensions; trade deals with some partners have been announced.",
     "The Russia-Ukraine war and the Israel-Gaza conflict continue; the Israel-Iran war of June 2025 ended with a ceasefire on 24 June 2025."),
    ("N05_Sep2012", "2012-09-14", "normal",
     "Western sanctions on Iran over its nuclear program were tightened in 2012, including an EU oil embargo from July 2012.",
     "The Syrian civil war is ongoing and Iran nuclear tensions persist; anti-US protests spread across parts of the Middle East in September 2012."),
    ("N06_Nov2013", "2013-11-15", "normal",
     "Nuclear talks between Iran and world powers are under way in Geneva; no major new tariff escalation reported.",
     "The Syrian civil war continues; a September 2013 agreement on Syria's chemical weapons averted planned US strikes."),
    ("N07_Jul2014", "2014-07-01", "normal",
     "Western sanctions on Russia over its annexation of Crimea are in place and have been widened; no major new tariff escalation reported.",
     "The conflict in eastern Ukraine is ongoing; ISIS has seized large areas of Iraq and Syria and declared a caliphate on 29 June 2014."),
    ("N08_Dec2016", "2016-12-15", "normal",
     "US President-elect Trump has criticised trade agreements such as NAFTA and TPP and signalled possible tariffs, but none have been imposed yet.",
     "The Syrian civil war is ongoing, with Aleppo recaptured by Syrian government forces in December 2016."),
    ("N09_Nov2017", "2017-11-15", "normal",
     "The US is renegotiating NAFTA and has launched several trade investigations; no major new tariffs on China yet.",
     "North Korea conducted a nuclear test in September 2017 and US-North Korea rhetoric is very heated; the Syrian civil war continues."),
    ("N10_Nov2019", "2019-11-15", "normal",
     "The US-China trade war is ongoing with tariffs in place on both sides, but a 'phase one' trade deal is being negotiated and some tariff increases have been delayed.",
     "Protests in Hong Kong are ongoing; Turkey launched an offensive in northern Syria in October 2019."),
    ("N11_Dec2020", "2020-12-15", "normal",
     "The US-China Phase One deal is in effect and existing tariffs remain; no major new escalation reported.",
     "The COVID-19 pandemic continues, with the first vaccines approved and being rolled out in December 2020; no new major armed conflict reported."),
    ("N12_Apr2021", "2021-04-15", "normal",
     "Existing US tariffs on China remain; on 15 April 2021 the US announced new sanctions on Russia over cyber activity and election interference.",
     "Russia has massed troops near Ukraine's border in spring 2021; the COVID-19 pandemic continues."),
    ("N13_Jul2021", "2021-07-15", "normal",
     "Existing US tariffs on China remain; no major new tariff escalation reported.",
     "No new major armed conflict reported; the US withdrawal from Afghanistan is under way."),
    ("N14_Jul2023", "2023-07-14", "normal",
     "Existing US tariffs on China remain; the US and allies have restricted advanced chip exports to China; Western sanctions on Russia remain.",
     "The Russia-Ukraine war is ongoing, with Ukraine's counteroffensive under way."),
    ("N15_Mar2024", "2024-03-15", "normal",
     "Existing US tariffs on China remain; Western sanctions on Russia remain.",
     "The Russia-Ukraine war and the Israel-Gaza war continue; Houthi militants continue attacks on Red Sea shipping."),
]

DESC_PATH = os.path.join(HERE, "backtest_v2_descriptions.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v2_results.json")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def phase_a_fetch(selected):
    """Fetch real historical data and build the 14 factor descriptions per date."""
    descs = load_json(DESC_PATH, {})
    for event, date, label, tariff, geo in selected:
        if event in descs:
            continue
        t0 = time.time()
        try:
            d = build_historical_descriptions(date)
        except Exception as e:
            print(f"[A] {event} {date}: FAILED to fetch data: {e}", flush=True)
            continue
        d["tariff_sanctions"] = tariff
        d["geopolitical_risk"] = geo
        descs[event] = {"date": date, "label": label, "descriptions": d}
        save_json(DESC_PATH, descs)
        print(f"[A] {event} {date}: data ready ({time.time()-t0:.0f}s)", flush=True)
    return descs


def _score_one(item):
    key, desc = item
    for attempt in range(2):
        try:
            return key, score_factor(key, desc).score
        except Exception as e:
            err = str(e)
            time.sleep(2)
    print(f"    {key} FAILED: {err[:120]}", flush=True)
    return key, None


def phase_b_score(descs, selected):
    results = load_json(RESULTS_PATH, {})
    for event, date, label, _, _ in selected:
        if event in results or event not in descs:
            continue
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=7) as ex:
            pairs = list(ex.map(_score_one, descs[event]["descriptions"].items()))
        results[event] = {"date": date, "label": label, "factor_scores": dict(pairs)}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs if v is None]
        print(f"[B] {event} {date}: scored ({time.time()-t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", default="", help="comma-separated dates to run (default: all)")
    args = ap.parse_args()
    wanted = {d.strip() for d in args.dates.split(",") if d.strip()}
    selected = [row for row in DATES if not wanted or row[1] in wanted]

    t0 = time.time()
    print(f"Running {len(selected)} dates", flush=True)
    descs = phase_a_fetch(selected)
    phase_b_score(descs, selected)
    print(f"DONE in {time.time()-t0:.0f}s", flush=True)
