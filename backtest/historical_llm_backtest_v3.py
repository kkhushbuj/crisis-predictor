"""
backtest/historical_llm_backtest_v3.py — CrisisPredictor
Third, fully fresh check: 40 NEW dates (20 stress, 20 normal), none used in any earlier backtest, with the risk
cutoffs (30 / 55 / 75, alarm at 55) already fixed. Labels and news texts are fixed BEFORE any scoring and are not
changed afterwards. Same method as v2: real historical data for the 12 numeric factors, short neutral facts for the
2 news factors (no market commentary).

    python backtest/historical_llm_backtest_v3.py
Then:
    python backtest/analyze_v3.py
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from historical_llm_backtest import build_historical_descriptions  # noqa: E402
from historical_llm_backtest_v2 import _score_one  # noqa: E402

NO_TARIFF = "No major new tariff or sanctions escalation reported."
WARS = "Iraq and Afghanistan wars continue; no new major escalation reported."

# (event, date, label, tariff_sanctions text, geopolitical_risk text)
DATES = [
    # ---------------- STRESS (20) ----------------
    ("T01_Apr2000_dotcom", "2000-04-14", "stress", NO_TARIFF,
     "No major new armed conflict reported; US forces remain in the Balkans after the 1999 Kosovo war."),
    ("T02_Apr2001_nasdaq_low", "2001-04-04", "stress", NO_TARIFF,
     "A US spy plane collided with a Chinese fighter jet on 1 April 2001, creating a diplomatic standoff; Israeli-Palestinian violence continues."),
    ("T03_Sep2001_post_911", "2001-09-21", "stress", NO_TARIFF,
     "The September 11, 2001 terrorist attacks occurred ten days earlier; the US is preparing a military response and building an international coalition."),
    ("T04_Jul2002_scandals", "2002-07-23", "stress", NO_TARIFF,
     "The US war on terror continues in Afghanistan; the US is debating possible action against Iraq; Israeli-Palestinian violence continues."),
    ("T05_Oct2002_bear_low", "2002-10-09", "stress",
     "The US imposed tariffs on steel imports in March 2002, which drew complaints from trading partners.",
     "The US Congress is debating a resolution authorizing the use of force against Iraq; the US war on terror continues in Afghanistan."),
    ("T06_Mar2003_pre_Iraq", "2003-03-11", "stress",
     "US tariffs on steel imports imposed in March 2002 remain in place.",
     "The US and allies have massed troops in the region around Iraq while diplomatic efforts at the UN Security Council continue."),
    ("T07_Jan2008_global_selloff", "2008-01-22", "stress", NO_TARIFF, WARS),
    ("T08_Jul2008_bear_market", "2008-07-15", "stress", NO_TARIFF,
     "Iraq and Afghanistan wars continue; tensions over Iran's nuclear program persist, with Iran test-firing missiles on 9 July 2008."),
    ("T09_Nov2008_GFC_low", "2008-11-20", "stress", NO_TARIFF, WARS),
    ("T10_Feb2010_greece", "2010-02-05", "stress", NO_TARIFF,
     "Iraq and Afghanistan wars continue; the US is increasing troop levels in Afghanistan; Iran nuclear tensions persist."),
    ("T11_Oct2011_euro_low", "2011-10-03", "stress", NO_TARIFF,
     "The NATO-led intervention in Libya is winding down after the fall of Tripoli; the Syrian government crackdown on protests continues."),
    ("T12_Sep2015_china_low", "2015-09-29", "stress",
     "Western sanctions on Russia remain in place; the Iran nuclear deal reached in July 2015 is awaiting implementation.",
     "The Syrian civil war continues and Russia is building up forces in Syria; Europe faces a large inflow of refugees."),
    ("T13_Jan2016_global_selloff", "2016-01-20", "stress",
     "Western sanctions on Russia remain in place; sanctions on Iran were lifted on 16 January 2016.",
     "The Syrian civil war and the Ukraine conflict continue; North Korea conducted a nuclear test on 6 January 2016; Saudi Arabia and Iran cut diplomatic ties in early January 2016."),
    ("T14_Jun2016_brexit", "2016-06-27", "stress",
     "Western sanctions on Russia remain in place; no major new tariff escalation reported.",
     "The UK voted to leave the European Union in a referendum on 23 June 2016; the Syrian civil war and the Ukraine conflict continue."),
    ("T15_Oct2018_selloff", "2018-10-29", "stress",
     "The US-China trade war is ongoing, with US tariffs on about 250 billion dollars of Chinese goods and Chinese retaliation in place; US sanctions on Iran's oil sector are due to be re-imposed in November 2018.",
     "The disappearance and killing of journalist Jamal Khashoggi at the Saudi consulate in Istanbul on 2 October 2018 has strained US-Saudi relations; the Syrian civil war continues."),
    ("T16_Aug2019_yuan_tariff", "2019-08-05", "stress",
     "On 1 August 2019 the US announced a new 10% tariff on 300 billion dollars of Chinese imports, effective September; China let the yuan weaken past 7 per dollar on 5 August 2019.",
     "Protests in Hong Kong are intensifying; tensions with Iran in the Gulf persist."),
    ("T17_May2022_bear", "2022-05-20", "stress",
     "Western sanctions on Russia remain in place; US tariffs on Chinese goods remain.",
     "The Russia-Ukraine war continues, with heavy fighting in the Donbas and the fall of Mariupol in May 2022."),
    ("T18_Sep2022_low", "2022-09-30", "stress",
     "Western sanctions on Russia remain in place; US tariffs on Chinese goods remain.",
     "The Russia-Ukraine war continues; Russia announced the annexation of four Ukrainian regions on 30 September 2022; the Nord Stream pipelines were damaged in late September 2022."),
    ("T19_Oct2023_rate_selloff", "2023-10-27", "stress",
     "Existing US tariffs on China remain; Western sanctions on Russia remain.",
     "The Israel-Hamas war began after the attack of 7 October 2023, with Israeli ground operations expanding in Gaza; the Russia-Ukraine war continues."),
    ("T20_Mar2025_tariff_correction", "2025-03-13", "stress",
     "The US imposed 25% tariffs on steel and aluminum imports effective 12 March 2025, and tariffs on Canada, Mexico and China in early March 2025, with some exemptions; trading partners announced retaliation.",
     "The Russia-Ukraine war and the Israel-Gaza conflict continue; US-led talks on a Ukraine ceasefire are under way."),

    # ---------------- NORMAL (20) ----------------
    ("M01_Feb2004", "2004-02-13", "normal",
     "US steel tariffs were removed in December 2003; no major new tariffs reported.", WARS),
    ("M02_Nov2004", "2004-11-15", "normal", NO_TARIFF,
     "The Iraq war continues, with a major US assault on Fallujah under way."),
    ("M03_Jun2005", "2005-06-15", "normal", NO_TARIFF, WARS),
    ("M04_Dec2005", "2005-12-15", "normal", NO_TARIFF,
     "Iraq held parliamentary elections on 15 December 2005; the Iraq and Afghanistan wars continue."),
    ("M05_Mar2006", "2006-03-15", "normal", NO_TARIFF,
     "The Iraq war continues amid sectarian violence; Iran's nuclear program is under review at the UN Security Council."),
    ("M06_Mar2012", "2012-03-15", "normal",
     "Western sanctions on Iran over its nuclear program are tightening; no major new tariff escalation reported.",
     "The Syrian civil war is ongoing and Iran nuclear tensions persist."),
    ("M07_Dec2012", "2012-12-14", "normal",
     "Western sanctions on Iran remain in place; no major new tariff escalation reported.",
     "The Syrian civil war continues; no new major escalation reported."),
    ("M08_Mar2013", "2013-03-15", "normal",
     "Western sanctions on Iran remain in place; no major new tariff escalation reported.",
     "The Syrian civil war continues; North Korea conducted a nuclear test in February 2013."),
    ("M09_Apr2014", "2014-04-15", "normal",
     "Western sanctions on Russia over its annexation of Crimea were imposed in March 2014.",
     "Pro-Russian separatists are seizing government buildings in eastern Ukraine; the Syrian civil war continues."),
    ("M10_May2015", "2015-05-15", "normal",
     "Western sanctions on Russia remain in place; negotiations on the Trans-Pacific Partnership continue.",
     "The Syrian civil war and the conflict in eastern Ukraine continue; Iran nuclear talks continue."),
    ("M11_Feb2017", "2017-02-15", "normal",
     "The new US administration has withdrawn from the Trans-Pacific Partnership and signalled possible border taxes and tariffs, but none have been imposed yet.",
     "The Syrian civil war continues; North Korea test-fired a missile on 12 February 2017."),
    ("M12_Sep2017", "2017-09-15", "normal",
     "The US is renegotiating NAFTA and has opened several trade investigations; no major new tariffs on China yet.",
     "North Korea conducted its sixth nuclear test on 3 September 2017 and fired a missile over Japan on 15 September 2017; US-North Korea rhetoric is heated."),
    ("M13_Dec2017", "2017-12-15", "normal",
     "The US is renegotiating NAFTA; no major tariffs on China imposed yet.",
     "US-North Korea tensions persist; the US recognized Jerusalem as Israel's capital on 6 December 2017."),
    ("M14_Jul2019", "2019-07-15", "normal",
     "The US-China trade war is ongoing with tariffs in place, and negotiations resumed after the G20 meeting in late June 2019.",
     "Tensions with Iran in the Gulf persist; protests in Hong Kong are ongoing."),
    ("M15_Dec2019", "2019-12-13", "normal",
     "The US and China announced a phase one trade deal on 13 December 2019, with planned tariff increases suspended.",
     "Protests in Hong Kong continue; US-Iran tensions persist."),
    ("M16_Jan2021", "2021-01-15", "normal",
     "Existing US tariffs on China remain; the US-China Phase One deal is in effect.",
     "The COVID-19 pandemic continues with vaccine rollouts under way; political tension in the US ahead of the 20 January 2021 inauguration."),
    ("M17_Oct2021", "2021-10-15", "normal",
     "Existing US tariffs on China remain; no major new tariff escalation reported.",
     "No new major armed conflict reported; the COVID-19 pandemic continues."),
    ("M18_Dec2023", "2023-12-15", "normal",
     "Existing US tariffs on China remain; Western sanctions on Russia remain.",
     "The Israel-Hamas war and the Russia-Ukraine war continue; Houthi attacks on Red Sea shipping have led some shipping companies to suspend transits."),
    ("M19_May2024", "2024-05-15", "normal",
     "The US announced higher tariffs on Chinese electric vehicles and other goods on 14 May 2024; Western sanctions on Russia remain.",
     "The Russia-Ukraine war and the Israel-Gaza war continue."),
    ("M20_Nov2024", "2024-11-15", "normal",
     "Existing US tariffs on China remain; the incoming US administration has signalled further tariffs.",
     "The Russia-Ukraine war and the Israel-Gaza war continue; the Israel-Hezbollah conflict is ongoing."),
]

DESC_PATH = os.path.join(HERE, "backtest_v3_descriptions.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v3_results.json")


def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def main():
    t0 = time.time()
    descs, results = load_json(DESC_PATH, {}), load_json(RESULTS_PATH, {})
    for event, date, label, tariff, geo in DATES:
        if event in results:
            continue
        if event not in descs:
            try:
                d = build_historical_descriptions(date)
            except Exception as e:
                print(f"[A] {event} {date}: FAILED to fetch data: {e}", flush=True)
                continue
            d["tariff_sanctions"], d["geopolitical_risk"] = tariff, geo
            descs[event] = {"date": date, "label": label, "descriptions": d}
            save_json(DESC_PATH, descs)
        with ThreadPoolExecutor(max_workers=7) as ex:
            pairs = list(ex.map(_score_one, descs[event]["descriptions"].items()))
        results[event] = {"date": date, "label": label, "factor_scores": dict(pairs)}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs if v is None]
        print(f"[{len(results)}/{len(DATES)}] {event} {date} scored ({time.time() - t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    print(f"DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
