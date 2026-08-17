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
    active_key = NAV_KEYS.get(active, NAV_KEYS["Home"])
    inject_global_theme()

    st.markdown(
        f"""
<style>
.block-container{{
  max-width:1600px!important;
  padding:.42rem 1.15rem 1.55rem!important;
}}

.orb-nav-logo{{
  height:54px;
  display:flex;
  align-items:center;
}}
.orb-nav-logo img{{
  width:210px;
  max-height:50px;
  object-fit:contain;
  object-position:left center;
}}

[class*="st-key-site_nav_"] button{{
  width:100%!important;
  min-height:45px!important;
  padding:.42rem .50rem!important;
  border:1px solid var(--orb-border)!important;
  border-radius:12px!important;
  background:var(--orb-surface)!important;
  color:var(--orb-muted)!important;
  box-shadow:none!important;
  font-size:.74rem!important;
  line-height:1.08!important;
  font-weight:780!important;
  transition:all .15s ease!important;
}}
[class*="st-key-site_nav_"] button:hover{{
  color:var(--orb-text)!important;
  background:var(--orb-primary-soft)!important;
  border-color:var(--orb-primary)!important;
  transform:translateY(-1px)!important;
}}

.st-key-{active_key} button{{
  color:var(--orb-primary)!important;
  background:var(--orb-primary-soft)!important;
  border-color:var(--orb-primary)!important;
  box-shadow:inset 0 -3px 0 var(--orb-primary)!important;
}}


.st-key-owner_dev_analytics button{{
  color:var(--orb-primary)!important;
  border-color:var(--orb-primary)!important;
  background:var(--orb-primary-soft)!important;
  font-weight:900!important;
}}
.st-key-owner_dev_analytics button:hover{{
  box-shadow:inset 0 -3px 0 var(--orb-primary)!important;
}}

@media(max-width:1220px){{
  .orb-nav-logo img{{width:190px}}
  [class*="st-key-site_nav_"] button{{
    font-size:.66rem!important;
    padding:.34rem .24rem!important;
  }}
}}

@media(max-width:900px){{
  .block-container{{padding:.32rem .72rem 1.2rem!important}}
  .orb-nav-logo img{{width:150px}}
  [class*="st-key-site_nav_"] button{{
    min-height:42px!important;
    font-size:.64rem!important;
  }}
}}

@media(max-width:700px){{
  .orb-nav-logo{{justify-content:center}}
  [class*="st-key-site_nav_"] button{{
    font-size:.70rem!important;
  }}
}}

/* ============================================================
   ORBIDENSE BRAND + NAV V2 - VISUAL OVERRIDES ONLY
   No route/session/callback/theme/analytics logic is changed.
   ============================================================ */

.orb-nav-logo{{
  display:flex!important;
  align-items:center!important;
  min-height:78px!important;
  overflow:visible!important;
}}

.orb-nav-logo img{{
  width:min(268px,100%)!important;
  max-width:268px!important;
  max-height:82px!important;
  height:auto!important;
  object-fit:contain!important;
  object-position:left center!important;
  display:block!important;
  filter:drop-shadow(0 5px 16px rgba(0,0,0,.24))!important;
}}

/* Public navigation */
[class*="st-key-site_nav_"] button{{
  min-height:46px!important;
  padding:.42rem .60rem!important;
  border-radius:12px!important;
  border:1px solid rgba(89,157,188,.24)!important;
  background:linear-gradient(
    180deg,
    rgba(11,35,52,.80),
    rgba(7,27,42,.74)
  )!important;
  color:var(--orb-muted,#b9c9d4)!important;
  font-size:.76rem!important;
  font-weight:760!important;
  letter-spacing:-.008em!important;
  white-space:nowrap!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.035),
    0 4px 14px rgba(0,0,0,.10)!important;
  transition:
    transform .16s ease,
    border-color .16s ease,
    background .16s ease,
    color .16s ease,
    box-shadow .16s ease!important;
}}

[class*="st-key-site_nav_"] button:hover{{
  color:var(--orb-text,#f4fbff)!important;
  border-color:rgba(53,230,223,.46)!important;
  background:linear-gradient(
    180deg,
    rgba(13,48,66,.94),
    rgba(8,34,50,.90)
  )!important;
  transform:translateY(-1px)!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.05),
    0 7px 18px rgba(0,0,0,.14)!important;
}}

/* Active public page - existing key/callback logic is reused */
.st-key-{active_key} button{{
  color:var(--orb-primary,#35e6df)!important;
  border-color:rgba(53,230,223,.58)!important;
  background:linear-gradient(
    180deg,
    rgba(14,65,74,.78),
    rgba(8,40,53,.82)
  )!important;
  box-shadow:
    inset 0 -3px 0 var(--orb-primary,#35e6df),
    inset 0 1px 0 rgba(255,255,255,.055),
    0 7px 18px rgba(0,0,0,.12)!important;
}}

/* Private owner Analytics entry - styling only */
.st-key-owner_dev_analytics button{{
  min-height:46px!important;
  padding:.42rem .58rem!important;
  border-radius:12px!important;
  border:1px solid rgba(53,230,223,.34)!important;
  background:linear-gradient(
    180deg,
    rgba(10,49,62,.82),
    rgba(7,31,45,.80)
  )!important;
  color:var(--orb-primary,#35e6df)!important;
  font-size:.74rem!important;
  font-weight:820!important;
  white-space:nowrap!important;
}}

.st-key-owner_dev_analytics button:hover{{
  color:var(--orb-text,#f4fbff)!important;
  border-color:rgba(53,230,223,.64)!important;
  transform:translateY(-1px)!important;
}}

/* Responsive logo/nav balance */
@media(max-width:1220px){{
  .orb-nav-logo{{min-height:70px!important}}
  .orb-nav-logo img{{
    width:min(232px,100%)!important;
    max-width:232px!important;
    max-height:72px!important;
  }}
  [class*="st-key-site_nav_"] button{{
    font-size:.68rem!important;
    padding:.36rem .38rem!important;
  }}
  .st-key-owner_dev_analytics button{{
    font-size:.67rem!important;
    padding:.36rem .38rem!important;
  }}
}}

@media(max-width:900px){{
  .orb-nav-logo{{min-height:62px!important}}
  .orb-nav-logo img{{
    width:min(202px,100%)!important;
    max-width:202px!important;
    max-height:64px!important;
  }}
  [class*="st-key-site_nav_"] button,
  .st-key-owner_dev_analytics button{{
    min-height:42px!important;
    font-size:.63rem!important;
  }}
}}

@media(max-width:760px){{
  .orb-nav-logo img{{
    width:min(176px,100%)!important;
    max-width:176px!important;
    max-height:58px!important;
  }}
}}


/* ============================================================
   ORBIDENSE BRAND + NAV V3 - COMPACT HEADER
   VISUAL OVERRIDES ONLY.
   ============================================================ */

.orb-nav-logo{{
  min-height:88px!important;
  display:flex!important;
  align-items:center!important;
  overflow:visible!important;
}}

.orb-nav-logo img{{
  width:min(310px,100%)!important;
  max-width:310px!important;
  max-height:94px!important;
  height:auto!important;
  object-fit:contain!important;
  object-position:left center!important;
  display:block!important;
  filter:drop-shadow(0 6px 17px rgba(0,0,0,.22))!important;
}}

[class*="st-key-site_nav_"] button{{
  min-height:44px!important;
  padding:.34rem .48rem!important;
  border-radius:10px!important;
  border:1px solid rgba(90,157,188,.30)!important;
  background:linear-gradient(180deg,rgba(13,39,56,.86),rgba(8,29,44,.82))!important;
  color:#d3e0e8!important;
  font-size:.76rem!important;
  font-weight:750!important;
  letter-spacing:-.006em!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 3px 10px rgba(0,0,0,.08)!important;
}}

[class*="st-key-site_nav_"] button:hover{{
  color:#f2fbff!important;
  border-color:rgba(52,225,221,.56)!important;
  background:linear-gradient(180deg,rgba(14,54,70,.94),rgba(8,37,51,.92))!important;
  transform:translateY(-1px)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 5px 14px rgba(0,0,0,.12)!important;
}}

.st-key-{active_key} button{{
  color:#31e6df!important;
  border-color:rgba(49,230,223,.68)!important;
  background:linear-gradient(180deg,rgba(14,67,76,.84),rgba(8,43,56,.88))!important;
  box-shadow:inset 0 -3px 0 #24e3e8,inset 0 1px 0 rgba(255,255,255,.06),0 5px 14px rgba(0,0,0,.10)!important;
}}

.st-key-owner_dev_analytics button{{
  min-height:44px!important;
  padding:.34rem .46rem!important;
  border-radius:10px!important;
  border:1px solid rgba(49,230,223,.42)!important;
  background:linear-gradient(180deg,rgba(11,52,63,.86),rgba(7,34,47,.84))!important;
  color:#31e6df!important;
  font-size:.73rem!important;
  font-weight:800!important;
}}

div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
  margin-top:-.15rem!important;
  margin-bottom:-1.15rem!important;
  align-items:center!important;
}}

@media(max-width:1220px){{
  .orb-nav-logo{{min-height:78px!important}}
  .orb-nav-logo img{{
    width:min(272px,100%)!important;
    max-width:272px!important;
    max-height:83px!important;
  }}
  [class*="st-key-site_nav_"] button{{
    min-height:42px!important;
    font-size:.68rem!important;
    padding:.30rem .34rem!important;
  }}
  .st-key-owner_dev_analytics button{{
    min-height:42px!important;
    font-size:.67rem!important;
    padding:.30rem .34rem!important;
  }}
}}

@media(max-width:900px){{
  .orb-nav-logo{{min-height:68px!important}}
  .orb-nav-logo img{{
    width:min(232px,100%)!important;
    max-width:232px!important;
    max-height:71px!important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    margin-bottom:-.65rem!important;
  }}
}}

@media(max-width:760px){{
  .orb-nav-logo{{min-height:60px!important}}
  .orb-nav-logo img{{
    width:min(198px,100%)!important;
    max-width:198px!important;
    max-height:61px!important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    margin-bottom:-.25rem!important;
  }}
}}


/* ============================================================
   ORBIDENSE BRAND + NAV V4 - FINAL VERTICAL BRAND
   HOME HEADER VISUALS ONLY
   ============================================================ */

/*
  AGREED BRAND LAYOUT
  Shield on top.
  ORBIDENSE directly below the shield.
  Tagline below ORBIDENSE.
  Brand is intentionally taller than the navigation controls.
*/
.orb-nav-logo{{
  min-height:158px!important;
  height:auto!important;
  display:flex!important;
  align-items:center!important;
  justify-content:flex-start!important;
  overflow:visible!important;
}}

.orb-nav-logo img{{
  width:min(264px,100%)!important;
  max-width:264px!important;
  max-height:152px!important;
  height:auto!important;
  object-fit:contain!important;
  object-position:left center!important;
  display:block!important;
  filter:drop-shadow(0 7px 20px rgba(0,0,0,.24))!important;
}}

/*
  NAVIGATION
  Keep the navigation visually subordinate to the brand.
  This changes presentation only; existing labels, keys and callbacks remain.
*/
[class*="st-key-site_nav_"] button{{
  min-height:46px!important;
  height:46px!important;
  padding:.36rem .54rem!important;
  border-radius:11px!important;
  border:1px solid rgba(92,160,190,.30)!important;
  background:linear-gradient(
    180deg,
    rgba(12,38,55,.88),
    rgba(8,29,43,.84)
  )!important;
  color:#d7e3ea!important;
  font-size:.76rem!important;
  font-weight:760!important;
  letter-spacing:-.006em!important;
  white-space:nowrap!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.035),
    0 4px 12px rgba(0,0,0,.09)!important;
  transition:
    transform .16s ease,
    color .16s ease,
    border-color .16s ease,
    background .16s ease,
    box-shadow .16s ease!important;
}}

[class*="st-key-site_nav_"] button:hover{{
  color:#f5fbff!important;
  border-color:rgba(48,228,221,.56)!important;
  background:linear-gradient(
    180deg,
    rgba(14,54,70,.95),
    rgba(8,37,51,.92)
  )!important;
  transform:translateY(-1px)!important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.05),
    0 6px 16px rgba(0,0,0,.13)!important;
}}

/* Existing active key is reused. */
.st-key-{active_key} button{{
  color:#31e6df!important;
  border-color:rgba(49,230,223,.68)!important;
  background:linear-gradient(
    180deg,
    rgba(14,67,76,.86),
    rgba(8,43,56,.90)
  )!important;
  box-shadow:
    inset 0 -3px 0 #24e3e8,
    inset 0 1px 0 rgba(255,255,255,.06),
    0 6px 16px rgba(0,0,0,.10)!important;
}}

/* Private Analytics button: visual alignment only. */
.st-key-owner_dev_analytics button{{
  min-height:46px!important;
  height:46px!important;
  padding:.36rem .50rem!important;
  border-radius:11px!important;
  border:1px solid rgba(49,230,223,.42)!important;
  background:linear-gradient(
    180deg,
    rgba(11,52,63,.88),
    rgba(7,34,47,.86)
  )!important;
  color:#31e6df!important;
  font-size:.73rem!important;
  font-weight:800!important;
}}

/*
  Center the navigation vertically against the taller brand.
  No grid/column definitions are changed.
*/
div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
  align-items:center!important;
  margin-top:-.20rem!important;
  margin-bottom:-1.45rem!important;
}}

/*
  Keep the header compact despite the taller brand.
  This does not touch the hero itself.
*/
div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo) > div{{
  align-self:center!important;
}}

/* Responsive brand proportions */
@media(max-width:1220px){{
  .orb-nav-logo{{
    min-height:142px!important;
  }}
  .orb-nav-logo img{{
    width:min(238px,100%)!important;
    max-width:238px!important;
    max-height:138px!important;
  }}
  [class*="st-key-site_nav_"] button{{
    min-height:44px!important;
    height:44px!important;
    font-size:.68rem!important;
    padding:.32rem .36rem!important;
  }}
  .st-key-owner_dev_analytics button{{
    min-height:44px!important;
    height:44px!important;
    font-size:.67rem!important;
    padding:.32rem .36rem!important;
  }}
}}

@media(max-width:900px){{
  .orb-nav-logo{{
    min-height:126px!important;
  }}
  .orb-nav-logo img{{
    width:min(212px,100%)!important;
    max-width:212px!important;
    max-height:122px!important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    margin-bottom:-.95rem!important;
  }}
}}

@media(max-width:760px){{
  .orb-nav-logo{{
    min-height:108px!important;
  }}
  .orb-nav-logo img{{
    width:min(184px,100%)!important;
    max-width:184px!important;
    max-height:104px!important;
  }}
  div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){{
    margin-bottom:-.45rem!important;
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
