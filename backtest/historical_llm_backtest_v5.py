"""
backtest/historical_llm_backtest_v5.py — CrisisPredictor
The SAME 120 dates as v4 (60 stress, 60 normal, picked by a fixed random rule), scored with ALL 14 factors.
v4 left out the 2 news factors; here they are included. Nothing else changes: same real historical data for the
12 numeric factors (taken from the v4 descriptions file), alarm cutoff 55 locked.

The 2 news texts per date are short neutral facts from general knowledge, as in v2/v3. They come from the timeline
below (the latest entry that started on or before the date). They contain only trade/geopolitical facts that had
already happened by then and no market commentary. The timeline was written before any scoring.

    python backtest/historical_llm_backtest_v5.py
Then:
    python backtest/analyze_v5.py
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(HERE))
sys.path.append(HERE)

from historical_llm_backtest_v2 import _score_one  # noqa: E402

NO_TARIFF = "No major new tariff or sanctions escalation reported."
WARS = "Iraq and Afghanistan wars continue; no new major escalation reported."

# (starts on, text) — the latest entry starting on or before the date is used.
TARIFF = [
    ("2000-01-01", NO_TARIFF),
    ("2002-03-20", "The US imposed tariffs on steel imports in March 2002, which drew complaints from trading partners."),
    ("2003-12-04", "US steel tariffs were removed in December 2003; no major new tariffs reported."),
    ("2006-12-23", "UN Security Council sanctions on Iran over its nuclear program are in place; no major new tariff escalation reported."),
    ("2010-06-09", "UN and Western sanctions on Iran over its nuclear program were tightened in June 2010; no major new tariff escalation reported."),
    ("2012-01-23", "Western sanctions on Iran over its nuclear program are tightening; an EU oil embargo on Iran was agreed in January 2012."),
    ("2014-03-17", "Western sanctions on Russia over its annexation of Crimea are in place."),
    ("2015-07-14", "Western sanctions on Russia remain in place; a nuclear deal with Iran was reached in July 2015."),
    ("2016-01-16", "Western sanctions on Russia remain in place; sanctions on Iran were lifted in January 2016."),
    ("2017-01-23", "The new US administration withdrew from the Trans-Pacific Partnership in January 2017 and has signalled possible tariffs, but none have been imposed on China yet."),
    ("2018-09-24", "The US-China trade war is ongoing, with US tariffs on about 250 billion dollars of Chinese goods and Chinese retaliation in place."),
    ("2018-12-01", "The US-China trade war is ongoing, with US tariffs on about 250 billion dollars of Chinese goods in place; a 90-day truce was agreed on 1 December 2018 and talks continue."),
    ("2019-05-10", "The US-China trade war is ongoing; US tariffs on 200 billion dollars of Chinese goods were raised to 25% in May 2019."),
    ("2019-10-11", "The US-China trade war is ongoing, with a phase one trade deal under negotiation; some planned tariff increases have been delayed."),
    ("2020-01-15", "The US-China Phase One trade deal was signed in January 2020; existing tariffs remain."),
    ("2022-02-24", "Western countries announced sanctions on Russia after its invasion of Ukraine on 24 February 2022; US tariffs on Chinese goods remain."),
    ("2022-03-01", "Western sanctions on Russia imposed after the February 2022 invasion of Ukraine are in place and have been widened; US tariffs on Chinese goods remain."),
    ("2023-01-01", "Existing US tariffs on China remain; Western sanctions on Russia remain."),
    ("2024-05-14", "The US announced higher tariffs on Chinese electric vehicles and other goods on 14 May 2024; Western sanctions on Russia remain."),
    ("2025-01-20", "The new US administration took office on 20 January 2025 and has signalled new tariffs; existing tariffs on China remain; Western sanctions on Russia remain."),
    ("2025-03-12", "The US imposed tariffs on Canada, Mexico and China in early March 2025, with some exemptions, and 25% tariffs on steel and aluminum took effect on 12 March; trading partners announced retaliation."),
]

GEO = [
    ("2000-01-01", "No major new armed conflict reported; US forces remain in the Balkans after the 1999 Kosovo war."),
    ("2000-10-12", "A suicide attack on the US Navy ship USS Cole in Yemen killed 17 sailors on 12 October 2000; Israeli-Palestinian violence has escalated since late September 2000."),
    ("2001-04-01", "A US spy plane collided with a Chinese fighter jet on 1 April 2001 and was held in China until the crew was released on 11 April; Israeli-Palestinian violence continues."),
    ("2001-09-11", "Terrorist attacks on 11 September 2001 hit New York and Washington; the US is preparing a military response and building an international coalition."),
    ("2001-10-07", "The US and allies began military action in Afghanistan on 7 October 2001 after the 11 September attacks; anthrax letters have been reported in the US."),
    ("2001-12-07", "The Taliban government in Afghanistan has fallen; the US war on terror continues; Israeli-Palestinian violence continues."),
    ("2002-01-29", "The US war on terror continues in Afghanistan; the US president described Iran, Iraq and North Korea as an 'axis of evil' on 29 January 2002; Israeli-Palestinian violence continues."),
    ("2002-03-29", "Israel launched a large military operation in the West Bank in late March 2002; the US war on terror continues in Afghanistan."),
    ("2002-05-15", "The US war on terror continues in Afghanistan; the US is debating possible action against Iraq; Israeli-Palestinian violence continues."),
    ("2002-09-12", "The US president addressed the UN General Assembly on Iraq on 12 September 2002; the US war on terror continues in Afghanistan."),
    ("2003-05-01", "The US-led occupation of Iraq continues amid insurgent attacks; the Afghanistan war continues."),
    ("2004-03-11", "Terrorist bombings in Madrid on 11 March 2004 killed about 190 people; Iraq and Afghanistan wars continue."),
    ("2004-04-04", "Heavy fighting in Fallujah and uprisings in parts of Iraq began in April 2004; Iraq and Afghanistan wars continue."),
    ("2004-05-01", WARS),
    ("2004-11-08", "A major US assault on Fallujah took place in November 2004; Iraq and Afghanistan wars continue."),
    ("2005-01-30", "Iraq held national elections on 30 January 2005; Iraq and Afghanistan wars continue."),
    ("2005-05-01", WARS),
    ("2005-10-01", "Iraq and Afghanistan wars continue; tensions over Iran's nuclear program are rising."),
    ("2006-02-22", "The Iraq war continues amid rising sectarian violence after the bombing of a major mosque in Samarra on 22 February 2006; Iran's nuclear program has been referred to the UN Security Council."),
    ("2006-08-14", "A ceasefire ended the Israel-Hezbollah war in August 2006; the Iraq war continues amid sectarian violence; Iran's nuclear program is under UN Security Council review."),
    ("2006-10-09", "North Korea conducted a nuclear test on 9 October 2006; the Iraq war continues with a US troop surge under way from early 2007; Iran nuclear tensions persist."),
    ("2008-01-01", WARS),
    ("2008-08-12", "The Russia-Georgia war of August 2008 ended in a ceasefire but tensions remain; Iraq and Afghanistan wars continue."),
    ("2008-12-27", "Terrorist attacks in Mumbai in late November 2008 raised India-Pakistan tensions; Israel launched an offensive in Gaza on 27 December 2008; Iraq and Afghanistan wars continue."),
    ("2009-01-18", "A ceasefire ended Israel's Gaza offensive in January 2009; Iraq and Afghanistan wars continue."),
    ("2009-02-17", "The US announced a troop increase for Afghanistan on 17 February 2009; Iraq and Afghanistan wars continue."),
    ("2010-03-26", "A South Korean navy ship sank on 26 March 2010 and the cause is under investigation; Iraq and Afghanistan wars continue."),
    ("2010-05-20", "An international investigation found North Korea responsible for sinking a South Korean navy ship; tensions on the Korean peninsula are elevated; Iraq and Afghanistan wars continue."),
    ("2012-01-01", "The Syrian civil war is ongoing and Iran nuclear tensions persist."),
    ("2012-11-21", "A ceasefire ended an eight-day Israel-Gaza conflict in November 2012; the Syrian civil war continues; Iran nuclear tensions persist."),
    ("2013-02-12", "The Syrian civil war continues; North Korea conducted a nuclear test in February 2013."),
    ("2013-09-14", "A chemical weapons attack near Damascus in August 2013 prompted threats of US strikes; a September 2013 agreement on Syria's chemical weapons averted them; the Syrian civil war continues."),
    ("2013-11-24", "An interim nuclear deal with Iran was signed on 24 November 2013; the Syrian civil war continues."),
    ("2014-03-18", "Russia annexed Crimea in March 2014; the Syrian civil war continues."),
    ("2014-09-23", "The conflict in eastern Ukraine and the Syrian civil war continue; a US-led coalition is conducting air strikes against ISIS in Iraq and Syria."),
    ("2015-11-13", "Terrorist attacks in Paris on 13 November 2015 killed 130 people; the Syrian civil war continues, with Russia and a US-led coalition conducting air strikes; Europe faces a large inflow of refugees."),
    ("2016-07-15", "The UK voted to leave the European Union on 23 June 2016; a coup attempt took place in Turkey on 15 July 2016; the Syrian civil war continues."),
    ("2016-12-22", "The Syrian civil war continues, with Aleppo recaptured by Syrian government forces in December 2016."),
    ("2017-02-12", "The Syrian civil war continues; North Korea test-fired a missile on 12 February 2017."),
    ("2017-04-07", "The US launched missile strikes on a Syrian air base on 7 April 2017; North Korea has test-fired missiles; the Syrian civil war continues."),
    ("2018-10-02", "Journalist Jamal Khashoggi disappeared at the Saudi consulate in Istanbul on 2 October 2018, straining US-Saudi relations; the Syrian civil war continues."),
    ("2018-12-01", "The arrest of Huawei's CFO in Canada on 1 December 2018 has heightened US-China tensions; the Syrian civil war continues."),
    ("2019-02-14", "A suicide attack in Kashmir on 14 February 2019 sharply raised India-Pakistan tensions; the Syrian civil war continues."),
    ("2019-06-13", "Tensions with Iran in the Gulf are rising after attacks on oil tankers in May and June 2019; large protests are under way in Hong Kong."),
    ("2019-10-09", "Protests in Hong Kong are ongoing; Turkey launched an offensive in northern Syria in October 2019; US-Iran tensions persist."),
    ("2020-03-11", "COVID-19 was declared a pandemic by the WHO on 11 March 2020; widespread lockdowns are in force; an oil price war between Saudi Arabia and Russia began in March 2020."),
    ("2020-04-12", "COVID-19 was declared a pandemic by the WHO on 11 March 2020; widespread lockdowns are in force; Saudi Arabia, Russia and other producers agreed an oil output cut on 12 April 2020."),
    ("2020-11-09", "The COVID-19 pandemic continues, with the first vaccines being approved; no new major armed conflict reported."),
    ("2021-01-01", "The COVID-19 pandemic continues with vaccination under way; no new major armed conflict reported."),
    ("2021-05-21", "A ceasefire ended 11 days of Israel-Hamas fighting in May 2021; the COVID-19 pandemic continues."),
    ("2021-07-01", "The COVID-19 pandemic continues; the US withdrawal from Afghanistan is under way."),
    ("2021-08-15", "The Taliban took control of Afghanistan in August 2021 after the US withdrawal; Russia has massed troops near Ukraine's border; the COVID-19 pandemic continues."),
    ("2022-02-24", "Russia invaded Ukraine on 24 February 2022; Western countries are responding with sanctions and military aid to Ukraine."),
    ("2022-02-25", "The Russia-Ukraine war, ongoing since 24 February 2022, continues; energy and grain supply disruptions continue."),
    ("2023-11-19", "The Israel-Hamas war, which began on 7 October 2023, and the Russia-Ukraine war continue; Houthi attacks on Red Sea shipping continue."),
    ("2025-01-19", "A ceasefire in the Israel-Gaza war took effect on 19 January 2025; the Russia-Ukraine war continues."),
    ("2025-03-18", "The Russia-Ukraine war continues, with US-led ceasefire talks under way; the Israel-Gaza ceasefire broke down on 18 March 2025 with renewed Israeli strikes."),
]

DATES_PATH = os.path.join(HERE, "backtest_v4_dates.json")
V4_DESC_PATH = os.path.join(HERE, "backtest_v4_descriptions.json")
RESULTS_PATH = os.path.join(HERE, "backtest_v5_results.json")
TEXTS_PATH = os.path.join(HERE, "backtest_v5_news_texts.json")


def pick(timeline, date):
    return [t for s, t in timeline if s <= date][-1]


def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, obj):
    json.dump(obj, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)


def main():
    t0 = time.time()
    dates, v4 = load_json(DATES_PATH, []), load_json(V4_DESC_PATH, {})
    results = load_json(RESULTS_PATH, {})
    texts = {d["date"]: {"tariff_sanctions": pick(TARIFF, d["date"]), "geopolitical_risk": pick(GEO, d["date"])} for d in dates}
    save_json(TEXTS_PATH, texts)
    for item in dates:
        date, label = item["date"], item["label"]
        if date in results or date not in v4:
            continue
        descs = dict(v4[date]["descriptions"])
        descs.update(texts[date])
        with ThreadPoolExecutor(max_workers=7) as ex:
            pairs = list(ex.map(_score_one, descs.items()))
        results[date] = {"date": date, "label": label, "factor_scores": dict(pairs)}
        save_json(RESULTS_PATH, results)
        failed = [k for k, v in pairs if v is None]
        print(f"[{len(results)}/{len(dates)}] {date} {label} scored ({time.time() - t0:.0f}s){' FAILED: ' + str(failed) if failed else ''}", flush=True)
    print(f"DONE in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
