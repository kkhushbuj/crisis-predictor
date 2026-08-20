import streamlit as st
import os

st.set_page_config(
    page_title="CrisisPredictor - AI Financial Crisis Early-Warning",
    page_icon="warning",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #F7F7F5 !important;
}

div[data-testid="stPageLink"] {
    position: fixed !important;
    top: 20px !important;
    right: 48px !important;
    z-index: 99999 !important;
    width: auto !important;
    height: auto !important;
    display: block !important;
}
div[data-testid="stPageLink"] * {
    width: auto !important;
    height: auto !important;
    min-height: 0 !important;
    max-width: none !important;
    flex: none !important;
    align-items: center !important;
}
div[data-testid="stPageLink"] a {
    background: #1A1A18 !important;
    color: #FFFFFF !important;
    opacity: 1 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 18px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    text-decoration: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}
div[data-testid="stPageLink"] a span,
div[data-testid="stPageLink"] a p {
    color: #FFFFFF !important;
    opacity: 1 !important;
}
[data-testid="stPageLink"] a:hover {
    background: #333330 !important;
}
[data-testid="stPageLink"] svg { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.page_link("pages/analysis.py", label="Get Started ->")

landing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

iframe_fixes = """
<style>
#welcomeModal { display: none !important; }
body { background: #F7F7F5 !important; }
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

st.components.v1.html(html_content, height=1600, scrolling=True, width=None)