from __future__ import annotations

import streamlit as st

THEME_OPTIONS = ("Midnight", "Atlas", "System")

MIDNIGHT = {
    "name": "Midnight",
    "mode": "dark",
    "bg": "#03101A",
    "surface": "#071B29",
    "surface_2": "#0A2333",
    "surface_3": "#0E2A3B",
    "border": "#173E50",
    "border_soft": "rgba(95,158,191,.18)",
    "text": "#F4FAFD",
    "muted": "#9EB4C1",
    "muted_2": "#78909F",
    "primary": "#31E2EB",
    "primary_hover": "#65F3F4",
    "primary_soft": "rgba(49,226,235,.10)",
    "blue": "#3D8EF7",
    "green": "#35D88A",
    "purple": "#9A74F5",
    "orange": "#F79A42",
    "red": "#E74A3C",
    "chart_bg": "rgba(5,17,27,.54)",
    "chart_grid": "rgba(121,181,207,.09)",
    "chart_axis": "#8097A8",
    "map_land": "#0B1D2B",
    "map_water": "#04101A",
    "shadow": "0 14px 34px rgba(0,0,0,.16)",
}

ATLAS = {
    "name": "Atlas",
    "mode": "light",
    "bg": "#F4F8FA",
    "surface": "#FFFFFF",
    "surface_2": "#EAF1F5",
    "surface_3": "#DDEAF0",
    "border": "#D2E0E7",
    "border_soft": "rgba(24,84,112,.14)",
    "text": "#102A3A",
    "muted": "#58717F",
    "muted_2": "#728893",
    "primary": "#007F9D",
    "primary_hover": "#006D88",
    "primary_soft": "rgba(0,127,157,.09)",
    "blue": "#176FC1",
    "green": "#16845C",
    "purple": "#7457BF",
    "orange": "#C96F1A",
    "red": "#C83C31",
    "chart_bg": "#FFFFFF",
    "chart_grid": "rgba(16,42,58,.08)",
    "chart_axis": "#5D7481",
    "map_land": "#E1E8EC",
    "map_water": "#F4F8FA",
    "shadow": "0 12px 30px rgba(31,62,77,.08)",
}


def _system_mode() -> str:
    """Best-effort browser/Streamlit theme detection with a safe fallback."""
    try:
        context = getattr(st, "context", None)
        theme = getattr(context, "theme", None)
        theme_type = str(getattr(theme, "type", "") or "").lower()
        if theme_type == "light":
            return "Atlas"
        if theme_type == "dark":
            return "Midnight"
    except Exception:
        pass
    return "Midnight"


def ensure_theme_state() -> str:
    value = st.session_state.get("orbidense_theme_choice")
    if value not in THEME_OPTIONS:
        st.session_state["orbidense_theme_choice"] = "Midnight"
    return st.session_state["orbidense_theme_choice"]


def selected_theme_name() -> str:
    choice = ensure_theme_state()
    if choice == "System":
        return _system_mode()
    return choice


def get_theme_tokens() -> dict:
    return dict(ATLAS if selected_theme_name() == "Atlas" else MIDNIGHT)


def inject_global_theme() -> None:
    t = get_theme_tokens()
    mode = t["mode"]

    atlas_extra = """
    [data-testid="stAppViewContainer"]{
      background:
        radial-gradient(circle at 82% 6%, rgba(0,127,157,.06), transparent 30%),
        #F4F8FA!important;
    }
    [data-testid="stMainBlockContainer"]{
      background:transparent!important;
    }

    /* Strong Atlas page typography */
    .orb-h1,.orb-section-title,.orb-creator-name,
    .hf-title,.hf-panel h4,.hf-question .t,.hf-metric .v,.hf-signal h4,
    .orb-big,.orb-signal .value,.orb-story-copy{
      color:#102A3A!important;
    }
    .orb-sub,.orb-note,.orb-source,.orb-creator-role,
    .hf-copy,.hf-sub,.hf-note,.hf-question .c,.hf-metric .l,.hf-signal-sub,
    .orb-signal .context,.orb-viz-sub,.orb-rank-name{
      color:#58717F!important;
    }
    .orb-kicker,.orb-section-eyebrow,.orb-story-title{
      color:#007F9D!important;
    }

    /* Atlas cards and analytical containers */
    .orb-card,.orb-hero,.orb-passport-panel,.orb-creator,
    .orb-signal,.orb-story,.orb-viz-shell,
    .hf-panel,.hf-question,.hf-metric,.hf-signal,.hf-signal-card{
      background:#FFFFFF!important;
      border:1px solid #D7E3E8!important;
      box-shadow:0 10px 28px rgba(31,62,77,.07)!important;
    }

    .orb-viz-shell{
      background:#EEF4F7!important;
      border-color:#D4E2E8!important;
    }

    /* Selectors */
    div[data-testid="stSelectbox"] [data-baseweb="select"]>div,
    div[data-testid="stMultiSelect"] [data-baseweb="select"]>div{
      background:#FFFFFF!important;
      border-color:#CBDCE4!important;
      color:#102A3A!important;
      box-shadow:0 6px 18px rgba(31,62,77,.04)!important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"]>div:hover,
    div[data-testid="stMultiSelect"] [data-baseweb="select"]>div:hover{
      border-color:#007F9D!important;
    }

    /* Segmented control: pale blue-grey, not harsh white */
    .st-key-v41_outlook_section_main button,
    .st-key-v41_outlook_section_exposure button{
      background:#EEF4F7!important;
      color:#526D7A!important;
      border-color:#D5E2E8!important;
    }
    .st-key-v41_outlook_section_main button:hover,
    .st-key-v41_outlook_section_exposure button:hover{
      color:#102A3A!important;
      border-color:#007F9D!important;
      background:#E6F2F5!important;
    }
    .st-key-v41_outlook_section_main button[aria-pressed="true"],
    .st-key-v41_outlook_section_exposure button[aria-pressed="true"]{
      color:#006B83!important;
      border-color:#007F9D!important;
      background:#E1F5F7!important;
      box-shadow:inset 0 -3px 0 #007F9D!important;
    }

    /* Plotly outer containers should visually join Atlas */
    [data-testid="stPlotlyChart"]{
      background:#FFFFFF!important;
      border:1px solid #D8E4EA!important;
      border-radius:16px!important;
      box-shadow:0 10px 24px rgba(31,62,77,.055)!important;
      overflow:hidden!important;
    }

    /* DataFrame / expander light surfaces */
    [data-testid="stExpander"],
    [data-testid="stDataFrame"]{
      background:#FFFFFF!important;
      border-color:#D8E4EA!important;
    }

    .home-final-hero{
      background:
        linear-gradient(90deg,rgba(244,248,250,.98) 0%,rgba(244,248,250,.92) 43%,rgba(244,248,250,.12) 74%),
        var(--orb-bg)!important;
      border-color:#D7E3E8!important;
    }
    """

    st.markdown(
        f"""
<style>
:root {{
  --orb-bg:{t["bg"]};
  --orb-surface:{t["surface"]};
  --orb-surface-2:{t["surface_2"]};
  --orb-surface-3:{t["surface_3"]};
  --orb-border:{t["border"]};
  --orb-border-soft:{t["border_soft"]};
  --orb-text:{t["text"]};
  --orb-muted:{t["muted"]};
  --orb-muted-2:{t["muted_2"]};
  --orb-primary:{t["primary"]};
  --orb-primary-hover:{t["primary_hover"]};
  --orb-primary-soft:{t["primary_soft"]};
  --orb-blue:{t["blue"]};
  --orb-green:{t["green"]};
  --orb-purple:{t["purple"]};
  --orb-orange:{t["orange"]};
  --orb-red:{t["red"]};
  --orb-shadow:{t["shadow"]};
}}

html, body, [data-testid="stAppViewContainer"] {{
  color:var(--orb-text)!important;
}}
[data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(circle at 83% 7%, color-mix(in srgb, var(--orb-primary) 7%, transparent), transparent 30%),
    var(--orb-bg)!important;
}}
[data-testid="stHeader"] {{
  background:transparent!important;
}}

.orb-h1,.orb-section-title,.orb-creator-name,
.hf-title,.hf-panel h4,.hf-question .t,.hf-metric .v,.hf-signal h4,
.orb-big,.orb-signal .value,.orb-story-copy {{
  color:var(--orb-text)!important;
}}
.orb-sub,.orb-note,.orb-source,.orb-creator-role,
.hf-copy,.hf-sub,.hf-note,.hf-question .c,.hf-metric .l,.hf-signal-sub,
.orb-signal .context,.orb-viz-sub,.orb-rank-name {{
  color:var(--orb-muted)!important;
}}
.orb-kicker,.orb-section-eyebrow,.orb-story-title {{
  color:var(--orb-primary)!important;
}}

.orb-card,.orb-hero,.orb-passport-panel,.orb-creator,
.orb-signal,.orb-story,.orb-viz-shell,
.hf-panel,.hf-question,.hf-metric,.hf-signal,.hf-signal-card {{
  background:linear-gradient(145deg,var(--orb-surface),var(--orb-surface-2))!important;
  border-color:var(--orb-border-soft)!important;
  box-shadow:var(--orb-shadow)!important;
}}

div[data-testid="stSelectbox"] [data-baseweb="select"]>div,
div[data-testid="stMultiSelect"] [data-baseweb="select"]>div {{
  background:var(--orb-surface)!important;
  border-color:var(--orb-border)!important;
  color:var(--orb-text)!important;
}}

.st-key-v41_outlook_section_main button,
.st-key-v41_outlook_section_exposure button {{
  background:var(--orb-surface)!important;
  color:var(--orb-muted)!important;
  border-color:var(--orb-border)!important;
}}
.st-key-v41_outlook_section_main button:hover,
.st-key-v41_outlook_section_exposure button:hover {{
  color:var(--orb-text)!important;
  border-color:var(--orb-primary)!important;
  background:var(--orb-primary-soft)!important;
}}
.st-key-v41_outlook_section_main button[aria-pressed="true"],
.st-key-v41_outlook_section_exposure button[aria-pressed="true"] {{
  color:var(--orb-primary)!important;
  border-color:var(--orb-primary)!important;
  background:var(--orb-primary-soft)!important;
  box-shadow:inset 0 -3px 0 var(--orb-primary)!important;
}}

[data-testid="stExpander"],
[data-testid="stDataFrame"] {{
  border-color:var(--orb-border-soft)!important;
  background:var(--orb-surface)!important;
}}

.st-key-orbidense_theme_choice div[data-baseweb="select"]>div {{
  min-height:44px!important;
  border-radius:12px!important;
  background:var(--orb-surface)!important;
  border:1px solid var(--orb-border)!important;
  color:var(--orb-text)!important;
}}
.st-key-orbidense_theme_choice label {{
  display:none!important;
}}

{atlas_extra if mode == "light" else ""}
</style>
        """,
        unsafe_allow_html=True,
    )




def render_theme_selector() -> str:
    ensure_theme_state()
    st.selectbox(
        "Appearance",
        THEME_OPTIONS,
        key="orbidense_theme_choice",
        label_visibility="collapsed",
        format_func=lambda x: {
            "Midnight": "🌙 Midnight",
            "Atlas": "☀️ Atlas",
            "System": "◐ System",
        }.get(x, x),
    )
    return selected_theme_name()
