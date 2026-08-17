from __future__ import annotations

import streamlit as st


THEMES = {
    "Midnight": {
        "label": "🌙 Midnight",
        "mode": "dark",
        "bg": "#020C14",
        "bg_alt": "#041724",
        "surface": "#071D2B",
        "surface_2": "#0A2637",
        "surface_3": "#0E3348",
        "text": "#F5FAFC",
        "muted": "#A9C0CB",
        "muted_2": "#7997A6",
        "primary": "#25E0E7",
        "primary_2": "#19B9D1",
        "primary_soft": "rgba(37,224,231,.12)",
        "secondary": "#4BE3A6",
        "accent": "#6FB6FF",
        "border": "rgba(94,176,207,.34)",
        "border_soft": "rgba(94,176,207,.17)",
        "shadow": "0 14px 38px rgba(0,0,0,.25)",
        "chart_bg": "#071A27",
        "chart_grid": "rgba(137,190,213,.15)",
        "chart_axis": "#A6BCC7",
        "map_land": "#0B2B3D",
        "map_water": "#03101A",
        "nav_bg": "#071D2B",
        "nav_hover": "#0B3C4D",
        "nav_active": "#075B69",
        "input_bg": "#092535",
        "input_text": "#F4FAFC",
        "hero_overlay": "rgba(2,12,20,.88)",
        "hero_text": "#FFFFFF",
        "plot_template": "plotly_dark",
        "colorway": ["#25E0E7","#4BE3A6","#6FB6FF","#A88BFF","#FFB45B","#FF6F70"],
    },
    "Aurora": {
        "label": "🌌 Aurora",
        "mode": "dark",
        "bg": "#090B1B",
        "bg_alt": "#11142C",
        "surface": "#151A34",
        "surface_2": "#1B2141",
        "surface_3": "#252B52",
        "text": "#FBFAFF",
        "muted": "#C7C3DB",
        "muted_2": "#9993B5",
        "primary": "#9A87FF",
        "primary_2": "#48DCEB",
        "primary_soft": "rgba(154,135,255,.15)",
        "secondary": "#45E2AE",
        "accent": "#F08BFF",
        "border": "rgba(165,151,255,.38)",
        "border_soft": "rgba(165,151,255,.19)",
        "shadow": "0 16px 44px rgba(3,2,17,.36)",
        "chart_bg": "#12162F",
        "chart_grid": "rgba(190,180,255,.16)",
        "chart_axis": "#B7B1D0",
        "map_land": "#232A55",
        "map_water": "#080A18",
        "nav_bg": "#151A34",
        "nav_hover": "#282E57",
        "nav_active": "#40387A",
        "input_bg": "#191F3D",
        "input_text": "#FBFAFF",
        "hero_overlay": "rgba(10,10,30,.84)",
        "hero_text": "#FFFFFF",
        "plot_template": "plotly_dark",
        "colorway": ["#9A87FF","#48DCEB","#45E2AE","#F08BFF","#FFB86B","#FF718B"],
    },
    "Daylight": {
        "label": "☀️ Daylight",
        "mode": "light",
        "bg": "#F2F7F9",
        "bg_alt": "#E8F0F4",
        "surface": "#FFFFFF",
        "surface_2": "#F6FAFC",
        "surface_3": "#E6F1F5",
        "text": "#102B3B",
        "muted": "#496776",
        "muted_2": "#6B8795",
        "primary": "#007E91",
        "primary_2": "#00667E",
        "primary_soft": "rgba(0,126,145,.10)",
        "secondary": "#087857",
        "accent": "#355CC9",
        "border": "rgba(38,93,118,.30)",
        "border_soft": "rgba(38,93,118,.15)",
        "shadow": "0 12px 32px rgba(24,60,78,.12)",
        "chart_bg": "#FFFFFF",
        "chart_grid": "rgba(42,87,107,.15)",
        "chart_axis": "#526E7D",
        "map_land": "#D8E8EE",
        "map_water": "#EDF5F8",
        "nav_bg": "#FFFFFF",
        "nav_hover": "#E7F4F5",
        "nav_active": "#D3EFF1",
        "input_bg": "#FFFFFF",
        "input_text": "#102B3B",
        "hero_overlay": "rgba(4,19,29,.78)",
        "hero_text": "#FFFFFF",
        "plot_template": "plotly_white",
        "colorway": ["#007E91","#087857","#355CC9","#7C55C7","#CB6B16","#C94452"],
    },
}

# Preserve browser/session values from earlier versions.
_THEME_ALIASES = {
    "Atlas": "Aurora",
    "System": "Daylight",
}


def ensure_theme_state() -> str:
    current = st.session_state.get("orbidense_theme", "Midnight")
    current = _THEME_ALIASES.get(current, current)
    if current not in THEMES:
        current = "Midnight"

    st.session_state["orbidense_theme"] = current

    selector = st.session_state.get("orbidense_theme_choice")
    selector = _THEME_ALIASES.get(selector, selector)
    if selector not in THEMES:
        st.session_state["orbidense_theme_choice"] = current

    return current


def get_theme_tokens() -> dict:
    return THEMES[ensure_theme_state()].copy()


def _theme_css(t: dict) -> str:
    return f"""
<style>
:root{{
  --orb-bg:{t['bg']};
  --orb-bg-alt:{t['bg_alt']};
  --orb-surface:{t['surface']};
  --orb-surface-2:{t['surface_2']};
  --orb-surface-3:{t['surface_3']};
  --orb-text:{t['text']};
  --orb-muted:{t['muted']};
  --orb-muted-2:{t['muted_2']};
  --orb-primary:{t['primary']};
  --orb-primary-2:{t['primary_2']};
  --orb-primary-soft:{t['primary_soft']};
  --orb-secondary:{t['secondary']};
  --orb-accent:{t['accent']};
  --orb-border:{t['border']};
  --orb-border-soft:{t['border_soft']};
  --orb-shadow:{t['shadow']};
  --orb-nav-bg:{t['nav_bg']};
  --orb-nav-hover:{t['nav_hover']};
  --orb-nav-active:{t['nav_active']};
  --orb-input-bg:{t['input_bg']};
  --orb-input-text:{t['input_text']};
  --orb-hero-overlay:{t['hero_overlay']};
  --orb-hero-text:{t['hero_text']};
}}

html, body, .stApp, [data-testid="stAppViewContainer"],
section[data-testid="stMain"]{{
  background:
    radial-gradient(circle at 88% -8%, var(--orb-primary-soft), transparent 30%),
    linear-gradient(180deg,var(--orb-bg) 0%,var(--orb-bg-alt) 100%)!important;
  color:var(--orb-text)!important;
}}

[data-testid="stMainBlockContainer"],
.block-container{{
  color:var(--orb-text)!important;
}}

[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4{{
  color:var(--orb-text);
}}

[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"] p,
small{{
  color:var(--orb-muted)!important;
}}

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
textarea{{
  background:var(--orb-input-bg)!important;
  color:var(--orb-input-text)!important;
  border-color:var(--orb-border)!important;
}}

[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="input"] input,
[data-baseweb="base-input"] input,
textarea{{
  color:var(--orb-input-text)!important;
  opacity:1!important;
}}

[data-baseweb="menu"]{{
  background:var(--orb-surface)!important;
  border:1px solid var(--orb-border)!important;
}}
[data-baseweb="menu"] [role="option"]{{
  color:var(--orb-text)!important;
}}
[data-baseweb="menu"] [role="option"]:hover{{
  background:var(--orb-primary-soft)!important;
}}

[data-testid="stAlert"],
[data-testid="stExpander"]{{
  background:var(--orb-surface)!important;
  color:var(--orb-text)!important;
  border-color:var(--orb-border-soft)!important;
}}

[data-testid="stDataFrame"],
[data-testid="stTable"]{{
  color:var(--orb-text)!important;
}}

hr{{
  border-color:var(--orb-border-soft)!important;
}}

::selection{{
  background:var(--orb-primary);
  color:#FFFFFF;
}}
</style>
"""


def inject_global_theme() -> None:
    st.markdown(_theme_css(get_theme_tokens()), unsafe_allow_html=True)


def _apply_theme_choice() -> None:
    chosen = st.session_state.get("orbidense_theme_choice", "Midnight")
    chosen = _THEME_ALIASES.get(chosen, chosen)
    if chosen not in THEMES:
        chosen = "Midnight"
    st.session_state["orbidense_theme"] = chosen


def render_theme_selector() -> str:
    current = ensure_theme_state()
    if st.session_state.get("orbidense_theme_choice") not in THEMES:
        st.session_state["orbidense_theme_choice"] = current

    choice = st.selectbox(
        "Theme",
        options=list(THEMES.keys()),
        format_func=lambda name: THEMES[name]["label"],
        key="orbidense_theme_choice",
        label_visibility="collapsed",
        on_change=_apply_theme_choice,
    )

    if st.session_state.get("orbidense_theme") != choice:
        st.session_state["orbidense_theme"] = choice

    return choice
