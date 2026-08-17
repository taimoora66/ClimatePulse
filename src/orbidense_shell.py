from __future__ import annotations

from pathlib import Path
import base64
import pandas as pd
import streamlit as st

LOGO = Path('assets/orbidense_logo.png')
CCKP = Path('data/climate_intelligence/cckp_country_projections.parquet')

ROUTE_MAP = {
    'Home': ('Home', None),
    'Climate Outlook': ('Climate Outlook', None),
    'Population Exposure': ('Climate Outlook', 'Population Exposure'),
    'Climate Action': ('Climate Action', None),
    'Compare': ('Compare', None),
    'Global Insights': ('Global Insights', None),
    'About': ('About', None),
}

@st.cache_data(show_spinner=False)
def _country_catalog() -> list[str]:
    if not CCKP.exists():
        return []
    try:
        d = pd.read_parquet(CCKP, columns=['iso3', 'country'])
        d = d.dropna().drop_duplicates().sort_values(['country', 'iso3'])
        return [f'{r.country} · {r.iso3}' for r in d.itertuples(index=False)]
    except Exception:
        return []

def _logo_uri() -> str:
    if not LOGO.exists():
        return ''
    return 'data:image/png;base64,' + base64.b64encode(LOGO.read_bytes()).decode('ascii')

def _css() -> None:
    st.markdown('''
<style>
[data-testid="stSidebar"]{display:none!important}
[data-testid="collapsedControl"]{display:none!important}
[data-testid="stSidebarCollapsedControl"]{display:none!important}
[data-testid="stAppViewContainer"] > .main{margin-left:0!important}
.block-container{max-width:1540px!important;padding:.35rem 1.05rem 1.5rem!important}
.orb-shell-header{position:relative;z-index:20;display:flex;align-items:center;gap:16px;min-height:61px;margin:0 0 5px;padding:5px 8px 7px;border-bottom:1px solid rgba(61,160,213,.20);background:linear-gradient(180deg,rgba(2,13,23,.99),rgba(2,13,23,.94))}
.orb-shell-brand{flex:0 0 250px;display:flex;align-items:center}.orb-shell-brand img{width:228px;max-height:50px;object-fit:contain;object-position:left center}
.orb-shell-status{margin-left:auto;display:inline-flex;align-items:center;gap:6px;color:#7aeedc;font-size:.62rem;font-weight:850;white-space:nowrap;border:1px solid rgba(0,230,211,.24);background:rgba(0,230,211,.06);border-radius:999px;padding:6px 9px}.orb-shell-dot{width:7px;height:7px;border-radius:50%;background:#20e59d;box-shadow:0 0 10px rgba(32,229,157,.75)}
div[data-testid="stSegmentedControl"]{margin-top:-59px!important;margin-left:252px!important;margin-right:255px!important;min-height:56px!important;display:flex!important;align-items:center!important}div[data-testid="stSegmentedControl"] > div{gap:2px!important}div[data-testid="stSegmentedControl"] button{background:transparent!important;border:0!important;box-shadow:none!important;min-height:43px!important;border-radius:0!important;color:#b9c8d3!important;font-size:.73rem!important;font-weight:700!important}div[data-testid="stSegmentedControl"] button[aria-pressed="true"]{color:#33e5df!important;border-bottom:2px solid #20dff1!important}
.orb-search-caption{color:#708a9d;font-size:.58rem;margin-top:1px;margin-bottom:-6px}div[data-testid="stSelectbox"] > div > div{border-radius:12px!important}
.orbidense-ai-fab,.orbidense-ai,.ai-fab,.floating-ai,[data-testid="stChatFloatingInputContainer"]{display:none!important}
@media(max-width:1100px){.orb-shell-brand{flex-basis:195px}.orb-shell-brand img{width:178px}.orb-shell-status{display:none}div[data-testid="stSegmentedControl"]{margin-left:197px!important;margin-right:0!important}}
@media(max-width:760px){.block-container{padding:.25rem .55rem 1rem!important}.orb-shell-header{min-height:48px;padding:3px 4px}.orb-shell-brand{flex-basis:155px}.orb-shell-brand img{width:150px;max-height:39px}div[data-testid="stSegmentedControl"]{margin:0!important;overflow-x:auto!important;min-height:42px!important;padding-bottom:2px!important}div[data-testid="stSegmentedControl"] button{min-width:max-content!important;font-size:.65rem!important;padding:.25rem .5rem!important}.orb-search-caption{display:none}}
</style>
''', unsafe_allow_html=True)

def render_orbidense_top_nav(nav_view: str) -> None:
    _css()
    logo = _logo_uri()
    brand = f'<img src="{logo}" alt="ORBIDENSE">' if logo else '<div style="color:#fff;font-size:1.2rem;font-weight:950">ORBIDENSE</div>'
    st.markdown(f'''<div id="top" class="orb-shell-header"><div class="orb-shell-brand">{brand}</div><div class="orb-shell-status"><span class="orb-shell-dot"></span> Production data ready</div></div>''', unsafe_allow_html=True)

    active_label = 'Home'
    for label, (route, _) in ROUTE_MAP.items():
        if route == nav_view and label != 'Population Exposure':
            active_label = label
            break

    selected = st.segmented_control('ORBIDENSE main navigation', options=list(ROUTE_MAP.keys()), default=active_label, key='orbidense_top_nav', label_visibility='collapsed')
    if selected:
        route, target = ROUTE_MAP[selected]
        if route != nav_view or target:
            st.session_state['main_navigation'] = route
            if target:
                st.session_state['orbidense_outlook_target'] = target
            st.rerun()

    countries = _country_catalog()
    if countries:
        st.markdown('<div class="orb-search-caption">Search a country or territory and open its Climate Outlook</div>', unsafe_allow_html=True)
        chosen = st.selectbox('Search countries or places', ['Search countries or places…'] + countries, index=0, key='orbidense_country_jump', label_visibility='collapsed')
        if chosen != 'Search countries or places…':
            st.session_state['orbidense_selected_iso3'] = chosen.rsplit(' · ', 1)[-1].strip().upper()
            st.session_state['main_navigation'] = 'Climate Outlook'
            st.rerun()
