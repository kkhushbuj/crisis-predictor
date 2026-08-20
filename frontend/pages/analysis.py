"""
frontend/pages/analysis.py — CrisisPredictor Dashboard
Sidebar + SQLite history + streaming per-node factor cards + toggle animation + ticker + chatbot.
Light theme.
"""

import os
import sys
import time
import sqlite3
import json
from zoneinfo import ZoneInfo
from datetime import datetime

UK_TZ = ZoneInfo("Europe/London")

def uk_time_str():
    return datetime.now(UK_TZ).strftime("%Y-%m-%d %H:%M")

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from dotenv import load_dotenv

from graph.crisis_graph import app
from tools.scoring_tools import FACTOR_LABELS, CATEGORY_FACTORS

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))


def get_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'crisis_checkpoints.db')


def init_history_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            strength TEXT,
            timestamp TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_history(status, strength, timestamp, result):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO analysis_history (status, strength, timestamp, result_json) VALUES (?, ?, ?, ?)",
        (status, strength, timestamp, json.dumps(result))
    )
    conn.commit()
    conn.close()


def load_history(limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT id, status, strength, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "status": r[1], "strength": r[2], "time": r[3]} for r in rows]


def load_history_detail(history_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute("SELECT result_json FROM analysis_history WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


init_history_table()

st.set_page_config(page_title="CrisisPredictor", page_icon="⚠️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
[data-testid="stSidebarNav"] { display: none !important; }
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #F7F7F5 !important;
    font-family: 'Inter', sans-serif !important;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding: 24px 32px 60px !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E4E4E0 !important;
    min-width: 240px !important; max-width: 240px !important;
    transform: none !important;
    visibility: visible !important;
}
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebar"] * { color: #1A1A18 !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 500 !important;
    border-radius: 8px !important; border: 1px solid #DDDCD6 !important;
    background: #FFFFFF !important; color: #1A1A18 !important;
}
.stButton > button:hover { background: #F0F0EC !important; }

.semi-card {
    background: #FFFFFF; border: 1px solid #E4E4E0;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 8px;
}
.card-key {
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.06em; color: #6B6A63; margin-bottom: 5px;
}
.card-val { font-size: 0.85rem; color: #2C2C28; line-height: 1.5; }

.sec-label {
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: #6B6A63; margin: 20px 0 10px;
    display: flex; align-items: center; gap: 8px;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: #E4E4E0; }

.metric-card { background: #FFFFFF; border: 1px solid #E4E4E0; border-radius: 12px; padding: 20px; text-align: center; }
.metric-num-on { font-size: 1.8rem; font-weight: 600; color: #C0392B; }
.metric-num-off { font-size: 1.8rem; font-weight: 600; color: #1E8449; }
.metric-lbl { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #999; margin-bottom: 8px; }
.bar-track { height: 5px; background: #EDEDE8; border-radius: 3px; margin-top: 10px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; background: #1A1A18; }

.toggle-switch{
    width:64px;height:32px;border-radius:16px;
    position:relative;margin:0 auto;
    transition:background 0.3s ease;
}
.toggle-on{background:#C0392B;box-shadow:none;}
.toggle-off{background:#1E8449;box-shadow:none;}
.toggle-flip{background:#C0392B;animation:toggle-flicker 1s ease-in-out infinite;}
@keyframes toggle-flicker{
    0%,100%{background:#1E8449;}
    50%{background:#C0392B;}
}
.toggle-knob{
    width:26px;height:26px;border-radius:50%;
    background:#FFFFFF;position:absolute;top:3px;
    box-shadow:0 1px 3px rgba(0,0,0,0.2);
    transition:left 0.3s ease;
}
.toggle-on .toggle-knob{left:35px;}
.toggle-off .toggle-knob{left:3px;}
.toggle-flip .toggle-knob{animation:knob-slide 1s ease-in-out infinite;}
@keyframes knob-slide{
    0%,100%{left:3px;}
    50%{left:35px;}
}

.hero-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px 20px; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: #F0F0EC; border: 1px solid #DDDCD6;
    border-radius: 20px; padding: 5px 14px; font-size: 10.5px; font-weight: 600;
    color: #6B6A63; margin-bottom: 20px; letter-spacing: 0.05em;
}
.bdot { width: 7px; height: 7px; border-radius: 50%; background: #C0392B; animation: blink 1.8s ease-in-out infinite; display: inline-block; }
@keyframes blink { 0%,100%{opacity:0.3;} 50%{opacity:1;} }
.crisis-icon { font-size: 60px; margin-bottom: 10px; }
.hero-greeting { font-size: 1.6rem; font-weight: 600; color: #1A1A18; margin-bottom: 8px; text-align: center; }
.hero-greeting em { font-style: normal; color: #C0392B; }
.hero-sub { font-size: 0.85rem; color: #6B6A63; margin-bottom: 20px; text-align: center; line-height: 1.7; max-width: 600px; }

.reasoning-card {
    background: #F7F7F5; border-left: 2px solid #C0392B;
    border-radius: 0 10px 10px 0; padding: 12px 16px;
    font-size: 0.85rem; color: #2C2C28; line-height: 1.75; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


def smart_truncate(text, limit: int = 1200) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 80]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 80)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."


def score_badge(key, scores):
    score = scores.get(key)
    if score is None:
        return ""
    if score > 0:
        color, label = "#1E8449", "Bullish"
    elif score < 0:
        color, label = "#C0392B", "Bearish"
    else:
        color, label = "#888", "Neutral"
    sign = "+" if score > 0 else ""
    return f"<div style='margin-top:6px;font-size:0.75rem;font-weight:600'><span style='color:#888'>Score: </span><span style='color:{color}'>{sign}{score}</span><span style='color:{color}'>&nbsp;&nbsp;{label}</span></div>"


if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{int(time.time())}"

with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
        <div style='width:32px;height:32px;border-radius:8px;background:#F0F0EC;border:1px solid #DDDCD6;display:flex;align-items:center;justify-content:center;font-size:15px'>⚠️</div>
        <span style='font-size:16px;font-weight:600;color:#1A1A18'>CrisisPredictor</span>
    </div>
    <div style='font-size:0.72rem;color:#6B6A63;margin-bottom:18px'>14-Factor Crisis Early-Warning</div>
    """, unsafe_allow_html=True)

    st.page_link("app.py", label="Home", use_container_width=True)

    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.result = None
        st.rerun()

    st.markdown("<hr style='border-color:#E4E4E0;margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#6B6A63;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>HISTORY</div>", unsafe_allow_html=True)

    if st.session_state.history:
        for item in st.session_state.history[:10]:
            label = f"{item['status']}  {item.get('strength','?')}  {item['time']}"
            if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                result_r = load_history_detail(item['id'])
                if result_r is not None:
                    st.session_state.result = result_r
                    st.rerun()


if not st.session_state.result:
    st.markdown(f"""
    <div class='hero-wrap'>
        <div class='hero-badge'><span class='bdot'></span> LIVE · 14-Factor Crisis Analysis</div>
        <div class='crisis-icon'>⚠️</div>
        <div class='hero-greeting'>Hi! I am <em>CrisisPredictor</em></div>
        <div class='hero-sub'>
            AI-powered financial crisis early-warning system · 14 real-time factors<br>
            Credit/Systemic · Liquidity/Shock · Macro · Geopolitical
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style='padding:0 0 12px'>
        <div style='font-size:1.3rem;font-weight:600;color:#1A1A18;margin-bottom:4px'>
            Financial Crisis Analysis
        </div>
        <div style='font-size:0.75rem;color:#6B6A63'>14-Factor Agentic RAG · Real-time APIs</div>
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.result:
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("<div style='padding-top:60px;text-align:center'>", unsafe_allow_html=True)
        analyse = st.button("Run Analysis →", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if analyse:
        st.session_state.thread_id = f"session_{int(time.time())}"

        progress_bar = st.progress(0, text="Starting analysis...")
        ph_credit = st.empty()
        ph_liquidity = st.empty()
        ph_macro = st.empty()
        ph_geo = st.empty()

        def make_cards(data, factor_keys, label):
            html = f"<div class='sec-label'>{label}</div>"
            for fk in factor_keys:
                val = smart_truncate(data.get(fk, "Loading..."))
                html += f"<div class='semi-card'><div class='card-key'>{FACTOR_LABELS[fk]}</div><div class='card-val'>{val}</div></div>"
            return html

        result = {}
        nodes_done = 0
        total_nodes = 5

        try:
            for chunk in app.stream(
                {},
                config={"configurable": {"thread_id": st.session_state.thread_id}},
                stream_mode="updates"
            ):
                for node_name, node_data in chunk.items():
                    for k, v in node_data.items():
                        if v:
                            result[k] = v
                    nodes_done += 1
                    pct = int((nodes_done / total_nodes) * 100)

                    if node_name == "fetch_credit_systemic":
                        progress_bar.progress(pct, text="Credit/Systemic factors loaded")
                        ph_credit.markdown(make_cards(result, CATEGORY_FACTORS["credit_systemic"], "Credit/Systemic"), unsafe_allow_html=True)

                    elif node_name == "fetch_liquidity_shock":
                        progress_bar.progress(pct, text="Liquidity/Shock factors loaded")
                        ph_liquidity.markdown(make_cards(result, CATEGORY_FACTORS["liquidity_shock"], "Liquidity/Shock"), unsafe_allow_html=True)

                    elif node_name == "fetch_macro":
                        progress_bar.progress(pct, text="Macro factors loaded")
                        ph_macro.markdown(make_cards(result, CATEGORY_FACTORS["macro"], "Macro"), unsafe_allow_html=True)

                    elif node_name == "fetch_geopolitical":
                        progress_bar.progress(pct, text="Geopolitical signals loaded")
                        ph_geo.markdown(make_cards(result, CATEGORY_FACTORS["geopolitical"], "Geopolitical"), unsafe_allow_html=True)

                    elif node_name == "generate_prediction":
                        progress_bar.progress(100, text="Prediction complete")

            progress_bar.empty()
            st.session_state.result = result

            pred_text = result.get("prediction", "")
            status_hist = "OFF"
            strength_hist = "0%"
            for line in pred_text.split("\n"):
                if "CRISIS_STATUS:" in line:
                    status_hist = line.split(":")[-1].strip()
                if "STRENGTH:" in line:
                    strength_hist = line.split(":")[-1].strip()

            save_history(status_hist, strength_hist, uk_time_str(), result)
            st.session_state.history = load_history()
            st.rerun()

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

if st.session_state.result:
    result = st.session_state.result
    prediction = result.get("prediction", "")
    scores = result.get("scores", {})

    status = "OFF"
    strength = 0
    reasoning_text = ""
    confidence = "Medium"
    bullish = []
    bearish = []

    for line in prediction.split("\n"):
        line = line.strip()
        if "CRISIS_STATUS:" in line:
            status = line.split(":")[-1].strip()
        elif "STRENGTH:" in line:
            try: strength = int(float(line.split(":")[-1].strip().replace("%", "")))
            except: pass
        elif "REASONING:" in line:
            reasoning_text = line.replace("REASONING:", "").strip()
        elif "CONFIDENCE:" in line:
            confidence = line.replace("CONFIDENCE:", "").strip()
        elif "BULLISH_FACTORS:" in line:
            bullish = [x.strip() for x in line.replace("BULLISH_FACTORS:", "").split("|") if x.strip()]
        elif "BEARISH_FACTORS:" in line:
            bearish = [x.strip() for x in line.replace("BEARISH_FACTORS:", "").split("|") if x.strip()]

    st.markdown("<div>", unsafe_allow_html=True)

    for category, cat_label in [("credit_systemic", "Credit/Systemic"), ("liquidity_shock", "Liquidity/Shock"),
                                  ("macro", "Macro"), ("geopolitical", "Geopolitical")]:
        st.markdown(f"<div class='sec-label'>{cat_label}</div>", unsafe_allow_html=True)
        for fk in CATEGORY_FACTORS[category]:
            st.markdown(f"<div class='semi-card'><div class='card-key'>{FACTOR_LABELS[fk]}</div><div class='card-val'>{smart_truncate(result.get(fk,'N/A'))}</div>{score_badge(fk, scores)}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#E4E4E0;margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1rem;font-weight:600;color:#1A1A18;margin-bottom:14px'>Prediction</div>", unsafe_allow_html=True)

    p1, p2 = st.columns([1.2, 2.6])
    with p1:
        toggle_class = "toggle-on" if status == "ON" else "toggle-off"
        status_class = "metric-num-on" if status == "ON" else "metric-num-off"
        toggle_placeholder = st.empty()
        result_key = str(result.get("prediction", ""))[:50]
        if st.session_state.get("last_animated_result") != result_key:
            toggle_placeholder.markdown("""
            <div class='metric-card'>
                <div class='metric-lbl'>Crisis Status</div>
                <div class='toggle-switch toggle-flip'><div class='toggle-knob'></div></div>
                <div class='metric-lbl' style='margin-top:8px;color:#999'>Calculating...</div>
            </div>""", unsafe_allow_html=True)
            time.sleep(5)
            st.session_state.last_animated_result = result_key
        toggle_placeholder.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Crisis Status</div>
            <div class='toggle-switch {toggle_class}'><div class='toggle-knob'></div></div>
            <div class='{status_class}' style='margin-top:8px'>{status}</div>
            <div class='metric-lbl' style='margin-top:10px'>Strength: {strength}%</div>
            <div class='bar-track'><div class='bar-fill' style='width:{strength}%'></div></div>
        </div>""", unsafe_allow_html=True)
    with p2:
        bullish_html = "".join([f"<div style='font-size:0.8rem;color:#1E8449;margin-bottom:4px'>+ {b}</div>" for b in bullish[:3]])
        bearish_html = "".join([f"<div style='font-size:0.8rem;color:#C0392B;margin-bottom:4px'>- {b}</div>" for b in bearish[:3]])
        st.markdown(f"""
        <div class='metric-card' style='text-align:left'>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px'>
                <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bullish (Stabilizing)</div>{bullish_html}</div>
                <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bearish (Destabilizing)</div>{bearish_html}</div>
            </div>
            <div style='margin-top:12px;font-size:0.7rem;color:#888'>Confidence: <strong style='color:#C0392B'>{confidence}</strong></div>
        </div>""", unsafe_allow_html=True)

    if reasoning_text:
        st.markdown(f"<div class='reasoning-card'>{reasoning_text}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#E4E4E0;margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1rem;font-weight:600;color:#1A1A18;margin-bottom:6px'>Ask a follow-up question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem;color:#6B6A63;margin-bottom:14px'>Ask about factors, crisis patterns, or how CrisisPredictor works</div>", unsafe_allow_html=True)

    if "followup_history" not in st.session_state:
        st.session_state.followup_history = []

    for qa in st.session_state.followup_history:
        st.markdown(f"<div style='background:#F7F7F5;border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:0.8rem;color:#2C2C28'><strong style='color:#C0392B'>You:</strong> {qa['q']}<br><strong style='color:#C0392B'>CrisisPredictor:</strong> {qa['a']}</div>", unsafe_allow_html=True)

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        followup_q = st.text_input("Question", placeholder="e.g. Why is geopolitical risk elevated? What would push this into Crisis?", label_visibility="collapsed", key="followup_input")
    with q_col2:
        ask_clicked = st.button("Ask →", use_container_width=True)

    if ask_clicked and followup_q.strip():
        from langchain_openai import ChatOpenAI
        followup_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        context = f"""You are CrisisPredictor's assistant. You ONLY answer questions about:
- The current crisis analysis and its factor scores
- How CrisisPredictor works (its 14 factors, methodology, data sources)
- General financial/economic concepts directly relevant to interpreting this analysis

If the user asks something unrelated to crisis analysis, financial markets, or how this tool works
(e.g. general trivia, unrelated current events, personal questions), politely decline and redirect
them back to asking about the crisis analysis instead. Do not answer unrelated questions.

Current crisis analysis:
{prediction}

User question: {followup_q.strip()}

Answer concisely and precisely, referencing the actual factor scores above where relevant."""
        with st.spinner("Thinking..."):
            answer = followup_llm.invoke(context)
        st.session_state.followup_history.append({"q": followup_q.strip(), "a": answer.content})
        st.rerun()

    st.markdown("""
    <div style='background:#FDF2F2;border:1px solid #F0D0D0;border-radius:10px;padding:11px 15px;font-size:0.72rem;color:#C0392B;line-height:1.6;margin-top:18px'>
        Warning: This analysis is generated by an AI research tool for informational and academic purposes only.
        It does NOT constitute financial advice. Always consult a qualified financial advisor.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def one_word_signal(score):
    if score is None:
        return "N/A"
    if score > 3:
        return "Bullish"
    elif score > 0:
        return "Mild+"
    elif score < -3:
        return "Bearish"
    elif score < 0:
        return "Mild-"
    else:
        return "Neutral"


@st.cache_data(ttl=900)
def get_ticker_data(scores_snapshot):
    factor_labels = list(FACTOR_LABELS.items())

    def signal_color(signal):
        if signal in ("Bullish", "Mild+"):
            return "#1E8449"
        elif signal in ("Bearish", "Mild-"):
            return "#C0392B"
        else:
            return "#6B6A63"

    factor_html = ""
    for key, label in factor_labels:
        score_val = scores_snapshot.get(key)
        signal = one_word_signal(score_val)
        color = signal_color(signal)
        factor_html += f"<span style='margin-right:32px'><strong style='color:#1A1A18'>{label}</strong> <span style='color:{color};font-weight:600'>{signal}</span></span>"

    return factor_html


current_scores = st.session_state.result.get("scores", {}) if st.session_state.result else {}
ticker_html = get_ticker_data(current_scores)

st.markdown(f"""
<style>
.ticker-wrap {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #FFFFFF;
    border-top: 1px solid #E4E4E0;
    padding: 8px 0; overflow: hidden;
}}
.ticker-move {{
    display: inline-block; white-space: nowrap;
    animation: ticker-scroll 40s linear infinite;
    font-size: 0.78rem; font-family: 'Inter', sans-serif;
}}
@keyframes ticker-scroll {{
    0% {{ transform: translateX(100vw); }}
    100% {{ transform: translateX(-100%); }}
}}
</style>
<div class='ticker-wrap'>
    <div class='ticker-move'>{ticker_html}&nbsp;&nbsp;&nbsp;&nbsp;{ticker_html}</div>
</div>
""", unsafe_allow_html=True)