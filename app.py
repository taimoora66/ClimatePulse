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
)
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox
from src.api.air_quality import get_current_air_quality
from src.api.current_weather import get_current_weather
from src.api.today_forecast import get_today_forecast
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

st.set_page_config(
    page_title="ClimatePulse",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
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
        "ClimatePulse analytics initialization error:",
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
.block-container {
    max-width: 1540px;
    padding-top: 1rem;
    padding-bottom: 2.4rem;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}
[data-testid="stSidebar"] {
    background: #050d16;
    border-right: 1px solid var(--cp-border);
}
[data-testid="stSidebar"] * { color: #dce7ef; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
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
.cp-brand { font-weight: 800; font-size: 1.45rem; color: white; margin: 2px 0; }
.cp-brand-sub { color: var(--cp-muted); font-size: .86rem; margin-bottom: 1.15rem; }
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
    .block-container { padding-left: .65rem; padding-right: .65rem; padding-top: .55rem; }
    .cp-place-title { font-size: 1.38rem; }
    .cp-place-meta { gap: 8px; font-size: .76rem; }
    .cp-kpi-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
    .cp-kpi { padding: 12px; }
    .cp-kpi-value { font-size: 1.15rem; }
    .cp-current-temp { font-size: 2rem; }
}

/* Functional sidebar navigation */
.st-key-main_navigation [role="radiogroup"] {
    gap: 6px;
}

.st-key-main_navigation label {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 8px 10px;
    margin: 0;
}

.st-key-main_navigation label:hover {
    background: #0b1825;
}

.st-key-main_navigation label:has(input:checked) {
    background: #0b2236;
    border-color: rgba(57,169,255,.36);
}

.st-key-main_navigation label:has(input:checked) p {
    color: #79c9ff !important;
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

</style>
    """,
    unsafe_allow_html=True,
)

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
    """
    Fetch current weather and air quality concurrently.

    Both calls are independent, so running them together
    reduces the waiting time for live conditions.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        weather_future = executor.submit(
            get_current_weather,
            latitude,
            longitude,
            timezone=timezone,
        )

        air_future = executor.submit(
            get_current_air_quality,
            latitude,
            longitude,
            timezone=timezone,
        )

        weather_data = weather_future.result()
        air_data = air_future.result()

    return {
        "weather": weather_data,
        "air": air_data,
    }


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
    ttl=43200,
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
    ttl=43200,
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

# A stale authentication flag from an older app session must never bypass the
# secret developer gate.
if not DEVELOPER_MODE:
    st.session_state["cp_analytics_authenticated"] = False


with st.sidebar:

    st.markdown(
        """
<div class="cp-brand">🌍 ClimatePulse</div>
<div class="cp-brand-sub">Global Climate Intelligence</div>
        """,
        unsafe_allow_html=True,
    )

    # Dashboard remains in the codebase but is intentionally removed from
    # the visible navigation because Home already contains the main dashboard.
    if st.session_state.get("main_navigation") == "Dashboard":
        st.session_state["main_navigation"] = "Home"

    # Public users never see Developer Analytics in the normal sidebar.
    navigation_options = [
        "Home",
        "Map Explorer",
        "Climate Timeline",
        "Climate Trends",
        "Data & Methods",
        "Compare Places",
        "Global Rankings",
        "Climate Passport",
        "About",
    ]

    if DEVELOPER_MODE:
        navigation_options.insert(-1, "Developer Analytics")

    # If a stale session points at the old public Analytics item, recover safely.
    if st.session_state.get("main_navigation") == "Analytics":
        st.session_state["main_navigation"] = (
            "Developer Analytics" if DEVELOPER_MODE else "Home"
        )

    nav_view = st.radio(
        "Navigation",
        options=navigation_options,
        key="main_navigation",
        label_visibility="collapsed",
        width="stretch",
        format_func=lambda value: {
            "Home": "✦   Home",
            "Map Explorer": "▧   Map Explorer",
            "Climate Timeline": "⟶   Climate Timeline",
            "Climate Trends": "↗   Climate Trends",
            "Data & Methods": "▤   Data & Methods",
            "Compare Places": "⇄   Compare Places",
            "Global Rankings": "▲   Global Rankings",
            "Climate Passport": "◈   Climate Passport",
            "Developer Analytics": "▥   Developer Analytics",
            "About": "◎   About ClimatePulse",
        }[value],
    )

    st.markdown(
        '<div class="cp-sidebar-title">Recent searches</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.recent_searches:
        for recent in st.session_state.recent_searches:
            st.markdown(
                f'<div class="cp-recent">📍 {recent}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption(
            "Your recently selected places will appear here."
        )

    st.markdown(
        """
<div class="cp-data-box">
<b style="color:#eaf4fb;">Data &amp; Models</b><br>
Weather: Open-Meteo<br>
Climate: ERA5 / CRU / CMIP6<br>
Database: PostgreSQL / Neon<br>
Maps: CARTO + MapTiler
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
            "ClimatePulse analytics tracking error:",
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
            "Developer analytics could not connect to the ClimatePulse database."
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
        st.markdown("## ▥ ClimatePulse Developer Analytics")
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
    # This keeps public ClimatePulse resilient even if the optional
    # analytics dashboard has a local dependency problem.
    try:
        from src.analytics_dashboard import render_analytics_dashboard

        render_analytics_dashboard()
    except Exception as dashboard_error:
        st.error(
            "Developer analytics dashboard could not be rendered. "
            "The public ClimatePulse application remains available."
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

st.markdown(
    '<div id="dashboard"></div>',
    unsafe_allow_html=True,
)

search_col, status_col = st.columns(
    [5.0, 1.35],
    gap="medium",
    vertical_alignment="center",
)

with search_col:
    st.markdown(
        """
<div class="cp-search-panel">
<div class="cp-search-kicker">GLOBAL PLACE SEARCH</div>
<div class="cp-search-title">Explore any city, place or country</div>
<div class="cp-search-help">Search globally to move ClimatePulse, load live conditions and connect historical climate context.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    selected_search_result = st_searchbox(
        global_search,
        key="global_place_search",
        label=None,
        placeholder="Search Milan, Islamabad, Tokyo, Pakistan...",
        debounce=300,
        edit_after_submit="option",
        clear_on_submit=False,
        style_overrides=GLOBAL_SEARCHBOX_STYLE,
    )

with status_col:
    # Public visitors see only system status. Audience numbers remain private
    # and are shown here only after the developer has authenticated.
    developer_authenticated = bool(
        st.session_state.get("cp_analytics_authenticated", False)
    )

    if developer_authenticated and ANALYTICS_READY:
        try:
            active_visitors = int(
                get_analytics_summary().get("active_now", 0)
            )
            audience_text = f"{active_visitors:,} active now"
            audience_sub = "Developer view"
        except Exception:
            audience_text = "Analytics unavailable"
            audience_sub = "Developer view"
    else:
        audience_text = "All systems normal"
        audience_sub = "Live Earth online"

    st.markdown(
        f"""
<div class="cp-audience-wrap">
    <div class="cp-audience-pill">
        <span class="cp-audience-dot"></span>
        <span>{audience_text}</span>
        <span class="cp-audience-sub">· {audience_sub}</span>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

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
            print("ClimatePulse search analytics error:", analytics_event_error)

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
            st.error(
                "Location conversion failed: "
                f"{error}"
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
# make that browser point the actual global ClimatePulse selection BEFORE
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
                print("ClimatePulse location analytics error:", analytics_event_error)

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
if active_point_location:
    try:
        live_environment = cached_live_environment(
            active_point_location[
                "latitude"
            ],
            active_point_location[
                "longitude"
            ],
            active_point_location.get(
                "timezone",
                "auto",
            ),
        )

        current_weather = (
            live_environment
            .get(
                "weather",
                {},
            )
            .get(
                "current",
                {},
            )
        )

        current_air = (
            live_environment
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
        current_weather = {}
        current_air = {}

# Historical fallback for a point when DB history is missing.
@st.cache_data(
    ttl=21600,
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
        today_forecast = cached_today_forecast(
            active_point_location[
                "latitude"
            ],
            active_point_location[
                "longitude"
            ],
            active_point_location.get(
                "timezone",
                "auto",
            ),
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
# ClimatePulse therefore uses:
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
        "Climate Timeline",
        "Climate Trends",
        "Compare Places",
        "Climate Passport",
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
                "ClimatePulse will resume this location's "
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
        st.warning(
            "National historical climate could not be loaded from "
            "the World Bank CCKP aggregate service. Live map and "
            "centroid conditions remain available."
        )

        if country_data_error:
            with st.expander(
                "Technical data-source detail",
                expanded=False,
            ):
                st.code(
                    country_data_error
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

global_ai_context = {
    "selected_location": ai_selected_name,
    "scope": ai_scope,
    "current_weather": ai_weather,
    "current_air_quality": ai_air,
    "history_status": st.session_state.get(
        "history_status"
    ),
    "historical_trend": trend,
    "country_iso3": country_iso3,
    "country_data_loaded": bool(
        country_national is not None
        and not country_national.empty
    ),
}

render_persistent_ai(
    global_ai_context
)


if city is not None:
    title = f"{city['city_name']}, {city['country_name']}"

    live_timezone = None

    try:
        live_timezone = (
            live_environment
            .get("weather", {})
            .get("timezone")
        )
    except Exception:
        live_timezone = None

    timezone_label = (
        live_timezone
        or (
            "Local timezone"
            if city["timezone"] == "auto"
            else city["timezone"]
        )
    )

    selected_scope_note = None

    if st.session_state.selected_location:
        selected_scope_note = (
            st.session_state.selected_location
            .get("scope_note")
        )

    scope_html = (
        f"<span>◌ Point-based ERA5 at selected centroid</span>"
        if selected_scope_note
        else ""
    )

    meta = (
        f"◈ {city['latitude']:.4f}°, {city['longitude']:.4f}°"
        f"<span>◉ {timezone_label}</span>"
        f"<span>ERA5 1990–2025</span>"
        f"{scope_html}"
    )
elif st.session_state.selected_country:
    title = maptiler_result_label(
        st.session_state.selected_country
    )

    if (
        country_national is not None
        and not country_national.empty
    ):
        country_source_label = (
            "National climate data ready"
        )
    elif country_data_error:
        country_source_label = (
            "National data source unavailable"
        )
    else:
        country_source_label = (
            "Retrieving national climate data"
        )

    meta = (
        f"◈ {country_iso3 or 'Country'}"
        f"<span>World Bank CCKP national averages</span>"
        f"<span>CRU historical national series</span>"
        f"<span>{country_source_label}</span>"
    )
else:
    if nav_view == "Home":
        title = "Live Earth Intelligence"
        meta = "Current conditions, forecast, health context, compound signals and climate change"
    else:
        title = "Global Climate Intelligence"
        meta = "Search any city, place or country to explore climate conditions and long-term trends"

if nav_view != "Home":
    st.markdown(
        f"""
<div class="cp-topline"><div>
<div class="cp-place-title">{title}</div>
<div class="cp-place-meta">{meta}</div>
</div></div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DERIVED CLIMATE PRODUCT DATA
# =========================================================
#
# These variables must be created before Climate Passport,
# Dashboard Fingerprint, or Climate Trends attempts to use
# them. Keeping them here prevents NameError on navigation.
# =========================================================

warming_rate = None
warming_text = "N/A"
climate_fingerprint = None
climate_signature = "Climate profile unavailable"

if (
    summary is not None
    and not summary.empty
):
    warming_rate = (
        safe_float(
            trend.get(
                "warming_rate_c_per_decade"
            )
        )
        if trend
        else None
    )

    warming_text = (
        f"{warming_rate:+.2f}°C/decade"
        if warming_rate is not None
        else "N/A"
    )

    climate_fingerprint = (
        build_climate_fingerprint(
            summary,
            warming_rate,
        )
    )

    climate_signature = (
        fingerprint_signature(
            climate_fingerprint
        )
    )



# =========================================================
# FUTURISTIC HOME
# =========================================================

if nav_view == "Home":
    render_home_page(
        city=city,
        point_location=(
            st.session_state.get(
                "selected_location"
            )
        ),
        summary=summary,
        anomalies=anomalies,
        trend=trend,
        country_feature=country_feature,
        country_location=country_location,
        country_national=country_national,
        country_iso3=country_iso3,
    )
    st.stop()


if nav_view == "Dashboard":
    render_dashboard_page(
        city=city,
        point_location=(
            st.session_state.get(
                "selected_location"
            )
        ),
        summary=summary,
        anomalies=anomalies,
        trend=trend,
        country_feature=country_feature,
        country_location=country_location,
        country_national=country_national,
    )
    st.stop()


if nav_view == "AI Assistant":
    render_ai_page(
        global_ai_context
    )
    st.stop()


# =========================================================
# CLIMATE TIMELINE
# =========================================================

if nav_view == "Climate Timeline":
    render_climate_timeline_page(
        city=city,
        point_location=(
            st.session_state.get(
                "selected_location"
            )
        ),
        summary=summary,
        anomalies=anomalies,
        country_feature=country_feature,
        country_national=country_national,
        country_iso3=country_iso3,
    )
    st.stop()


# =========================================================
# COMPARE PLACES
# =========================================================

if nav_view == "Compare Places":

    st.markdown(
        """<div class="cp-compare-hero">
<div class="cp-compare-title">⇄ Compare Places</div>
<div class="cp-compare-sub">
Compare two to four places across <b>Past</b>, <b>Recent Climate</b>,
<b>Now</b>, <b>Observed Trend</b> and an optional
<b>2041–2049 multi-model CMIP6 ensemble</b>. Future uncertainty is shown
as model spread rather than as artificial emissions scenarios.
</div>
</div>""",
        unsafe_allow_html=True,
    )

    control_a, control_b = st.columns(
        [
            0.8,
            1.7,
        ],
        gap="medium",
    )

    with control_a:
        compare_count = st.selectbox(
            "Number of places",
            options=[
                2,
                3,
                4,
            ],
            index=0,
            key="compare_count",
        )

    with control_b:
        future_mode = st.selectbox(
            "Future climate ensemble",
            options=[
                "Off",
                "Core 4 models",
                "All 7 models",
            ],
            index=0,
            key="future_ensemble_mode",
            help=(
                "Core 4 is recommended for routine use. "
                "All 7 gives a broader model-spread check "
                "but uses heavier climate API calls."
            ),
        )

    if future_mode == "Core 4 models":
        selected_future_models = [
            "CMCC_CM2_VHR4",
            "MRI_AGCM3_2_S",
            "EC_Earth3P_HR",
            "MPI_ESM1_2_XR",
        ]
    elif future_mode == "All 7 models":
        selected_future_models = list(
            CLIMATE_MODELS
        )
    else:
        selected_future_models = []

    include_future = bool(
        selected_future_models
    )

    if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
        try:
            track_event_once(
                f"compare_config::{compare_count}::{future_mode}",
                "compare_configuration",
                category="compare",
                page_name=nav_view,
                metadata={
                    "place_count": compare_count,
                    "future_mode": future_mode,
                    "model_count": len(selected_future_models),
                },
            )
        except Exception as analytics_event_error:
            print("ClimatePulse compare analytics error:", analytics_event_error)

    st.markdown(
        """<div class="cp-compare-warning">
<b>Scope:</b> country selections use a centroid-point proxy rather than
a national area average. Future low/median/high values represent the
spread across selected climate models — not low/medium/high emissions
pathways.
</div>""",
        unsafe_allow_html=True,
    )

    selector_columns = st.columns(
        compare_count,
        gap="small",
    )

    selected_features = []

    for index in range(
        compare_count
    ):
        state_key = (
            f"compare_feature_{index}"
        )

        with selector_columns[index]:
            result = st_searchbox(
                global_search,
                key=(
                    f"compare_search_{index}"
                ),
                label=(
                    f"Place {index + 1}"
                ),
                placeholder=(
                    "Search country, city or place..."
                ),
                debounce=300,
                edit_after_submit="option",
                clear_on_submit=False,
                style_overrides=GLOBAL_SEARCHBOX_STYLE,
            )

            if result:
                st.session_state[
                    state_key
                ] = result

            stored = st.session_state.get(
                state_key
            )

            if stored:
                selected_features.append(
                    stored
                )

    clear_col, note_col = st.columns(
        [
            0.8,
            3.2,
        ],
        vertical_alignment="center",
    )

    with clear_col:
        if st.button(
            "Clear comparison",
            width="stretch",
        ):
            for index in range(4):
                st.session_state.pop(
                    f"compare_feature_{index}",
                    None,
                )
            st.rerun()

    with note_col:
        st.caption(
            "Historical metrics appear when the ERA5 record "
            "for that location is ready."
        )

    if len(selected_features) < 2:
        st.markdown(
            """<div class="cp-landing">
<b>Select at least two locations</b><br>
<span class="cp-muted">
ClimatePulse can compare two, three or four locations side by side.
</span>
</div>""",
            unsafe_allow_html=True,
        )
        st.stop()

    if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
        try:
            compare_labels = [
                maptiler_result_label(feature)
                for feature in selected_features
            ]
            compare_signature = "|".join(compare_labels) + f"|{future_mode}"
            track_event_once(
                f"compare_selection::{compare_signature}",
                "compare_places_selected",
                category="compare",
                page_name=nav_view,
                metadata={
                    "places": compare_labels,
                    "place_count": len(compare_labels),
                    "future_mode": future_mode,
                },
            )
        except Exception as analytics_event_error:
            print("ClimatePulse compare selection analytics error:", analytics_event_error)

    comparison_records = []

    with st.spinner(
        (
            "Preparing historical, live and CMIP6 ensemble data..."
            if include_future
            else "Preparing historical and live comparison..."
        )
    ):
        for feature in selected_features:
            comparison_records.append(
                comparison_snapshot(
                    feature,
                    include_future=include_future,
                    future_models=selected_future_models,
                )
            )

    # -----------------------------------------------------
    # OVERVIEW CARDS
    # -----------------------------------------------------

    st.markdown(
        "### Side-by-side overview"
    )

    overview_columns = st.columns(
        len(comparison_records),
        gap="small",
    )

    for column, record in zip(
        overview_columns,
        comparison_records,
    ):
        values = comparison_metrics(
            record
        )

        current_text = (
            f"{values['current_temp']:.1f}°C"
            if values["current_temp"] is not None
            else "N/A"
        )
        baseline_text = (
            f"{values['baseline_temp']:.1f}°C"
            if values["baseline_temp"] is not None
            else "Loading"
        )
        trend_text = (
            f"{values['warming_rate']:+.2f}°C/dec"
            if values["warming_rate"] is not None
            else "Loading"
        )

        if values["future_temp_median"] is not None:
            future_text = (
                f"{values['future_temp_median']:.1f}°C"
            )
            future_range = (
                f"{values['future_temp_low']:.1f}–"
                f"{values['future_temp_high']:.1f}°C "
                f"({values['future_model_count']} models)"
            )
        else:
            future_text = (
                "Off"
                if not include_future
                else "Unavailable"
            )
            future_range = "—"

        with column:
            st.markdown(
                f"""<div class="cp-compare-place">
<div class="cp-compare-name">{record["label"]}</div>
<div class="cp-compare-type">{record["scope"]}</div>
<div class="cp-compare-big">{current_text}</div>
<div class="cp-compare-caption">Current temperature</div>

<div class="cp-compare-mini">
<div class="cp-compare-mini-card">
<div class="cp-compare-mini-label">1991–2020 baseline</div>
<div class="cp-compare-mini-value">{baseline_text}</div>
</div>
<div class="cp-compare-mini-card">
<div class="cp-compare-mini-label">Observed warming</div>
<div class="cp-compare-mini-value">{trend_text}</div>
</div>
<div class="cp-compare-mini-card">
<div class="cp-compare-mini-label">2041–2049 median</div>
<div class="cp-compare-mini-value">{future_text}</div>
</div>
<div class="cp-compare-mini-card">
<div class="cp-compare-mini-label">Model spread</div>
<div class="cp-compare-mini-value">{future_range}</div>
</div>
</div>
</div>""",
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------
    # DETAILED MATRIX
    # -----------------------------------------------------

    st.markdown(
        "### Past · Recent · Now · Trend · Future"
    )

    matrix_rows = []

    for record in comparison_records:
        values = comparison_metrics(
            record
        )

        future_hot_range = None
        if values["future_hot30_median"] is not None:
            future_hot_range = (
                f"{values['future_hot30_low']:.0f}–"
                f"{values['future_hot30_high']:.0f}"
            )

        matrix_rows.append(
            {
                "Place": record["label"],
                "Scope": record["scope"],
                "Past mean temp 1991–2020 (°C)": values["baseline_temp"],
                "Past annual precip (mm)": values["baseline_precip"],
                "Past hot days ≥30°C / yr": values["baseline_hot30"],
                "Past days ≥35°C / yr": values["baseline_hot35"],
                "Recent mean temp 2016–2025 (°C)": values["recent_temp"],
                "Recent change vs baseline (°C)": values["recent_temp_delta"],
                "Now temp (°C)": values["current_temp"],
                "Feels like (°C)": values["current_feels"],
                "Humidity (%)": values["current_humidity"],
                "European AQI": values["current_aqi"],
                "Latest anomaly (°C)": values["latest_anomaly"],
                "Observed trend (°C/decade)": values["warming_rate"],
                "Future temp median (°C)": values["future_temp_median"],
                "Future temp model min (°C)": values["future_temp_low"],
                "Future temp model max (°C)": values["future_temp_high"],
                "Future hot days median / yr": values["future_hot30_median"],
                "Future hot days model range": future_hot_range,
                "Future precip median (mm/yr)": values["future_precip_median"],
                "Future model count": values["future_model_count"],
            }
        )

    comparison_df = pd.DataFrame(
        matrix_rows
    )

    dark_dataframe(
        comparison_df
    )

    chart_labels = [
        record["label"]
        for record in comparison_records
    ]

    chart_metrics = [
        comparison_metrics(record)
        for record in comparison_records
    ]

    # -----------------------------------------------------
    # TEMPERATURE / TREND
    # -----------------------------------------------------

    chart_a, chart_b = st.columns(
        2,
        gap="medium",
    )

    with chart_a:
        with st.container(border=True):
            st.markdown(
                '<div class="cp-section-heading">Temperature evolution</div>',
                unsafe_allow_html=True,
            )

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=chart_labels,
                    y=[
                        values["baseline_temp"]
                        for values in chart_metrics
                    ],
                    name="1991–2020",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=chart_labels,
                    y=[
                        values["recent_temp"]
                        for values in chart_metrics
                    ],
                    name="2016–2025",
                )
            )

            if include_future:
                fig.add_trace(
                    go.Bar(
                        x=chart_labels,
                        y=[
                            values["future_temp_median"]
                            for values in chart_metrics
                        ],
                        error_y=dict(
                            type="data",
                            symmetric=False,
                            array=[
                                (
                                    values["future_temp_high"]
                                    - values["future_temp_median"]
                                )
                                if (
                                    values["future_temp_high"] is not None
                                    and values["future_temp_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                            arrayminus=[
                                (
                                    values["future_temp_median"]
                                    - values["future_temp_low"]
                                )
                                if (
                                    values["future_temp_low"] is not None
                                    and values["future_temp_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                        ),
                        name="2041–2049 ensemble",
                    )
                )

            fig.update_layout(
                barmode="group"
            )
            style_plotly(
                fig,
                height=330,
                y_title="°C",
            )
            st.plotly_chart(
                fig,
                width="stretch",
                config={
                    "displayModeBar": False,
                },
            )

    with chart_b:
        with st.container(border=True):
            st.markdown(
                '<div class="cp-section-heading">Observed warming rate</div>',
                unsafe_allow_html=True,
            )

            fig = go.Figure(
                go.Bar(
                    x=chart_labels,
                    y=[
                        values["warming_rate"]
                        for values in chart_metrics
                    ],
                )
            )
            style_plotly(
                fig,
                height=330,
                y_title="°C / decade",
            )
            fig.update_layout(
                showlegend=False
            )
            st.plotly_chart(
                fig,
                width="stretch",
                config={
                    "displayModeBar": False,
                },
            )

    # -----------------------------------------------------
    # FUTURE ENSEMBLE
    # -----------------------------------------------------

    if include_future:

        future_a, future_b = st.columns(
            2,
            gap="medium",
        )

        with future_a:
            with st.container(border=True):
                st.markdown(
                    '<div class="cp-section-heading">Future hot days</div>',
                    unsafe_allow_html=True,
                )

                fig = go.Figure(
                    go.Bar(
                        x=chart_labels,
                        y=[
                            values["future_hot30_median"]
                            for values in chart_metrics
                        ],
                        error_y=dict(
                            type="data",
                            symmetric=False,
                            array=[
                                (
                                    values["future_hot30_high"]
                                    - values["future_hot30_median"]
                                )
                                if (
                                    values["future_hot30_high"] is not None
                                    and values["future_hot30_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                            arrayminus=[
                                (
                                    values["future_hot30_median"]
                                    - values["future_hot30_low"]
                                )
                                if (
                                    values["future_hot30_low"] is not None
                                    and values["future_hot30_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                        ),
                    )
                )
                style_plotly(
                    fig,
                    height=310,
                    y_title="Days ≥30°C / year",
                )
                fig.update_layout(
                    showlegend=False
                )
                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={
                        "displayModeBar": False,
                    },
                )

        with future_b:
            with st.container(border=True):
                st.markdown(
                    '<div class="cp-section-heading">Future annual precipitation</div>',
                    unsafe_allow_html=True,
                )

                fig = go.Figure(
                    go.Bar(
                        x=chart_labels,
                        y=[
                            values["future_precip_median"]
                            for values in chart_metrics
                        ],
                        error_y=dict(
                            type="data",
                            symmetric=False,
                            array=[
                                (
                                    values["future_precip_high"]
                                    - values["future_precip_median"]
                                )
                                if (
                                    values["future_precip_high"] is not None
                                    and values["future_precip_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                            arrayminus=[
                                (
                                    values["future_precip_median"]
                                    - values["future_precip_low"]
                                )
                                if (
                                    values["future_precip_low"] is not None
                                    and values["future_precip_median"] is not None
                                )
                                else 0
                                for values in chart_metrics
                            ],
                        ),
                    )
                )
                style_plotly(
                    fig,
                    height=310,
                    y_title="mm / year",
                )
                fig.update_layout(
                    showlegend=False
                )
                st.plotly_chart(
                    fig,
                    width="stretch",
                    config={
                        "displayModeBar": False,
                    },
                )

        st.markdown(
            "### Model agreement"
        )

        agreement_columns = st.columns(
            len(comparison_records),
            gap="small",
        )

        for column, record in zip(
            agreement_columns,
            comparison_records,
        ):
            values = comparison_metrics(
                record
            )

            with column:
                st.markdown(
                    f"**{record['label']}**"
                )
                st.metric(
                    "Temperature",
                    values["future_temp_agreement"],
                )
                st.metric(
                    "Hot days",
                    values["future_hot_agreement"],
                )
                st.metric(
                    "Precipitation",
                    values["future_precip_agreement"],
                )

        with st.expander(
            "Individual CMIP6 model results",
            expanded=False,
        ):
            model_rows = []

            for record in comparison_records:
                ensemble = (
                    record.get(
                        "future_ensemble"
                    )
                    or {}
                )

                for model_result in ensemble.get(
                    "models",
                    []
                ):
                    model_rows.append(
                        {
                            "Place": record["label"],
                            "Model": model_result.get("model"),
                            "Mean temp 2041–2049 (°C)": model_result.get(
                                "future_mean_temperature_c"
                            ),
                            "Hot days ≥30°C / yr": model_result.get(
                                "future_hot_days_30c_per_year"
                            ),
                            "Annual precip (mm)": model_result.get(
                                "future_annual_precipitation_mm"
                            ),
                        }
                    )

            if model_rows:
                st.dataframe(
                    pd.DataFrame(model_rows),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info(
                    "No future-model results were returned."
                )


    # -----------------------------------------------------
    # CLIMATE TRAJECTORY
    # -----------------------------------------------------

    st.markdown(
        "### Climate trajectory"
    )

    trajectory_fig = go.Figure()

    for record in comparison_records:
        values = comparison_metrics(
            record
        )

        x_values = []
        y_values = []

        if values["baseline_temp"] is not None:
            x_values.append("1991–2020")
            y_values.append(
                values["baseline_temp"]
            )

        if values["recent_temp"] is not None:
            x_values.append("2016–2025")
            y_values.append(
                values["recent_temp"]
            )

        if values["future_temp_median"] is not None:
            x_values.append("2041–2049")
            y_values.append(
                values["future_temp_median"]
            )

        if len(y_values) >= 2:
            trajectory_fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines+markers",
                    name=record["label"],
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x}: %{y:.2f}°C"
                        "<extra></extra>"
                    ),
                )
            )

    if trajectory_fig.data:
        style_plotly(
            trajectory_fig,
            height=390,
            y_title="Mean temperature (°C)",
        )
        trajectory_fig.update_layout(
            hovermode="x unified",
        )
        st.plotly_chart(
            trajectory_fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "responsive": True,
            },
        )

    # True country-average SSP trajectories when all selections
    # are countries.
    country_selections = []
    all_country_mode = True

    for feature in selected_features:
        if maptiler_feature_type(feature) != "country":
            all_country_mode = False
            break

        iso3 = selected_feature_iso3(
            feature
        )

        if not iso3:
            all_country_mode = False
            break

        country_selections.append(
            (
                maptiler_result_label(feature),
                iso3,
            )
        )

    if all_country_mode:

        st.markdown(
            "### Country scenario trajectories to 2100"
        )

        scenario_name = st.selectbox(
            "Shared Socioeconomic Pathway",
            options=list(
                CCKP_SCENARIOS.keys()
            ),
            index=1,
            key="country_compare_scenario",
        )

        scenario_code = CCKP_SCENARIOS[
            scenario_name
        ]

        scenario_fig = go.Figure()

        scenario_rows = []

        for display_name, iso3 in (
            country_selections
        ):
            try:
                traj = (
                    cached_country_scenario_trajectory(
                        iso3,
                        scenario_code,
                    )
                )
            except Exception:
                traj = None

            if traj is None or traj.empty:
                continue

            scenario_fig.add_trace(
                go.Scatter(
                    x=traj["period"],
                    y=traj["median_c"],
                    mode="lines+markers",
                    name=display_name,
                    customdata=traj[
                        ["p10_c", "p90_c"]
                    ].values,
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x}<br>"
                        "Median: %{y:.2f}°C<br>"
                        "P10–P90: %{customdata[0]:.2f}–"
                        "%{customdata[1]:.2f}°C"
                        "<extra></extra>"
                    ),
                )
            )

            for _, row in traj.iterrows():
                scenario_rows.append(
                    {
                        "Country": display_name,
                        "ISO3": iso3,
                        "Scenario": scenario_name,
                        "Period": row["period"],
                        "Median warming (°C)": row["median_c"],
                        "P10 (°C)": row["p10_c"],
                        "P90 (°C)": row["p90_c"],
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
                "Scenario data table",
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

            st.caption(
                "These country trajectories use World Bank CCKP "
                "national spatial averages. City/place projections "
                "remain point-based."
            )



    # -----------------------------------------------------
    # VERDICT
    # -----------------------------------------------------

    verdict = comparison_verdict(
        comparison_records
    )
    narrative = comparison_narrative(
        comparison_records
    )

    st.markdown(
        f"""<div class="cp-verdict">
<div class="cp-verdict-title">Data-based comparison verdict</div>
<div class="cp-compare-sub">{narrative}</div>

<div class="cp-verdict-grid">
<div class="cp-verdict-card">
<div class="cp-verdict-label">Warmest right now</div>
<div class="cp-verdict-value">{verdict.get("warmest_now", "N/A")}</div>
</div>
<div class="cp-verdict-card">
<div class="cp-verdict-label">Fastest observed warming</div>
<div class="cp-verdict-value">{verdict.get("fastest_historical_warming", "N/A")}</div>
</div>
<div class="cp-verdict-card">
<div class="cp-verdict-label">Most baseline hot days</div>
<div class="cp-verdict-value">{verdict.get("most_baseline_hot_days", "N/A")}</div>
</div>
<div class="cp-verdict-card">
<div class="cp-verdict-label">Highest future ensemble heat</div>
<div class="cp-verdict-value">{verdict.get("highest_future_heat", "Enable ensemble")}</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div class="cp-product-note">
Future model ranges show CMIP6 model spread, not emissions-scenario
uncertainty. Open-Meteo recommends comparing multiple climate models,
and local precipitation generally carries greater model uncertainty
than long-period temperature change.
</div>""",
        unsafe_allow_html=True,
    )

    st.download_button(
        "Download comparison CSV",
        data=comparison_df.to_csv(
            index=False
        ),
        file_name="climatepulse_comparison.csv",
        mime="text/csv",
        width="stretch",
    )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Compare Places</div>',
        unsafe_allow_html=True,
    )
    st.stop()





# =========================================================
# GLOBAL COUNTRY WARMING RANKINGS
# =========================================================

if nav_view == "Global Rankings":

    st.markdown(
        """<div class="cp-rank-hero">
<div class="cp-rank-title">▲ Global Country Warming Rankings</div>
<div class="cp-rank-sub">
Rank countries by projected mean-temperature change using World Bank
Climate Change Knowledge Portal country-level CMIP6 spatial aggregates.
Unlike centroid-based country views, these are national spatial averages.
</div>
</div>""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(
        [1.15, 1.15, .8],
        gap="medium",
    )

    with c1:
        scenario_label = st.selectbox(
            "Emissions pathway",
            options=list(
                CCKP_SCENARIOS.keys()
            ),
            index=1,
            key="global_rank_scenario",
        )

    scenario_code = CCKP_SCENARIOS[
        scenario_label
    ]

    with c2:
        period_label = st.selectbox(
            "Projection period",
            options=list(
                CCKP_PERIODS.keys()
            ),
            index=1,
            key="global_rank_period",
        )

    period_code = CCKP_PERIODS[
        period_label
    ]

    if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
        try:
            track_event_once(
                f"rankings::{scenario_code}::{period_code}",
                "global_rankings_view",
                category="rankings",
                page_name=nav_view,
                metadata={
                    "scenario": scenario_code,
                    "scenario_label": scenario_label,
                    "period": period_code,
                    "period_label": period_label,
                },
            )
        except Exception as analytics_event_error:
            print("ClimatePulse rankings analytics error:", analytics_event_error)

    with c3:
        top_n = st.selectbox(
            "Show top / bottom",
            options=[5, 10, 15, 20],
            index=1,
            key="global_rank_n",
        )

    st.markdown(
        f'<span class="cp-scenario-pill">{scenario_label} · {period_label}</span>',
        unsafe_allow_html=True,
    )

    try:
        ranking_df = cached_country_projection_rankings(
            scenario_code,
            period_code,
        )
    except Exception as error:
        st.error(
            "Unable to load World Bank CCKP country projections."
        )

        with st.expander(
            "Technical data-source detail",
            expanded=False,
        ):
            st.code(
                str(error)
            )

        st.stop()

    if ranking_df is None or ranking_df.empty:
        st.error(
            "Country ranking data could not be parsed from the "
            "World Bank CCKP response. ClimatePulse did not "
            "substitute estimated or invented values."
        )
        st.caption(
            "Try another SSP/period once. If the message persists, "
            "the World Bank endpoint may be temporarily unavailable."
        )
        st.stop()

    ranking_df = ranking_df.copy()

    for column in [
        "projected_warming_c",
        "p10_c",
        "p90_c",
    ]:
        ranking_df[column] = pd.to_numeric(
            ranking_df[column],
            errors="coerce",
        )

    ranking_df = (
        ranking_df
        .dropna(
            subset=["projected_warming_c"]
        )
        .sort_values(
            "projected_warming_c",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    ranking_df["rank"] = (
        ranking_df.index + 1
    )

    hottest = ranking_df.head(
        top_n
    ).copy()

    least = (
        ranking_df
        .sort_values(
            "projected_warming_c",
            ascending=True,
        )
        .head(top_n)
        .copy()
    )

    warmest_row = (
        ranking_df.iloc[0]
        if not ranking_df.empty
        else None
    )

    least_row = (
        ranking_df.iloc[-1]
        if not ranking_df.empty
        else None
    )

    median_value = safe_float(
        ranking_df[
            "projected_warming_c"
        ].median()
    )

    st.markdown(
        f"""<div class="cp-rank-grid">
<div class="cp-rank-card">
<div class="cp-rank-label">Highest projected warming</div>
<div class="cp-rank-value">{warmest_row["country_name"] if warmest_row is not None else "N/A"}</div>
<div class="cp-rank-note">{fmt(warmest_row["projected_warming_c"] if warmest_row is not None else None, ".2f")}°C</div>
</div>
<div class="cp-rank-card">
<div class="cp-rank-label">Lowest projected warming</div>
<div class="cp-rank-value">{least_row["country_name"] if least_row is not None else "N/A"}</div>
<div class="cp-rank-note">{fmt(least_row["projected_warming_c"] if least_row is not None else None, ".2f")}°C</div>
</div>
<div class="cp-rank-card">
<div class="cp-rank-label">Country median</div>
<div class="cp-rank-value">{fmt(median_value, ".2f")}°C</div>
<div class="cp-rank-note">Median across returned countries</div>
</div>
<div class="cp-rank-card">
<div class="cp-rank-label">Countries ranked</div>
<div class="cp-rank-value">{len(ranking_df)}</div>
<div class="cp-rank-note">National spatial aggregates</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    tab_most, tab_least, tab_all = st.tabs(
        [
            "Most warming",
            "Least warming",
            "All countries",
        ]
    )

    with tab_most:
        fig = go.Figure(
            go.Bar(
                x=hottest["projected_warming_c"],
                y=hottest["country_name"],
                orientation="h",
                customdata=hottest[
                    ["iso3", "p10_c", "p90_c"]
                ].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Median: %{x:.2f}°C<br>"
                    "ISO3: %{customdata[0]}<br>"
                    "P10–P90: %{customdata[1]:.2f}–"
                    "%{customdata[2]:.2f}°C"
                    "<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            yaxis=dict(
                autorange="reversed"
            ),
            xaxis_title=(
                "Projected warming vs 1995–2014 (°C)"
            ),
            showlegend=False,
        )
        style_plotly(
            fig,
            height=max(
                330,
                34 * len(hottest),
            ),
        )
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "responsive": True,
            },
        )
        st.dataframe(
            hottest[
                [
                    "rank",
                    "country_name",
                    "iso3",
                    "projected_warming_c",
                    "p10_c",
                    "p90_c",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn(
                    "Rank",
                    format="%d",
                ),
                "country_name": "Country",
                "iso3": "ISO3",
                "projected_warming_c": st.column_config.NumberColumn(
                    "Median warming",
                    format="%.2f °C",
                ),
                "p10_c": st.column_config.NumberColumn(
                    "P10",
                    format="%.2f °C",
                ),
                "p90_c": st.column_config.NumberColumn(
                    "P90",
                    format="%.2f °C",
                ),
            },
        )

    with tab_least:
        fig = go.Figure(
            go.Bar(
                x=least["projected_warming_c"],
                y=least["country_name"],
                orientation="h",
                customdata=least[
                    ["iso3", "p10_c", "p90_c"]
                ].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Median: %{x:.2f}°C<br>"
                    "P10–P90: %{customdata[1]:.2f}–"
                    "%{customdata[2]:.2f}°C"
                    "<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            xaxis_title=(
                "Projected warming vs 1995–2014 (°C)"
            ),
            showlegend=False,
        )
        style_plotly(
            fig,
            height=max(
                330,
                34 * len(least),
            ),
        )
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "responsive": True,
            },
        )
        st.dataframe(
            least[
                [
                    "country_name",
                    "iso3",
                    "projected_warming_c",
                    "p10_c",
                    "p90_c",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    with tab_all:
        filter_text = st.text_input(
            "Filter countries",
            placeholder=(
                "Country name or ISO3..."
            ),
            key="rank_filter",
        )

        filtered = ranking_df.copy()

        if filter_text.strip():
            q = filter_text.strip().casefold()

            filtered = filtered[
                filtered["country_name"]
                .astype(str)
                .str.casefold()
                .str.contains(q, na=False)
                |
                filtered["iso3"]
                .astype(str)
                .str.casefold()
                .str.contains(q, na=False)
            ]

        st.dataframe(
            filtered[
                [
                    "rank",
                    "country_name",
                    "iso3",
                    "projected_warming_c",
                    "p10_c",
                    "p90_c",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn(
                    "Rank",
                    format="%d",
                ),
                "country_name": "Country",
                "iso3": "ISO3",
                "projected_warming_c": st.column_config.ProgressColumn(
                    "Median warming",
                    format="%.2f °C",
                    min_value=float(
                        ranking_df[
                            "projected_warming_c"
                        ].min()
                    ),
                    max_value=float(
                        ranking_df[
                            "projected_warming_c"
                        ].max()
                    ),
                ),
                "p10_c": st.column_config.NumberColumn(
                    "P10",
                    format="%.2f °C",
                ),
                "p90_c": st.column_config.NumberColumn(
                    "P90",
                    format="%.2f °C",
                ),
            },
        )

    st.markdown(
        "### Scenario sensitivity"
    )

    scenario_fig = go.Figure()

    for scenario_name, scenario_value in (
        CCKP_SCENARIOS.items()
    ):
        try:
            scenario_df = (
                cached_country_projection_rankings(
                    scenario_value,
                    period_code,
                )
            )

            if (
                scenario_df is None
                or scenario_df.empty
            ):
                continue

            scenario_df = scenario_df.sort_values(
                "projected_warming_c",
                ascending=False,
            ).head(10)

            scenario_fig.add_trace(
                go.Scatter(
                    x=scenario_df["country_name"],
                    y=scenario_df[
                        "projected_warming_c"
                    ],
                    mode="lines+markers",
                    name=scenario_name,
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "%{y:.2f}°C"
                        "<extra>%{fullData.name}</extra>"
                    ),
                )
            )

        except Exception:
            continue

    if scenario_fig.data:
        style_plotly(
            scenario_fig,
            height=390,
            y_title="Projected warming (°C)",
        )
        st.plotly_chart(
            scenario_fig,
            width="stretch",
            config={
                "displayModeBar": True,
                "responsive": True,
            },
        )

    st.markdown(
        """<div class="cp-method-box">
<b>Method:</b> World Bank CCKP CMIP6 country spatial averages.
Temperature change is the multi-model ensemble anomaly relative to
1995–2014. P10 and P90 communicate model uncertainty. This is a national
comparison, unlike ClimatePulse's centroid proxy used for ordinary
country point searches.
</div>""",
        unsafe_allow_html=True,
    )

    st.download_button(
        "Download ranking CSV",
        data=ranking_df.to_csv(
            index=False
        ),
        file_name=(
            f"climatepulse_country_warming_"
            f"{scenario_code}_{period_code}.csv"
        ),
        mime="text/csv",
        width="stretch",
    )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Global Rankings</div>',
        unsafe_allow_html=True,
    )

    st.stop()




# =========================================================
# CLIMATE PASSPORT
# =========================================================

if nav_view == "Climate Passport":

    passport_baseline_ready = False

    if (
        summary is not None
        and not summary.empty
        and "year" in summary.columns
    ):
        passport_baseline_years = summary[
            (
                summary["year"] >= 1991
            )
            &
            (
                summary["year"] <= 2020
            )
        ]

        passport_baseline_ready = (
            len(
                passport_baseline_years
            )
            >= 25
        )

    if (
        city is None
        or summary is None
        or summary.empty
        or climate_fingerprint is None
        or not passport_baseline_ready
    ):

        st.markdown(
            """
<div class="cp-landing">
<b>Climate Passport needs historical climate data</b><br>
<span class="cp-muted">
Search a location with sufficient ERA5 history. If it is a new place,
ClimatePulse will prepare its historical record before the passport can
be generated.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

        if city is not None:
            render_history_progress(
                city["city_id"]
            )

        st.stop()

    fp = climate_fingerprint

    if ANALYTICS_READY and AUDIENCE_ANALYTICS_READY:
        try:
            passport_location_label = (
                f"{city.get('city_name', '')}, {city.get('country_name', '')}"
                if isinstance(city, dict)
                else "Selected location"
            )
            track_event_once(
                f"passport::{passport_location_label}",
                "climate_passport_generated",
                category="climate_product",
                page_name=nav_view,
                metadata={
                    "location": passport_location_label,
                    "historical_period": "1990-2025",
                    "baseline": "1991-2020",
                },
            )
        except Exception as analytics_event_error:
            print("ClimatePulse passport analytics error:", analytics_event_error)

    passport_latest = (
        summary
        .sort_values(
            "year"
        )
        .iloc[-1]
    )

    passport_baseline = summary[
        (
            summary["year"] >= 1991
        )
        &
        (
            summary["year"] <= 2020
        )
    ]

    passport_mean_temp = safe_float(
        passport_baseline[
            "avg_temperature_c"
        ].mean()
    )

    passport_precip = safe_float(
        passport_baseline[
            "annual_precipitation_mm"
        ].mean()
    )

    passport_hot_days = safe_float(
        passport_baseline[
            "hot_days_30c"
        ].mean()
    )

    passport_extreme_days = safe_float(
        passport_baseline[
            "extreme_hot_days_35c"
        ].mean()
    )

    passport_record_high = safe_float(
        summary[
            "hottest_day_c"
        ].max()
    )

    passport_record_low = safe_float(
        summary[
            "coldest_day_c"
        ].min()
    )

    passport_html = f"""<div class="cp-passport">
<div class="cp-passport-eyebrow">ClimatePulse Climate Passport</div>
<div class="cp-passport-location">{city["city_name"]}, {city["country_name"]}</div>
<div class="cp-passport-meta">◈ {city["latitude"]:.4f}°, {city["longitude"]:.4f}° &nbsp; • &nbsp; ERA5 1990–2025 &nbsp; • &nbsp; Baseline 1991–2020</div>
<div class="cp-passport-signature">{climate_signature}</div>
</div>"""

    st.markdown(
        passport_html,
        unsafe_allow_html=True,
    )

    passport_left, passport_right = st.columns(
        [
            1.12,
            0.88,
        ],
        gap="medium",
    )

    with passport_left:

        st.markdown(
            f"""<div class="cp-passport-grid">
<div class="cp-passport-card">
<div class="cp-passport-label">Baseline mean temperature</div>
<div class="cp-passport-value">{fmt(passport_mean_temp, ".1f")}°C</div>
<div class="cp-passport-note">1991–2020 annual mean</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Baseline precipitation</div>
<div class="cp-passport-value">{fmt(passport_precip, ".0f")} mm</div>
<div class="cp-passport-note">Average annual total</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Hot days ≥30°C</div>
<div class="cp-passport-value">{fmt(passport_hot_days, ".0f")}</div>
<div class="cp-passport-note">Average days/year</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Very hot days ≥35°C</div>
<div class="cp-passport-value">{fmt(passport_extreme_days, ".0f")}</div>
<div class="cp-passport-note">Average days/year</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Warming trend</div>
<div class="cp-passport-value">{warming_text}</div>
<div class="cp-passport-note">1990–2025 linear trend</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Record high</div>
<div class="cp-passport-value">{fmt(passport_record_high, ".1f")}°C</div>
<div class="cp-passport-note">Daily maximum, 1990–2025</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Record low</div>
<div class="cp-passport-value">{fmt(passport_record_low, ".1f")}°C</div>
<div class="cp-passport-note">Daily minimum, 1990–2025</div>
</div>

<div class="cp-passport-card">
<div class="cp-passport-label">Latest annual mean</div>
<div class="cp-passport-value">{fmt(passport_latest["avg_temperature_c"], ".1f")}°C</div>
<div class="cp-passport-note">{int(passport_latest["year"])} ERA5</div>
</div>
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<div class="cp-product-note">
The Climate Passport summarizes the selected ERA5 grid point. For a
large administrative region, it represents the selected centroid rather
than an area-wide average.
</div>
            """,
            unsafe_allow_html=True,
        )

    with passport_right:

        passport_categories = [
            "Thermal Level",
            "Hot Extremes",
            "Rainfall",
            "Rainfall Variability",
            "Warming Signal",
        ]

        passport_values = [
            fp["thermal"]["score"],
            fp["hot_extremes"]["score"],
            fp["rainfall"]["score"],
            fp["variability"]["score"],
            fp["warming"]["score"],
        ]

        passport_values = [
            value
            if value is not None
            else 0
            for value in passport_values
        ]

        passport_radar = go.Figure()

        passport_radar.add_trace(
            go.Scatterpolar(
                r=(
                    passport_values
                    + [
                        passport_values[0]
                    ]
                ),
                theta=(
                    passport_categories
                    + [
                        passport_categories[0]
                    ]
                ),
                fill="toself",
                name="Climate Fingerprint",
                hovertemplate=(
                    "%{theta}: %{r:.0f}/100"
                    "<extra></extra>"
                ),
            )
        )

        passport_radar.update_layout(
            height=390,
            margin=dict(
                l=35,
                r=35,
                t=35,
                b=25,
            ),
            title=dict(
                text="Climate Fingerprint",
                x=0.5,
                font=dict(
                    size=15,
                ),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True,
                    range=[
                        0,
                        100,
                    ],
                    tickvals=[
                        0,
                        25,
                        50,
                        75,
                        100,
                    ],
                    gridcolor="rgba(130,170,195,.12)",
                    linecolor="rgba(130,170,195,.12)",
                    tickfont=dict(
                        size=8,
                        color="#68869a",
                    ),
                ),
                angularaxis=dict(
                    gridcolor="rgba(130,170,195,.10)",
                    linecolor="rgba(130,170,195,.10)",
                    tickfont=dict(
                        size=9,
                        color="#adc1cf",
                    ),
                ),
            ),
            font=dict(
                color="#d9e8f1",
            ),
        )

        st.plotly_chart(
            passport_radar,
            width="stretch",
            config={
                "displayModeBar": False,
            },
        )

    st.markdown(
        "### Fingerprint interpretation"
    )

    interpretation_columns = st.columns(
        5,
        gap="small",
    )

    interpretation_data = [
        (
            "Thermal",
            fp["thermal"],
        ),
        (
            "Heat",
            fp["hot_extremes"],
        ),
        (
            "Rainfall",
            fp["rainfall"],
        ),
        (
            "Variability",
            fp["variability"],
        ),
        (
            "Warming",
            fp["warming"],
        ),
    ]

    for column, (
        title_text,
        item,
    ) in zip(
        interpretation_columns,
        interpretation_data,
    ):
        with column:
            st.metric(
                title_text,
                (
                    f"{fingerprint_score_text(item['score'])}/100"
                ),
                item[
                    "label"
                ],
            )

    st.markdown(
        """
<div class="cp-product-note">
<b>How to read the Passport:</b> a higher fingerprint score means more of
that climate characteristic under the fixed ClimatePulse scale. It does
not mean “better”, “worse”, “safer” or “more dangerous”. Climate risk
would require separate hazard, exposure and vulnerability analysis.
</div>
        """,
        unsafe_allow_html=True,
    )

    passport_export = {
        "location": (
            f"{city['city_name']}, "
            f"{city['country_name']}"
        ),
        "latitude": float(
            city["latitude"]
        ),
        "longitude": float(
            city["longitude"]
        ),
        "historical_period": "1990-2025",
        "baseline": "1991-2020",
        "signature": climate_signature,
        "baseline_mean_temperature_c": (
            passport_mean_temp
        ),
        "baseline_precipitation_mm": (
            passport_precip
        ),
        "baseline_hot_days_30c": (
            passport_hot_days
        ),
        "baseline_extreme_hot_days_35c": (
            passport_extreme_days
        ),
        "warming_rate_c_per_decade": (
            warming_rate
        ),
        "record_high_c": (
            passport_record_high
        ),
        "record_low_c": (
            passport_record_low
        ),
        "fingerprint": {
            key: {
                "score": (
                    value[
                        "score"
                    ]
                ),
                "label": (
                    value[
                        "label"
                    ]
                ),
            }
            for key, value in fp.items()
        },
    }

    st.download_button(
        "Download Climate Passport (JSON)",
        data=json.dumps(
            passport_export,
            indent=2,
        ),
        file_name=(
            f"climatepulse_"
            f"{city['city_name'].lower().replace(' ', '_')}_"
            f"passport.json"
        ),
        mime="application/json",
        width="stretch",
    )

    st.caption(
        "Climate Passport is an interpretive ClimatePulse product "
        "based on ERA5 reanalysis and the selected point. "
        "It is not an official climate classification or risk assessment."
    )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Climate Passport</div>',
        unsafe_allow_html=True,
    )

    st.stop()



if nav_view == "About":
    render_about_page()
    st.stop()


if nav_view in {"Home", "Map Explorer"}:
    st.markdown('<div id="map-explorer"></div>', unsafe_allow_html=True)
    map_col, current_col = st.columns([1.55, 1], gap="medium")
    with map_col:
        render_map_fragment()

    with current_col:
        with st.container(border=True):
            if city is not None:
                temperature = current_weather.get("temperature_2m")
                feels_like = current_weather.get("apparent_temperature")
                humidity = current_weather.get("relative_humidity_2m")
                wind = current_weather.get("wind_speed_10m")
                precipitation_now = current_weather.get("precipitation")
                aqi = current_air.get("european_aqi")
                pm25 = current_air.get("pm2_5")
                st.markdown(
                    f"""
    <div class="cp-section-heading">☁️ &nbsp; Current Conditions <span class="cp-live-pill" style="float:right;">● Live</span></div>
    <div class="cp-current-temp">{fmt(temperature, '.1f')}°C</div>
    <div class="cp-muted">Feels like {fmt(feels_like, '.1f')}°C</div>
    <div class="cp-mini-grid">
    <div class="cp-mini-card"><div class="cp-mini-label">Humidity</div><div class="cp-mini-value">💧 {fmt(humidity, '.0f')}%</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Wind</div><div class="cp-mini-value">➤ {fmt(wind, '.1f')} km/h</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Precipitation</div><div class="cp-mini-value">🌧 {fmt(precipitation_now, '.1f')} mm</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">PM2.5</div><div class="cp-mini-value">{fmt(pm25, '.1f')} µg/m³</div></div>
    </div>
    <div class="cp-aqi"><div><div class="cp-mini-label">European Air Quality Index</div><div class="cp-mini-value">{aqi_note(aqi)}</div></div><div class="cp-aqi-value">{fmt(aqi, '.0f')}</div></div>
                    """,
                    unsafe_allow_html=True,
                )
            elif country_feature:

                if (
                    country_national is not None
                    and not country_national.empty
                ):
                    country_baseline = country_national[
                        (
                            country_national[
                                "year"
                            ] >= 1991
                        )
                        &
                        (
                            country_national[
                                "year"
                            ] <= 2020
                        )
                    ]

                    country_recent = country_national[
                        (
                            country_national[
                                "year"
                            ] >= 2015
                        )
                        &
                        (
                            country_national[
                                "year"
                            ] <= 2024
                        )
                    ]

                    national_temp = safe_float(
                        country_baseline[
                            "mean_temperature_c"
                        ].mean()
                    )

                    recent_temp = safe_float(
                        country_recent[
                            "mean_temperature_c"
                        ].mean()
                    )

                    national_precip = safe_float(
                        country_baseline[
                            "annual_precipitation_mm"
                        ].mean()
                    )

                    national_trend = safe_float(
                        country_national.attrs.get(
                            "warming_rate_c_per_decade"
                        )
                    )

                    centroid_temp = safe_float(
                        country_live_weather.get(
                            "temperature_2m"
                        )
                    )

                    st.markdown(
                        f"""
<div class="cp-section-heading">🌍 &nbsp; National Climate Overview</div>
<div class="cp-current-temp">{fmt(national_temp, '.1f')}°C</div>
<div class="cp-muted">1991–2020 national mean temperature</div>

<div class="cp-mini-grid" style="margin-top:18px;">
<div class="cp-mini-card">
<div class="cp-mini-label">Recent 2015–2024</div>
<div class="cp-mini-value">{fmt(recent_temp, '.1f')}°C</div>
</div>
<div class="cp-mini-card">
<div class="cp-mini-label">Warming trend</div>
<div class="cp-mini-value">{fmt(national_trend, '+.2f')}°C/dec</div>
</div>
<div class="cp-mini-card">
<div class="cp-mini-label">Baseline precipitation</div>
<div class="cp-mini-value">{fmt(national_precip, '.0f')} mm</div>
</div>
<div class="cp-mini-card">
<div class="cp-mini-label">Centroid weather now</div>
<div class="cp-mini-value">{fmt(centroid_temp, '.1f')}°C</div>
</div>
</div>

<div class="cp-product-note">
Historical values above are national spatial averages. “Centroid weather now”
is only a point proxy and is not national current weather.
</div>
                        """,
                        unsafe_allow_html=True,
                    )

                else:
                    centroid_temp = safe_float(
                        country_live_weather.get(
                            "temperature_2m"
                        )
                    )

                    centroid_humidity = safe_float(
                        country_live_weather.get(
                            "relative_humidity_2m"
                        )
                    )

                    st.markdown(
                        f"""
<div class="cp-section-heading">🌍 &nbsp; Country Climate</div>
<div class="cp-current-temp">{fmt(centroid_temp, '.1f')}°C</div>
<div class="cp-muted">
Live weather at the selected country centroid. This is a geographic
reference point, not a national-average current temperature.
</div>

<div class="cp-mini-grid" style="margin-top:18px;">
<div class="cp-mini-card">
<div class="cp-mini-label">Centroid humidity</div>
<div class="cp-mini-value">{fmt(centroid_humidity, '.0f')}%</div>
</div>
<div class="cp-mini-card">
<div class="cp-mini-label">National history</div>
<div class="cp-mini-value">Unavailable</div>
</div>
</div>
                        """,
                        unsafe_allow_html=True,
                    )

            else:
                st.markdown(
                    """
    <div class="cp-section-heading">ClimatePulse Explorer</div>
    <div class="cp-current-temp">Explore anywhere.</div>
    <div class="cp-muted">Search above to move the map instantly. Cities, towns, villages, neighbourhoods and many administrative areas can load point-based weather, air quality and ERA5 climate analytics.</div>
    <div class="cp-mini-grid" style="margin-top:18px;">
    <div class="cp-mini-card"><div class="cp-mini-label">Climate history</div><div class="cp-mini-value">1990–2025</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Database</div><div class="cp-mini-value">PostgreSQL / Neon</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Weather</div><div class="cp-mini-value">Open-Meteo</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Climate</div><div class="cp-mini-value">ERA5 / CRU / CMIP6</div></div>
    </div>
                    """,
                    unsafe_allow_html=True,
                )


if (
    nav_view == "Home"
    and city is not None
    and today_forecast
    and today_context
    and (
        today_context.get(
            "baseline_sample_count"
        )
        or 0
    ) >= 100
):

    forecast_high = safe_float(
        today_forecast.get(
            "temperature_max_c"
        )
    )

    forecast_low = safe_float(
        today_forecast.get(
            "temperature_min_c"
        )
    )

    typical_high = safe_float(
        today_context.get(
            "typical_high_c"
        )
    )

    typical_low = safe_float(
        today_context.get(
            "typical_low_c"
        )
    )

    high_p10 = safe_float(
        today_context.get(
            "high_p10_c"
        )
    )

    high_p90 = safe_float(
        today_context.get(
            "high_p90_c"
        )
    )

    high_percentile = safe_float(
        today_context.get(
            "high_percentile"
        )
    )

    seasonal_shift = safe_float(
        today_context.get(
            "seasonal_shift_c"
        )
    )

    record_high = safe_float(
        today_context.get(
            "seasonal_record_high_c"
        )
    )

    record_high_date = (
        today_context.get(
            "seasonal_record_high_date"
        )
    )

    difference_high = None

    if (
        forecast_high is not None
        and typical_high is not None
    ):
        difference_high = (
            forecast_high
            - typical_high
        )

    normal_label, normal_color = (
        today_normal_label(
            high_percentile
        )
    )

    if difference_high is None:
        difference_text = "N/A"
    else:
        difference_text = (
            f"{difference_high:+.1f}°C"
        )

    if high_percentile is None:
        percentile_text = "N/A"
        percentile_note = (
            "Not enough baseline observations"
        )
    else:
        percentile_text = (
            f"{high_percentile:.0f}th"
        )

        percentile_note = (
            f"Warmer than about "
            f"{high_percentile:.0f}% of comparable "
            f"1991–2020 days"
        )

    if (
        high_p10 is not None
        and high_p90 is not None
    ):
        normal_range_text = (
            f"{high_p10:.1f}–"
            f"{high_p90:.1f}°C"
        )
    else:
        normal_range_text = "N/A"

    if seasonal_shift is None:
        shift_text = "N/A"
    else:
        shift_text = (
            f"{seasonal_shift:+.1f}°C"
        )

    if record_high is None:
        record_text = "N/A"
        record_note = ""
    else:
        record_text = (
            f"{record_high:.1f}°C"
        )
        record_note = (
            safe_date_label(
                record_high_date
            )
        )

    if (
        forecast_high is not None
        and typical_high is not None
    ):
        if difference_high >= 2:
            story = (
                f"Today's forecast high is "
                f"{difference_high:.1f}°C above the "
                f"1991–2020 seasonal average."
            )

        elif difference_high <= -2:
            story = (
                f"Today's forecast high is "
                f"{abs(difference_high):.1f}°C below the "
                f"1991–2020 seasonal average."
            )

        else:
            story = (
                "Today's forecast high is close to the "
                "1991–2020 seasonal average."
            )

    else:
        story = (
            "Historical comparison is unavailable."
        )

    intel_html = f"""<div class="cp-intel">
<div class="cp-intel-top">
<div>
<div class="cp-intel-title">◉ Is Today Normal?</div>
<div class="cp-intel-sub">Today's forecast compared with ERA5 days within ±7 calendar days of this date, using the 1991–2020 climate baseline.</div>
</div>
<div class="cp-intel-status" style="color:{normal_color}; border-color:{normal_color}55;">{normal_label}</div>
</div>

<div class="cp-intel-grid">
<div class="cp-intel-card">
<div class="cp-intel-label">Today's forecast high</div>
<div class="cp-intel-value">{forecast_high:.1f}°C</div>
<div class="cp-intel-note">Typical: {typical_high:.1f}°C • {difference_text}</div>
</div>

<div class="cp-intel-card">
<div class="cp-intel-label">Climate percentile</div>
<div class="cp-intel-value">{percentile_text}</div>
<div class="cp-intel-note">{percentile_note}</div>
</div>

<div class="cp-intel-card">
<div class="cp-intel-label">Typical high range</div>
<div class="cp-intel-value">{normal_range_text}</div>
<div class="cp-intel-note">10th–90th percentile, 1991–2020</div>
</div>

<div class="cp-intel-card">
<div class="cp-intel-label">Seasonal warming shift</div>
<div class="cp-intel-value">{shift_text}</div>
<div class="cp-intel-note">2016–2025 vs 1991–2000 average high</div>
</div>

<div class="cp-intel-card">
<div class="cp-intel-label">Seasonal record high</div>
<div class="cp-intel-value">{record_text}</div>
<div class="cp-intel-note">{record_note}</div>
</div>
</div>

<div class="cp-intel-story">{story} This is climatological context, not a statement that climate change caused today's weather.</div>
</div>"""

    st.markdown(
        intel_html,
        unsafe_allow_html=True,
    )


if nav_view == "Map Explorer":

    if country_feature:
        render_country_national_dashboard(
            compact=True
        )

    if (
        city is not None
        and st.session_state.get(
            "history_status"
        )
        != "ready"
    ):
        render_history_progress(
            city["city_id"]
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Map Explorer</div>',
        unsafe_allow_html=True,
    )

    st.stop()


if (
    nav_view == "Data & Methods"
    and country_feature
):
    st.markdown(
        "### Country Data & Methods"
    )

    st.markdown(
        """
**Historical national climate:** World Bank Climate Change Knowledge
Portal (CCKP), spatially aggregated CRU country time series.

**Historical temperature and precipitation:** 1901–2024.

**Reference baseline:** 1991–2020.

**Observed national warming trend:** linear least-squares slope over
1971–2024, reported in °C per decade.

**Future national projections:** CCKP CMIP6 country spatial averages,
multi-model ensemble, with SSP1-2.6, SSP2-4.5, SSP3-7.0 and SSP5-8.5.

**Projection uncertainty:** P10 / median / P90 across the climate-model
ensemble.

**Current weather for a country:** when shown, this is the weather at
the selected country-search centroid only. It is explicitly a point
proxy and is not interpreted as a national average.
        """
    )

    if (
        country_national is not None
        and not country_national.empty
    ):
        st.dataframe(
            country_national,
            width="stretch",
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn(
                    "Year",
                    format="%d",
                ),
                "mean_temperature_c": st.column_config.NumberColumn(
                    "National mean temperature",
                    format="%.2f °C",
                ),
                "annual_precipitation_mm": st.column_config.NumberColumn(
                    "National annual precipitation",
                    format="%.0f mm",
                ),
            },
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Country Data & Methods</div>',
        unsafe_allow_html=True,
    )

    st.stop()


if nav_view == "Data & Methods":

    st.markdown(
        "### Data & Methods"
    )

    st.markdown(
        """
**Historical climate:** ERA5 reanalysis accessed through
Open-Meteo and stored in PostgreSQL/Neon.

**Historical period:** 1990–2025.

**Reference period:** 1991–2020.

**Temperature anomaly:** annual mean temperature minus the
1991–2020 mean for the selected ERA5 grid point.

**Warming trend:** least-squares regression slope calculated
in PostgreSQL and expressed in °C per decade.

**Spatial meaning:** ERA5 is gridded reanalysis. For cities,
towns, neighbourhoods and administrative areas, ClimatePulse
shows the grid point nearest the selected coordinate or
centroid rather than a boundary-wide average.
        """
    )

    if (
        summary is not None
        and not summary.empty
    ):
        tab1, tab2 = st.tabs(
            [
                "Annual climate data",
                "Temperature anomalies",
            ]
        )

        with tab1:
            st.dataframe(
                summary,
                width="stretch",
                hide_index=True,
            )

        with tab2:
            st.dataframe(
                anomalies,
                width="stretch",
                hide_index=True,
            )

    elif city is not None:
        render_history_progress(
            city["city_id"]
        )

        st.info(
            "Historical tables will appear automatically "
            "when this location's background import finishes."
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Data & Methods</div>',
        unsafe_allow_html=True,
    )

    st.stop()



# =========================================================
# COUNTRY DASHBOARD / CLIMATE TRENDS
# =========================================================

if (
    country_feature
    and nav_view in {
        "Home",
        "Climate Trends",
    }
):
    render_country_national_dashboard(
        compact=False
    )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • National Climate Intelligence</div>',
        unsafe_allow_html=True,
    )

    st.stop()


if (
    city is None
    or summary is None
    or summary.empty
    or anomalies is None
    or anomalies.empty
):

    if city is not None:

        render_history_progress(
            city["city_id"]
        )

        st.markdown(
            """
<div class="cp-landing">
<b>Live conditions are ready</b><br>
<span class="cp-muted">
ClimatePulse is preparing the 1990–2025 ERA5 history in the
background. You can continue using the map and live conditions;
historical charts appear automatically when the import completes.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
<div class="cp-landing">
<b>Start exploring</b><br>
<span class="cp-muted">
Search for any city, town, village, neighbourhood or place.
The map follows your selection immediately.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Global Climate Intelligence</div>',
        unsafe_allow_html=True,
    )

    st.stop()

if nav_view == "Climate Trends":
    st.markdown("### Climate Trends")

latest = summary.iloc[-1]
latest_anomaly = anomalies.iloc[-1]
latest_year = int(latest["year"])

st.markdown(
    f"""
<div class="cp-kpi-grid">
<div class="cp-kpi"><div class="cp-kpi-label">🌡 Mean Temp ({latest_year})</div><div class="cp-kpi-value cp-cyan">{latest['avg_temperature_c']:.1f}°C</div><div class="cp-kpi-note">Annual mean</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">↗ Temperature Anomaly</div><div class="cp-kpi-value cp-red">{latest_anomaly['anomaly_c']:+.2f}°C</div><div class="cp-kpi-note">vs 1991–2020</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">⌁ Warming Trend</div><div class="cp-kpi-value cp-blue">{warming_text}</div><div class="cp-kpi-note">Linear trend</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">☀ Days ≥30°C</div><div class="cp-kpi-value cp-orange">{int(latest['hot_days_30c'])}</div><div class="cp-kpi-note">Hot days</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">🔥 Days ≥35°C</div><div class="cp-kpi-value cp-red">{int(latest['extreme_hot_days_35c'])}</div><div class="cp-kpi-note">Extreme heat</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">🌧 Precipitation ({latest_year})</div><div class="cp-kpi-value cp-blue">{latest['annual_precipitation_mm']:.0f} mm</div><div class="cp-kpi-note">Annual total</div></div>
</div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CLIMATE FINGERPRINT
# =========================================================

if (
    nav_view == "Home"
    and climate_fingerprint
):

    fp = climate_fingerprint

    fingerprint_html = f"""<div class="cp-fingerprint-wrap">
<div class="cp-fingerprint-header">
<div>
<div class="cp-fingerprint-title">◈ Climate Fingerprint</div>
<div class="cp-fingerprint-sub">A compact descriptive signature of this location's 1991–2020 climate and 1990–2025 warming signal.</div>
</div>
<div class="cp-fingerprint-badge">{climate_signature}</div>
</div>

<div class="cp-fingerprint-metrics">
<div class="cp-fingerprint-metric">
<div class="cp-fingerprint-label">Thermal Level</div>
<div class="cp-fingerprint-score">{fingerprint_score_text(fp["thermal"]["score"])}</div>
<div class="cp-fingerprint-desc">{fp["thermal"]["label"]} · {fmt(fp["thermal"]["raw"], ".1f")}°C baseline mean</div>
</div>

<div class="cp-fingerprint-metric">
<div class="cp-fingerprint-label">Hot Extremes</div>
<div class="cp-fingerprint-score">{fingerprint_score_text(fp["hot_extremes"]["score"])}</div>
<div class="cp-fingerprint-desc">{fp["hot_extremes"]["label"]} hot-day profile</div>
</div>

<div class="cp-fingerprint-metric">
<div class="cp-fingerprint-label">Rainfall Amount</div>
<div class="cp-fingerprint-score">{fingerprint_score_text(fp["rainfall"]["score"])}</div>
<div class="cp-fingerprint-desc">{fp["rainfall"]["label"]} · {fmt(fp["rainfall"]["raw"], ".0f")} mm/year</div>
</div>

<div class="cp-fingerprint-metric">
<div class="cp-fingerprint-label">Rainfall Variability</div>
<div class="cp-fingerprint-score">{fingerprint_score_text(fp["variability"]["score"])}</div>
<div class="cp-fingerprint-desc">{fp["variability"]["label"]} year-to-year variation</div>
</div>

<div class="cp-fingerprint-metric">
<div class="cp-fingerprint-label">Warming Signal</div>
<div class="cp-fingerprint-score">{fingerprint_score_text(fp["warming"]["score"])}</div>
<div class="cp-fingerprint-desc">{fp["warming"]["label"]} · {warming_text}</div>
</div>
</div>

<div class="cp-product-note">
Fingerprint scores are descriptive 0–100 indices built from fixed climate anchors. They are designed to summarize climate character, not to rank safety, quality of life or climate risk.
</div>
</div>"""

    st.markdown(
        fingerprint_html,
        unsafe_allow_html=True,
    )

    radar_categories = [
        "Thermal Level",
        "Hot Extremes",
        "Rainfall",
        "Rainfall Variability",
        "Warming Signal",
    ]

    radar_values = [
        fp["thermal"]["score"],
        fp["hot_extremes"]["score"],
        fp["rainfall"]["score"],
        fp["variability"]["score"],
        fp["warming"]["score"],
    ]

    radar_values = [
        value
        if value is not None
        else 0
        for value in radar_values
    ]

    radar_fig = go.Figure()

    radar_fig.add_trace(
        go.Scatterpolar(
            r=(
                radar_values
                + [
                    radar_values[0]
                ]
            ),
            theta=(
                radar_categories
                + [
                    radar_categories[0]
                ]
            ),
            fill="toself",
            name="Climate Fingerprint",
            line=dict(
                width=2,
            ),
            hovertemplate=(
                "%{theta}: %{r:.0f}/100"
                "<extra></extra>"
            ),
        )
    )

    radar_fig.update_layout(
        height=320,
        margin=dict(
            l=35,
            r=35,
            t=20,
            b=25,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[
                    0,
                    100,
                ],
                tickvals=[
                    0,
                    25,
                    50,
                    75,
                    100,
                ],
                tickfont=dict(
                    size=9,
                    color="#668398",
                ),
                gridcolor="rgba(130,170,195,.12)",
                linecolor="rgba(130,170,195,.12)",
            ),
            angularaxis=dict(
                tickfont=dict(
                    size=10,
                    color="#a9becd",
                ),
                gridcolor="rgba(130,170,195,.10)",
                linecolor="rgba(130,170,195,.10)",
            ),
        ),
        font=dict(
            color="#d7e5ee",
        ),
    )

    with st.expander(
        "View fingerprint radar",
        expanded=False,
    ):
        st.plotly_chart(
            radar_fig,
            width="stretch",
            config={
                "displayModeBar": False,
            },
        )



st.markdown('<div id="climate-trends"></div>', unsafe_allow_html=True)
chart1, chart2, chart3 = st.columns(3, gap="medium")
with chart1:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Average Temperature Trend</div>', unsafe_allow_html=True)
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=summary["year"], y=summary["avg_temperature_c"], mode="lines+markers", name="Annual mean",
            line=dict(color="#42d5e6", width=2), marker=dict(color="#42d5e6", size=4),
        ))
        baseline = anomalies["baseline_temperature_c"].dropna() if "baseline_temperature_c" in anomalies.columns else pd.Series(dtype=float)
        if not baseline.empty:
            fig_temp.add_hline(y=float(baseline.iloc[-1]), line_dash="dash", line_color="#9aa9b5")
        style_plotly(fig_temp, height=280, y_title="°C")
        st.plotly_chart(fig_temp, width="stretch", config={"displayModeBar": False, "responsive": True})

with chart2:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Extreme Heat Days</div>', unsafe_allow_html=True)
        fig_heat = go.Figure()
        fig_heat.add_trace(go.Bar(x=summary["year"], y=summary["hot_days_30c"], name="≥30°C", marker_color="#ff9f43"))
        fig_heat.add_trace(go.Bar(x=summary["year"], y=summary["extreme_hot_days_35c"], name="≥35°C", marker_color="#ff5b5b"))
        fig_heat.update_layout(barmode="overlay")
        style_plotly(fig_heat, height=280, y_title="Days")
        st.plotly_chart(fig_heat, width="stretch", config={"displayModeBar": False, "responsive": True})

with chart3:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Total Precipitation</div>', unsafe_allow_html=True)
        fig_rain = go.Figure()
        fig_rain.add_trace(go.Scatter(
            x=summary["year"], y=summary["annual_precipitation_mm"], mode="lines+markers", name="Annual precipitation",
            line=dict(color="#4da8ff", width=2), marker=dict(color="#4da8ff", size=4),
            fill="tozeroy", fillcolor="rgba(77,168,255,.10)",
        ))
        style_plotly(fig_rain, height=280, y_title="mm")
        st.plotly_chart(fig_rain, width="stretch", config={"displayModeBar": False, "responsive": True})

secondary1, secondary2 = st.columns([1.15, 1], gap="medium")
with secondary1:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Temperature Anomaly</div>', unsafe_allow_html=True)
        colors = ["#ff6666" if value >= 0 else "#3aa7ff" for value in anomalies["anomaly_c"]]
        fig_anomaly = go.Figure(go.Bar(x=anomalies["year"], y=anomalies["anomaly_c"], marker_color=colors, name="Anomaly"))
        fig_anomaly.add_hline(y=0, line_width=1, line_color="#8597a6")
        style_plotly(fig_anomaly, height=255, y_title="°C")
        fig_anomaly.update_layout(showlegend=False)
        st.plotly_chart(fig_anomaly, width="stretch", config={"displayModeBar": False, "responsive": True})

with secondary2:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Climate Snapshot</div>', unsafe_allow_html=True)
        hottest_year_row = summary.loc[summary["avg_temperature_c"].idxmax()]
        coldest_year_row = summary.loc[summary["avg_temperature_c"].idxmin()]
        most_extreme_heat_row = summary.loc[summary["extreme_hot_days_35c"].idxmax()]
        st.markdown(
            f"""
<div class="cp-mini-grid">
<div class="cp-mini-card"><div class="cp-mini-label">Hottest year</div><div class="cp-mini-value">{int(hottest_year_row['year'])}</div><div class="cp-kpi-note">{hottest_year_row['avg_temperature_c']:.2f}°C mean</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Coolest year</div><div class="cp-mini-value">{int(coldest_year_row['year'])}</div><div class="cp-kpi-note">{coldest_year_row['avg_temperature_c']:.2f}°C mean</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Most ≥35°C days</div><div class="cp-mini-value">{int(most_extreme_heat_row['extreme_hot_days_35c'])} days</div><div class="cp-kpi-note">{int(most_extreme_heat_row['year'])}</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Hottest daily maximum</div><div class="cp-mini-value">{summary['hottest_day_c'].max():.1f}°C</div><div class="cp-kpi-note">1990–2025 record</div></div>
</div>
            """,
            unsafe_allow_html=True,
        )

if nav_view == "Home":
    st.markdown('<div id="data-methods"></div>', unsafe_allow_html=True)
    with st.expander("Technical Details & Data"):
        st.markdown(
            """
    **Climate source:** ERA5 reanalysis accessed programmatically through Open-Meteo.

    **Historical period:** 1990–2025.

    **Climate reference period:** 1991–2020.

    **Temperature anomaly:** annual mean temperature minus the city's 1991–2020 ERA5 mean.

    **Warming trend:** least-squares regression slope calculated in PostgreSQL using annual mean temperatures and expressed in °C per decade.

    **Extreme heat indicators:** number of days where daily maximum temperature is at least 30°C and 35°C.

    ERA5 represents gridded reanalysis conditions around the selected coordinates rather than a single physical weather station.
            """
        )
        tab1, tab2 = st.tabs(["Annual climate data", "Temperature anomalies"])
        with tab1:
            st.dataframe(summary, width="stretch", hide_index=True)
        with tab2:
            st.dataframe(anomalies, width="stretch", hide_index=True)


st.markdown(
    '<div class="cp-footer">ClimatePulse • Python + PostgreSQL + Neon + MapTiler + CARTO + Open-Meteo + ERA5 + Streamlit</div>',
   unsafe_allow_html=True,
)