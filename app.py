import hashlib
import hmac
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from src.orbidense_router import render_site_router, EARLY_PUBLIC_CSS


from src.home_v2 import render_home_v2
from src.ui_v27 import (
    dark_dataframe,
    inject_v27_ui,
    style_plotly_v27,
)
from src.analytics import (
    capture_streamlit_context,
    ensure_analytics_database,
    get_analytics_summary,
    is_local_session,
    render_analytics_heartbeat,
    track_event_once,
    track_local_sessions_enabled,
    track_pageview,
    record_error,
    record_data_quality,
)
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox
from src.api.air_quality import get_current_air_quality
from src.api.current_weather import get_current_weather
from src.api.today_forecast import get_today_forecast
from src.api.home_environment import get_home_environment
from src.api.point_history import get_point_history
from src.api.future_climate import (
    CLIMATE_MODELS,
    get_midcentury_ensemble,
)
from src.api.country_rankings import (
    CCKP_PERIODS,
    CCKP_SCENARIOS,
    get_country_projection_rankings,
    get_country_scenario_trajectory,
)
from src.api.country_dashboard import (
    get_country_historical_climate,
)
from src.api.maptiler_search import search_maptiler_places
from src.queries.insights import get_today_climate_context
from src.profile import (
    BUILDER_BIO,
    BUILDER_HEADLINE,
    BUILDER_NAME,
    GITHUB_URL,
    LINKEDIN_URL,
    PORTFOLIO_URL,
    PROJECT_MOTIVATION,
    PROFILE_PHOTO_PATH,
)
from src.about_page import render_about_page
from src.home_page import (
    render_home_page,
    render_dashboard_page,
    render_climate_timeline_page,
)
from src.ai_assistant import (
    render_ai_page,
    render_persistent_ai,
)
from src.live_globe import cached_country_field
from src.climate_intelligence.pages import (
    render_country_climate_outlook,
    render_climate_action_progress,
)

from src.about_professional import render_professional_about
from src.intelligence_pages import (
    inject_intelligence_theme,
    render_climate_outlook,
    render_climate_action,
    render_compare,
    render_global_insights,
    render_climate_passport,
    render_about_science,
)

from src.queries.climate import (
    get_annual_climate_summary,
    get_city_details,
    get_climate_trend,
    get_temperature_anomalies,
)
from src.services.climate_service import (
    ensure_city_history,
    get_history_job_status,
)

load_dotenv()


def get_maptiler_key():
    try:
        if "MAPTILER_KEY" in st.secrets:
            return st.secrets["MAPTILER_KEY"]
    except Exception:
        pass
    return os.getenv("MAPTILER_KEY")


MAPTILER_KEY = get_maptiler_key()

# =========================================================
# ORBIDENSE — BRAND CONFIGURATION
# =========================================================

APP_NAME = "ORBIDENSE"
APP_TAGLINE = "Earth Data · Risk Intelligence · Better Decisions"
APP_SHORT_TAGLINE = "Earth Intelligence & Environmental Risk"
APP_LOGO_PATH = Path("assets/orbidense_logo.png")
APP_FAVICON_PATH = Path("assets/orbidense_favicon.png")


st.set_page_config(
    page_title=APP_NAME,
    page_icon=str(APP_FAVICON_PATH) if APP_FAVICON_PATH.exists() else (str(APP_LOGO_PATH) if APP_LOGO_PATH.exists() else "🌍"),
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(EARLY_PUBLIC_CSS, unsafe_allow_html=True)

# =========================================================
# ORBIDENSE — MOBILE RESPONSIVE PRESENTATION
# CSS only: no application logic is modified.
# =========================================================
st.markdown('\n<style>\n/* ORBIDENSE MOBILE OPTIMIZATION V1\n   Presentation only.\n   No routing, calculations, data, sessions, themes or APIs are changed.\n*/\n\n/* =========================================================\n   GLOBAL SAFETY\n   ========================================================= */\nhtml,\nbody,\n.stApp,\n[data-testid="stAppViewContainer"],\n[data-testid="stMain"],\n[data-testid="stMainBlockContainer"],\n.block-container {\n    box-sizing: border-box !important;\n    min-width: 0 !important;\n}\n\nimg,\nsvg,\ncanvas,\nvideo {\n    max-width: 100%;\n}\n\n/* =========================================================\n   TABLET\n   ========================================================= */\n@media (max-width: 1024px) {\n\n    [data-testid="stMainBlockContainer"],\n    .block-container {\n        width: 100% !important;\n        max-width: 100% !important;\n        padding-left: .85rem !important;\n        padding-right: .85rem !important;\n    }\n\n    /* Keep every chart/component inside the viewport. */\n    [data-testid="stPlotlyChart"],\n    [data-testid="stDataFrame"],\n    [data-testid="stTable"],\n    [data-testid="stIFrame"],\n    iframe {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n    }\n\n    /* Home hero signal must participate in document flow. */\n    .hf-signal {\n        position: relative !important;\n        top: auto !important;\n        right: auto !important;\n        width: 100% !important;\n        max-width: 100% !important;\n        margin-top: 1rem !important;\n    }\n\n    .hf-signal-grid,\n    .hf-metrics {\n        min-width: 0 !important;\n    }\n}\n\n\n/* =========================================================\n   PHONE / PORTRAIT\n   ========================================================= */\n@media (max-width: 760px) {\n\n    html,\n    body,\n    .stApp,\n    [data-testid="stAppViewContainer"],\n    [data-testid="stMain"] {\n        width: 100% !important;\n        max-width: 100vw !important;\n        overflow-x: hidden !important;\n    }\n\n    [data-testid="stMainBlockContainer"],\n    .block-container {\n        width: 100% !important;\n        max-width: 100vw !important;\n        padding: .30rem .82rem 1.25rem !important;\n        margin: 0 !important;\n        overflow-x: hidden !important;\n    }\n\n\n    /* =====================================================\n       HEADER + BRAND\n       Keep current navigation logic.\n       Turn desktop row into touch-friendly horizontal rail.\n       ===================================================== */\n\n    div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo) {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-height: 78px !important;\n        height: auto !important;\n\n        display: flex !important;\n        flex-wrap: nowrap !important;\n        align-items: center !important;\n\n        gap: .42rem !important;\n\n        overflow-x: auto !important;\n        overflow-y: hidden !important;\n\n        padding: .28rem .15rem .44rem !important;\n\n        scrollbar-width: none !important;\n        -webkit-overflow-scrolling: touch;\n        scroll-snap-type: x proximity;\n    }\n\n    div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo)::-webkit-scrollbar {\n        display: none !important;\n    }\n\n    div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo) > div {\n        flex: 0 0 auto !important;\n        width: auto !important;\n        min-width: 0 !important;\n        scroll-snap-align: start;\n    }\n\n    .orb-nav-logo {\n        width: 112px !important;\n        min-width: 112px !important;\n        height: 68px !important;\n        min-height: 68px !important;\n\n        display: flex !important;\n        align-items: center !important;\n        justify-content: flex-start !important;\n\n        overflow: hidden !important;\n    }\n\n    .orb-nav-logo img {\n        width: 108px !important;\n        max-width: 108px !important;\n        max-height: 66px !important;\n\n        object-fit: contain !important;\n        object-position: left center !important;\n\n        transform: none !important;\n    }\n\n    [class*="st-key-site_nav_"] {\n        width: auto !important;\n        min-width: 0 !important;\n    }\n\n    [class*="st-key-site_nav_"] button {\n        width: auto !important;\n        min-width: 102px !important;\n        height: 44px !important;\n        min-height: 44px !important;\n\n        padding: .38rem .72rem !important;\n\n        border-radius: 11px !important;\n\n        font-size: .70rem !important;\n        line-height: 1.08 !important;\n        white-space: nowrap !important;\n\n        touch-action: manipulation;\n    }\n\n    /* Theme remains reachable but compact. */\n    [class*="st-key-orbidense_theme"] {\n        width: 126px !important;\n        min-width: 126px !important;\n    }\n\n    [class*="st-key-orbidense_theme"]\n    [data-baseweb="select"] > div {\n        min-height: 44px !important;\n        height: 44px !important;\n        font-size: .72rem !important;\n    }\n\n\n    /* =====================================================\n       ZOOM CONTROL\n       Mobile already has browser/pinch zoom.\n       Remove desktop floating obstruction only on phones.\n       ===================================================== */\n\n    .st-key-orbidense_zoom_controls,\n    [class*="st-key-orbidense_zoom_controls"] {\n        display: none !important;\n        visibility: hidden !important;\n        pointer-events: none !important;\n    }\n\n\n    /* =====================================================\n       STREAMLIT COLUMNS\n       Desktop code stays unchanged.\n       Reflow ordinary page columns vertically on phones.\n       Header/navigation row above is explicitly excluded.\n       ===================================================== */\n\n    div[data-testid="stHorizontalBlock"]:not(:has(.orb-nav-logo)) {\n        display: flex !important;\n        flex-direction: column !important;\n        flex-wrap: nowrap !important;\n        width: 100% !important;\n        gap: .68rem !important;\n    }\n\n    div[data-testid="stHorizontalBlock"]:not(:has(.orb-nav-logo)) > div {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n        flex: 1 1 100% !important;\n    }\n\n\n    /* =====================================================\n       HOME HERO\n       ===================================================== */\n\n    .home-final-hero {\n        width: 100% !important;\n        max-width: 100% !important;\n\n        min-height: auto !important;\n\n        padding: 1.18rem 1rem 8.9rem !important;\n        margin: 0 !important;\n\n        border-radius: 16px !important;\n\n        background-size:\n            auto,\n            132% auto,\n            auto,\n            auto !important;\n\n        background-position:\n            center,\n            center bottom,\n            center,\n            center !important;\n\n        overflow: hidden !important;\n    }\n\n    .hf-kicker {\n        max-width: 100% !important;\n\n        font-size: .60rem !important;\n        line-height: 1.35 !important;\n        letter-spacing: .105em !important;\n\n        white-space: normal !important;\n        overflow-wrap: anywhere !important;\n    }\n\n    .hf-title {\n        width: 100% !important;\n        max-width: 100% !important;\n\n        margin: .55rem 0 .75rem !important;\n\n        font-size: clamp(1.95rem, 9.1vw, 2.55rem) !important;\n        line-height: 1.04 !important;\n        letter-spacing: -.035em !important;\n\n        white-space: normal !important;\n        overflow-wrap: normal !important;\n        word-break: normal !important;\n    }\n\n    .hf-copy {\n        width: 100% !important;\n        max-width: 100% !important;\n\n        font-size: .89rem !important;\n        line-height: 1.52 !important;\n\n        overflow-wrap: anywhere !important;\n    }\n\n    .hf-signal {\n        position: relative !important;\n        inset: auto !important;\n\n        width: 100% !important;\n        max-width: 100% !important;\n\n        margin: 1rem 0 0 !important;\n        padding: .90rem !important;\n\n        border-radius: 14px !important;\n\n        backdrop-filter: blur(9px) !important;\n    }\n\n    .hf-signal h4 {\n        font-size: .90rem !important;\n    }\n\n    .hf-signal-sub {\n        margin-bottom: .72rem !important;\n        font-size: .64rem !important;\n    }\n\n    .hf-signal-grid {\n        display: grid !important;\n        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;\n        gap: .58rem !important;\n\n        width: 100% !important;\n        min-width: 0 !important;\n    }\n\n    .hf-signal-card {\n        width: 100% !important;\n        min-width: 0 !important;\n\n        padding: .76rem !important;\n        border-radius: 11px !important;\n    }\n\n    .hf-signal-card .v {\n        font-size: 1.05rem !important;\n    }\n\n    .hf-signal-card .l {\n        font-size: .62rem !important;\n        line-height: 1.38 !important;\n        overflow-wrap: anywhere !important;\n    }\n\n\n    /* Home metric strip */\n    .hf-metrics {\n        width: 100% !important;\n\n        display: grid !important;\n        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;\n\n        border-radius: 14px !important;\n\n        overflow: hidden !important;\n    }\n\n    .hf-metric {\n        min-width: 0 !important;\n        min-height: 68px !important;\n\n        padding: .78rem !important;\n\n        border-right: 0 !important;\n        border-bottom: 1px solid rgba(71,159,202,.12) !important;\n    }\n\n    .hf-metric:last-child {\n        grid-column: 1 / -1 !important;\n    }\n\n    .hf-metric .v {\n        font-size: 1.10rem !important;\n    }\n\n    .hf-metric .l {\n        font-size: .62rem !important;\n    }\n\n\n    /* =====================================================\n       HOME PANELS / QUESTION CARDS\n       ===================================================== */\n\n    .hf-panel,\n    .hf-question {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n\n        height: auto !important;\n\n        padding: .9rem !important;\n        border-radius: 14px !important;\n    }\n\n    .hf-hot {\n        grid-template-columns: 24px minmax(0,1fr) auto !important;\n        gap: .50rem !important;\n    }\n\n    .hf-place,\n    .hf-val,\n    .hf-note,\n    .hf-question .c {\n        overflow-wrap: anywhere !important;\n    }\n\n\n    /* =====================================================\n       GENERIC ORBIDENSE INTELLIGENCE PANELS\n       ===================================================== */\n\n    .orb-hero,\n    .orb-card,\n    .orb-panel,\n    .orb-context-bar,\n    .orb-trust-strip,\n    .orb-section,\n    .orb-kpi,\n    .orb-insight-card {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n        box-sizing: border-box !important;\n    }\n\n    .orb-hero {\n        padding: 1rem !important;\n        border-radius: 15px !important;\n    }\n\n    .orb-section-title {\n        font-size: clamp(1.18rem, 6vw, 1.55rem) !important;\n        line-height: 1.12 !important;\n        overflow-wrap: anywhere !important;\n    }\n\n    .orb-sub {\n        font-size: .82rem !important;\n        line-height: 1.48 !important;\n    }\n\n    .orb-context-bar {\n        display: grid !important;\n        grid-template-columns: repeat(2, minmax(0,1fr)) !important;\n        gap: .45rem !important;\n    }\n\n    .orb-context-cell {\n        min-width: 0 !important;\n    }\n\n    .orb-context-value {\n        white-space: normal !important;\n        overflow-wrap: anywhere !important;\n    }\n\n\n    /* =====================================================\n       INPUTS / SELECTS / BUTTONS\n       ===================================================== */\n\n    [data-baseweb="select"],\n    [data-baseweb="input"],\n    [data-baseweb="base-input"],\n    [data-testid="stTextInput"],\n    [data-testid="stSelectbox"] {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n    }\n\n    .stButton,\n    .stButton > button {\n        max-width: 100% !important;\n    }\n\n    .stButton > button {\n        min-height: 44px !important;\n        border-radius: 11px !important;\n        white-space: normal !important;\n        line-height: 1.15 !important;\n        touch-action: manipulation;\n    }\n\n\n    /* =====================================================\n       TABS + SEGMENTED CONTROLS\n       Never crush them into unreadable labels.\n       ===================================================== */\n\n    [data-baseweb="tab-list"],\n    [role="tablist"] {\n        display: flex !important;\n        flex-wrap: nowrap !important;\n\n        width: 100% !important;\n\n        overflow-x: auto !important;\n        overflow-y: hidden !important;\n\n        scrollbar-width: none !important;\n        -webkit-overflow-scrolling: touch;\n    }\n\n    [data-baseweb="tab-list"]::-webkit-scrollbar,\n    [role="tablist"]::-webkit-scrollbar {\n        display: none !important;\n    }\n\n    [role="tab"] {\n        flex: 0 0 auto !important;\n        min-width: max-content !important;\n\n        padding-left: .80rem !important;\n        padding-right: .80rem !important;\n\n        white-space: nowrap !important;\n    }\n\n\n    /* =====================================================\n       CHARTS / MAPS / DATA\n       ===================================================== */\n\n    [data-testid="stPlotlyChart"],\n    [data-testid="stIFrame"],\n    iframe,\n    .js-plotly-plot,\n    .plot-container,\n    .svg-container {\n        width: 100% !important;\n        max-width: 100% !important;\n        min-width: 0 !important;\n    }\n\n    [data-testid="stDataFrame"],\n    [data-testid="stTable"] {\n        width: 100% !important;\n        max-width: 100% !important;\n\n        overflow-x: auto !important;\n        -webkit-overflow-scrolling: touch;\n    }\n\n\n    /* =====================================================\n       TYPOGRAPHY\n       ===================================================== */\n\n    h1 {\n        font-size: clamp(1.75rem, 8vw, 2.30rem) !important;\n        line-height: 1.08 !important;\n    }\n\n    h2 {\n        font-size: clamp(1.38rem, 6.8vw, 1.82rem) !important;\n        line-height: 1.12 !important;\n    }\n\n    h3 {\n        font-size: clamp(1.08rem, 5vw, 1.35rem) !important;\n        line-height: 1.18 !important;\n    }\n\n    p,\n    li,\n    label {\n        overflow-wrap: anywhere;\n    }\n\n\n    /* =====================================================\n       FLOATING CONTROLS\n       ===================================================== */\n\n    .hf-back {\n        right: .80rem !important;\n        bottom: .90rem !important;\n    }\n\n    .hf-back a {\n        width: 42px !important;\n        height: 42px !important;\n        font-size: 1.12rem !important;\n    }\n\n\n    /* =====================================================\n       STREAMLIT TOOLBAR\n       Keep it out of content.\n       ===================================================== */\n\n    [data-testid="stToolbar"] {\n        transform: scale(.86);\n        transform-origin: top right;\n    }\n}\n\n\n/* =========================================================\n   VERY SMALL PHONES\n   ========================================================= */\n@media (max-width: 430px) {\n\n    [data-testid="stMainBlockContainer"],\n    .block-container {\n        padding-left: .68rem !important;\n        padding-right: .68rem !important;\n    }\n\n    .orb-nav-logo {\n        width: 98px !important;\n        min-width: 98px !important;\n    }\n\n    .orb-nav-logo img {\n        width: 94px !important;\n        max-width: 94px !important;\n    }\n\n    [class*="st-key-site_nav_"] button {\n        min-width: 94px !important;\n        padding-left: .58rem !important;\n        padding-right: .58rem !important;\n        font-size: .67rem !important;\n    }\n\n    [class*="st-key-orbidense_theme"] {\n        width: 118px !important;\n        min-width: 118px !important;\n    }\n\n    .home-final-hero {\n        padding-left: .86rem !important;\n        padding-right: .86rem !important;\n        padding-bottom: 8.2rem !important;\n    }\n\n    .hf-title {\n        font-size: clamp(1.78rem, 9.4vw, 2.20rem) !important;\n    }\n\n    .hf-copy {\n        font-size: .84rem !important;\n    }\n\n    .hf-signal {\n        padding: .78rem !important;\n    }\n\n    .hf-signal-card {\n        padding: .67rem !important;\n    }\n\n    .hf-signal-card .v {\n        font-size: .98rem !important;\n    }\n\n    .hf-signal-card .l {\n        font-size: .58rem !important;\n    }\n\n    .orb-context-bar {\n        grid-template-columns: 1fr !important;\n    }\n}\n\n\n/* =========================================================\n   LANDSCAPE PHONE\n   ========================================================= */\n@media (max-width: 900px) and (orientation: landscape) {\n\n    .home-final-hero {\n        padding-bottom: 4.6rem !important;\n    }\n\n    .hf-signal-grid {\n        grid-template-columns: repeat(4, minmax(0,1fr)) !important;\n    }\n}\n</style>\n', unsafe_allow_html=True)


st.markdown('\n<style>\n/* ORBIDENSE MOBILE HEADER OFFSET FIX */\n\n@media (max-width: 760px) {\n\n    :root {\n        --orb-header-h: 78px !important;\n        --orb-content-top: 0px !important;\n    }\n\n    [data-testid="stMain"],\n    [data-testid="stMainBlockContainer"],\n    .block-container {\n        padding-top: 0 !important;\n        margin-top: 0 !important;\n    }\n\n    .home-final-hero {\n        margin-top: .35rem !important;\n    }\n}\n</style>\n', unsafe_allow_html=True)

# =========================================================
# ORBIDENSE — ACCESSIBILITY / VIEW SCALE
# =========================================================
# This controls the visual scale of the complete Streamlit application.
# It changes presentation only; maps, data, calculations and routing are untouched.
if "orbidense_ui_scale" not in st.session_state:
    st.session_state["orbidense_ui_scale"] = 1.0

UI_SCALE_MIN = 0.80
UI_SCALE_MAX = 1.20
UI_SCALE_STEP = 0.10
# Analytics is useful, but it must never prevent the climate app from loading.
try:
    ensure_analytics_database()
    ANALYTICS_READY = True
    ANALYTICS_INIT_ERROR = None
except Exception as analytics_error:
    ANALYTICS_READY = False
    ANALYTICS_INIT_ERROR = str(
        analytics_error
    )
    print(
        "ORBIDENSE analytics initialization error:",
        analytics_error,
    )

inject_v27_ui()

st.markdown(
    """
<style>
:root {
    --cp-bg: #06101b;
    --cp-card: #0d1b2a;
    --cp-border: rgba(139,179,208,.16);
    --cp-text: #f5f9fc;
    --cp-muted: #92a7b8;
    --cp-blue: #39a9ff;
    --cp-cyan: #36d4e6;
    --cp-green: #43d17b;
    --cp-orange: #ff9f43;
    --cp-red: #ff5b5b;
}
html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp { background: var(--cp-bg); color: var(--cp-text); }

/* =========================================================
   APP SHELL / TOP-SPACING FIX
   =========================================================
   Streamlit reserves a header band even when its background is transparent.
   Collapse that reservation so every ORBIDENSE page starts near the top.
   Keep the toolbar available as a small floating control at the top-right.
*/
[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    background: transparent !important;
    border: 0 !important;
    overflow: visible !important;
}

[data-testid="stToolbar"] {
    position: fixed !important;
    top: .35rem !important;
    right: .45rem !important;
    z-index: 1000000 !important;
}

[data-testid="stAppViewContainer"] > .main {
    padding-top: 0 !important;
}

.block-container,
[data-testid="stMainBlockContainer"] {
    max-width: none !important;
    width: 100% !important;
    box-sizing: border-box !important;
    padding-top: .35rem !important;
    padding-bottom: 2.4rem !important;
    padding-left: 1.1rem !important;
    padding-right: 1.1rem !important;
}

/*
   The main workspace must reflow whenever Streamlit opens/closes the sidebar.
   No hard-coded left margin or fixed content width is retained.
*/
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"] {
    width: 100% !important;
    max-width: none !important;
    min-width: 0 !important;
}

[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"] {
    flex: 1 1 auto !important;
    transition: width .22s ease, margin .22s ease !important;
}

[data-testid="stSidebar"] {
    background: #050d16;
    border-right: 1px solid var(--cp-border);
    padding-top: 0 !important;
}

[data-testid="stSidebarContent"] {
    padding-top: .55rem !important;
}

[data-testid="stSidebar"] * { color: #dce7ef; }

[data-testid="stDecoration"],
#MainMenu,
footer {
    display: none !important;
}

/* =========================================================
   HOME CLEANUP
   =========================================================
   The large ORBIDENSE Home hero repeated information already communicated
   by the navigation/search and pushed the live globe below the fold.
   Hide it globally by its dedicated V19 wrapper. The globe and Global Pulse
   columns then move upward automatically without changing any weather/data logic.
*/
.cp-v19-wrap {
    display: none !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

/* Tighten the first Home content section after the location control. */
.cp-v19-wrap + div,
.cp-v19-wrap + [data-testid="stVerticalBlock"] {
    margin-top: 0 !important;
}

h3 {
    scroll-margin-top: .5rem;
}
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}

[data-baseweb="input"] {
    background: #0b1724 !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
}
[data-baseweb="input"] input { color: #f4f8fb !important; }
.stButton > button {
    border-radius: 10px;
    border: 1px solid var(--cp-border);
    background: #102235;
    color: #f6fbff;
    min-height: 42px;
    font-weight: 650;
}
.stButton > button[kind="primary"] { background: #1677c8; border-color: #2c91e6; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--cp-border) !important;
    border-radius: 14px !important;
    background: linear-gradient(145deg, rgba(14,30,46,.94), rgba(8,20,32,.98));
}
[data-testid="stExpander"] {
    border: 1px solid var(--cp-border);
    border-radius: 12px;
    background: #0a1724;
}
/* =========================================================
   ORBIDENSE BRANDING
   ========================================================= */

.cp-brand {
    font-weight: 850;
    font-size: 1.42rem;
    letter-spacing: .015em;
    color: #f5fbff;
    margin: 2px 0 3px 0;
}

.cp-brand-sub {
    color: var(--cp-muted);
    font-size: .76rem;
    margin-bottom: 1rem;
}

.cp-brand-ai {
    color: #62e985;
}

.orbidense-sidebar-tagline {
    text-align: center;
    text-transform: uppercase;
    font-size: .58rem;
    font-weight: 720;
    letter-spacing: .105em;
    line-height: 1.45;
    color: #7894a8;
    padding: 0 8px 13px 8px;
    margin-top: -8px;
    border-bottom: 1px solid rgba(139,179,208,.09);
}

/* Sidebar brand image */
[data-testid="stSidebar"] [data-testid="stImage"] {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stImage"] img {
    max-height: 150px;
    width: 100% !important;
    object-fit: contain;
}

/* =========================================================
   ORBIDENSE — NATIVE EXPLORE SIDEBAR CONTROL
   Uses Streamlit's actual native controls in this installed build:
   OPEN   -> [data-testid="stSidebarCollapseButton"]
   CLOSED -> [data-testid="stExpandSidebarButton"]

   No JavaScript, no iframe/component injection, no duplicate control.
   ========================================================= */

/* ---------- OPEN SIDEBAR: collapse navigation ---------- */
[data-testid="stSidebarCollapseButton"] {
    width: calc(100% - 22px) !important;
    margin: 10px 11px 12px 11px !important;
    padding: 0 !important;
    position: sticky !important;
    top: 10px !important;
    z-index: 2147482000 !important;
}

[data-testid="stSidebarCollapseButton"] > button,
[data-testid="stSidebarCollapseButton"] button {
    width: 100% !important;
    min-width: 0 !important;
    height: 46px !important;
    min-height: 46px !important;
    padding: 0 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 9px !important;
    border-radius: 13px !important;
    border: 1px solid rgba(54, 212, 230, .80) !important;
    background: linear-gradient(135deg, rgba(10, 42, 60, .99), rgba(5, 23, 37, 1)) !important;
    box-shadow: 0 9px 26px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.05) !important;
    color: #f6fbff !important;
    cursor: pointer !important;
    overflow: hidden !important;
    transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease, background .16s ease !important;
}

[data-testid="stSidebarCollapseButton"] button::after {
    content: "Explore" !important;
    display: inline-block !important;
    font-size: .92rem !important;
    line-height: 1 !important;
    font-weight: 800 !important;
    letter-spacing: .015em !important;
    color: #f6fbff !important;
    white-space: nowrap !important;
}

[data-testid="stSidebarCollapseButton"] button svg {
    width: 20px !important;
    height: 20px !important;
    color: #71edf0 !important;
    flex: 0 0 auto !important;
}

[data-testid="stSidebarCollapseButton"] button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(113, 237, 240, 1) !important;
    background: linear-gradient(135deg, rgba(12, 52, 72, .99), rgba(6, 29, 45, .99)) !important;
    box-shadow: 0 12px 32px rgba(0,0,0,.42), 0 0 0 3px rgba(54,212,230,.08) !important;
}

/* ---------- CLOSED SIDEBAR: restore navigation ----------
   IMPORTANT: In the user's installed Streamlit build the restore control is
   the button itself, not a wrapper. That is why earlier selectors did not
   enlarge the tiny top-left chevron. */
[data-testid="stExpandSidebarButton"] {
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 2147483001 !important;
    width: 132px !important;
    min-width: 132px !important;
    max-width: 132px !important;
    height: 46px !important;
    min-height: 46px !important;
    max-height: 46px !important;
    margin: 0 !important;
    padding: 0 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 9px !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    border-radius: 13px !important;
    border: 1px solid rgba(54, 212, 230, .84) !important;
    background: linear-gradient(135deg, rgba(10, 42, 60, .995), rgba(5, 23, 37, 1)) !important;
    box-shadow: 0 10px 30px rgba(0,0,0,.48), 0 0 22px rgba(54,212,230,.08) !important;
    color: #f6fbff !important;
    cursor: pointer !important;
    overflow: hidden !important;
    transition: transform .16s ease, border-color .16s ease, box-shadow .16s ease, background .16s ease !important;
}

[data-testid="stExpandSidebarButton"]::after {
    content: "Explore" !important;
    display: inline-block !important;
    font-size: .92rem !important;
    line-height: 1 !important;
    font-weight: 800 !important;
    letter-spacing: .015em !important;
    color: #f6fbff !important;
    white-space: nowrap !important;
}

[data-testid="stExpandSidebarButton"] svg {
    width: 20px !important;
    height: 20px !important;
    color: #71edf0 !important;
    flex: 0 0 auto !important;
}

[data-testid="stExpandSidebarButton"]:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(113,237,240,1) !important;
    background: linear-gradient(135deg, rgba(12,53,73,.995), rgba(6,29,45,.995)) !important;
    box-shadow: 0 13px 34px rgba(0,0,0,.50), 0 0 0 3px rgba(54,212,230,.09) !important;
}

/* The restore button lives inside Streamlit's header. The app keeps the
   header visually collapsed, but overflow must remain visible/clickable. */
[data-testid="stHeader"] {
    overflow: visible !important;
    pointer-events: none !important;
}

[data-testid="stHeader"] [data-testid="stExpandSidebarButton"],
[data-testid="stHeader"] [data-testid="stToolbar"] {
    pointer-events: auto !important;
}

@media (max-width: 760px) {
    [data-testid="stExpandSidebarButton"] {
        top: 10px !important;
        left: 10px !important;
        width: 116px !important;
        min-width: 116px !important;
        max-width: 116px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 13px !important;
    }
}

/* A subtle edge handle makes the dashboard state obvious. */
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(80, 188, 228, .16) !important;
    box-shadow: 10px 0 32px rgba(0, 0, 0, .13);
}

/* Compact ORBIDENSE Home identity. Keeps the top area dense. */
.orbidense-home-head {
    margin: 0 0 8px 0;
    padding: 0;
}

.orbidense-home-wordmark {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 66px;
    padding: 2px 0 0 2px;
}

.orbidense-home-title {
    color: #f5fbff;
    font-size: 1.50rem;
    font-weight: 850;
    letter-spacing: .025em;
    line-height: 1.05;
}

.orbidense-home-title span {
    color: #72e8a4;
}

.orbidense-home-tagline {
    margin-top: 5px;
    color: #5ea7cb;
    font-size: .70rem;
    font-weight: 700;
    letter-spacing: .095em;
    text-transform: uppercase;
}

/* Compact live-global pulse next to the ORBIDENSE wordmark. */
.orbidense-pulse-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(72px, 1fr));
    gap: 7px;
    width: 100%;
}

.orbidense-pulse-mini {
    min-height: 55px;
    padding: 8px 10px;
    border-radius: 11px;
    border: 1px solid rgba(91, 171, 205, .18);
    background: linear-gradient(180deg, rgba(10, 29, 43, .86), rgba(6, 20, 31, .88));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.025);
}

.orbidense-pulse-label {
    color: #6e9db7;
    font-size: .58rem;
    font-weight: 720;
    letter-spacing: .055em;
    text-transform: uppercase;
    white-space: nowrap;
}

.orbidense-pulse-value {
    margin-top: 3px;
    color: #f4fbff;
    font-size: .88rem;
    font-weight: 820;
    line-height: 1.05;
    white-space: nowrap;
}

.orbidense-pulse-place {
    margin-top: 2px;
    color: #51d9e5;
    font-size: .56rem;
    line-height: 1.1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

@media (max-width: 1100px) {
    .orbidense-pulse-strip { grid-template-columns: repeat(2, minmax(72px, 1fr)); }
}


/* Keep the exact supplied logo compact and un-cropped. */
.orbidense-home-head [data-testid="stImage"] {
    margin: 0 !important;
}

.orbidense-home-head [data-testid="stImage"] img {
    object-fit: contain !important;
}

/* Search sits immediately below the identity with no redundant intro card. */
.orbidense-search-row {
    margin-top: -2px;
    margin-bottom: 7px;
}

.cp-nav { display: grid; gap: 5px; margin: .4rem 0 1.1rem 0; }
.cp-nav a {
    display: block; padding: 9px 11px; border-radius: 9px;
    color: #aebdca !important; text-decoration: none !important; border: 1px solid transparent;
}
.cp-nav a.active { color: #79c9ff !important; background: #0b2236; border-color: rgba(57,169,255,.36); }
.cp-sidebar-title { color: white; font-size: .92rem; font-weight: 700; margin: .65rem 0 .35rem; }
.cp-recent { padding: 7px 0; color: #aebdca; font-size: .88rem; border-bottom: 1px solid rgba(139,179,208,.07); }
.cp-data-box {
    border: 1px solid var(--cp-border); border-radius: 12px; background: #07121d;
    padding: 13px; margin-top: 1rem; color: #9fb0be; font-size: .79rem; line-height: 1.75;
}
.cp-topline { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: .35rem; }
.cp-place-title { color: white; font-size: 1.75rem; font-weight: 800; line-height: 1.15; margin: 0; }
.cp-place-meta { display: flex; flex-wrap: wrap; gap: 14px; color: var(--cp-muted); font-size: .83rem; margin-top: 6px; }
.cp-live-pill {
    display: inline-flex; align-items: center; gap: 6px; background: rgba(67,209,123,.12);
    border: 1px solid rgba(67,209,123,.23); color: #79e9a8; border-radius: 999px; padding: 5px 9px; font-size: .75rem;
}
.cp-section-heading { color: white; font-weight: 750; font-size: 1rem; margin: 0 0 .55rem; }
.cp-current-temp { font-size: 2.45rem; font-weight: 700; color: white; letter-spacing: -1px; margin-top: .2rem; }
.cp-muted { color: var(--cp-muted); }
.cp-mini-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; margin-top: 13px; }
.cp-mini-card { background: #102235; border: 1px solid rgba(139,179,208,.09); border-radius: 9px; padding: 10px; }
.cp-mini-label { color: #89a0b3; font-size: .72rem; margin-bottom: 2px; }
.cp-mini-value { color: #f6fbff; font-size: .95rem; font-weight: 650; }
.cp-aqi {
    margin-top: 11px; padding: 11px; border-radius: 10px; border: 1px solid rgba(139,179,208,.10);
    background: #091724; display: flex; align-items: center; justify-content: space-between;
}
.cp-aqi-value { font-size: 1.35rem; color: #72e59f; font-weight: 750; }
.cp-kpi-grid { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 10px; margin: 12px 0 14px; }
.cp-kpi {
    min-width: 0; background: linear-gradient(145deg,#0f2031,#0a1826);
    border: 1px solid var(--cp-border); border-radius: 12px; padding: 14px 14px 13px;
}
.cp-kpi-label { color: #9eb0bf; font-size: .77rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cp-kpi-value { color: white; font-size: 1.35rem; font-weight: 750; margin-top: 6px; letter-spacing: -.3px; }
.cp-kpi-note { color: #738a9d; font-size: .72rem; margin-top: 6px; }
.cp-blue { color: #55b6ff; } .cp-cyan { color: #47d8e8; } .cp-orange { color: #ffad5b; }
.cp-red { color: #ff7070; } .cp-green { color: #63dc91; }
.cp-landing {
    border: 1px solid var(--cp-border); border-radius: 14px;
    background: linear-gradient(145deg,#0d1d2c,#081521); padding: 20px; margin-top: 12px;
}
.cp-footer { color: #6f8496; font-size: .76rem; text-align: center; padding: 1.2rem 0 .2rem; }
@media (max-width: 1100px) { .cp-kpi-grid { grid-template-columns: repeat(3,minmax(0,1fr)); } }
@media (max-width: 700px) {
    .block-container { padding-left: .65rem; padding-right: .65rem; padding-top: .20rem !important; }
    .cp-place-title { font-size: 1.38rem; }
    .cp-place-meta { gap: 8px; font-size: .76rem; }
    .cp-kpi-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
    .cp-kpi { padding: 12px; }
    .cp-kpi-value { font-size: 1.15rem; }
    .cp-current-temp { font-size: 2rem; }
}

/* =========================================================
   ORBIDENSE — PROFESSIONAL COMMAND SIDEBAR
   Visual-only redesign. Navigation values and page routing are unchanged.
   ========================================================= */

/* Command rail shell */
[data-testid="stSidebar"] {
    width: 318px !important;
    min-width: 318px !important;
    background:
        radial-gradient(circle at 50% -8%, rgba(20, 108, 132, .12), transparent 30%),
        linear-gradient(180deg, #06121d 0%, #040c14 58%, #050f18 100%) !important;
    border-right: 1px solid rgba(70, 180, 211, .20) !important;
    box-shadow: 14px 0 42px rgba(0, 0, 0, .24) !important;
}

[data-testid="stSidebarContent"] {
    padding: 14px 18px 18px 18px !important;
}

/* Exact supplied ORBIDENSE artwork — prominent, never cropped. */
[data-testid="stSidebar"] [data-testid="stImage"] {
    margin: 12px auto 4px auto !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stImage"] img {
    display: block !important;
    width: 100% !important;
    max-width: 238px !important;
    max-height: 228px !important;
    margin: 0 auto !important;
    object-fit: contain !important;
    filter: drop-shadow(0 12px 28px rgba(15, 187, 219, .09));
}

/* Hide the old duplicate tagline; the supplied artwork already carries the brand. */
.orbidense-sidebar-tagline {
    display: none !important;
}

/* Section divider matching the reference design. */
.orbidense-side-section {
    display: flex;
    align-items: center;
    gap: 11px;
    margin: 11px 2px 12px 2px;
    color: #7690a7;
    font-size: .69rem;
    line-height: 1;
    font-weight: 760;
    letter-spacing: .15em;
    text-transform: uppercase;
    white-space: nowrap;
}

.orbidense-side-section::before,
.orbidense-side-section::after {
    content: "";
    height: 1px;
    flex: 1 1 auto;
    background: linear-gradient(90deg, transparent, rgba(102, 173, 202, .25));
}

.orbidense-side-section::after {
    background: linear-gradient(90deg, rgba(102, 173, 202, .25), transparent);
}

/* Native Streamlit radio remains the functional navigation. */
.st-key-main_navigation [role="radiogroup"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 9px !important;
}

.st-key-main_navigation [role="radiogroup"] > label {
    position: relative !important;
    width: 100% !important;
    min-height: 57px !important;
    margin: 0 !important;
    padding: 0 42px 0 16px !important;
    display: flex !important;
    align-items: center !important;
    border-radius: 13px !important;
    border: 1px solid rgba(83, 157, 187, .13) !important;
    background:
        linear-gradient(135deg, rgba(10, 30, 44, .96), rgba(7, 20, 31, .96)) !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.025),
        0 7px 20px rgba(0,0,0,.10) !important;
    cursor: pointer !important;
    overflow: hidden !important;
    transition:
        transform .17s ease,
        border-color .17s ease,
        background .17s ease,
        box-shadow .17s ease !important;
}

/* Remove the default radio circle without changing the radio itself. */
.st-key-main_navigation [role="radiogroup"] > label > div:first-child {
    display: none !important;
}

.st-key-main_navigation [role="radiogroup"] > label p {
    margin: 0 !important;
    color: #dce8f0 !important;
    font-size: .92rem !important;
    line-height: 1.15 !important;
    font-weight: 650 !important;
    letter-spacing: -.005em !important;
    white-space: nowrap !important;
}

/* Right chevron: visual cue only. */
.st-key-main_navigation [role="radiogroup"] > label::after {
    content: "›";
    position: absolute;
    right: 16px;
    top: 50%;
    transform: translateY(-52%);
    color: #c7d8e4;
    font-size: 1.55rem;
    line-height: 1;
    font-weight: 300;
    opacity: .88;
    transition: transform .17s ease, color .17s ease;
}

.st-key-main_navigation [role="radiogroup"] > label:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(48, 211, 226, .38) !important;
    background:
        linear-gradient(135deg, rgba(11, 41, 56, .98), rgba(7, 27, 40, .98)) !important;
    box-shadow:
        0 10px 26px rgba(0,0,0,.18),
        0 0 0 1px rgba(42, 211, 226, .04) !important;
}

.st-key-main_navigation [role="radiogroup"] > label:hover::after {
    transform: translate(2px, -52%);
    color: #52edf0;
}

/* Active state: teal edge, glow, stronger typography. */
.st-key-main_navigation [role="radiogroup"] > label:has(input:checked) {
    border-color: rgba(29, 222, 226, .72) !important;
    background:
        linear-gradient(105deg, rgba(7, 79, 94, .86), rgba(7, 34, 48, .97) 66%, rgba(6, 26, 38, .98)) !important;
    box-shadow:
        0 9px 28px rgba(0,0,0,.20),
        inset 4px 0 0 #28e4e4,
        0 0 23px rgba(24, 222, 226, .08) !important;
}

.st-key-main_navigation [role="radiogroup"] > label:has(input:checked) p {
    color: #69f3ef !important;
    font-weight: 780 !important;
}

.st-key-main_navigation [role="radiogroup"] > label:has(input:checked)::after {
    color: #55f0ed !important;
}

/* Private developer item gets a subtle restricted-access treatment. */
.st-key-main_navigation [role="radiogroup"] > label:has(p:nth-child(1)) {
    isolation: isolate;
}

/* Developer-only system card */
.orbidense-dev-status {
    position: relative;
    margin: 9px 1px 8px 1px;
    padding: 14px 15px;
    border-radius: 13px;
    border: 1px solid rgba(69, 214, 145, .20);
    background:
        linear-gradient(135deg, rgba(7, 33, 39, .94), rgba(6, 23, 32, .96));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.025);
}

.orbidense-dev-status-top {
    display: flex;
    align-items: center;
    gap: 9px;
    color: #56e99a;
    font-size: .85rem;
    font-weight: 760;
}

.orbidense-dev-dot {
    width: 9px;
    height: 9px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: #48e68f;
    box-shadow: 0 0 0 5px rgba(72,230,143,.06), 0 0 13px rgba(72,230,143,.45);
}

.orbidense-dev-status-sub {
    margin: 6px 0 0 18px;
    color: #8aa2b4;
    font-size: .70rem;
    line-height: 1.55;
}

/* Native collapse control — small square in the upper-right of the rail. */
[data-testid="stSidebarCollapseButton"] {
    position: absolute !important;
    top: 14px !important;
    right: 13px !important;
    width: 42px !important;
    height: 42px !important;
    z-index: 2147482000 !important;
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stSidebarCollapseButton"] button {
    width: 42px !important;
    min-width: 42px !important;
    height: 42px !important;
    min-height: 42px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 12px !important;
    border: 1px solid rgba(117, 177, 207, .31) !important;
    background: rgba(7, 20, 31, .93) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,.24) !important;
    color: #e7f6fb !important;
}

[data-testid="stSidebarCollapseButton"] button::after {
    content: none !important;
}

[data-testid="stSidebarCollapseButton"] button:hover {
    border-color: rgba(51, 226, 229, .70) !important;
    background: rgba(8, 38, 50, .98) !important;
    box-shadow: 0 0 0 3px rgba(51,226,229,.06), 0 9px 25px rgba(0,0,0,.27) !important;
}

/* Closed-state restore control stays available at all times. */
[data-testid="stExpandSidebarButton"] {
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 2147483001 !important;
    width: 46px !important;
    min-width: 46px !important;
    max-width: 46px !important;
    height: 46px !important;
    min-height: 46px !important;
    max-height: 46px !important;
    padding: 0 !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    visibility: visible !important;
    opacity: 1 !important;
    border-radius: 13px !important;
    border: 1px solid rgba(51, 226, 229, .55) !important;
    background: rgba(7, 24, 35, .97) !important;
    color: #e9fbff !important;
    box-shadow: 0 10px 30px rgba(0,0,0,.38), 0 0 18px rgba(51,226,229,.07) !important;
    pointer-events: auto !important;
}

[data-testid="stExpandSidebarButton"]::after {
    content: none !important;
}

[data-testid="stExpandSidebarButton"]:hover {
    border-color: rgba(51, 226, 229, .90) !important;
    background: rgba(8, 42, 54, .99) !important;
}

[data-testid="stHeader"] {
    overflow: visible !important;
}

[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] {
    pointer-events: auto !important;
}

@media (max-width: 760px) {
    [data-testid="stSidebar"] {
        width: min(88vw, 318px) !important;
        min-width: min(88vw, 318px) !important;
    }

    [data-testid="stSidebarContent"] {
        padding-left: 14px !important;
        padding-right: 14px !important;
    }

    .st-key-main_navigation [role="radiogroup"] > label {
        min-height: 54px !important;
    }
}


.cp-intel {
    background:
        linear-gradient(
            135deg,
            rgba(16, 38, 56, .98),
            rgba(7, 22, 35, .98)
        );
    border: 1px solid rgba(54, 212, 230, .20);
    border-radius: 14px;
    padding: 17px;
    margin: 12px 0 14px 0;
}

.cp-intel-top {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: 12px;
}

.cp-intel-title {
    font-size: 1.12rem;
    color: #ffffff;
    font-weight: 780;
}

.cp-intel-sub {
    color: #8fa7b9;
    font-size: .78rem;
    margin-top: 3px;
}

.cp-intel-status {
    border-radius: 999px;
    padding: 5px 9px;
    font-size: .74rem;
    font-weight: 700;
    border: 1px solid rgba(139,179,208,.16);
    white-space: nowrap;
}

.cp-intel-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0,1fr));
    gap: 9px;
    margin-top: 13px;
}

.cp-intel-card {
    background: #0b1b2a;
    border: 1px solid rgba(139,179,208,.11);
    border-radius: 10px;
    padding: 11px;
    min-width: 0;
}

.cp-intel-label {
    color: #8fa6b7;
    font-size: .70rem;
}

.cp-intel-value {
    color: #f7fbfd;
    font-size: 1.05rem;
    font-weight: 750;
    margin-top: 4px;
}

.cp-intel-note {
    color: #71899b;
    font-size: .68rem;
    margin-top: 4px;
    line-height: 1.35;
}

.cp-intel-story {
    margin-top: 11px;
    color: #c8d6e0;
    font-size: .86rem;
    line-height: 1.55;
}

.cp-about-hero {
    background:
        linear-gradient(
            135deg,
            #0e2234,
            #081724
        );
    border: 1px solid rgba(57,169,255,.18);
    border-radius: 16px;
    padding: 24px;
    margin: 10px 0 16px 0;
}

.cp-about-name {
    font-size: 1.7rem;
    font-weight: 800;
    color: white;
}

.cp-about-headline {
    color: #62c4ff;
    font-size: .95rem;
    margin-top: 4px;
}

.cp-about-copy {
    color: #b7c8d4;
    line-height: 1.65;
    margin-top: 13px;
    max-width: 900px;
}

.cp-stack-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0,1fr));
    gap: 9px;
    margin: 12px 0;
}

.cp-stack-card {
    background: #0b1a29;
    border: 1px solid rgba(139,179,208,.12);
    border-radius: 11px;
    padding: 13px;
}

.cp-stack-title {
    color: #ffffff;
    font-size: .83rem;
    font-weight: 700;
}

.cp-stack-copy {
    color: #859bad;
    font-size: .73rem;
    line-height: 1.45;
    margin-top: 4px;
}

@media (max-width: 1000px) {
    .cp-intel-grid {
        grid-template-columns: repeat(3, minmax(0,1fr));
    }

    .cp-stack-grid {
        grid-template-columns: repeat(2, minmax(0,1fr));
    }
}

@media (max-width: 650px) {
    .cp-intel-grid {
        grid-template-columns: repeat(2, minmax(0,1fr));
    }

    .cp-stack-grid {
        grid-template-columns: 1fr;
    }

    .cp-intel-top {
        display: block;
    }

    .cp-intel-status {
        display: inline-block;
        margin-top: 8px;
    }
}


/* =========================================================
   CLIMATE FINGERPRINT + PASSPORT
   ========================================================= */

.cp-fingerprint-wrap {
    background:
        linear-gradient(
            135deg,
            rgba(10, 30, 46, .98),
            rgba(6, 18, 30, .98)
        );
    border: 1px solid rgba(72, 197, 255, .18);
    border-radius: 16px;
    padding: 18px;
    margin: 14px 0 16px 0;
}

.cp-fingerprint-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}

.cp-fingerprint-title {
    font-size: 1.08rem;
    font-weight: 800;
    color: #ffffff;
}

.cp-fingerprint-sub {
    color: #86a2b5;
    font-size: .76rem;
    line-height: 1.45;
    margin-top: 3px;
}

.cp-fingerprint-badge {
    border: 1px solid rgba(75, 194, 255, .28);
    background: rgba(17, 64, 92, .42);
    color: #74cfff;
    border-radius: 999px;
    padding: 6px 10px;
    font-size: .72rem;
    font-weight: 700;
    white-space: nowrap;
}

.cp-fingerprint-metrics {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 9px;
    margin-top: 11px;
}

.cp-fingerprint-metric {
    background: rgba(12, 31, 47, .92);
    border: 1px solid rgba(135, 179, 207, .10);
    border-radius: 11px;
    padding: 11px;
}

.cp-fingerprint-label {
    color: #88a2b4;
    font-size: .67rem;
    line-height: 1.3;
}

.cp-fingerprint-score {
    color: #ffffff;
    font-size: 1.18rem;
    font-weight: 800;
    margin-top: 4px;
}

.cp-fingerprint-desc {
    color: #69869a;
    font-size: .66rem;
    margin-top: 3px;
    line-height: 1.35;
}

.cp-passport {
    background:
        radial-gradient(
            circle at 85% 15%,
            rgba(47, 166, 255, .14),
            transparent 28%
        ),
        linear-gradient(
            145deg,
            #10283c,
            #081725 72%
        );
    border: 1px solid rgba(81, 187, 255, .22);
    border-radius: 19px;
    padding: 22px;
    margin: 10px 0 15px 0;
    position: relative;
    overflow: hidden;
}

.cp-passport::after {
    content: "";
    position: absolute;
    width: 190px;
    height: 190px;
    right: -65px;
    bottom: -70px;
    border: 1px solid rgba(84, 197, 255, .09);
    border-radius: 50%;
    box-shadow:
        0 0 0 28px rgba(84, 197, 255, .025),
        0 0 0 56px rgba(84, 197, 255, .018);
}

.cp-passport-eyebrow {
    color: #58bdf8;
    text-transform: uppercase;
    letter-spacing: .14em;
    font-size: .65rem;
    font-weight: 800;
}

.cp-passport-location {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 850;
    line-height: 1.1;
    margin-top: 6px;
}

.cp-passport-meta {
    color: #91a9ba;
    font-size: .78rem;
    margin-top: 8px;
}

.cp-passport-signature {
    display: inline-block;
    margin-top: 13px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(52, 183, 255, .10);
    border: 1px solid rgba(52, 183, 255, .18);
    color: #8ad5ff;
    font-size: .75rem;
    font-weight: 720;
}

.cp-passport-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 15px 0;
}

.cp-passport-card {
    background: #0b1d2c;
    border: 1px solid rgba(136, 181, 211, .11);
    border-radius: 11px;
    padding: 12px;
}

.cp-passport-label {
    color: #7893a6;
    font-size: .68rem;
}

.cp-passport-value {
    color: #ffffff;
    font-size: 1.13rem;
    font-weight: 780;
    margin-top: 4px;
}

.cp-passport-note {
    color: #648195;
    font-size: .65rem;
    margin-top: 3px;
}

.cp-product-note {
    background: rgba(15, 36, 52, .75);
    border-left: 3px solid #43b9f5;
    border-radius: 8px;
    padding: 10px 12px;
    color: #9db2c1;
    font-size: .73rem;
    line-height: 1.5;
    margin-top: 10px;
}

@media (max-width: 1000px) {
    .cp-fingerprint-metrics {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .cp-passport-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 650px) {
    .cp-fingerprint-metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .cp-passport-grid {
        grid-template-columns: 1fr 1fr;
    }

    .cp-fingerprint-header {
        display: block;
    }

    .cp-fingerprint-badge {
        display: inline-block;
        margin-top: 8px;
    }

    .cp-passport-location {
        font-size: 1.55rem;
    }
}


/* =========================================================
   COMPARE PLACES
   ========================================================= */

.cp-compare-hero {
    background:
        linear-gradient(
            135deg,
            rgba(14, 36, 54, .98),
            rgba(6, 19, 31, .98)
        );
    border: 1px solid rgba(62, 187, 255, .18);
    border-radius: 16px;
    padding: 19px;
    margin: 10px 0 14px 0;
}

.cp-compare-title {
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 820;
}

.cp-compare-sub {
    color: #8fa8ba;
    font-size: .79rem;
    line-height: 1.55;
    margin-top: 5px;
}

.cp-compare-place {
    background: #0a1927;
    border: 1px solid rgba(139,179,208,.13);
    border-radius: 13px;
    padding: 14px;
    min-height: 190px;
}

.cp-compare-name {
    color: #ffffff;
    font-size: 1.02rem;
    font-weight: 760;
    line-height: 1.3;
}

.cp-compare-type {
    color: #5fc3ff;
    font-size: .67rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-top: 4px;
}

.cp-compare-big {
    color: #ffffff;
    font-size: 1.65rem;
    font-weight: 820;
    margin-top: 12px;
}

.cp-compare-caption {
    color: #7893a6;
    font-size: .69rem;
    margin-top: 2px;
}

.cp-compare-mini {
    display: grid;
    grid-template-columns: repeat(2,minmax(0,1fr));
    gap: 7px;
    margin-top: 11px;
}

.cp-compare-mini-card {
    background: #102235;
    border: 1px solid rgba(139,179,208,.08);
    border-radius: 8px;
    padding: 8px;
}

.cp-compare-mini-label {
    color: #809aae;
    font-size: .64rem;
}

.cp-compare-mini-value {
    color: #eff8fe;
    font-size: .82rem;
    font-weight: 680;
    margin-top: 2px;
}

.cp-verdict {
    background:
        linear-gradient(
            135deg,
            rgba(13, 38, 55, .95),
            rgba(8, 26, 40, .95)
        );
    border: 1px solid rgba(67, 209, 123, .18);
    border-radius: 14px;
    padding: 16px;
    margin: 13px 0;
}

.cp-verdict-title {
    color: #ffffff;
    font-size: 1rem;
    font-weight: 780;
}

.cp-verdict-grid {
    display: grid;
    grid-template-columns: repeat(4,minmax(0,1fr));
    gap: 8px;
    margin-top: 10px;
}

.cp-verdict-card {
    background: rgba(8, 25, 38, .8);
    border: 1px solid rgba(139,179,208,.10);
    border-radius: 9px;
    padding: 10px;
}

.cp-verdict-label {
    color: #7891a4;
    font-size: .64rem;
}

.cp-verdict-value {
    color: #ffffff;
    font-size: .86rem;
    font-weight: 700;
    margin-top: 3px;
    line-height: 1.35;
}

.cp-compare-warning {
    border-left: 3px solid #ffb35c;
    background: rgba(255,179,92,.06);
    border-radius: 7px;
    padding: 9px 11px;
    color: #aebfcb;
    font-size: .72rem;
    line-height: 1.5;
    margin: 10px 0;
}

@media (max-width: 850px) {
    .cp-verdict-grid {
        grid-template-columns: repeat(2,minmax(0,1fr));
    }
}

@media (max-width: 520px) {
    .cp-verdict-grid {
        grid-template-columns: 1fr;
    }
}


/* Global Rankings */
.cp-rank-hero {
    background: linear-gradient(135deg, rgba(14,37,56,.98), rgba(7,20,33,.98));
    border: 1px solid rgba(72,197,255,.18);
    border-radius: 16px;
    padding: 19px;
    margin: 10px 0 14px 0;
}
.cp-rank-title { color:#fff; font-size:1.35rem; font-weight:820; }
.cp-rank-sub { color:#8ca5b7; font-size:.79rem; line-height:1.55; margin-top:5px; }
.cp-rank-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:9px; margin:12px 0 14px; }
.cp-rank-card { background:#0b1c2a; border:1px solid rgba(139,179,208,.11); border-radius:11px; padding:12px; }
.cp-rank-label { color:#7f99ac; font-size:.67rem; }
.cp-rank-value { color:#fff; font-size:1.12rem; font-weight:780; margin-top:4px; line-height:1.25; }
.cp-rank-note { color:#678295; font-size:.65rem; margin-top:4px; }
.cp-scenario-pill { display:inline-flex; border:1px solid rgba(83,193,255,.20); background:rgba(83,193,255,.08); border-radius:999px; padding:5px 9px; color:#8dd5ff; font-size:.70rem; font-weight:700; }
.cp-method-box { background:rgba(11,29,43,.8); border-left:3px solid #43b9f5; border-radius:8px; padding:10px 12px; color:#9fb2bf; font-size:.72rem; line-height:1.52; margin-top:10px; }
@media (max-width:900px) { .cp-rank-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:520px) { .cp-rank-grid { grid-template-columns:1fr; } }


.cp-country-overview {
    margin: 18px 0 12px 0;
    padding: 14px 16px;
    background: linear-gradient(
        135deg,
        rgba(15, 39, 58, .96),
        rgba(8, 24, 38, .96)
    );
    border: 1px solid rgba(72, 197, 255, .16);
    border-radius: 13px;
}
.cp-country-overview-title {
    color: #ffffff;
    font-size: 1.05rem;
    font-weight: 800;
}
.cp-country-overview-sub {
    color: #86a2b5;
    font-size: .72rem;
    margin-top: 3px;
}


/* =========================================================
   PROFESSIONAL ABOUT / CREATOR PAGE
   ========================================================= */

.about-main-hero {
    background:
        linear-gradient(
            135deg,
            rgba(13, 37, 56, 0.98),
            rgba(7, 22, 35, 0.98)
        );
    border: 1px solid rgba(91, 195, 255, 0.16);
    border-radius: 18px;
    padding: 28px 30px;
    margin: 8px 0 26px 0;
}

.about-eyebrow {
    color: #43b9f5;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}

.about-main-title {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 850;
    line-height: 1.12;
}

.about-main-subtitle {
    color: #79cfff;
    font-size: 0.96rem;
    font-weight: 600;
    margin-top: 8px;
}

.about-main-copy {
    color: #a5bac8;
    font-size: 0.84rem;
    line-height: 1.72;
    max-width: 920px;
    margin-top: 16px;
}

.creator-shell {
    margin-top: 2px;
    margin-bottom: 12px;
}

.creator-card {
    background:
        linear-gradient(
            145deg,
            rgba(12, 31, 46, 0.98),
            rgba(8, 24, 37, 0.98)
        );
    border: 1px solid rgba(139, 179, 208, 0.13);
    border-radius: 16px;
    padding: 24px 26px;
    min-height: 218px;
}

.creator-label {
    color: #43b9f5;
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    font-weight: 800;
}

.creator-name {
    color: #ffffff;
    font-size: 1.62rem;
    font-weight: 850;
    margin-top: 7px;
}

.creator-role {
    color: #5ec8ff;
    font-size: 0.87rem;
    font-weight: 650;
    margin-top: 5px;
}

.creator-university {
    color: #8ea9ba;
    font-size: 0.76rem;
    margin-top: 4px;
}

.creator-bio {
    color: #b2c3ce;
    font-size: 0.80rem;
    line-height: 1.66;
    margin-top: 16px;
}

.creator-focus {
    color: #7390a2;
    font-size: 0.70rem;
    margin-top: 15px;
}

.profile-photo-card {
    background:
        linear-gradient(
            145deg,
            rgba(12, 31, 46, 0.98),
            rgba(8, 24, 37, 0.98)
        );
    border: 1px solid rgba(139, 179, 208, 0.13);
    border-radius: 16px;
    padding: 10px;
    text-align: center;
}

.profile-photo-card img {
    border-radius: 13px !important;
    object-fit: cover !important;
    border: 1px solid rgba(92, 190, 240, 0.18);
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.20);
}

.profile-photo-caption {
    color: #6f8ea1;
    font-size: 0.63rem;
    margin-top: 8px;
}

.profile-photo-placeholder {
    width: 100%;
    min-height: 215px;
    border-radius: 13px;
    border: 1px dashed rgba(116, 171, 205, 0.28);
    background: #0b1c2a;
    color: #7792a5;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    font-size: 0.75rem;
    text-align: center;
    padding: 18px;
}

.profile-photo-icon {
    font-size: 1.8rem;
    margin-bottom: 8px;
}

.about-section-title {
    color: #ffffff;
    font-size: 1.03rem;
    font-weight: 800;
    margin-top: 30px;
    margin-bottom: 12px;
}

.about-feature-card {
    min-height: 146px;
    background: #0b1c2a;
    border: 1px solid rgba(139, 179, 208, 0.11);
    border-radius: 12px;
    padding: 16px;
}

.about-feature-icon {
    color: #4ec7ff;
    font-size: 1.03rem;
    margin-bottom: 8px;
}

.about-feature-title {
    color: #ffffff;
    font-size: 0.81rem;
    font-weight: 750;
}

.about-feature-copy {
    color: #829dad;
    font-size: 0.69rem;
    line-height: 1.5;
    margin-top: 6px;
}

.about-info-card {
    background: #091925;
    border: 1px solid rgba(139, 179, 208, 0.11);
    border-radius: 13px;
    padding: 20px;
    min-height: 190px;
    margin-top: 20px;
}

.about-info-label {
    color: #4ec7ff;
    font-size: 0.61rem;
    font-weight: 800;
    letter-spacing: 0.11em;
}

.about-info-heading {
    color: #ffffff;
    font-size: 0.98rem;
    font-weight: 750;
    margin-top: 8px;
}

.about-info-copy {
    color: #91a8b7;
    font-size: 0.74rem;
    line-height: 1.66;
    margin-top: 10px;
}

.tech-chip-wrap {
    margin-top: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
}

.tech-chip {
    background: rgba(58, 172, 235, 0.09);
    color: #95d9ff;
    border: 1px solid rgba(58, 172, 235, 0.18);
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 0.67rem;
    font-weight: 600;
}

.about-note {
    background: rgba(11, 29, 43, 0.75);
    border-left: 3px solid #43b9f5;
    border-radius: 8px;
    padding: 11px 13px;
    color: #8ea6b6;
    font-size: 0.70rem;
    line-height: 1.55;
    margin-top: 18px;
}

.about-footer {
    text-align: center;
    color: #59768a;
    font-size: 0.66rem;
    margin-top: 30px;
    padding: 18px 0 8px;
}

@media (max-width: 850px) {
    .about-main-hero {
        padding: 22px;
    }

    .about-main-title {
        font-size: 1.65rem;
    }

    .creator-card {
        padding: 20px;
    }

    .about-feature-card {
        min-height: 132px;
    }
}


/* V22 readability fixes */
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input,
div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] input {
    color: #f4fbff !important;
    -webkit-text-fill-color: #f4fbff !important;
    caret-color: #ffffff !important;
    background: #0a1d2a !important;
}

div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stChatInput"] textarea::placeholder,
div[data-testid="stChatInput"] input::placeholder {
    color: #7f9baa !important;
    -webkit-text-fill-color: #7f9baa !important;
    opacity: 1 !important;
}

[data-testid="stExpander"] {
    border-color: rgba(73, 214, 246, .14) !important;
}

[data-testid="stExpander"] details {
    background: rgba(4, 17, 27, .82) !important;
}


/* =========================================================
   V34 — PROFESSIONAL GLOBAL SEARCH + AUDIENCE STATUS
   ========================================================= */
.cp-search-panel {
    border: 1px solid rgba(65, 201, 244, .18);
    border-radius: 16px;
    padding: 11px 13px 12px;
    background:
        radial-gradient(circle at 92% 8%, rgba(51, 211, 239, .08), transparent 34%),
        linear-gradient(145deg, rgba(9, 26, 40, .98), rgba(5, 17, 28, .98));
    box-shadow:
        0 14px 34px rgba(0, 0, 0, .22),
        inset 0 0 0 1px rgba(255,255,255,.018);
}

.cp-search-kicker {
    color: #5fdcff;
    font-size: .64rem;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: 2px;
}

.cp-search-title {
    color: #f6fbff;
    font-size: .91rem;
    font-weight: 720;
    margin-bottom: 1px;
}

.cp-search-help {
    color: #7894a8;
    font-size: .68rem;
    line-height: 1.35;
    margin-bottom: 7px;
}

.cp-audience-wrap {
    height: 100%;
    min-height: 78px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
}

.cp-audience-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 38px;
    padding: 8px 12px;
    border-radius: 999px;
    border: 1px solid rgba(75, 220, 164, .24);
    background:
        linear-gradient(135deg, rgba(20, 67, 55, .30), rgba(7, 27, 29, .82));
    color: #b9f7d4;
    font-size: .75rem;
    font-weight: 730;
    white-space: nowrap;
    box-shadow: 0 10px 26px rgba(0,0,0,.18);
}

.cp-audience-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #52e99d;
    box-shadow: 0 0 10px rgba(82, 233, 157, .78);
    flex: 0 0 auto;
}

.cp-audience-sub {
    color: #6f9f8c;
    font-size: .62rem;
    font-weight: 600;
    margin-left: 2px;
}

@media (max-width: 800px) {
    .cp-search-panel {
        padding: 10px 11px 11px;
    }

    .cp-audience-wrap {
        min-height: 42px;
        justify-content: flex-start;
    }
}


/* FINAL SIDEBAR CONTROL OVERRIDE — no legacy Explore text */
[data-testid="stSidebarCollapseButton"] button::after,
[data-testid="stExpandSidebarButton"]::after {
    content: none !important;
    display: none !important;
}

/* =========================================================
   ORBIDENSE — RESPONSIVE WORKSPACE + VIEW CONTROLS
   =========================================================
   1) The dashboard must consume the released sidebar width immediately.
   2) Zoom controls scale the complete interface, not Plotly/map camera zoom.
   3) Uses Chromium/Edge-supported :has() to detect Streamlit's collapsed rail.
*/

/* Smooth layout transition while opening/closing the navigation rail. */
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.block-container {
    transition: width .22s ease, margin .22s ease, padding .22s ease !important;
}

/* When Streamlit exposes the restore-sidebar button, the rail is collapsed.
   Force the content canvas to release every reserved sidebar pixel. */
html:has([data-testid="stExpandSidebarButton"]) [data-testid="stAppViewContainer"],
body:has([data-testid="stExpandSidebarButton"]) [data-testid="stAppViewContainer"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}

html:has([data-testid="stExpandSidebarButton"]) [data-testid="stAppViewContainer"] > .main,
body:has([data-testid="stExpandSidebarButton"]) [data-testid="stAppViewContainer"] > .main,
html:has([data-testid="stExpandSidebarButton"]) [data-testid="stMain"],
body:has([data-testid="stExpandSidebarButton"]) [data-testid="stMain"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin-left: 0 !important;
    padding-left: 0 !important;
    flex: 1 1 100% !important;
}

html:has([data-testid="stExpandSidebarButton"]) [data-testid="stMainBlockContainer"],
body:has([data-testid="stExpandSidebarButton"]) [data-testid="stMainBlockContainer"],
html:has([data-testid="stExpandSidebarButton"]) .block-container,
body:has([data-testid="stExpandSidebarButton"]) .block-container {
    width: 100% !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: 1.05rem !important;
    padding-right: 1.05rem !important;
}

/* Extra fallback for Streamlit builds that retain a hidden sidebar shell. */
body:has([data-testid="stExpandSidebarButton"]) [data-testid="stSidebar"] {
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}

/* ---------- Professional whole-interface zoom controller ---------- */
.st-key-orbidense_zoom_controls,
[class*="st-key-orbidense_zoom_controls"] {
    position: fixed !important;
    top: 12px !important;
    right: 74px !important;
    z-index: 2147482500 !important;
    width: 166px !important;
    min-width: 166px !important;
    margin: 0 !important;
    padding: 6px !important;
    border: 1px solid rgba(49, 201, 220, .30) !important;
    border-radius: 15px !important;
    background: linear-gradient(145deg, rgba(7,26,39,.98), rgba(4,15,25,.96)) !important;
    box-shadow: 0 14px 34px rgba(0,0,0,.38), 0 0 0 1px rgba(79,231,235,.03) inset !important;
    backdrop-filter: blur(18px) saturate(135%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(135%) !important;
}

.st-key-orbidense_zoom_controls [data-testid="stHorizontalBlock"],
[class*="st-key-orbidense_zoom_controls"] [data-testid="stHorizontalBlock"] {
    gap: 6px !important;
    align-items: center !important;
}

.st-key-orbidense_zoom_controls [data-testid="column"],
[class*="st-key-orbidense_zoom_controls"] [data-testid="column"] {
    min-width: 0 !important;
    padding: 0 !important;
}

.st-key-orbidense_zoom_controls .stButton,
[class*="st-key-orbidense_zoom_controls"] .stButton {
    margin: 0 !important;
}

.st-key-orbidense_zoom_controls .stButton > button,
[class*="st-key-orbidense_zoom_controls"] .stButton > button {
    width: 100% !important;
    min-width: 0 !important;
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 7px !important;
    border-radius: 10px !important;
    border: 1px solid rgba(70, 193, 218, .22) !important;
    background: linear-gradient(180deg, rgba(14,42,58,.98), rgba(8,28,41,.98)) !important;
    color: #eafaff !important;
    font-size: .84rem !important;
    line-height: 1 !important;
    font-weight: 850 !important;
    letter-spacing: .015em !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035), 0 3px 10px rgba(0,0,0,.18) !important;
    cursor: pointer !important;
    transition: transform .16s ease, border-color .16s ease, background .16s ease, box-shadow .16s ease !important;
}

/* Make +/- controls visually distinct from the reset indicator. */
.st-key-orbidense_zoom_controls [data-testid="column"]:first-child button,
.st-key-orbidense_zoom_controls [data-testid="column"]:last-child button,
[class*="st-key-orbidense_zoom_controls"] [data-testid="column"]:first-child button,
[class*="st-key-orbidense_zoom_controls"] [data-testid="column"]:last-child button {
    font-size: 1.08rem !important;
    color: #64edf0 !important;
}

.st-key-orbidense_zoom_controls [data-testid="column"]:nth-child(2) button,
[class*="st-key-orbidense_zoom_controls"] [data-testid="column"]:nth-child(2) button {
    background: rgba(8,24,36,.98) !important;
    color: #a9cfdb !important;
    font-variant-numeric: tabular-nums !important;
}

.st-key-orbidense_zoom_controls .stButton > button:hover,
[class*="st-key-orbidense_zoom_controls"] .stButton > button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(61, 232, 235, .72) !important;
    background: linear-gradient(180deg, rgba(15,57,70,.99), rgba(8,37,50,.99)) !important;
    color: #ffffff !important;
    box-shadow: 0 7px 18px rgba(0,0,0,.26), 0 0 16px rgba(56,225,230,.08) !important;
}

.st-key-orbidense_zoom_controls .stButton > button:active,
[class*="st-key-orbidense_zoom_controls"] .stButton > button:active {
    transform: translateY(0) scale(.97) !important;
}

.st-key-orbidense_zoom_controls .stButton > button:focus-visible,
[class*="st-key-orbidense_zoom_controls"] .stButton > button:focus-visible {
    outline: 2px solid rgba(74,231,236,.68) !important;
    outline-offset: 2px !important;
}

@media (max-width: 780px) {
    .st-key-orbidense_zoom_controls,
    [class*="st-key-orbidense_zoom_controls"] {
        top: 10px !important;
        right: 56px !important;
        width: 150px !important;
        min-width: 150px !important;
        padding: 5px !important;
    }
}

/* Exact Streamlit key selectors: these override the default white button theme. */
.st-key-orbidense_zoom_out button,
.st-key-orbidense_zoom_reset button,
.st-key-orbidense_zoom_in button {
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 .65rem !important;
    border: 1px solid rgba(44, 211, 226, .38) !important;
    border-radius: 10px !important;
    background: linear-gradient(180deg, #0c2636 0%, #071a27 100%) !important;
    color: #dffbff !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 5px 14px rgba(0,0,0,.24) !important;
    font-weight: 800 !important;
    transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease, background .15s ease !important;
}

.st-key-orbidense_zoom_out button,
.st-key-orbidense_zoom_in button {
    color: #55e8ee !important;
    font-size: 1.08rem !important;
}

.st-key-orbidense_zoom_reset button {
    min-width: 58px !important;
    color: #f4fbff !important;
    background: linear-gradient(180deg, #102f40 0%, #0a2231 100%) !important;
    font-variant-numeric: tabular-nums !important;
}

.st-key-orbidense_zoom_out button:hover,
.st-key-orbidense_zoom_reset button:hover,
.st-key-orbidense_zoom_in button:hover {
    transform: translateY(-1px) !important;
    border-color: rgba(71, 238, 241, .85) !important;
    background: linear-gradient(180deg, #123a4a 0%, #0a2837 100%) !important;
    box-shadow: 0 8px 20px rgba(0,0,0,.30), 0 0 16px rgba(52,225,231,.10) !important;
}

/* Make the controller itself compact and integrated into the app chrome. */
.st-key-orbidense_zoom_controls {
    width: 176px !important;
    min-width: 176px !important;
    padding: 6px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(48, 202, 219, .28) !important;
    background: rgba(4, 18, 29, .96) !important;
    box-shadow: 0 12px 30px rgba(0,0,0,.34), inset 0 1px 0 rgba(255,255,255,.025) !important;
}
</style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# ORBIDENSE — PERSISTENT EXPLORE BUTTON
# Sidebar collapse/restore is handled entirely by Streamlit's native controls.
# They are branded as “Explore” through CSS above, so no injected JavaScript
# or deprecated components.html iframe is required.

# =========================================================
# RESPONSIVE INTERFACE DENSITY / ACCESSIBILITY SCALE
# =========================================================
# Do not CSS-zoom the .stApp canvas: scaling the root canvas can leave blank
# viewport regions and visually split the application. Instead we scale the
# root typographic/rem system. Streamlit's flex/grid containers remain 100%
# fluid and Plotly/Map components continue to resize to the real viewport.
_ui_scale = float(st.session_state.get("orbidense_ui_scale", 1.0))
_ui_font_percent = int(round(_ui_scale * 100))

st.markdown(
    f"""
<style>
/* Responsive density scaling: fonts, rem-based controls, spacing and cards
   adapt while the application itself always occupies the full viewport. */
html {{
    font-size: {_ui_font_percent}% !important;
}}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.block-container {{
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
}}

/* Never reserve invisible horizontal canvas after the sidebar closes. */
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    margin-right: 0 !important;
    padding-right: 0 !important;
}}

[data-testid="stMainBlockContainer"],
.block-container {{
    margin-left: 0 !important;
    margin-right: 0 !important;
    padding-left: clamp(.8rem, 1.2vw, 1.35rem) !important;
    padding-right: clamp(.8rem, 1.2vw, 1.35rem) !important;
}}

/* Let responsive rows wrap instead of shrinking into a partial-width canvas. */
[data-testid="stHorizontalBlock"] {{
    width: 100% !important;
    max-width: 100% !important;
}}

/* Plotly and iframe/component hosts follow their parent width at every density. */
[data-testid="stPlotlyChart"],
[data-testid="stIFrame"],
iframe {{
    max-width: 100% !important;
}}

/* Small screens get a slightly tighter canvas automatically. */
@media (max-width: 900px) {{
    [data-testid="stMainBlockContainer"],
    .block-container {{
        padding-left: .7rem !important;
        padding-right: .7rem !important;
    }}
}}
</style>
    """,
    unsafe_allow_html=True,
)

# Persistent controls remain available with the navigation rail open or closed.
with st.container(key="orbidense_zoom_controls"):
    _zoom_out, _zoom_reset, _zoom_in = st.columns([1, 1.35, 1], gap="small")

    with _zoom_out:
        if st.button(
            "−",
            key="orbidense_zoom_out",
            help="Zoom out the full ORBIDENSE interface (maps keep their own map zoom)",
            use_container_width=True,
        ):
            st.session_state["orbidense_ui_scale"] = round(
                max(UI_SCALE_MIN, _ui_scale - UI_SCALE_STEP), 2
            )
            st.rerun()

    with _zoom_reset:
        if st.button(
            f"{int(round(_ui_scale * 100))}%",
            key="orbidense_zoom_reset",
            help="Reset the full ORBIDENSE interface to 100%",
            use_container_width=True,
        ):
            st.session_state["orbidense_ui_scale"] = 1.0
            st.rerun()

    with _zoom_in:
        if st.button(
            "+",
            key="orbidense_zoom_in",
            help="Zoom in the full ORBIDENSE interface (maps keep their own map zoom)",
            use_container_width=True,
        ):
            st.session_state["orbidense_ui_scale"] = round(
                min(UI_SCALE_MAX, _ui_scale + UI_SCALE_STEP), 2
            )
            st.rerun()


DEFAULT_STATE = {
    "selected_city_id": None,
    "selected_location": None,
    "selected_country": None,
    "map_lat": 20.0,
    "map_lon": 0.0,
    "map_zoom": 1.35,
    "map_label": "World",
    "recent_searches": [],
    "history_status": None,
    "history_retry_after_seconds": None,
    "main_navigation": "Home",
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value

# V20: Dashboard was merged into Home.


def safe_float(value):
    if value is None:
        return None
    return float(value)


def fmt(value, pattern, fallback="N/A"):
    if value is None:
        return fallback
    try:
        return format(float(value), pattern)
    except (TypeError, ValueError):
        return fallback


def stable_maptiler_id(maptiler_id):
    value = str(maptiler_id)
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, byteorder="big", signed=False)
    return number & 0x7FFFFFFFFFFFFFFF


def _first_nonempty(*values):
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _normalized_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def maptiler_english_name(feature):
    """
    Prefer an international/English display name.

    MapTiler returns localized fields when a language is
    requested. We also keep safe fallbacks for older result
    shapes.
    """
    properties = feature.get("properties", {})

    return _first_nonempty(
        feature.get("text_en"),
        feature.get("text"),
        properties.get("text_en"),
        properties.get("name_en"),
        properties.get("name"),
        feature.get("name"),
    ) or "Unknown location"


def maptiler_english_place_name(feature):
    properties = feature.get("properties", {})

    return _first_nonempty(
        feature.get("place_name_en"),
        feature.get("place_name"),
        properties.get("place_name_en"),
        properties.get("place_name"),
        maptiler_english_name(feature),
    ) or "Unknown location"


def maptiler_matching_name(feature):
    """
    Preserve the name/script that matched what the user typed.
    This is useful for Urdu, Chinese, Russian, Arabic, etc.
    """
    return _first_nonempty(
        feature.get("matching_text"),
        feature.get("matching_place_name"),
    )


def maptiler_result_label(feature):
    """
    Human-facing search label:
      English/international name first,
      matched local-script alias second when useful.
    """
    english_label = maptiler_english_place_name(feature)
    matched = maptiler_matching_name(feature)

    if matched:
        english_norm = _normalized_text(english_label)
        matched_norm = _normalized_text(matched)

        if (
            matched_norm
            and matched_norm not in english_norm
            and english_norm not in matched_norm
        ):
            return f"{english_label}  ·  {matched}"

    return english_label


def maptiler_feature_type(feature):
    """
    Normalize MapTiler's richer feature taxonomy.

    Important:
    - A feature administratively typed as a region can still
      be a real city (Berlin/Tokyo-style cases). MapTiler's
      place_designation is used first for this reason.
    - Regions/counties are allowed to produce point-based
      climate analytics at their centroid.
    - Countries remain map-only because one country centroid
      is not representative of national climate.
    """
    properties = feature.get("properties", {})

    place_types = feature.get("place_type", [])

    if isinstance(place_types, str):
        place_types = [place_types]

    place_types = {
        str(value).lower()
        for value in place_types
        if value
    }

    designation = str(
        properties.get("place_designation")
        or feature.get("place_designation")
        or ""
    ).lower()

    inhabited_designations = {
        "city",
        "town",
        "village",
        "hamlet",
        "suburb",
        "neighbourhood",
        "quarter",
        "borough",
        "isolated_dwelling",
        "farm",
        "city_block",
    }

    if designation in inhabited_designations:
        return "place"

    if "country" in place_types:
        return "country"

    if place_types.intersection(
        {
            "municipality",
            "joint_municipality",
            "joint_submunicipality",
            "municipal_district",
            "locality",
            "neighbourhood",
            "place",
            "postal_code",
        }
    ):
        return "place"

    if place_types.intersection(
        {
            "region",
            "subregion",
            "county",
        }
    ):
        return "area"

    if place_types.intersection(
        {
            "address",
            "road",
            "poi",
        }
    ):
        return "local_point"

    return "location"


def maptiler_coordinates(feature):
    """
    Return (longitude, latitude).

    MapTiler can return Point geometries or a centroid for
    polygon/administrative features. Prefer the explicit
    center, then a Point geometry.
    """
    center = feature.get("center")

    if (
        isinstance(center, (list, tuple))
        and len(center) >= 2
        and isinstance(center[0], (int, float))
        and isinstance(center[1], (int, float))
    ):
        return float(center[0]), float(center[1])

    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates")

    if (
        geometry.get("type") == "Point"
        and isinstance(coordinates, (list, tuple))
        and len(coordinates) >= 2
        and isinstance(coordinates[0], (int, float))
        and isinstance(coordinates[1], (int, float))
    ):
        return float(coordinates[0]), float(coordinates[1])

    properties = feature.get("properties", {})

    lon = (
        properties.get("lon")
        or properties.get("longitude")
    )

    lat = (
        properties.get("lat")
        or properties.get("latitude")
    )

    if lon is not None and lat is not None:
        return float(lon), float(lat)

    return None


def _context_name(item):
    properties = item.get("properties", {})

    return _first_nonempty(
        item.get("text_en"),
        item.get("text"),
        properties.get("text_en"),
        properties.get("name_en"),
        properties.get("name"),
        item.get("place_name_en"),
        item.get("place_name"),
    )


def extract_context_value(feature, prefixes):
    """
    Extract hierarchy values using either context IDs or
    MapTiler place types, while preferring English labels.
    """
    for item in feature.get("context", []):
        item_id = str(item.get("id", "")).lower()
        item_types = item.get("place_type", [])

        if isinstance(item_types, str):
            item_types = [item_types]

        item_types = {
            str(value).lower()
            for value in item_types
            if value
        }

        item_properties = item.get("properties", {})

        matches_id = any(
            item_id.startswith(prefix)
            for prefix in prefixes
        )

        matches_type = bool(
            item_types.intersection(
                set(prefixes)
            )
        )

        if matches_id or matches_type:
            name = _context_name(item)

            short_code = _first_nonempty(
                item.get("short_code"),
                item_properties.get("short_code"),
                item_properties.get("country_code"),
            )

            return name, short_code

    return None, None


def maptiler_to_climate_location(feature):
    """
    Convert any climate-capable MapTiler feature to the
    database/service location dictionary.

    For regions/counties, ERA5 represents the selected
    centroid/grid point, NOT an area-average climate.
    """
    properties = feature.get("properties", {})
    coordinates = maptiler_coordinates(feature)

    if not coordinates:
        raise ValueError(
            "Selected MapTiler result has no usable coordinates."
        )

    longitude, latitude = coordinates

    name = maptiler_english_name(feature)

    country_name, country_short_code = extract_context_value(
        feature,
        prefixes=("country",),
    )

    admin1, _ = extract_context_value(
        feature,
        prefixes=(
            "region",
            "subregion",
            "state",
            "province",
        ),
    )

    if not country_name:
        country_name = _first_nonempty(
            properties.get("country_name_en"),
            properties.get("country_name"),
            properties.get("country"),
        )

    # Country features may carry their own country code.
    country_code = _first_nonempty(
        country_short_code,
        properties.get("country_code"),
        properties.get("country_code_alpha_2"),
    )

    if country_code:
        country_code = (
            str(country_code)
            .split("-")[-1]
            .upper()
        )

    if not country_name:
        # Safe final fallback: use the last hierarchy item
        # from the English full label.
        english_full = maptiler_english_place_name(feature)

        if "," in english_full:
            country_name = (
                english_full
                .split(",")[-1]
                .strip()
            )

    external_source_id = (
        feature.get("id")
        or f"{name}|{latitude:.6f}|{longitude:.6f}"
    )

    population = (
        properties.get("population")
        or feature.get("population")
    )

    result_type = maptiler_feature_type(feature)

    return {
        "id": stable_maptiler_id(
            external_source_id
        ),
        "name": name,
        "country": country_name,
        "country_code": country_code,
        "admin1": admin1,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "population": population,

        # UI-only metadata. The database upsert safely
        # ignores these extra fields.
        "result_type": result_type,
        "scope_note": (
            "Climate values represent the selected area's "
            "centroid/grid point, not an area-wide average."
            if result_type == "area"
            else None
        ),
        "matched_name": maptiler_matching_name(feature),
    }


def climate_location_label(location):
    parts = []

    for value in [
        location.get("name"),
        location.get("admin1"),
        location.get("country"),
    ]:
        if (
            value
            and str(value) not in parts
        ):
            parts.append(
                str(value)
            )

    label = ", ".join(parts)

    if location.get("country_code"):
        label += (
            f" - "
            f"{location['country_code']}"
        )

    matched_name = location.get(
        "matched_name"
    )

    if (
        matched_name
        and _normalized_text(matched_name)
        not in _normalized_text(label)
    ):
        label += f"  ·  {matched_name}"

    return label or "Selected location"


def update_map_from_feature(feature):
    coordinates = maptiler_coordinates(
        feature
    )

    if not coordinates:
        return

    longitude, latitude = coordinates
    result_type = maptiler_feature_type(
        feature
    )

    st.session_state.map_lon = longitude
    st.session_state.map_lat = latitude
    st.session_state.map_label = (
        maptiler_result_label(
            feature
        )
    )

    zoom_by_type = {
        "country": 4.0,
        "area": 6.5,
        "place": 9.5,
        "local_point": 13.0,
        "location": 10.0,
    }

    st.session_state.map_zoom = (
        zoom_by_type.get(
            result_type,
            9.0,
        )
    )


def add_recent(label):
    recent = list(st.session_state.recent_searches)
    if label in recent:
        recent.remove(label)
    recent.insert(0, label)
    st.session_state.recent_searches = recent[:5]



def clamp_score(
    value,
    low,
    high,
):
    """
    Convert a climate characteristic to a 0–100 descriptive scale.

    These are product-level descriptive indices, NOT hazard/risk
    probabilities and NOT a comparison against a global city database.
    """
    value = safe_float(
        value
    )

    if value is None:
        return None

    if high <= low:
        return 0.0

    score = (
        (value - low)
        / (high - low)
        * 100.0
    )

    return max(
        0.0,
        min(
            100.0,
            score,
        ),
    )


def fingerprint_level(
    score,
    labels=(
        "Low",
        "Moderate",
        "High",
    ),
):
    if score is None:
        return "N/A"

    if score < 34:
        return labels[0]

    if score < 67:
        return labels[1]

    return labels[2]


def build_climate_fingerprint(
    summary,
    warming_rate,
):
    """
    Build a five-axis descriptive Climate Fingerprint.

    Axes
    ----
    Thermal Level:
        1991–2020 mean annual temperature.

    Hot Extremes:
        Baseline average number of >=30°C and >=35°C days.

    Rainfall Amount:
        Baseline mean annual precipitation.

    Rainfall Variability:
        Coefficient of variation of annual precipitation.

    Warming Signal:
        Linear temperature trend in °C/decade.

    The 0–100 scales are intentionally descriptive and use fixed
    engineering anchors. They are not a risk score and do not imply
    that a higher number is universally worse.
    """
    if (
        summary is None
        or summary.empty
    ):
        return None

    baseline = summary[
        (
            summary["year"] >= 1991
        )
        &
        (
            summary["year"] <= 2020
        )
    ].copy()

    if baseline.empty:
        return None

    mean_temp = safe_float(
        baseline[
            "avg_temperature_c"
        ].mean()
    )

    hot30 = safe_float(
        baseline[
            "hot_days_30c"
        ].mean()
    )

    hot35 = safe_float(
        baseline[
            "extreme_hot_days_35c"
        ].mean()
    )

    precip_mean = safe_float(
        baseline[
            "annual_precipitation_mm"
        ].mean()
    )

    precip_std = safe_float(
        baseline[
            "annual_precipitation_mm"
        ].std()
    )

    precip_cv = None

    if (
        precip_mean is not None
        and precip_mean > 0
        and precip_std is not None
    ):
        precip_cv = (
            precip_std
            / precip_mean
        )

    thermal_score = clamp_score(
        mean_temp,
        -5.0,
        30.0,
    )

    hot_score_30 = clamp_score(
        hot30,
        0.0,
        180.0,
    )

    hot_score_35 = clamp_score(
        hot35,
        0.0,
        90.0,
    )

    if (
        hot_score_30 is not None
        and hot_score_35 is not None
    ):
        hot_extreme_score = (
            0.55 * hot_score_30
            + 0.45 * hot_score_35
        )
    else:
        hot_extreme_score = None

    rainfall_score = clamp_score(
        precip_mean,
        150.0,
        2200.0,
    )

    variability_score = clamp_score(
        precip_cv,
        0.08,
        0.45,
    )

    warming_score = clamp_score(
        warming_rate,
        -0.1,
        0.8,
    )

    return {
        "thermal": {
            "score": thermal_score,
            "raw": mean_temp,
            "label": fingerprint_level(
                thermal_score,
                (
                    "Cool",
                    "Temperate",
                    "Warm",
                ),
            ),
            "unit": "°C baseline mean",
        },

        "hot_extremes": {
            "score": hot_extreme_score,
            "raw": hot30,
            "label": fingerprint_level(
                hot_extreme_score,
                (
                    "Limited",
                    "Seasonal",
                    "Frequent",
                ),
            ),
            "unit": "hot-day profile",
        },

        "rainfall": {
            "score": rainfall_score,
            "raw": precip_mean,
            "label": fingerprint_level(
                rainfall_score,
                (
                    "Dry",
                    "Moderate",
                    "Wet",
                ),
            ),
            "unit": "mm/year",
        },

        "variability": {
            "score": variability_score,
            "raw": precip_cv,
            "label": fingerprint_level(
                variability_score,
                (
                    "Stable",
                    "Variable",
                    "Highly variable",
                ),
            ),
            "unit": "year-to-year",
        },

        "warming": {
            "score": warming_score,
            "raw": warming_rate,
            "label": fingerprint_level(
                warming_score,
                (
                    "Weak",
                    "Moderate",
                    "Strong",
                ),
            ),
            "unit": "trend signal",
        },
    }


def fingerprint_signature(
    fingerprint,
):
    if not fingerprint:
        return "Climate profile unavailable"

    return " · ".join(
        [
            fingerprint[
                "thermal"
            ][
                "label"
            ],
            (
                fingerprint[
                    "rainfall"
                ][
                    "label"
                ]
                + " rainfall"
            ),
            (
                fingerprint[
                    "hot_extremes"
                ][
                    "label"
                ]
                + " hot extremes"
            ),
            (
                fingerprint[
                    "warming"
                ][
                    "label"
                ]
                + " warming signal"
            ),
        ]
    )


def fingerprint_score_text(
    value,
):
    if value is None:
        return "N/A"

    return str(
        int(
            round(
                value
            )
        )
    )



def comparison_scope_label(
    result_type,
):
    return {
        "country": "Country centroid proxy",
        "area": "Area centroid",
        "place": "City / settlement",
        "local_point": "Local point",
        "location": "Selected point",
    }.get(
        result_type,
        "Selected point",
    )


def comparison_location_from_feature(
    feature,
):
    """
    Convert search results into a point usable by the comparison page.

    Countries are allowed here ONLY as centroid-based proxies. The UI
    explicitly labels them as such because one point cannot represent
    all climates within a country.
    """
    location = maptiler_to_climate_location(
        feature
    )

    result_type = maptiler_feature_type(
        feature
    )

    if result_type == "country":
        country_name = (
            maptiler_english_name(
                feature
            )
        )

        location[
            "name"
        ] = country_name

        location[
            "country"
        ] = country_name

        location[
            "result_type"
        ] = "country"

        location[
            "scope_note"
        ] = (
            "Country comparison uses the selected country's "
            "MapTiler centroid as a point proxy. It is not "
            "a national area-average climate."
        )

    return location


def comparison_snapshot(
    feature,
    include_future=False,
    future_models=None,
):
    """
    Build one comparison record: historical ERA5, current
    conditions, observed trend and optional CMIP6 ensemble.
    """
    location = comparison_location_from_feature(
        feature
    )
    result_type = maptiler_feature_type(
        feature
    )
    label = maptiler_result_label(
        feature
    )

    record = {
        "label": label,
        "location": location,
        "result_type": result_type,
        "scope": comparison_scope_label(
            result_type
        ),
        "city_id": None,
        "history_status": "not_started",
        "summary": None,
        "anomalies": None,
        "trend": None,
        "current": {},
        "air": {},
        "future_ensemble": None,
    }

    try:
        history_result = ensure_city_history(
            location
        )
        record["city_id"] = history_result.get(
            "city_id"
        )
        record["history_status"] = history_result.get(
            "history_status",
            "loading",
        )
    except Exception:
        record["history_status"] = "unavailable"

    if record["city_id"] is not None:
        try:
            (
                _city,
                record["summary"],
                record["anomalies"],
                record["trend"],
            ) = cached_dashboard_data(
                record["city_id"]
            )
        except Exception:
            pass

    try:
        live = cached_live_environment(
            location["latitude"],
            location["longitude"],
            location.get(
                "timezone",
                "auto",
            ),
        )
        record["current"] = (
            live.get(
                "weather",
                {}
            ).get(
                "current",
                {}
            )
        )
        record["air"] = (
            live.get(
                "air",
                {}
            ).get(
                "current",
                {}
            )
        )
    except Exception:
        pass

    if include_future and future_models:
        try:
            record["future_ensemble"] = (
                cached_midcentury_ensemble(
                    location["latitude"],
                    location["longitude"],
                    tuple(
                        future_models
                    ),
                )
            )
        except Exception:
            record["future_ensemble"] = None

    return record


def comparison_metrics(
    record,
):
    summary_data = record.get(
        "summary"
    )
    anomaly_data = record.get(
        "anomalies"
    )
    trend_data = record.get(
        "trend"
    )

    baseline_temp = None
    baseline_precip = None
    baseline_hot30 = None
    baseline_hot35 = None
    recent_temp = None
    recent_hot30 = None
    latest_anomaly = None
    warming_rate_value = None

    if (
        summary_data is not None
        and not summary_data.empty
        and "year" in summary_data.columns
    ):
        baseline = summary_data[
            (summary_data["year"] >= 1991)
            &
            (summary_data["year"] <= 2020)
        ]
        recent = summary_data[
            (summary_data["year"] >= 2016)
            &
            (summary_data["year"] <= 2025)
        ]

        if not baseline.empty:
            baseline_temp = safe_float(
                baseline["avg_temperature_c"].mean()
            )
            baseline_precip = safe_float(
                baseline[
                    "annual_precipitation_mm"
                ].mean()
            )
            baseline_hot30 = safe_float(
                baseline["hot_days_30c"].mean()
            )
            baseline_hot35 = safe_float(
                baseline[
                    "extreme_hot_days_35c"
                ].mean()
            )

        if not recent.empty:
            recent_temp = safe_float(
                recent["avg_temperature_c"].mean()
            )
            recent_hot30 = safe_float(
                recent["hot_days_30c"].mean()
            )

    if (
        anomaly_data is not None
        and not anomaly_data.empty
    ):
        latest_anomaly = safe_float(
            anomaly_data
            .sort_values("year")
            .iloc[-1]["anomaly_c"]
        )

    if trend_data:
        warming_rate_value = safe_float(
            trend_data.get(
                "warming_rate_c_per_decade"
            )
        )

    current = record.get(
        "current",
        {}
    )
    air = record.get(
        "air",
        {}
    )
    ensemble = record.get(
        "future_ensemble"
    ) or {}

    current_temp = safe_float(
        current.get("temperature_2m")
    )
    current_feels = safe_float(
        current.get("apparent_temperature")
    )
    current_humidity = safe_float(
        current.get("relative_humidity_2m")
    )
    current_aqi = safe_float(
        air.get("european_aqi")
    )

    future_temp_median = safe_float(
        ensemble.get(
            "temperature_median_c"
        )
    )
    future_temp_low = safe_float(
        ensemble.get(
            "temperature_min_c"
        )
    )
    future_temp_high = safe_float(
        ensemble.get(
            "temperature_max_c"
        )
    )

    future_hot30_median = safe_float(
        ensemble.get(
            "hot_days_30c_median"
        )
    )
    future_hot30_low = safe_float(
        ensemble.get(
            "hot_days_30c_min"
        )
    )
    future_hot30_high = safe_float(
        ensemble.get(
            "hot_days_30c_max"
        )
    )

    future_precip_median = safe_float(
        ensemble.get(
            "precipitation_median_mm"
        )
    )
    future_precip_low = safe_float(
        ensemble.get(
            "precipitation_min_mm"
        )
    )
    future_precip_high = safe_float(
        ensemble.get(
            "precipitation_max_mm"
        )
    )

    recent_temp_delta = None
    if (
        recent_temp is not None
        and baseline_temp is not None
    ):
        recent_temp_delta = (
            recent_temp
            - baseline_temp
        )

    future_temp_delta = None
    if (
        future_temp_median is not None
        and baseline_temp is not None
    ):
        future_temp_delta = (
            future_temp_median
            - baseline_temp
        )

    return {
        "baseline_temp": baseline_temp,
        "baseline_precip": baseline_precip,
        "baseline_hot30": baseline_hot30,
        "baseline_hot35": baseline_hot35,
        "recent_temp": recent_temp,
        "recent_hot30": recent_hot30,
        "recent_temp_delta": recent_temp_delta,
        "current_temp": current_temp,
        "current_feels": current_feels,
        "current_humidity": current_humidity,
        "current_aqi": current_aqi,
        "latest_anomaly": latest_anomaly,
        "warming_rate": warming_rate_value,
        "future_temp_median": future_temp_median,
        "future_temp_low": future_temp_low,
        "future_temp_high": future_temp_high,
        "future_temp_delta": future_temp_delta,
        "future_hot30_median": future_hot30_median,
        "future_hot30_low": future_hot30_low,
        "future_hot30_high": future_hot30_high,
        "future_precip_median": future_precip_median,
        "future_precip_low": future_precip_low,
        "future_precip_high": future_precip_high,
        "future_model_count": ensemble.get(
            "model_count",
            0,
        ),
        "future_temp_agreement": ensemble.get(
            "temperature_agreement",
            "Not available",
        ),
        "future_hot_agreement": ensemble.get(
            "hot_days_agreement",
            "Not available",
        ),
        "future_precip_agreement": ensemble.get(
            "precipitation_agreement",
            "Not available",
        ),
    }


def comparison_verdict(
    records,
):
    if not records:
        return {}

    metrics_by_label = {
        record["label"]: comparison_metrics(
            record
        )
        for record in records
    }

    def max_label(key):
        available = [
            (
                label,
                values.get(key),
            )
            for label, values
            in metrics_by_label.items()
            if values.get(key) is not None
        ]
        if not available:
            return "Not enough data"
        return max(
            available,
            key=lambda row: row[1],
        )[0]

    return {
        "warmest_now": max_label(
            "current_temp"
        ),
        "fastest_historical_warming": max_label(
            "warming_rate"
        ),
        "most_baseline_hot_days": max_label(
            "baseline_hot30"
        ),
        "highest_future_heat": max_label(
            "future_temp_median"
        ),
        "largest_future_warming": max_label(
            "future_temp_delta"
        ),
    }


def comparison_narrative(
    records,
):
    verdict = comparison_verdict(
        records
    )
    parts = []

    warmest = verdict.get(
        "warmest_now"
    )
    fastest = verdict.get(
        "fastest_historical_warming"
    )
    future = verdict.get(
        "highest_future_heat"
    )

    if warmest not in {
        None,
        "Not enough data",
    }:
        parts.append(
            f"{warmest} is currently warmest among "
            f"the selected locations."
        )

    if fastest not in {
        None,
        "Not enough data",
    }:
        parts.append(
            f"{fastest} has the largest observed historical "
            f"warming rate in the available ERA5 record."
        )

    if future not in {
        None,
        "Not enough data",
    }:
        parts.append(
            f"The CMIP6 ensemble gives {future} the highest "
            f"median mid-century mean temperature among "
            f"the selected locations."
        )

    if not parts:
        return (
            "More historical or future data are needed "
            "for a comparative verdict."
        )

    return " ".join(parts)


def alpha3_country_code(
    country_code,
):
    if not country_code:
        return None

    value = str(country_code).strip().upper()

    if len(value) == 3:
        return value

    try:
        import pycountry

        country = pycountry.countries.get(
            alpha_2=value
        )

        if country:
            return country.alpha_3

    except Exception:
        pass

    return None


def selected_feature_iso3(
    feature,
):
    try:
        location = maptiler_to_climate_location(
            feature
        )

        return alpha3_country_code(
            location.get(
                "country_code"
            )
        )

    except Exception:
        return None


def today_normal_label(
    percentile,
):
    if percentile is None:
        return (
            "Historical context unavailable",
            "#92a7b8",
        )

    value = float(
        percentile
    )

    if value >= 97:
        return (
            "Exceptionally hot",
            "#ff5b5b",
        )

    if value >= 90:
        return (
            "Unusually hot",
            "#ff8a55",
        )

    if value >= 75:
        return (
            "Warmer than typical",
            "#ffb35c",
        )

    if value <= 3:
        return (
            "Exceptionally cool",
            "#4da8ff",
        )

    if value <= 10:
        return (
            "Unusually cool",
            "#62b8ff",
        )

    if value <= 25:
        return (
            "Cooler than typical",
            "#7dc7ff",
        )

    return (
        "Within the typical range",
        "#63dc91",
    )


def safe_date_label(
    value,
):
    if value is None:
        return "N/A"

    try:
        return value.strftime(
            "%d %b %Y"
        )
    except AttributeError:
        return str(value)


def aqi_note(aqi):
    if aqi is None:
        return "AQI unavailable"
    try:
        value = float(aqi)
    except (TypeError, ValueError):
        return "AQI unavailable"
    if value <= 20:
        return "Very good"
    if value <= 40:
        return "Good"
    if value <= 60:
        return "Moderate"
    if value <= 80:
        return "Poor"
    if value <= 100:
        return "Very poor"
    return "Extremely poor"


def map_style_url(style_name):
    if style_name == "Street":
        return "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    if style_name == "Dark":
        return "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    if MAPTILER_KEY:
        return f"https://api.maptiler.com/maps/satellite/style.json?key={MAPTILER_KEY}"
    return "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


def build_map(style_name):
    df = pd.DataFrame({
        "label": [st.session_state.map_label],
        "latitude": [st.session_state.map_lat],
        "longitude": [st.session_state.map_lon],
    })
    marker = pdk.Layer(
        "ScatterplotLayer", data=df, get_position=["longitude", "latitude"],
        get_radius=120, radius_min_pixels=7, radius_max_pixels=16,
        get_fill_color=[255,82,82,235], get_line_color=[255,255,255,240],
        line_width_min_pixels=2, stroked=True, filled=True, pickable=True,
    )
    view = pdk.ViewState(
        latitude=st.session_state.map_lat, longitude=st.session_state.map_lon,
        zoom=st.session_state.map_zoom, pitch=0, bearing=0,
    )
    return pdk.Deck(
        map_style=map_style_url(style_name), initial_view_state=view, layers=[marker],
        tooltip={"html": "<b>{label}</b>", "style": {"backgroundColor": "#07111c", "color": "#ffffff"}},
    )


@st.fragment
def render_map_fragment():
    """
    Map-style changes rerun only this fragment instead
    of re-executing SQL, weather, AQI, and charts.
    """
    with st.container(border=True):
        map_style_name = st.segmented_control(
            "Map style",
            options=[
                "Street",
                "Dark",
                "Satellite",
            ],
            default="Street",
            key="map_style_selector",
            label_visibility="collapsed",
        ) or "Street"

        st.pydeck_chart(
            build_map(map_style_name),
            width="stretch",
            height=330,
        )


def style_plotly(
    fig,
    height=290,
    y_title=None,
):
    fig = style_plotly_v27(
        fig
    )

    fig.update_layout(
        height=height,
        margin=dict(
            l=42,
            r=24,
            t=35,
            b=35,
        ),
        hovermode="x unified",
    )

    if y_title:
        fig.update_yaxes(
            title=y_title
        )

    return fig

def cached_dashboard_data(city_id):
    """
    Load the four PostgreSQL dashboard datasets in parallel
    and keep the result cached for six hours.

    Historical ERA5 analytics change very rarely, so a long
    cache dramatically reduces repeat Neon round trips.
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        city_future = executor.submit(
            get_city_details,
            city_id,
        )
        summary_future = executor.submit(
            get_annual_climate_summary,
            city_id,
        )
        anomaly_future = executor.submit(
            get_temperature_anomalies,
            city_id,
        )
        trend_future = executor.submit(
            get_climate_trend,
            city_id,
        )

        city = city_future.result()
        summary = summary_future.result()
        anomalies = anomaly_future.result()
        trend = trend_future.result()

    return city, summary, anomalies, trend


@st.cache_data(
    ttl=600,
    max_entries=128,
    show_spinner=False,
)
def cached_live_environment(
    latitude,
    longitude,
    timezone,
):
    """Canonical current-weather + AQI bundle.

    Performance V2 routes point live conditions through the same compact
    provider bundle used by Home. This removes duplicate Open-Meteo calls
    when current weather and AQI are requested together.
    """
    return get_home_environment(latitude, longitude, timezone)


@st.cache_data(
    ttl=600,
    max_entries=256,
    show_spinner=False,
)
def cached_home_bundle_for_app(latitude, longitude, timezone):
    """One consolidated Home request for live weather, forecast and AQI."""
    return get_home_environment(latitude, longitude, timezone)


@st.cache_data(
    ttl=1800,
    max_entries=128,
    show_spinner=False,
)
def cached_today_forecast(
    latitude,
    longitude,
    timezone,
):
    return get_today_forecast(
        latitude,
        longitude,
        timezone=timezone,
    )


@st.cache_data(
    ttl=21600,
    max_entries=128,
    show_spinner=False,
)
def cached_today_climate_context(
    city_id,
    target_date,
    forecast_high_c,
    forecast_low_c,
):
    return get_today_climate_context(
        city_id=city_id,
        target_date=target_date,
        forecast_high_c=forecast_high_c,
        forecast_low_c=forecast_low_c,
        window_days=7,
    )


@st.cache_data(
    ttl=86400,
    max_entries=128,
    show_spinner=False,
)
def cached_midcentury_ensemble(
    latitude,
    longitude,
    model_names,
):
    """Cache one multi-model future ensemble for 24 hours."""
    return get_midcentury_ensemble(
        latitude=latitude,
        longitude=longitude,
        model_names=tuple(
            model_names
        ),
    )


@st.cache_data(
    ttl=43200,
    max_entries=256,
    show_spinner=False,
)
def cached_country_historical_climate(
    iso3_code,
):
    """
    National spatial-average historical climate from
    World Bank CCKP / CRU.
    """
    return get_country_historical_climate(
        iso3_code=iso3_code,
    )


@st.cache_data(
    ttl=86400,
    max_entries=64,
    show_spinner=False,
)
def cached_country_projection_rankings(
    scenario,
    period,
):
    return get_country_projection_rankings(
        scenario=scenario,
        period=period,
    )


@st.cache_data(
    ttl=86400,
    max_entries=256,
    show_spinner=False,
)
def cached_country_scenario_trajectory(
    iso3_code,
    scenario,
):
    return get_country_scenario_trajectory(
        iso3_code=iso3_code,
        scenario=scenario,
    )


@st.cache_data(
    ttl=3600,
    max_entries=256,
    show_spinner=False,
)
def cached_maptiler_search(query):
    """
    Cache autocomplete results for one hour.
    MapTiler is asked to return English/international names,
    while matching_* fields preserve local-script matches.
    """
    return search_maptiler_places(
        query,
        limit=10,
        language="en",
    )


def _search_priority(feature):
    result_type = maptiler_feature_type(
        feature
    )

    return {
        "place": 0.18,
        "area": 0.12,
        "local_point": 0.08,
        "country": 0.05,
        "location": 0.00,
    }.get(
        result_type,
        0.00,
    )


def _feature_search_score(
    feature,
    query,
):
    relevance = safe_float(
        feature.get("relevance")
    ) or 0.0

    score = relevance + _search_priority(
        feature
    )

    query_norm = _normalized_text(
        query
    )

    candidates = [
        maptiler_english_name(feature),
        maptiler_matching_name(feature),
        feature.get("matching_place_name"),
    ]

    for candidate in candidates:
        candidate_norm = _normalized_text(
            candidate
        )

        if not candidate_norm:
            continue

        if candidate_norm == query_norm:
            score += 0.30

        elif (
            candidate_norm.startswith(
                query_norm
            )
            or query_norm.startswith(
                candidate_norm
            )
        ):
            score += 0.15

    return score


def global_search(search_term):
    """
    Fast multilingual autocomplete with international
    English display labels.

    Small settlements and administrative areas are retained
    instead of being discarded solely because they are not
    typed as a major city.
    """
    query = search_term.strip()

    if len(query) < 2:
        return []

    try:
        features = cached_maptiler_search(
            query
        )

    except Exception as error:
        print(
            "MapTiler search error:",
            error,
        )
        return []

    ranked = []
    seen = set()

    for feature in features:
        coordinates = maptiler_coordinates(
            feature
        )

        if not coordinates:
            continue

        longitude, latitude = coordinates

        result = dict(feature)

        result["result_type"] = (
            maptiler_feature_type(
                feature
            )
        )

        result["map_lon"] = longitude
        result["map_lat"] = latitude

        label = maptiler_result_label(
            feature
        )

        # Deduplicate repeated hierarchy variants.
        dedupe_key = (
            _normalized_text(label),
            round(latitude, 5),
            round(longitude, 5),
        )

        if dedupe_key in seen:
            continue

        seen.add(
            dedupe_key
        )

        ranked.append(
            (
                _feature_search_score(
                    feature,
                    query,
                ),
                label,
                result,
            )
        )

    ranked.sort(
        key=lambda row: row[0],
        reverse=True,
    )

    return [
        (label, result)
        for _, label, result in ranked[:10]
    ]


# =========================================================
# PRIVATE DEVELOPER ACCESS
# =========================================================

def _read_private_setting(name):
    """Read a private setting from Streamlit Secrets first, then .env."""
    try:
        if name in st.secrets:
            value = st.secrets[name]
            return str(value).strip() if value is not None else None
    except Exception:
        pass

    value = os.getenv(name)
    return str(value).strip() if value else None


def get_analytics_password():
    """Read the private developer password from Secrets / .env."""
    return _read_private_setting("ANALYTICS_PASSWORD")


def get_analytics_dev_key():
    """
    Read the private developer URL gate key.

    This key is deliberately separate from ANALYTICS_PASSWORD. A visitor must
    first know the exact private gate key before the Developer Analytics item is
    revealed, and must then enter the separate analytics password.
    """
    return _read_private_setting("ANALYTICS_DEV_KEY")


def _clean_developer_query_parameter():
    """
    Remove the developer gate token from the visible URL after it is accepted.

    Streamlit's query-parameter API updates the browser URL. We preserve any
    unrelated query parameters instead of clearing the entire query string.
    """
    try:
        current = st.query_params.to_dict()
        if "cp_gate" in current:
            current.pop("cp_gate", None)
            st.query_params.from_dict(current)
    except Exception:
        # URL cleanup is a privacy convenience; access control does not depend
        # on it succeeding because the validated gate state is session-scoped.
        pass


def developer_mode_requested():
    """
    Open the private developer gate only when the supplied URL token exactly
    matches ANALYTICS_DEV_KEY. A memorable key of 8+ characters is accepted.

    Public visitors see no Developer Analytics navigation item. The accepted
    gate is remembered only in this Streamlit browser session. The long token
    is removed from the visible URL immediately after validation.

    Example:
        ?cp_gate=<your-long-random-secret>

    The dashboard still requires the separate ANALYTICS_PASSWORD.
    """
    if st.session_state.get("cp_developer_gate_open", False):
        return True

    expected_key = get_analytics_dev_key()
    if not expected_key:
        return False

    # Allow a memorable developer key, but still refuse extremely short
    # values. The separate ANALYTICS_PASSWORD remains the second security layer.
    if len(expected_key) < 8:
        return False

    try:
        provided_key = st.query_params.get("cp_gate")
        if isinstance(provided_key, list):
            provided_key = provided_key[0] if provided_key else None
        provided_key = str(provided_key or "").strip()
    except Exception:
        provided_key = ""

    if not provided_key:
        return False

    if hmac.compare_digest(provided_key, expected_key):
        st.session_state["cp_developer_gate_open"] = True
        _clean_developer_query_parameter()
        return True

    # A wrong gate key reveals nothing and never opens developer mode.
    return False


DEVELOPER_MODE = bool(developer_mode_requested())

# Public visitors never receive Streamlit exception/traceback surfaces.
# Developer mode retains full diagnostics inside the private console.
if not DEVELOPER_MODE:
    st.html(
        """
<style>
[data-testid="stException"],
[data-testid="stExceptionDetails"],
div[data-testid="stAlert"] pre,
div[data-testid="stAlert"] code {
    display: none !important;
}
</style>
        """
    )

# A stale authentication flag from an older app session must never bypass the
# secret developer gate.
if not DEVELOPER_MODE:
    st.session_state["cp_analytics_authenticated"] = False


with st.sidebar:

    # =====================================================
    # ORBIDENSE — COMMAND SIDEBAR
    # =====================================================
    # Visual redesign only. All existing route values remain unchanged.

    if APP_LOGO_PATH.exists():
        st.image(
            str(APP_LOGO_PATH),
            width="stretch",
        )
    else:
        st.markdown(
            """
<div class="cp-brand" style="text-align:center; margin:38px 0 20px;">
    ORBIDENSE
</div>
            """,
            unsafe_allow_html=True,
        )

    # Dashboard remains in the codebase but is intentionally removed from
    # the visible navigation because Home already contains the main dashboard.
    if st.session_state.get("main_navigation") == "Dashboard":
        st.session_state["main_navigation"] = "Home"

    # Public users never see Developer Analytics.
    # Product simplification: Home already owns live map exploration.
    # The former Timeline/Trends pages are rebuilt as two distinct evidence products.
    legacy_routes = {
        "Map Explorer": "Home",
        "Climate Timeline": "Country Climate Outlook",
        "Climate Trends": "Climate Action & Progress",
        "Data & Methods": "Country Climate Outlook",
    }
    current_route = st.session_state.get("main_navigation")
    if current_route in legacy_routes:
        st.session_state["main_navigation"] = legacy_routes[current_route]


    # ORBIDENSE intelligence redesign:
    # normalize stale browser/session routes from previous public navigation.
    _legacy_public_routes = {
        "Dashboard": "Home",
        "Map Explorer": "Home",
        "Climate Timeline": "Climate Outlook",
        "Climate Trends": "Climate Outlook",
        "Country Climate Outlook": "Climate Outlook",
        "Climate Action & Progress": "Climate Action",
        "Compare Places": "Compare",
        "Global Rankings": "Global Insights",
        "Data & Methods": "About",
    }
    _legacy_current = st.session_state.get("main_navigation")
    if _legacy_current in _legacy_public_routes:
        st.session_state["main_navigation"] = _legacy_public_routes[_legacy_current]


    navigation_options = [
        "Home",
        "Climate Outlook",
        "Climate Action",
        "Compare",
        "Global Insights",
        "About",
    ]

    # The existing private developer gate is the only condition that reveals
    # Developer Analytics. Nothing developer-specific is exposed publicly.
    if DEVELOPER_MODE:
        navigation_options.insert(-1, "Developer Analytics")

    # Recover safely from stale sessions that referenced an older analytics item.
    if st.session_state.get("main_navigation") == "Analytics":
        st.session_state["main_navigation"] = (
            "Developer Analytics" if DEVELOPER_MODE else "Home"
        )

    st.markdown(
        '<div class="orbidense-side-section">Main Navigation</div>',
        unsafe_allow_html=True,
    )

    nav_view = st.session_state.get("main_navigation", "Home")
    # -----------------------------------------------------
    # PRIVATE SYSTEM STATUS
    # -----------------------------------------------------
    # This entire block is developer-only. Public users never receive a
    # System Status panel in the sidebar.
    if DEVELOPER_MODE:
        st.markdown(
            '<div class="orbidense-side-section">System Status</div>',
            unsafe_allow_html=True,
        )

        analytics_state = (
            "Analytics database ready"
            if ANALYTICS_READY
            else "Analytics database unavailable"
        )

        st.markdown(
            f"""
<div class="orbidense-dev-status">
    <div class="orbidense-dev-status-top">
        <span class="orbidense-dev-dot"></span>
        <span>Developer mode active</span>
    </div>
    <div class="orbidense-dev-status-sub">
        {analytics_state}<br>
        Private session · developer-only controls
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# FIRST-PARTY AUDIENCE ANALYTICS — NATIVE STREAMLIT CONTEXT
# =========================================================
# No custom JavaScript component is used here. Streamlit 1.61 exposes locale,
# timezone, theme, URL, embedding status and request headers through st.context.
# This avoids component-rendering failures while preserving useful analytics.
# Developer sessions are excluded, and localhost is excluded by default.

AUDIENCE_ANALYTICS_READY = False
LOCAL_ANALYTICS_SESSION = False

try:
    LOCAL_ANALYTICS_SESSION = is_local_session()
except Exception:
    LOCAL_ANALYTICS_SESSION = False

SHOULD_TRACK_AUDIENCE = bool(
    ANALYTICS_READY
    and not DEVELOPER_MODE
    and (
        not LOCAL_ANALYTICS_SESSION
        or track_local_sessions_enabled()
    )
)

if SHOULD_TRACK_AUDIENCE:
    try:
        context_allowed = capture_streamlit_context()

        if context_allowed:
            AUDIENCE_ANALYTICS_READY = True
            track_pageview(nav_view)
            render_analytics_heartbeat(nav_view)

    except Exception as analytics_tracking_error:
        # Analytics must never be allowed to break the climate application.
        AUDIENCE_ANALYTICS_READY = False
        print(
            "ORBIDENSE analytics tracking error:",
            analytics_tracking_error,
        )

# =========================================================
# PRIVATE DEVELOPER ANALYTICS PAGE
# =========================================================
# Normal visitors cannot see this item. To reveal it, the developer opens:
#   http://localhost:8501/?cp_gate=<ANALYTICS_DEV_KEY>
# or the deployed app URL with the same long secret gate key, then enters
# the separate ANALYTICS_PASSWORD. The gate token is removed from the visible
# URL after validation and remembered only for the current Streamlit session.

if nav_view == "Developer Analytics":

    if not DEVELOPER_MODE:
        st.session_state["main_navigation"] = "Home"
        st.rerun()

    if not ANALYTICS_READY:
        st.error(
            "Developer analytics could not connect to the ORBIDENSE database."
        )

        if ANALYTICS_INIT_ERROR:
            with st.expander("Technical detail", expanded=False):
                st.code(ANALYTICS_INIT_ERROR)

        st.stop()

    expected_dev_key = get_analytics_dev_key()
    expected_password = get_analytics_password()

    if not expected_dev_key or len(expected_dev_key) < 8:
        st.warning(
            "Developer analytics is locked because ANALYTICS_DEV_KEY is missing "
            "or shorter than 8 characters."
        )
        st.caption(
            "Use your own memorable private key (8+ characters) and store it only "
            "in .env / Streamlit Secrets."
        )
        st.stop()

    if not expected_password:
        st.warning(
            "Developer analytics is locked because ANALYTICS_PASSWORD is not configured."
        )
        st.caption(
            "Add ANALYTICS_PASSWORD to your local .env and to your deployment secrets."
        )
        st.stop()

    authenticated = bool(
        st.session_state.get("cp_analytics_authenticated", False)
    )

    if not authenticated:
        st.markdown("## ▥ ORBIDENSE Developer Analytics")
        st.caption("Private developer access · not part of public navigation")

        entered_password = st.text_input(
            "Developer analytics password",
            type="password",
            key="cp_analytics_password_input_v40",
        )

        login_col, _ = st.columns([1, 3])

        with login_col:
            login_clicked = st.button(
                "Unlock analytics",
                type="primary",
                width="stretch",
                key="cp_analytics_login_v40",
            )

        if login_clicked:
            if hmac.compare_digest(
                entered_password or "",
                expected_password,
            ):
                st.session_state["cp_analytics_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect developer password.")

        st.stop()

    # Import the heavy dashboard only after developer authentication.
    # This keeps public ORBIDENSE resilient even if the optional
    # analytics dashboard has a local dependency problem.
    try:
        from src.analytics_dashboard import render_analytics_dashboard

        render_analytics_dashboard()
    except Exception as dashboard_error:
        st.error(
            "Developer analytics dashboard could not be rendered. "
            "The public ORBIDENSE application remains available."
        )
        with st.expander("Developer analytics technical detail", expanded=True):
            st.exception(dashboard_error)

    logout_col, _ = st.columns([1, 4])
    with logout_col:
        if st.button(
            "Lock developer analytics",
            key="cp_analytics_logout_v40",
            width="stretch",
        ):
            st.session_state["cp_analytics_authenticated"] = False
            st.session_state["cp_developer_gate_open"] = False
            st.session_state["main_navigation"] = "Home"
            st.rerun()

    st.stop()

# =========================================================
# SEARCHBOX VISUAL THEME
# =========================================================
# streamlit-searchbox is a React component, so styling its inner control
# through ordinary Streamlit CSS is unreliable. These overrides are applied
# directly inside the component while preserving the existing autocomplete
# behavior.

GLOBAL_SEARCHBOX_STYLE = {
    "dropdown": {
        "rotate": True,
        "width": 18,
        "height": 18,
        "stroke": "#63dff7",
        "fill": "none",
    },
    "clear": {
        "width": 18,
        "height": 18,
        "icon": "cross",
        "stroke": "#8ba6b7",
        "clearable": "always",
    },
    "searchbox": {
        "control": {
            "backgroundColor": "#0a1b2a",
            "border": "1px solid rgba(83, 204, 239, 0.25)",
            "borderRadius": "12px",
            "minHeight": "46px",
            "boxShadow": "0 8px 22px rgba(0, 0, 0, 0.20)",
            "cursor": "text",
        },
        "input": {
            "color": "#f4fbff",
            "fontSize": "15px",
            "fontWeight": 550,
        },
        "placeholder": {
            "color": "#829bad",
            "fontSize": "14px",
        },
        "singleValue": {
            "color": "#f5fbff",
            "fontSize": "15px",
            "fontWeight": 650,
        },
        "menuList": {
            "backgroundColor": "#081725",
            "border": "1px solid rgba(83, 204, 239, 0.16)",
            "borderRadius": "10px",
            "paddingTop": "5px",
            "paddingBottom": "5px",
            "boxShadow": "0 18px 40px rgba(0,0,0,.34)",
        },
        "option": {
            "color": "#dceaf3",
            "backgroundColor": "#081725",
            "fontSize": "14px",
            "paddingTop": "10px",
            "paddingBottom": "10px",
            "highlightColor": "rgba(72, 205, 238, .20)",
        },
    },
}


# =========================================================
# TOP SEARCH BAR
# =========================================================
#
# Global Place Search is intentionally limited to the two
# location-discovery views:
#
#   • Home
#   • Map Explorer
#
# Other pages keep their own page-specific controls and do
# not inherit this large search/header block.
# =========================================================

def _header_global_pulse_html():
    """Return four compact live-global indicators for the Home header."""
    try:
        frame = cached_country_field()
        if frame is None or frame.empty:
            raise RuntimeError("No live country rows")

        def extreme(column, largest=True):
            values = pd.to_numeric(frame[column], errors="coerce")
            valid = values.dropna()
            if valid.empty:
                return None
            idx = valid.idxmax() if largest else valid.idxmin()
            return frame.loc[idx]

        hottest = extreme("temperature_c", True)
        coldest = extreme("temperature_c", False)
        windiest = extreme("wind_kmh", True)
        wettest = extreme("precipitation_mm", True)

        def card(label, row, column, suffix, decimals=1):
            if row is None:
                value, place = "—", "Live data"
            else:
                raw = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
                value = f"{raw:.{decimals}f}{suffix}" if pd.notna(raw) else "—"
                place = str(row.get("country", "—"))
            return f"""
<div class="orbidense-pulse-mini">
  <div class="orbidense-pulse-label">{label}</div>
  <div class="orbidense-pulse-value">{value}</div>
  <div class="orbidense-pulse-place">{place}</div>
</div>
"""

        return (
            '<div class="orbidense-pulse-strip">'
            + card("Hottest", hottest, "temperature_c", "°C")
            + card("Coldest", coldest, "temperature_c", "°C")
            + card("Wind", windiest, "wind_kmh", " km/h", 0)
            + card("Rain", wettest, "precipitation_mm", " mm")
            + '</div>'
        )
    except Exception:
        return ""


selected_search_result = None

# The legacy pre-router Home header/search was intentionally removed.
# Public branding, navigation and search are rendered once by the
# ORBIDENSE site router / Home renderer. This prevents the old AI-branded
# header from flashing during initial load and removes duplicate page chrome.



# =========================================================
# HANDLE SEARCH RESULT
# =========================================================

pending_location = None

if selected_search_result:

    result_type = selected_search_result.get(
        "result_type",
        "location",
    )

    # The map always follows a valid search selection.
    update_map_from_feature(
        selected_search_result
    )

    selected_label = (
        maptiler_result_label(
            selected_search_result
        )
    )

    add_recent(
        selected_label
    )

    if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
        try:
            track_event_once(
                f"search::{result_type}::{selected_label}",
                "search_select",
                category="search",
                page_name=nav_view,
                metadata={
                    "label": selected_label,
                    "result_type": result_type,
                    "country_code": (
                        selected_search_result.get("properties", {}).get("country_code")
                        if isinstance(selected_search_result.get("properties"), dict)
                        else None
                    ),
                },
            )
        except Exception as analytics_event_error:
            print("ORBIDENSE search analytics error:", analytics_event_error)

    # -----------------------------------------------------
    # COUNTRY
    # -----------------------------------------------------
    # Countries remain map-only. A single country centroid
    # would be scientifically misleading as "the climate of
    # the country".
    if result_type == "country":

        st.session_state.selected_country = (
            selected_search_result
        )

        st.session_state.selected_city_id = None
        st.session_state.selected_location = None
        st.session_state.history_status = None
        st.session_state.history_retry_after_seconds = None

    # -----------------------------------------------------
    # PLACE / AREA / LOCAL POINT
    # -----------------------------------------------------
    # Cities, towns, villages, hamlets, neighbourhoods,
    # municipalities, regions/counties, addresses and POIs
    # can all be represented by a coordinate for point-based
    # weather/reanalysis.
    else:

        try:
            pending_location = (
                maptiler_to_climate_location(
                    selected_search_result
                )
            )

        except Exception as error:
            record_error(
                error,
                component="location_search",
                operation="maptiler_to_climate_location",
                page_name=nav_view,
                severity="warning",
            )


# =========================================================
# AUTO-LOAD SELECTED LOCATION
# =========================================================

if pending_location:

    pending_id = pending_location.get(
        "id"
    )

    current_loaded_location = (
        st.session_state.get(
            "selected_location"
        )
    )

    current_loaded_id = None

    if current_loaded_location:
        current_loaded_id = (
            current_loaded_location.get(
                "id"
            )
        )

    if pending_id != current_loaded_id:

        # Critical V21 behavior:
        # keep the searched point immediately, BEFORE historical import.
        # This prevents a previous country selection from remaining active
        # when a small/local place has slow or unavailable ERA5 history.
        st.session_state.selected_location = (
            pending_location
        )

        st.session_state.selected_country = None
        st.session_state.selected_city_id = None

        st.session_state.history_status = (
            "loading"
        )

        st.session_state.history_retry_after_seconds = None

        try:
            result = ensure_city_history(
                pending_location
            )

            st.session_state.selected_city_id = (
                result.get(
                    "city_id"
                )
            )

            st.session_state.history_status = (
                result.get(
                    "history_status",
                    "loading",
                )
            )

        except Exception:
            # Live weather should still work from selected_location.
            st.session_state.history_status = (
                "unavailable"
            )

        st.rerun()



# =========================================================
# V27 BROWSER-LOCATION AUTO SYNC
# =========================================================
#
# Home's browser geolocation runs after the main app search logic.  When it
# succeeds it sets v27_location_sync_pending and reruns.  On this next pass,
# make that browser point the actual global ORBIDENSE selection BEFORE
# dashboard/history variables are created.
# =========================================================

if st.session_state.get(
    "v27_location_sync_pending"
):
    browser_point = st.session_state.get(
        "v21_browser_location"
    )

    if browser_point:
        if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
            try:
                track_event_once(
                    "browser_location_used",
                    "browser_location_used",
                    category="location",
                    page_name=nav_view,
                    metadata={
                        "source": "browser_geolocation",
                        "country_code": browser_point.get("country_code"),
                        "result_type": browser_point.get("result_type", "location"),
                    },
                )
            except Exception as analytics_event_error:
                print("ORBIDENSE location analytics error:", analytics_event_error)

        browser_id = browser_point.get(
            "id"
        )

        current_point = st.session_state.get(
            "selected_location"
        )

        current_id = (
            current_point.get(
                "id"
            )
            if isinstance(
                current_point,
                dict,
            )
            else None
        )

        if browser_id != current_id:
            st.session_state.selected_location = (
                browser_point
            )
            st.session_state.selected_country = None
            st.session_state.selected_city_id = None
            st.session_state.history_status = (
                "loading"
            )
            st.session_state.history_retry_after_seconds = None

            try:
                browser_history = ensure_city_history(
                    browser_point
                )

                st.session_state.selected_city_id = (
                    browser_history.get(
                        "city_id"
                    )
                )

                st.session_state.history_status = (
                    browser_history.get(
                        "history_status",
                        "loading",
                    )
                )
            except Exception:
                # Live weather remains immediately available even if ERA5
                # history is not yet ready.
                st.session_state.history_status = (
                    "unavailable"
                )

        st.session_state[
            "v27_location_sync_pending"
        ] = False

        # One clean rerun guarantees every downstream page sees the new
        # location and any newly resolved DB city/history id.
        st.rerun()


# =========================================================
# CITY / PLACE DATA
# =========================================================

city = None
summary = None
anomalies = None
trend = None
current_weather = {}
current_air = {}

# Keep the searched location useful immediately, even before a DB history job
# finishes. If a DB-backed city exists later, it becomes the richer source.
active_point_location = (
    st.session_state.get(
        "selected_location"
    )
)

if st.session_state.selected_city_id is not None:
    city_id = st.session_state.selected_city_id

    try:
        (
            city,
            summary,
            anomalies,
            trend,
        ) = cached_dashboard_data(
            city_id
        )

    except Exception:
        city = None
        summary = None
        anomalies = None
        trend = None

    if city is not None:
        active_point_location = city

# Normalize numeric historical columns when DB history exists.
if (
    summary is not None
    and not summary.empty
):
    for column in [
        "avg_temperature_c",
        "avg_max_temperature_c",
        "avg_min_temperature_c",
        "hottest_day_c",
        "coldest_day_c",
        "annual_precipitation_mm",
        "hot_days_30c",
        "extreme_hot_days_35c",
    ]:
        if column in summary.columns:
            summary[column] = pd.to_numeric(
                summary[column],
                errors="coerce",
            )

if (
    anomalies is not None
    and not anomalies.empty
):
    for column in [
        "annual_temperature_c",
        "baseline_temperature_c",
        "anomaly_c",
    ]:
        if column in anomalies.columns:
            anomalies[column] = pd.to_numeric(
                anomalies[column],
                errors="coerce",
            )

# Live point weather should not depend on database history.
# Home uses the same consolidated payload as its weather strip, avoiding
# duplicate current-weather/AQI requests before the page renders.
home_live_bundle = None
if active_point_location:
    try:
        if nav_view == "Home":
            home_live_bundle = cached_home_bundle_for_app(
                active_point_location["latitude"],
                active_point_location["longitude"],
                active_point_location.get("timezone", "auto"),
            )
            live_environment = home_live_bundle
        else:
            live_environment = cached_live_environment(
                active_point_location["latitude"],
                active_point_location["longitude"],
                active_point_location.get("timezone", "auto"),
            )

        current_weather = live_environment.get("weather", {}).get("current", {})
        current_air = live_environment.get("air", {}).get("current", {})

    except Exception:
        current_weather = {}
        current_air = {}

# Historical fallback for a point when DB history is missing.
@st.cache_data(
    ttl=86400,
    max_entries=64,
    show_spinner=False,
)
def cached_point_history(
    latitude,
    longitude,
):
    return get_point_history(
        float(latitude),
        float(longitude),
    )

history_required_views = {
    "Dashboard",
    "Climate Timeline",
    "Climate Trends",
    "Compare Places",
    "Climate Passport",
    "Climate Outlook",
    "Climate Action",
    "Compare",
    "Global Insights",
}

if (
    nav_view in history_required_views
    and active_point_location
    and (
        summary is None
        or summary.empty
    )
):
    try:
        point_history = cached_point_history(
            active_point_location[
                "latitude"
            ],
            active_point_location[
                "longitude"
            ],
        )

        summary = point_history[
            "summary"
        ]

        anomalies = point_history[
            "anomalies"
        ]

        if trend is None:
            trend = point_history[
                "trend"
            ]

        if isinstance(
            active_point_location,
            dict,
        ):
            active_point_location[
                "scope_note"
            ] = (
                active_point_location.get(
                    "scope_note"
                )
                or (
                    "Historical fallback is point-based reanalysis at the "
                    "selected coordinates."
                )
            )

    except Exception:
        # Live data remains useful even if the large archive request fails.
        pass

# Forecast uses whichever active point is available.
today_forecast = {}
today_context = None

if active_point_location is not None:
    try:
        if nav_view == "Home" and home_live_bundle:
            weather_payload = home_live_bundle.get("weather", {})
            daily = weather_payload.get("daily", {})

            def _first_daily(key):
                values = daily.get(key, [])
                return values[0] if values else None

            today_forecast = {
                "date": _first_daily("time"),
                "temperature_max_c": _first_daily("temperature_2m_max"),
                "temperature_min_c": _first_daily("temperature_2m_min"),
                "precipitation_mm": _first_daily("precipitation_sum"),
                "timezone": weather_payload.get("timezone"),
            }
        else:
            today_forecast = cached_today_forecast(
                active_point_location["latitude"],
                active_point_location["longitude"],
                active_point_location.get("timezone", "auto"),
            )

    except Exception:
        today_forecast = {}

    forecast_high_c = today_forecast.get(
        "temperature_max_c"
    )

    forecast_low_c = today_forecast.get(
        "temperature_min_c"
    )

    forecast_date = today_forecast.get(
        "date"
    )

    # The DB-based percentile context needs a real city_id.
    if (
        city is not None
        and forecast_date
        and forecast_high_c is not None
        and forecast_low_c is not None
    ):
        try:
            today_context = cached_today_climate_context(
                city[
                    "city_id"
                ],
                forecast_date,
                float(
                    forecast_high_c
                ),
                float(
                    forecast_low_c
                ),
            )

        except Exception:
            today_context = None


# =========================================================
# COUNTRY-LEVEL NATIONAL CLIMATE DATA
# =========================================================
#
# A country is fundamentally different from a city/point.
# ORBIDENSE therefore uses:
#
#   Historical national climate:
#       World Bank CCKP / CRU spatial country averages
#
#   Future national climate:
#       World Bank CCKP / CMIP6 country aggregates
#
#   Live conditions:
#       centroid weather only, explicitly labelled as a proxy
#
# This avoids presenting one centroid ERA5 grid cell as
# "the climate of the whole country".
# =========================================================

country_feature = (
    st.session_state.get(
        "selected_country"
    )
)

country_national = None
country_iso3 = None
country_location = None
country_live_weather = {}
country_live_air = {}
country_future_default = None
country_data_error = None
country_future_error = None

if country_feature:

    country_iso3 = selected_feature_iso3(
        country_feature
    )

    try:
        country_location = (
            maptiler_to_climate_location(
                country_feature
            )
        )
    except Exception:
        country_location = None

    country_data_error = None
    country_future_error = None

    country_heavy_views = {
        "Dashboard",
        "Country Climate Outlook",
        "Climate Action & Progress",
        "Compare Places",
        "Climate Passport",
        "Climate Outlook",
        "Climate Action",
        "Compare",
        "Global Insights",
    }

    if (
        country_iso3
        and nav_view in country_heavy_views
    ):
        try:
            country_national = (
                cached_country_historical_climate(
                    country_iso3
                )
            )
        except Exception as error:
            country_national = None
            country_data_error = str(
                error
            )

        try:
            country_future_default = (
                cached_country_scenario_trajectory(
                    country_iso3,
                    "ssp245",
                )
            )
        except Exception as error:
            country_future_default = None
            country_future_error = str(
                error
            )

    # A live "national weather" value does not exist.
    # We still provide the current weather at the country
    # search centroid as optional geographic context.
    if country_location:
        try:
            country_live = cached_live_environment(
                country_location[
                    "latitude"
                ],
                country_location[
                    "longitude"
                ],
                country_location.get(
                    "timezone",
                    "auto",
                ),
            )

            country_live_weather = (
                country_live
                .get(
                    "weather",
                    {},
                )
                .get(
                    "current",
                    {},
                )
            )

            country_live_air = (
                country_live
                .get(
                    "air",
                    {},
                )
                .get(
                    "current",
                    {},
                )
            )

        except Exception:
            country_live_weather = {}
            country_live_air = {}


# If national CCKP/CRU data are temporarily unavailable, provide a clearly
# labelled centroid-point historical fallback instead of an empty country page.
if (
    nav_view in {
        "Dashboard",
        "Climate Timeline",
        "Climate Trends",
        "Compare Places",
        "Climate Passport",
        "Climate Outlook",
        "Climate Action",
        "Compare",
        "Global Insights",
    }
    and country_feature
    and country_location
    and (
        country_national is None
        or country_national.empty
    )
):
    try:
        fallback = cached_point_history(
            country_location[
                "latitude"
            ],
            country_location[
                "longitude"
            ],
        )

        country_national = fallback[
            "country_frame"
        ]

        country_data_error = (
            "National spatial-average source unavailable; "
            "showing point-based historical fallback at the country centroid."
        )

    except Exception:
        pass



@st.fragment(
    run_every=5,
)
def render_history_progress(
    city_id,
):
    """
    Poll one background ERA5 import without rerunning the
    whole app every five seconds.
    """
    status = get_history_job_status(
        city_id
    )

    state = status.get(
        "status",
        "not_started",
    )

    completed = int(
        status.get(
            "completed_years",
            0,
        )
    )

    total = max(
        int(
            status.get(
                "total_years",
                36,
            )
        ),
        1,
    )

    if state == "ready":

        if (
            st.session_state.get(
                "history_status"
            )
            != "ready"
        ):
            st.session_state.history_status = (
                "ready"
            )

            cached_dashboard_data.clear()

            st.rerun()

        return

    if state in {
        "queued",
        "running",
        "waiting",
        "partial",
        "paused",
    }:

        progress = min(
            max(
                completed / total,
                0.0,
            ),
            1.0,
        )

        st.progress(
            progress,
            text=status.get(
                "message",
                "Preparing historical climate...",
            ),
        )

        if state in {
            "paused",
            "partial",
        }:
            st.caption(
                "ORBIDENSE will resume this location's "
                "missing years the next time it is opened."
            )

    elif state == "error":
        st.caption(
            "Historical climate is temporarily unavailable. "
            "Live conditions remain available."
        )

def render_country_national_dashboard(
    compact=False,
):
    """
    Render national historical and future climate for the
    currently selected country.
    """
    if not country_feature:
        return False

    country_name = maptiler_result_label(
        country_feature
    )

    if (
        country_national is None
        or country_national.empty
    ):
        record_data_quality(
            "world_bank_cckp",
            "national_historical_climate",
            "unavailable",
            metadata={"country": country_name},
        )
        if country_data_error:
            record_error(
                RuntimeError(str(country_data_error)),
                component="world_bank_cckp",
                operation="national_historical_climate",
                page_name=nav_view,
                severity="warning",
                metadata={"country": country_name},
            )
        return False

    national = country_national.copy()

    for column in [
        "mean_temperature_c",
        "annual_precipitation_mm",
    ]:
        if column in national.columns:
            national[column] = pd.to_numeric(
                national[column],
                errors="coerce",
            )

    baseline = national[
        (
            national["year"] >= 1991
        )
        &
        (
            national["year"] <= 2020
        )
    ]

    recent = national[
        (
            national["year"] >= 2015
        )
        &
        (
            national["year"] <= 2024
        )
    ]

    reference_1995_2014 = national[
        (
            national["year"] >= 1995
        )
        &
        (
            national["year"] <= 2014
        )
    ]

    latest = (
        national
        .sort_values(
            "year"
        )
        .iloc[-1]
    )

    baseline_temp = safe_float(
        baseline[
            "mean_temperature_c"
        ].mean()
    )

    recent_temp = safe_float(
        recent[
            "mean_temperature_c"
        ].mean()
    )

    baseline_precip = safe_float(
        baseline[
            "annual_precipitation_mm"
        ].mean()
    )

    recent_precip = safe_float(
        recent[
            "annual_precipitation_mm"
        ].mean()
    )

    latest_temp = safe_float(
        latest[
            "mean_temperature_c"
        ]
    )

    latest_precip = safe_float(
        latest[
            "annual_precipitation_mm"
        ]
    )

    warming_rate = safe_float(
        national.attrs.get(
            "warming_rate_c_per_decade"
        )
    )

    temp_change = None

    if (
        recent_temp is not None
        and baseline_temp is not None
    ):
        temp_change = (
            recent_temp
            - baseline_temp
        )

    precip_change_pct = None

    if (
        recent_precip is not None
        and baseline_precip not in {
            None,
            0,
        }
    ):
        precip_change_pct = (
            (
                recent_precip
                - baseline_precip
            )
            / baseline_precip
            * 100.0
        )

    future_mid = None
    future_low = None
    future_high = None

    if (
        country_future_default is not None
        and not country_future_default.empty
    ):
        future_row = country_future_default[
            country_future_default[
                "period"
            ]
            == "2040-2059"
        ]

        if not future_row.empty:
            future_mid = safe_float(
                future_row.iloc[0][
                    "median_c"
                ]
            )
            future_low = safe_float(
                future_row.iloc[0][
                    "p10_c"
                ]
            )
            future_high = safe_float(
                future_row.iloc[0][
                    "p90_c"
                ]
            )

    st.markdown(
        f"""<div class="cp-country-overview">
<div class="cp-country-overview-title">National Climate Overview</div>
<div class="cp-country-overview-sub">
{country_name} · country spatial averages, not a centroid climate proxy
</div>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""<div class="cp-kpi-grid">
<div class="cp-kpi">
<div class="cp-kpi-label">1991–2020 Mean Temperature</div>
<div class="cp-kpi-value cp-cyan">{fmt(baseline_temp, ".1f")}°C</div>
<div class="cp-kpi-note">National CRU average</div>
</div>

<div class="cp-kpi">
<div class="cp-kpi-label">Recent Climate 2015–2024</div>
<div class="cp-kpi-value cp-red">{fmt(recent_temp, ".1f")}°C</div>
<div class="cp-kpi-note">{fmt(temp_change, "+.2f")}°C vs baseline</div>
</div>

<div class="cp-kpi">
<div class="cp-kpi-label">Historical Warming Trend</div>
<div class="cp-kpi-value cp-blue">{fmt(warming_rate, "+.2f")}°C/dec</div>
<div class="cp-kpi-note">1971–2024 national series</div>
</div>

<div class="cp-kpi">
<div class="cp-kpi-label">Baseline Precipitation</div>
<div class="cp-kpi-value cp-blue">{fmt(baseline_precip, ".0f")} mm</div>
<div class="cp-kpi-note">1991–2020 annual mean</div>
</div>

<div class="cp-kpi">
<div class="cp-kpi-label">Recent Precipitation</div>
<div class="cp-kpi-value cp-cyan">{fmt(recent_precip, ".0f")} mm</div>
<div class="cp-kpi-note">{fmt(precip_change_pct, "+.1f")}% vs baseline</div>
</div>

<div class="cp-kpi">
<div class="cp-kpi-label">2040–2059 SSP2-4.5</div>
<div class="cp-kpi-value cp-orange">{fmt(future_mid, "+.2f")}°C</div>
<div class="cp-kpi-note">P10–P90: {fmt(future_low, "+.2f")} to {fmt(future_high, "+.2f")}°C vs 1995–2014</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    if compact:
        return True

    warmest_year = national.attrs.get(
        "warmest_year"
    )
    warmest_value = national.attrs.get(
        "warmest_temperature_c"
    )
    coolest_year = national.attrs.get(
        "coolest_year"
    )
    coolest_value = national.attrs.get(
        "coolest_temperature_c"
    )
    wettest_year = national.attrs.get(
        "wettest_year"
    )
    wettest_value = national.attrs.get(
        "wettest_precipitation_mm"
    )
    driest_year = national.attrs.get(
        "driest_year"
    )
    driest_value = national.attrs.get(
        "driest_precipitation_mm"
    )

    record_cols = st.columns(
        4,
        gap="small",
    )

    with record_cols[0]:
        st.metric(
            "Warmest annual mean",
            f"{fmt(warmest_value, '.1f')}°C",
            str(
                warmest_year
                or "N/A"
            ),
        )

    with record_cols[1]:
        st.metric(
            "Coolest annual mean",
            f"{fmt(coolest_value, '.1f')}°C",
            str(
                coolest_year
                or "N/A"
            ),
        )

    with record_cols[2]:
        st.metric(
            "Wettest year",
            f"{fmt(wettest_value, '.0f')} mm",
            str(
                wettest_year
                or "N/A"
            ),
        )

    with record_cols[3]:
        st.metric(
            "Driest year",
            f"{fmt(driest_value, '.0f')} mm",
            str(
                driest_year
                or "N/A"
            ),
        )

    chart_left, chart_right = st.columns(
        2,
        gap="medium",
    )

    with chart_left:
        with st.container(
            border=True
        ):
            st.markdown(
                '<div class="cp-section-heading">National Temperature History</div>',
                unsafe_allow_html=True,
            )

            fig = go.Figure()

            fig.add_trace(
                go.Scatter(
                    x=national[
                        "year"
                    ],
                    y=national[
                        "mean_temperature_c"
                    ],
                    mode="lines",
                    name="Annual mean temperature",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "%{y:.2f}°C"
                        "<extra></extra>"
                    ),
                )
            )

            if baseline_temp is not None:
                fig.add_hline(
                    y=baseline_temp,
                    line_dash="dash",
                    annotation_text=(
                        "1991–2020 baseline"
                    ),
                )

            style_plotly(
                fig,
                height=350,
                y_title="°C",
            )

            fig.update_layout(
                hovermode="x unified",
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={
                    "displayModeBar": True,
                    "responsive": True,
                },
            )

    with chart_right:
        with st.container(
            border=True
        ):
            st.markdown(
                '<div class="cp-section-heading">National Precipitation History</div>',
                unsafe_allow_html=True,
            )

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=national[
                        "year"
                    ],
                    y=national[
                        "annual_precipitation_mm"
                    ],
                    name="Annual precipitation",
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "%{y:.0f} mm"
                        "<extra></extra>"
                    ),
                )
            )

            if baseline_precip is not None:
                fig.add_hline(
                    y=baseline_precip,
                    line_dash="dash",
                    annotation_text=(
                        "1991–2020 baseline"
                    ),
                )

            style_plotly(
                fig,
                height=350,
                y_title="mm / year",
            )

            fig.update_layout(
                hovermode="x unified",
                showlegend=False,
            )

            st.plotly_chart(
                fig,
                width="stretch",
                config={
                    "displayModeBar": True,
                    "responsive": True,
                },
            )

    # -----------------------------------------------------
    # NATIONAL SSP SCENARIOS
    # -----------------------------------------------------

    st.markdown(
        "### Future National Warming Scenarios"
    )

    scenario_fig = go.Figure()
    scenario_rows = []

    for scenario_label, scenario_code in (
        CCKP_SCENARIOS.items()
    ):

        try:
            trajectory = (
                cached_country_scenario_trajectory(
                    country_iso3,
                    scenario_code,
                )
            )
        except Exception:
            trajectory = None

        if (
            trajectory is None
            or trajectory.empty
        ):
            continue

        scenario_fig.add_trace(
            go.Scatter(
                x=trajectory[
                    "period"
                ],
                y=trajectory[
                    "median_c"
                ],
                mode="lines+markers",
                name=scenario_label,
                customdata=trajectory[
                    [
                        "p10_c",
                        "p90_c",
                    ]
                ].values,
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{x}<br>"
                    "Median warming: %{y:.2f}°C<br>"
                    "P10–P90: %{customdata[0]:.2f}–"
                    "%{customdata[1]:.2f}°C"
                    "<extra></extra>"
                ),
            )
        )

        for _, row in (
            trajectory.iterrows()
        ):
            scenario_rows.append(
                {
                    "Scenario": scenario_label,
                    "Period": row[
                        "period"
                    ],
                    "Median warming (°C)": row[
                        "median_c"
                    ],
                    "P10 (°C)": row[
                        "p10_c"
                    ],
                    "P90 (°C)": row[
                        "p90_c"
                    ],
                }
            )

    if scenario_fig.data:
        style_plotly(
            scenario_fig,
            height=420,
            y_title=(
                "Temperature anomaly vs "
                "1995–2014 (°C)"
            ),
        )

        scenario_fig.update_layout(
            hovermode="x unified",
        )

        st.plotly_chart(
            scenario_fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "responsive": True,
            },
        )

        with st.expander(
            "Future scenario data table",
            expanded=False,
        ):
            st.dataframe(
                pd.DataFrame(
                    scenario_rows
                ),
                width="stretch",
                hide_index=True,
                column_config={
                    "Median warming (°C)": st.column_config.NumberColumn(
                        "Median warming",
                        format="%.2f °C",
                    ),
                    "P10 (°C)": st.column_config.NumberColumn(
                        "P10",
                        format="%.2f °C",
                    ),
                    "P90 (°C)": st.column_config.NumberColumn(
                        "P90",
                        format="%.2f °C",
                    ),
                },
            )

    # -----------------------------------------------------
    # NATIONAL DATA TABLE
    # -----------------------------------------------------

    with st.expander(
        "National historical data 1901–2024",
        expanded=False,
    ):
        st.dataframe(
            national,
            width="stretch",
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
                "mean_temperature_c": st.column_config.NumberColumn(
                    "Mean temperature",
                    format="%.2f °C",
                ),
                "annual_precipitation_mm": st.column_config.NumberColumn(
                    "Annual precipitation",
                    format="%.0f mm",
                ),
            },
        )

    st.markdown(
        """<div class="cp-method-box">
<b>Country methodology:</b> historical national values use World Bank
CCKP spatially aggregated CRU time series. Future values use CCKP
country-aggregated CMIP6 multi-model ensembles. Live weather shown
elsewhere for a country is only the search centroid and is never treated
as a national current-weather average.
</div>""",
        unsafe_allow_html=True,
    )

    return True



# =========================================================
# GLOBAL ASSISTANT CONTEXT
# =========================================================

if country_feature:
    ai_selected_name = (
        maptiler_result_label(
            country_feature
        )
    )

    ai_weather = country_live_weather
    ai_air = country_live_air
    ai_scope = (
        "Country search. Live weather is a centroid point proxy; "
        "historical country climate uses national spatial averages."
    )

elif active_point_location:
    ai_selected_name = (
        active_point_location.get(
            "city_name"
        )
        or active_point_location.get(
            "name"
        )
        or "Selected location"
    )

    ai_weather = current_weather
    ai_air = current_air
    ai_scope = (
        active_point_location.get(
            "scope_note"
        )
        if isinstance(
            active_point_location,
            dict,
        )
        else None
    )

else:
    ai_selected_name = None
    ai_weather = {}
    ai_air = {}
    ai_scope = None


# =========================================================
# ORBIDENSE PUBLIC SITE ROUTER — SINGLE SOURCE OF TRUTH
# =========================================================
#
# The router may receive either the new public labels or a legacy internal
# label from an older browser session / Home CTA. Normalize locally instead
# of rewriting st.session_state after a navigation widget has been created.
# This avoids StreamlitAPIException and guarantees every visible button lands
# on exactly one renderer.
# =========================================================

_raw_nav_view = render_site_router(
    st.session_state.get("main_navigation", nav_view)
)

_ROUTE_ALIASES = {
    # Home
    "Home": "Home",
    "Dashboard": "Home",
    "Map Explorer": "Home",

    # Climate Outlook
    "Climate Outlook": "Climate Outlook",
    "Country Climate Outlook": "Climate Outlook",
    "Climate Timeline": "Climate Outlook",
    "Outlook": "Climate Outlook",

    # Climate Action
    "Climate Action": "Climate Action",
    "Climate Action & Progress": "Climate Action",
    "Climate Trends": "Climate Action",
    "Action": "Climate Action",

    # Compare
    "Compare": "Compare",
    "Compare Places": "Compare",

    # Global
    "Global Insights": "Global Insights",
    "Global Rankings": "Global Insights",
    "Global": "Global Insights",

    # About
    "About": "About",
    "Data & Methods": "About",

    # Private developer page is handled earlier.
    "Developer Analytics": "Developer Analytics",
}

nav_view = _ROUTE_ALIASES.get(_raw_nav_view, _raw_nav_view)

# =========================================================
# GLOBAL ASSISTANT CONTEXT
# =========================================================
global_ai_context = {
    "selected_location": ai_selected_name,
    "scope": ai_scope,
    "current_weather": ai_weather,
    "current_air_quality": ai_air,
    "history_status": st.session_state.get("history_status"),
    "historical_trend": trend,
    "country_iso3": country_iso3,
    "country_data_loaded": bool(
        country_national is not None
        and not country_national.empty
    ),
}

# Mount once, before every public page, including Home.
# There is no separate public AI page.
render_persistent_ai(global_ai_context)

# =========================================================
# FINAL PUBLIC PAGE DISPATCH
# =========================================================
inject_intelligence_theme()

_orb_selected_iso3 = country_iso3 if country_iso3 else None

if nav_view == "Home":
    render_home_v2()
    st.stop()

if nav_view == "Climate Outlook":
    render_climate_outlook(
        preferred_iso3=_orb_selected_iso3
    )
    st.stop()

if nav_view == "Climate Action":
    render_climate_action(
        preferred_iso3=_orb_selected_iso3
    )
    st.stop()

if nav_view == "Compare":
    render_compare(
        preferred_iso3=_orb_selected_iso3
    )
    st.stop()

if nav_view == "Global Insights":
    render_global_insights()
    st.stop()

if nav_view == "About":
    render_professional_about()
    st.stop()

# This should never be reached for a public route. Do not silently fall back to
# the old generic "Global Climate Intelligence" page; that behavior was masking
# broken navigation.
st.error(
    f"ORBIDENSE routing error: unsupported route {nav_view!r}. "
    "Refresh the page once. If it persists, check src/orbidense_router.py."
)
st.stop()
