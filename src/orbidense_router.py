from __future__ import annotations

from pathlib import Path
import base64
import streamlit as st

from src.orbidense_theme import (
    ensure_theme_state,
    inject_global_theme,
    render_theme_selector,
)
from src.developer_analytics_gate import (
    close_developer_analytics,
    developer_analytics_requested,
    developer_mode_active,
    developer_gate_status,
    open_developer_analytics,
    process_developer_gate,
    render_analytics_password_gate,
)
from src.analytics_dashboard import render_analytics_dashboard

LOGO = Path("assets/orbidense_logo_header.png")

# IMPORTANT: these route values are intentionally unchanged.
ROUTES = {
    "Home": "Home",
    "Climate Outlook": "Country Climate Outlook",
    "Population Exposure": "Country Climate Outlook",
    "Climate Action": "Climate Action & Progress",
    "Compare": "Compare Places",
    "Global Insights": "Global Rankings",
    "About": "About",
}

NAV_KEYS = {
    "Home": "site_nav_home",
    "Climate Outlook": "site_nav_outlook",
    "Population Exposure": "site_nav_exposure",
    "Climate Action": "site_nav_action",
    "Compare": "site_nav_compare",
    "Global Insights": "site_nav_global",
    "About": "site_nav_about",
}

EARLY_PUBLIC_CSS = """
<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"]{
  display:none!important;
  visibility:hidden!important;
  width:0!important;
  min-width:0!important;
}
[data-testid="stAppViewContainer"]>.main{margin-left:0!important}
</style>
"""


def _logo_uri() -> str:
    if not LOGO.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii")


def display_route(internal: str) -> str:
    if (
        internal == ROUTES["Climate Outlook"]
        and st.session_state.get("orbidense_outlook_target") == "Population Exposure"
    ):
        return "Population Exposure"

    for label, route in ROUTES.items():
        if label != "Population Exposure" and route == internal:
            return label
    return "Home"


def request_route(label: str, target=None) -> None:
    if label not in ROUTES:
        raise ValueError(f"Unknown ORBIDENSE route: {label}")

    st.session_state["main_navigation"] = ROUTES[label]

    if label == "Population Exposure" or target == "Population Exposure":
        st.session_state["orbidense_outlook_target"] = "Population Exposure"
    elif label == "Climate Outlook":
        st.session_state.pop("orbidense_outlook_target", None)


def _shell_css(active: str) -> None:
    """
    Final fixed public shell. Presentation only.

    Route/session/theme/analytics behaviour is deliberately untouched.
    """
    active_key = NAV_KEYS.get(active, NAV_KEYS["Home"])
    inject_global_theme()

    st.markdown(
        f"""
<style>
/* ============================================================
   ORBIDENSE FIXED HEADER — FINAL
   Header geometry and page offset are paired so content can never
   render underneath the logo/navigation.
   ============================================================ */
:root{{
  --orb-header-h:136px;
  --orb-content-top:154px;
}}

[data-testid="stMainBlockContainer"],
.block-container{{
  max-width:1680px!important;
  padding-top:var(--orb-content-top)!important;
  padding-left:clamp(.80rem,1.45vw,1.65rem)!important;
  padding-right:clamp(.80rem,1.45vw,1.65rem)!important;
  padding-bottom:1.5rem!important;
}}

/* Only the public row that actually contains the brand becomes fixed. */
div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
  position:fixed!important;
  inset:0 0 auto 0!important;
  width:100vw!important;
  height:var(--orb-header-h)!important;
  min-height:var(--orb-header-h)!important;
  z-index:10000!important;
  display:flex!important;
  align-items:center!important;
  gap:8px!important;
  margin:0!important;
  padding:8px clamp(20px,2vw,36px)!important;
  box-sizing:border-box!important;
  overflow:visible!important;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb,var(--orb-bg) 96%,var(--orb-primary) 4%),
      var(--orb-bg)
    )!important;
  border-bottom:1px solid var(--orb-border-soft)!important;
  box-shadow:0 10px 28px rgba(0,0,0,.17)!important;
}}

div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo)>div{{
  min-width:0!important;
  align-self:center!important;
}}

/* Logo is prominent but contained inside header — no overlap below it. */
.orb-nav-logo{{
  width:100%!important;
  height:116px!important;
  min-height:116px!important;
  display:flex!important;
  align-items:center!important;
  justify-content:flex-start!important;
  overflow:hidden!important;
}}
.orb-nav-logo img{{
  width:min(278px,100%)!important;
  max-width:278px!important;
  max-height:114px!important;
  height:auto!important;
  object-fit:contain!important;
  object-position:left center!important;
  transform:none!important;
  filter:drop-shadow(0 7px 18px rgba(0,0,0,.20))!important;
}}

/* Route-specific colour identity. */
.st-key-site_nav_home{{--nav-accent:#24DCE5}}
.st-key-site_nav_outlook{{--nav-accent:#48B9FF}}
.st-key-site_nav_exposure{{--nav-accent:#42D9A1}}
.st-key-site_nav_action{{--nav-accent:#17DAB6}}
.st-key-site_nav_compare{{--nav-accent:#A486F8}}
.st-key-site_nav_global{{--nav-accent:#538DFF}}
.st-key-site_nav_about{{--nav-accent:#F3A94A}}

[class*="st-key-site_nav_"] button{{
  width:100%!important;
  min-height:50px!important;
  height:50px!important;
  padding:.38rem .46rem!important;
  border-radius:12px!important;
  border:1px solid
    color-mix(in srgb,var(--nav-accent) 40%,var(--orb-border))!important;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb,var(--orb-nav-bg) 92%,var(--nav-accent) 8%),
      var(--orb-surface-2)
    )!important;
  color:var(--orb-text)!important;
  font-size:clamp(.75rem,.68rem + .16vw,.87rem)!important;
  font-weight:900!important;
  letter-spacing:-.008em!important;
  white-space:nowrap!important;
  opacity:1!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.035),
    0 5px 14px rgba(0,0,0,.09)!important;
  transition:all .16s ease!important;
}}
[class*="st-key-site_nav_"] button:hover{{
  transform:translateY(-1px)!important;
  border-color:var(--nav-accent)!important;
  background:color-mix(in srgb,var(--nav-accent) 13%,var(--orb-nav-hover))!important;
}}
.st-key-{active_key} button{{
  border-color:var(--nav-accent)!important;
  background:color-mix(in srgb,var(--nav-accent) 18%,var(--orb-nav-active))!important;
  box-shadow:
    inset 0 -3px 0 var(--nav-accent),
    0 0 22px color-mix(in srgb,var(--nav-accent) 17%,transparent)!important;
}}

.st-key-site_nav_home button::before{{content:"⌂";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_outlook button::before{{content:"☁";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_exposure button::before{{content:"♙";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_action button::before{{content:"◇";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_compare button::before{{content:"⚖";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_global button::before{{content:"◎";margin-right:.32rem;color:var(--nav-accent)}}
.st-key-site_nav_about button::before{{content:"ⓘ";margin-right:.32rem;color:var(--nav-accent)}}

/* Theme remains a first-class header control. */
[class*="st-key-orbidense_theme"] [data-baseweb="select"]>div{{
  min-height:50px!important;
  height:50px!important;
  border-radius:12px!important;
  border:1px solid var(--orb-border)!important;
  background:var(--orb-surface)!important;
  color:var(--orb-text)!important;
  box-shadow:0 5px 14px rgba(0,0,0,.09)!important;
}}

/* Exact zoom container only. */
.st-key-orbidense_zoom_controls{{
  position:fixed!important;
  top:144px!important;
  right:18px!important;
  z-index:9990!important;
  width:154px!important;
  min-width:154px!important;
  padding:4px!important;
  border:1px solid var(--orb-border)!important;
  border-radius:12px!important;
  background:var(--orb-surface)!important;
  box-shadow:0 8px 22px rgba(0,0,0,.17)!important;
}}
.st-key-orbidense_zoom_controls [data-testid="stHorizontalBlock"]{{
  gap:4px!important;
}}
.st-key-orbidense_zoom_controls button{{
  min-height:33px!important;
  height:33px!important;
  padding:0 .35rem!important;
  border-radius:8px!important;
  border:1px solid var(--orb-border-soft)!important;
  background:var(--orb-surface-2)!important;
  color:var(--orb-text)!important;
  font-size:.73rem!important;
  font-weight:900!important;
  box-shadow:none!important;
}}

/* Tablet */
@media(max-width:1280px){{
  :root{{--orb-header-h:124px;--orb-content-top:142px}}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    padding-left:14px!important;padding-right:14px!important;gap:6px!important;
  }}
  .orb-nav-logo{{height:106px!important;min-height:106px!important}}
  .orb-nav-logo img{{width:min(236px,100%)!important;max-width:236px!important;max-height:104px!important}}
  [class*="st-key-site_nav_"] button{{font-size:.68rem!important;padding:.30rem .20rem!important}}
  .st-key-orbidense_zoom_controls{{top:132px!important}}
}}



/* Mobile: fixed, horizontally scrollable app bar rather than unreadably tiny buttons. */
@media(max-width:760px){{
  :root{{--orb-header-h:92px;--orb-content-top:100px}}


  /* Fixed navigation must not reserve a second layout-height. */
  [data-testid="stElementContainer"]:has(
    > div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo)
  ){{
    height:0!important;
    min-height:0!important;
    margin:0!important;
    padding:0!important;
    overflow:visible!important;
  }}

  [data-testid="stMainBlockContainer"],
  .block-container{{
    padding-top:var(--orb-content-top)!important;
  }}


  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    height:var(--orb-header-h)!important;
    min-height:var(--orb-header-h)!important;
    overflow-x:auto!important;
    overflow-y:hidden!important;
    flex-wrap:nowrap!important;
    justify-content:flex-start!important;
    padding:6px 10px 8px!important;
    gap:6px!important;
    scrollbar-width:thin!important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo)>div{{
    flex:0 0 auto!important;
    width:auto!important;
    min-width:max-content!important;
  }}
  .orb-nav-logo{{
    width:106px!important;
    min-width:106px!important;
    height:76px!important;
    min-height:76px!important;
  }}
  .orb-nav-logo img{{
    width:104px!important;
    max-width:104px!important;
    max-height:74px!important;
  }}
  [class*="st-key-site_nav_"] button{{
    min-width:116px!important;
    height:44px!important;
    min-height:44px!important;
    font-size:.72rem!important;
  }}
  .st-key-orbidense_zoom_controls{{
    display:none!important;
  }}
}}
</style>
        """,
        unsafe_allow_html=True,
    )












def render_site_router(current_internal_route: str) -> str:
    """
    Public ORBIDENSE shell plus an owner-only Developer Analytics hook.

    Public route mappings remain unchanged. Developer Analytics is rendered
    only after a valid cp_gate session and a second analytics password.
    """
    ensure_theme_state()
    process_developer_gate()

    # Temporary safe diagnostics. No secret values are exposed.
    try:
        _cp_debug = str(st.query_params.get("cp_debug", "") or "").strip()
    except Exception:
        _cp_debug = ""

    if _cp_debug == "1":
        _status = developer_gate_status()
        st.info(
            "Developer gate diagnostics — "
            f"env={_status['env_file_exists']} | "
            f"key={_status['dev_key_configured']} | "
            f"password={_status['analytics_password_configured']} | "
            f"received={_status['gate_received']} | "
            f"matched={_status['gate_matched']} | "
            f"developer={_status['developer_mode']}"
        )

    # Private analytics is intercepted here before normal page dispatch.
    # This avoids adding a public route or modifying app.py.
    if developer_analytics_requested():
        _shell_css("Home")

        top = st.columns([1.9, 5.6, 1.15, 1.0], gap="small", vertical_alignment="center")
        logo = _logo_uri()
        with top[0]:
            if logo:
                st.markdown(
                    f'<div id="top" class="orb-nav-logo"><img src="{logo}" alt="ORBIDENSE"></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="orb-nav-logo"><b style="color:var(--orb-text)">ORBIDENSE</b></div>',
                    unsafe_allow_html=True,
                )
        with top[2]:
            st.button(
                "Back to site",
                key="dev_analytics_back",
                width="stretch",
                on_click=close_developer_analytics,
            )
        with top[3]:
            render_theme_selector()

        inject_global_theme()

        if render_analytics_password_gate():
            render_analytics_dashboard()
        st.stop()

    active = display_route(current_internal_route)
    _shell_css(active)

    dev = developer_mode_active()

    if dev:
        cols = st.columns(
            [2.00, .62, 1.05, 1.21, .94, .74, 1.03, .62, .82, .98],
            gap="small",
            vertical_alignment="center",
        )
    else:
        cols = st.columns(
            [2.00, .64, 1.10, 1.27, .98, .78, 1.08, .66, 1.05],
            gap="small",
            vertical_alignment="center",
        )

    logo = _logo_uri()
    with cols[0]:
        if logo:
            st.markdown(
                f'<div id="top" class="orb-nav-logo"><img src="{logo}" alt="ORBIDENSE"></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div id="top" class="orb-nav-logo"><b style="color:var(--orb-text);font-size:1.1rem">ORBIDENSE</b></div>',
                unsafe_allow_html=True,
            )

    labels = [
        "Home",
        "Climate Outlook",
        "Population Exposure",
        "Climate Action",
        "Compare",
        "Global Insights",
        "About",
    ]

    for col, label in zip(cols[1:8], labels):
        with col:
            st.button(
                label,
                key=NAV_KEYS[label],
                width="stretch",
                on_click=request_route,
                args=(label,),
            )

    if dev:
        with cols[8]:
            st.button(
                "Analytics",
                key="owner_dev_analytics",
                width="stretch",
                on_click=open_developer_analytics,
                help="Private owner analytics",
            )

        with cols[9]:
            render_theme_selector()

    else:
        with cols[8]:
            render_theme_selector()

    inject_global_theme()

    return st.session_state.get(
        "main_navigation",
        current_internal_route,
    )
