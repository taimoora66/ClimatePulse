from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import math
import time
from typing import Any, Callable

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    px = None
    go = None

from src.analytics import (
    ACTIVE_WINDOW_MINUTES,
    get_v4_overview,
    get_v4_daily_visitors,
    get_v4_live_visitors,
    get_v4_device_visitors,
    get_v4_dimension_breakdown,
    get_v4_viewport_breakdown,
    get_v4_acquisition,
    get_v4_landing_pages,
    get_v4_content,
    get_v4_feature_adoption,
    get_v4_feature_daily,
    get_v4_retention,
    get_v4_performance_overview,
    get_v4_reliability_overview,
    get_v4_api_sources,
    get_journey_edges,
    get_exit_pages,
    get_session_depth_distribution,
    get_referrer_breakdown,
    get_campaign_breakdown,
    get_performance_summary,
    get_error_summary,
    get_recent_errors,
    get_data_quality_latest,
    get_privacy_summary,
    track_local_sessions_enabled,
    persistent_visitor_id_enabled,
)
from src.db import get_connection

try:
    from src.developer_analytics_gate import close_developer_analytics, logout_analytics
except Exception:  # pragma: no cover
    close_developer_analytics = None
    logout_analytics = None


LIVE_REFRESH_SECONDS = 15
LOGO_PATH = "assets/orbidense_logo_header.png"

# =============================================================================
# ORBIDENSE PRODUCT INTELLIGENCE V4.1 — VISUAL SYSTEM
# =============================================================================
V41_CSS = r"""
<style>
:root{
  --pi-bg:#03111d;
  --pi-bg2:#041623;
  --pi-panel:#071a29;
  --pi-panel2:#0a2031;
  --pi-panel3:#0b2436;
  --pi-border:rgba(77,169,219,.18);
  --pi-border-strong:rgba(70,196,238,.32);
  --pi-text:#eef8ff;
  --pi-muted:#829bad;
  --pi-dim:#61798b;
  --pi-blue:#1688ff;
  --pi-cyan:#2ee5ef;
  --pi-green:#50df8a;
  --pi-amber:#f2b84b;
  --pi-red:#ff6b6b;
  --pi-purple:#9c7bff;
}

/* Analytics owns its own shell. Hide the public-site fixed header and zoom widget. */
div[data-testid="stHorizontalBlock"]:has(.orb-nav-logo){display:none!important;}
.st-key-orbidense_zoom_controls{display:none!important;}
[data-testid="stMainBlockContainer"],.block-container{
  max-width:1920px!important;
  padding-top:.65rem!important;
  padding-left:.70rem!important;
  padding-right:.70rem!important;
  padding-bottom:1.3rem!important;
}
[data-testid="stAppViewContainer"],.stApp{background:var(--pi-bg)!important;}

.pi-shell-head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;margin:2px 0 14px;}
.pi-title{font-size:1.72rem;font-weight:950;color:var(--pi-text);line-height:1.02;letter-spacing:-.03em;margin:0;}
.pi-sub{font-size:.73rem;color:var(--pi-muted);margin-top:6px;line-height:1.45;}
.pi-kicker{font-size:.57rem;letter-spacing:.15em;font-weight:900;color:var(--pi-cyan);text-transform:uppercase;}
.pi-period{font-size:.67rem;color:#a9c2d2;border:1px solid var(--pi-border);border-radius:999px;padding:7px 10px;background:rgba(8,29,45,.72);white-space:nowrap;}
.pi-period .live{color:var(--pi-green);font-weight:850;}

.pi-card{background:linear-gradient(145deg,var(--pi-panel),var(--pi-panel2));border:1px solid var(--pi-border);border-radius:13px;padding:13px 14px;min-height:98px;box-shadow:0 14px 28px rgba(0,0,0,.11);}
.pi-card.compact{min-height:76px;padding:10px 12px;}
.pi-card.hero{border-color:var(--pi-border-strong);background:linear-gradient(145deg,#082035,#071725);}
.pi-label{font-size:.57rem;letter-spacing:.075em;text-transform:uppercase;color:#9fb4c2;font-weight:850;}
.pi-value{font-size:1.70rem;line-height:1.05;color:white;font-weight:950;margin-top:8px;letter-spacing:-.035em;}
.pi-value.sm{font-size:1.12rem;letter-spacing:-.01em;}
.pi-foot{font-size:.61rem;color:var(--pi-muted);margin-top:5px;line-height:1.35;}
.pi-good{font-size:.62rem;color:var(--pi-green);font-weight:800;margin-top:5px;}
.pi-warn{font-size:.62rem;color:var(--pi-amber);font-weight:800;margin-top:5px;}
.pi-bad{font-size:.62rem;color:var(--pi-red);font-weight:800;margin-top:5px;}
.pi-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--pi-green);margin-right:6px;box-shadow:0 0 10px rgba(80,223,138,.65);}

.pi-section{font-size:.68rem;text-transform:uppercase;letter-spacing:.085em;font-weight:900;color:#dcebf5;margin:9px 0 7px;}
.pi-section-line{height:1px;background:rgba(83,171,219,.12);margin:10px 0 12px;}
.pi-muted-note{font-size:.67rem;color:var(--pi-muted);line-height:1.5;}

.pi-side-brand{padding:4px 5px 10px;border-bottom:1px solid rgba(83,171,219,.12);margin-bottom:8px;}
.pi-side-brand .name{font-size:.78rem;color:#fff;font-weight:950;letter-spacing:.01em;}
.pi-side-brand .sub{font-size:.51rem;color:#7f97a7;letter-spacing:.11em;text-transform:uppercase;margin-top:2px;}
.pi-nav-group{font-size:.50rem;color:#688092;text-transform:uppercase;letter-spacing:.14em;font-weight:900;margin:14px 0 4px;}
.pi-status{border:1px solid rgba(80,223,138,.20);background:rgba(80,223,138,.055);border-radius:11px;padding:10px 11px;color:#bcead0;font-size:.62rem;line-height:1.4;}

/* Compact dark tables replace raw white dataframes for primary presentation. */
.pi-table-wrap{border:1px solid var(--pi-border);border-radius:11px;overflow:hidden;background:var(--pi-panel);}
.pi-table{width:100%;border-collapse:collapse;font-size:.64rem;color:#cbdce7;}
.pi-table th{padding:8px 9px;text-align:left;color:#8fa8b9;background:#081d2d;font-size:.54rem;text-transform:uppercase;letter-spacing:.055em;font-weight:850;border-bottom:1px solid var(--pi-border);}
.pi-table td{padding:8px 9px;border-bottom:1px solid rgba(88,159,196,.09);vertical-align:middle;}
.pi-table tr:last-child td{border-bottom:0;}
.pi-table td.num{text-align:right;font-variant-numeric:tabular-nums;color:#eaf7ff;}
.pi-table .pill{display:inline-block;padding:2px 6px;border-radius:999px;background:rgba(22,136,255,.10);border:1px solid rgba(22,136,255,.18);color:#98cdfa;}

.pi-feed{display:flex;flex-direction:column;gap:7px;}
.pi-feed-row{display:grid;grid-template-columns:minmax(0,1.4fr) .85fr .55fr;gap:8px;align-items:center;border-bottom:1px solid rgba(83,171,219,.08);padding:7px 2px;}
.pi-feed-row:last-child{border-bottom:0;}
.pi-feed-main{font-size:.65rem;color:#e7f4fb;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pi-feed-sub{font-size:.57rem;color:#7891a2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pi-feed-time{text-align:right;font-size:.57rem;color:#6f8797;font-variant-numeric:tabular-nums;}

.pi-feature-row{display:grid;grid-template-columns:minmax(120px,1.1fr) 2fr .42fr;gap:8px;align-items:center;margin:8px 0;}
.pi-feature-name{font-size:.61rem;color:#c7d9e5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.pi-track{height:7px;border-radius:999px;background:#0c2a3f;overflow:hidden;}
.pi-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--pi-blue),var(--pi-cyan));}
.pi-feature-value{text-align:right;font-size:.59rem;color:#9db4c4;font-variant-numeric:tabular-nums;}

.pi-privacy-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:8px;}
.pi-privacy-box{border:1px solid var(--pi-border);border-radius:11px;padding:11px;background:linear-gradient(145deg,var(--pi-panel),#061725);}
.pi-privacy-box b{display:block;color:#edf8ff;font-size:.67rem;margin-bottom:5px;}
.pi-privacy-box span{font-size:.60rem;color:#829bad;line-height:1.45;}
.pi-check{color:var(--pi-green);font-weight:900;margin-right:4px;}.pi-no{color:var(--pi-red);font-weight:900;margin-right:4px;}

/* Streamlit primitives within private analytics */
[data-testid="stRadio"] label{font-size:.67rem!important;color:#d9e8f2!important;}
[data-testid="stRadio"] div[role="radiogroup"]{gap:0!important;}
[data-testid="stRadio"] div[role="radiogroup"] label{padding:4px 7px!important;border-radius:8px!important;}
[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked){background:rgba(22,136,255,.16)!important;border:1px solid rgba(22,136,255,.22)!important;}
[data-testid="stSegmentedControl"] button{font-size:.64rem!important;min-height:34px!important;}
[data-testid="stButton"] button{border-radius:9px!important;min-height:36px!important;font-size:.66rem!important;}
[data-testid="stExpander"]{border:1px solid var(--pi-border)!important;border-radius:11px!important;background:var(--pi-panel)!important;}
.js-plotly-plot,.plot-container{border-radius:12px;overflow:hidden;}

@media(max-width:1050px){
  .pi-title{font-size:1.45rem}.pi-value{font-size:1.35rem}.pi-card{min-height:auto}.pi-privacy-grid{grid-template-columns:1fr 1fr;}
}
@media(max-width:760px){
  [data-testid="stMainBlockContainer"],.block-container{padding:.45rem!important;}
  .pi-title{font-size:1.28rem}.pi-sub{font-size:.66rem}.pi-privacy-grid{grid-template-columns:1fr;}
}
</style>
"""


# =============================================================================
# DATA + DISPLAY HELPERS
# =============================================================================
def _call(fn: Callable, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def _df(records: Any) -> pd.DataFrame:
    if records is None:
        return pd.DataFrame()
    if isinstance(records, pd.DataFrame):
        return records.copy()
    try:
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()


def _n(v: Any) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def _f(v: Any) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def _num(v: Any) -> str:
    return f"{_n(v):,}"


def _pct(v: Any, d: int = 1) -> str:
    return f"{_f(v):.{d}f}%"


def _duration(minutes: Any) -> str:
    total = max(0, int(round(_f(minutes) * 60)))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _safe(v: Any) -> str:
    return escape("—" if v is None or v == "" else str(v))


def _card(label: str, value: str, foot: str = "", *, compact: bool = False, state: str = "") -> None:
    cls = "pi-card compact" if compact else "pi-card"
    foot_cls = {"good": "pi-good", "warn": "pi-warn", "bad": "pi-bad"}.get(state, "pi-foot")
    dot = '<span class="pi-dot"></span>' if state == "good" else ""
    st.markdown(
        f'<div class="{cls}"><div class="pi-label">{_safe(label)}</div>'
        f'<div class="pi-value{" sm" if compact else ""}">{_safe(value)}</div>'
        f'<div class="{foot_cls}">{dot}{_safe(foot)}</div></div>',
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(f'<div class="pi-section">{_safe(title)}</div>', unsafe_allow_html=True)


def _empty(text: str) -> None:
    st.markdown(f'<div class="pi-card compact"><div class="pi-muted-note">{_safe(text)}</div></div>', unsafe_allow_html=True)


def _html_table(df: pd.DataFrame, columns: list[tuple[str, str]], max_rows: int = 10) -> None:
    if df.empty:
        _empty("No telemetry available for this period.")
        return
    show = df.head(max_rows)
    heads = "".join(f"<th>{_safe(label)}</th>" for _, label in columns)
    rows = []
    for _, row in show.iterrows():
        tds = []
        for key, _ in columns:
            val = row.get(key, "")
            numlike = isinstance(val, (int, float)) or (pd.notna(val) and str(val).replace(".", "", 1).isdigit())
            tds.append(f'<td class="{"num" if numlike else ""}">{_safe(val)}</td>')
        rows.append("<tr>" + "".join(tds) + "</tr>")
    st.markdown(
        '<div class="pi-table-wrap"><table class="pi-table"><thead><tr>' + heads +
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _plot_base(fig: Any, height: int = 260, legend: bool = True) -> Any:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8fa7b8", size=10),
        hoverlabel=dict(bgcolor="#0a2031", bordercolor="#27516a", font_color="#eff9ff"),
        legend=dict(orientation="h", y=1.04, x=0, font=dict(size=9)) if legend else dict(visible=False),
    )
    fig.update_xaxes(gridcolor="rgba(110,160,190,.07)", zeroline=False, linecolor="rgba(110,160,190,.10)")
    fig.update_yaxes(gridcolor="rgba(110,160,190,.07)", zeroline=False, linecolor="rgba(110,160,190,.10)")
    return fig


def _show(fig: Any) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "displayModeBar": False, "responsive": True})


def _line(df: pd.DataFrame, x: str, ys: list[str], height: int = 260) -> None:
    if df.empty or go is None or x not in df.columns:
        _empty("No time-series data available.")
        return
    fig = go.Figure()
    palette = ["#1688ff", "#2ee5ef", "#50df8a", "#9c7bff"]
    for i, y in enumerate([c for c in ys if c in df.columns]):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[y], mode="lines", name=y.replace("_", " ").title(),
            line=dict(width=2.2, color=palette[i % len(palette)]),
            fill="tozeroy" if i == 0 else None,
            fillcolor="rgba(22,136,255,.08)" if i == 0 else None,
        ))
    _show(_plot_base(fig, height, True))


def _hbar(df: pd.DataFrame, label: str, value: str, height: int = 260, color: str = "#1688ff") -> None:
    if df.empty or go is None or label not in df or value not in df:
        _empty("No ranked data available.")
        return
    d = df.copy().tail(12)
    d[value] = pd.to_numeric(d[value], errors="coerce").fillna(0)
    fig = go.Figure(go.Bar(x=d[value], y=d[label], orientation="h", marker_color=color,
                           hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>"))
    _show(_plot_base(fig, height, False))


def _donut(df: pd.DataFrame, names: str, values: str, height: int = 245) -> None:
    if df.empty or go is None or names not in df or values not in df:
        _empty("No composition data available.")
        return
    fig = go.Figure(go.Pie(
        labels=df[names], values=pd.to_numeric(df[values], errors="coerce").fillna(0), hole=.67,
        marker=dict(colors=["#1688ff", "#2ee5ef", "#50df8a", "#f2b84b", "#9c7bff", "#ff6b6b"]),
        textinfo="none", hovertemplate="<b>%{label}</b><br>%{value:,.0f} · %{percent}<extra></extra>",
    ))
    fig.add_annotation(text="Mix", x=.5, y=.5, showarrow=False, font=dict(size=12, color="#9ab2c2"))
    _show(_plot_base(fig, height, True))


def _heatmap_retention(df: pd.DataFrame, height: int = 330) -> None:
    if df.empty or go is None:
        _empty("Retention cohorts will populate as returning browser activity accumulates.")
        return
    d = df.copy().head(16).sort_values("cohort_day")
    cols = [c for c in ["d1_pct", "d7_pct", "d30_pct"] if c in d]
    if not cols:
        _empty("Retention cohort percentages are unavailable.")
        return
    z = [[_f(row[c]) for c in cols] for _, row in d.iterrows()]
    y = [str(x)[:10] for x in d["cohort_day"]]
    fig = go.Figure(go.Heatmap(
        z=z, x=[c.replace("_pct", "").upper() for c in cols], y=y,
        colorscale=[[0, "#071a29"], [.25, "#0c4c73"], [.55, "#1688ff"], [1, "#50df8a"]],
        text=[[f"{v:.1f}%" for v in row] for row in z], texttemplate="%{text}",
        colorbar=dict(title="Return %", thickness=8, len=.65),
        hovertemplate="Cohort %{y}<br>%{x}: %{z:.1f}%<extra></extra>",
    ))
    _show(_plot_base(fig, height, False))


def _sankey(edges: pd.DataFrame, height: int = 340) -> None:
    if edges.empty or go is None or not {"source", "target", "transitions"}.issubset(edges.columns):
        _empty("Journey transitions will appear after visitors move across multiple pages.")
        return
    d = edges.head(18).copy()
    nodes = list(dict.fromkeys(d["source"].astype(str).tolist() + d["target"].astype(str).tolist()))
    idx = {name: i for i, name in enumerate(nodes)}
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=nodes, pad=14, thickness=13, color="#0d3855", line=dict(color="#2c6a8b", width=.6)),
        link=dict(
            source=[idx[str(x)] for x in d["source"]],
            target=[idx[str(x)] for x in d["target"]],
            value=[max(1, _n(x)) for x in d["transitions"]],
            color="rgba(22,136,255,.22)",
        ),
    ))
    _show(_plot_base(fig, height, False))


def _feature_rows(df: pd.DataFrame, max_rows: int = 8) -> None:
    if df.empty:
        _empty("No feature adoption events available.")
        return
    d = df.head(max_rows).copy()
    maxv = max(1.0, pd.to_numeric(d.get("visitors", 0), errors="coerce").fillna(0).max())
    rows = []
    for _, r in d.iterrows():
        v = _f(r.get("visitors")); pct = 100.0 * v / maxv
        rows.append(
            f'<div class="pi-feature-row"><div class="pi-feature-name">{_safe(r.get("feature"))}</div>'
            f'<div class="pi-track"><div class="pi-fill" style="width:{pct:.1f}%"></div></div>'
            f'<div class="pi-feature-value">{_num(v)}</div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def _live_feed(df: pd.DataFrame, max_rows: int = 8) -> None:
    if df.empty:
        _empty("No visitors are active in the current heartbeat window.")
        return
    rows = []
    for _, r in df.head(max_rows).iterrows():
        device = _safe(r.get("device_category") or "Unknown")
        place = _safe(r.get("country_hint") or "Coarse location unavailable")
        page = _safe(r.get("current_page") or "Unknown")
        age = _n(r.get("seconds_ago"))
        rows.append(
            '<div class="pi-feed-row">'
            f'<div><div class="pi-feed-main">{page}</div><div class="pi-feed-sub">{place}</div></div>'
            f'<div class="pi-feed-sub">{device}</div><div class="pi-feed-time">{age}s</div></div>'
        )
    st.markdown('<div class="pi-feed">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def _db_health() -> dict[str, Any]:
    out = {"connected": False, "latency_ms": 0.0, "cache_hit_pct": 0.0, "connections": 0, "active_connections": 0, "size_mb": 0.0}
    started = time.perf_counter()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
                out["connected"] = True
                out["latency_ms"] = (time.perf_counter() - started) * 1000
                try:
                    cur.execute("SELECT COUNT(*) AS c, COUNT(*) FILTER(WHERE state='active') AS a FROM pg_stat_activity WHERE datname=current_database();")
                    row = cur.fetchone() or {}
                    out["connections"] = row.get("c", 0) if isinstance(row, dict) else row[0]
                    out["active_connections"] = row.get("a", 0) if isinstance(row, dict) else row[1]
                except Exception:
                    pass
                try:
                    cur.execute("SELECT 100.0*blks_hit/NULLIF(blks_hit+blks_read,0) AS hit FROM pg_stat_database WHERE datname=current_database();")
                    row = cur.fetchone() or {}
                    out["cache_hit_pct"] = _f(row.get("hit") if isinstance(row, dict) else row[0])
                except Exception:
                    pass
                try:
                    cur.execute("SELECT pg_database_size(current_database())/1024.0/1024.0 AS mb;")
                    row = cur.fetchone() or {}
                    out["size_mb"] = _f(row.get("mb") if isinstance(row, dict) else row[0])
                except Exception:
                    pass
    except Exception:
        pass
    return out


# =============================================================================
# SHELL
# =============================================================================
NAV = ["Overview", "Live", "Audience", "Acquisition", "Retention", "Content", "Journeys", "Features", "Performance", "Reliability", "Data & APIs", "Privacy"]


def _side_navigation() -> str:
    if st.session_state.get("pi_v41_view") not in NAV:
        st.session_state["pi_v41_view"] = "Overview"

    if st.runtime.exists():
        try:
            st.image(LOGO_PATH, width=135)
        except Exception:
            pass
    st.markdown('<div class="pi-side-brand"><div class="name">ORBIDENSE</div><div class="sub">Product Intelligence</div></div>', unsafe_allow_html=True)

    # Group labels are visual; a single radio keeps keyboard navigation stable.
    st.markdown('<div class="pi-nav-group">Command</div>', unsafe_allow_html=True)
    view = st.radio("Analytics section", NAV, key="pi_v41_view", label_visibility="collapsed")

    st.markdown('<div class="pi-nav-group">System status</div><div class="pi-status"><span class="pi-dot"></span>Telemetry online<br><span style="color:#71899a">Private owner console</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="pi-nav-group">Owner console</div>', unsafe_allow_html=True)
    if st.button("Back to site", key="pi_v41_back", width="stretch"):
        if close_developer_analytics:
            close_developer_analytics()
        st.session_state["main_navigation"] = "Home"
        st.rerun()
    if st.button("Lock analytics", key="pi_v41_lock", width="stretch"):
        if logout_analytics:
            logout_analytics()
        if close_developer_analytics:
            close_developer_analytics()
        st.session_state["main_navigation"] = "Home"
        st.rerun()
    return view


def _header(title: str, subtitle: str, days: int, overview: dict[str, Any]) -> None:
    left, right = st.columns([5.2, 1.8], vertical_alignment="center")
    with left:
        st.markdown(f'<div class="pi-kicker">ORBIDENSE / PRODUCT INTELLIGENCE</div><div class="pi-title">{_safe(title)}</div><div class="pi-sub">{_safe(subtitle)}</div>', unsafe_allow_html=True)
    with right:
        st.markdown(
            f'<div style="text-align:right"><span class="pi-period"><span class="live">● LIVE</span> &nbsp; {_num(overview.get("active_visitors"))} visitors &nbsp; · &nbsp; {days}d</span></div>',
            unsafe_allow_html=True,
        )


# =============================================================================
# SECTIONS
# =============================================================================
def _overview(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    daily = _df(_call(get_v4_daily_visitors, days, default=[]))
    live = _df(_call(get_v4_live_visitors, 60, default=[]))
    acq = _df(_call(get_v4_acquisition, days, 8, default=[]))
    features = _df(_call(get_v4_feature_adoption, days, 10, default=[]))
    pages = _df(_call(get_v4_content, days, 10, default=[]))
    dev = _df(_call(get_v4_device_visitors, days, default=[]))
    db = _db_health()
    perf = _call(get_v4_performance_overview, min(days, 30), default={}) or {}
    rel = _call(get_v4_reliability_overview, min(days, 30), default={}) or {}

    _header("Overview", "Real-time audience, product behavior and system health in one command surface.", days, ov)

    k = st.columns(6, gap="small")
    metrics = [
        ("Unique visitors", _num(ov.get("unique_visitors")), "Anonymous browsers"),
        ("Sessions", _num(ov.get("sessions")), "Visits in selected period"),
        ("Live now", _num(ov.get("active_visitors")), f'{_n(ov.get("active_sessions"))} active sessions'),
        ("Avg. session", _duration(ov.get("avg_session_minutes")), "Observed engaged time"),
        ("Pages / session", f'{_f(ov.get("pages_per_session")):.1f}', "Navigation depth"),
        ("Engagement", _pct(ov.get("engagement_pct")), "Engaged sessions"),
    ]
    for col, item in zip(k, metrics):
        with col:
            _card(*item)

    a, b, c = st.columns([1.45, .85, 1], gap="small")
    with a:
        _section("Visitors over time")
        _line(daily, "day", ["visitors", "sessions"], 270)
    with b:
        _section("Acquisition mix")
        _donut(acq, "channel", "visitors", 270)
    with c:
        _section("Top product activity")
        _feature_rows(features, 9)

    h = st.columns(6, gap="small")
    health = [
        ("System health", "Operational", "All monitored services", "good"),
        ("Database", "Healthy" if db["connected"] else "Unavailable", f'{db["latency_ms"]:.0f} ms', "good" if db["connected"] else "bad"),
        ("Cache", f'{db["cache_hit_pct"]:.1f}%', "DB cache hit", ""),
        ("API response P95", f'{_f(perf.get("p95_ms")):.0f} ms', "Observed telemetry", ""),
        ("Error rate", _pct(rel.get("error_rate_pct"), 2), "Failed performance samples", "warn" if _f(rel.get("error_rate_pct")) > 2 else "good"),
        ("Failed requests", _num(rel.get("failed_requests")), "Selected period", ""),
    ]
    for col, (lab, val, foot, state) in zip(h, health):
        with col:
            _card(lab, val, foot, compact=True, state=state)

    st.markdown('<div class="pi-section-line"></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1.15, .95, 1.08, 1.05, .82], gap="small")
    with c1:
        _section("Audience pulse")
        m = st.columns(3, gap="small")
        for col, item in zip(m, [("New", _num(ov.get("new_visitors"))), ("Returning", _num(ov.get("returning_visitors"))), ("Engaged", _pct(ov.get("engagement_pct")))]):
            with col:
                _card(item[0], item[1], compact=True)
        _line(daily, "day", ["visitors"], 185)
    with c2:
        _section("Devices")
        _donut(dev, "label", "visitors", 205)
    with c3:
        _section("Content leaders")
        if not pages.empty:
            _hbar(pages.sort_values("views"), "page_name", "views", 245)
        else:
            _empty("No page telemetry available.")
    with c4:
        _section("Live activity")
        _live_feed(live, 8)
    with c5:
        _section("Infrastructure")
        _card("DB latency", f'{db["latency_ms"]:.0f} ms', compact=True)
        _card("Cache hit", f'{db["cache_hit_pct"]:.1f}%', compact=True)
        _card("DB size", f'{db["size_mb"]:.1f} MB', compact=True)


@st.fragment(run_every=LIVE_REFRESH_SECONDS)
def _live(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    live = _df(_call(get_v4_live_visitors, 100, default=[]))
    pages = _df(_call(get_v4_content, 1, 10, default=[]))
    dev = _df(_call(get_v4_device_visitors, 1, default=[]))
    db = _db_health()
    perf = _call(get_v4_performance_overview, 1, default={}) or {}
    rel = _call(get_v4_reliability_overview, 1, default={}) or {}
    _header("Live Mission Control", f"Heartbeat window: {ACTIVE_WINDOW_MINUTES} minutes · refreshes every {LIVE_REFRESH_SECONDS}s.", days, ov)

    k = st.columns(5, gap="small")
    for col, item in zip(k, [
        ("Live visitors", _num(ov.get("active_visitors")), "Distinct visitor IDs", "good"),
        ("Active sessions", _num(ov.get("active_sessions")), "Open / recent sessions", ""),
        ("DB latency", f'{db["latency_ms"]:.0f} ms', "Live probe", "good" if db["connected"] else "bad"),
        ("P95 response", f'{_f(perf.get("p95_ms")):.0f} ms', "Last 24h", ""),
        ("Failed requests", _num(rel.get("failed_requests")), "Last 24h", "warn" if _n(rel.get("failed_requests")) else "good"),
    ]):
        with col:
            _card(item[0], item[1], item[2], state=item[3])

    left, mid, right = st.columns([1.4, .85, .8], gap="small")
    with left:
        _section("Global activity")
        mappable = pd.DataFrame()
        if not live.empty and "country_hint" in live:
            tmp = live.dropna(subset=["country_hint"]).copy()
            if not tmp.empty and tmp["country_hint"].astype(str).str.len().eq(3).all():
                mappable = tmp.groupby("country_hint", as_index=False).agg(visitors=("visitor_id", "nunique"))
        if not mappable.empty and go is not None:
            fig = go.Figure(go.Choropleth(
                locations=mappable["country_hint"], z=mappable["visitors"], locationmode="ISO-3",
                colorscale=[[0, "#0a2031"], [.5, "#1688ff"], [1, "#2ee5ef"]],
                marker_line_color="rgba(255,255,255,.08)", marker_line_width=.25,
                colorbar=dict(title="Visitors", thickness=8, len=.55),
            ))
            fig.update_geos(showframe=False, showcoastlines=False, bgcolor="rgba(0,0,0,0)", landcolor="#071827")
            _show(_plot_base(fig, 330, False))
        else:
            # Do not fake geography. Visualize current activity by available coarse country hint instead.
            country = live.groupby("country_hint", dropna=False).agg(visitors=("visitor_id", "nunique")).reset_index() if not live.empty and "country_hint" in live else pd.DataFrame()
            if not country.empty:
                country["country_hint"] = country["country_hint"].fillna("Unknown")
                _hbar(country.sort_values("visitors"), "country_hint", "visitors", 330, "#2ee5ef")
            else:
                _empty("No coarse geography is available for active visitors. Exact location is intentionally not inferred.")
    with mid:
        _section("Live activity feed")
        _live_feed(live, 12)
    with right:
        _section("Top pages right now")
        if not pages.empty:
            _hbar(pages.sort_values("unique_visitors"), "page_name", "unique_visitors", 235)
        else:
            _empty("No page activity in the current period.")
        _section("Live device mix")
        _donut(dev, "label", "visitors", 185)



def _audience(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    daily = _df(_call(get_v4_daily_visitors, days, default=[]))
    dev = _df(_call(get_v4_device_visitors, days, default=[]))
    browsers = _df(_call(get_v4_dimension_breakdown, "browser_family", days, 10, default=[]))
    osdf = _df(_call(get_v4_dimension_breakdown, "os_family", days, 10, default=[]))
    countries = _df(_call(get_v4_dimension_breakdown, "country_hint", days, 10, default=[]))
    languages = _df(_call(get_v4_dimension_breakdown, "language", days, 10, default=[]))
    viewports = _df(_call(get_v4_viewport_breakdown, days, default=[]))
    _header("Audience", "Unique visitors, returning behavior, device context and coarse geographic signals.", days, ov)

    k = st.columns(5, gap="small")
    for col, item in zip(k, [
        ("Unique visitors", _num(ov.get("unique_visitors")), "Browser-scoped IDs"),
        ("New visitors", _num(ov.get("new_visitors")), "First seen in period"),
        ("Returning", _num(ov.get("returning_visitors")), "Seen before period"),
        ("Engagement", _pct(ov.get("engagement_pct")), "Engaged sessions"),
        ("Avg. session", _duration(ov.get("avg_session_minutes")), "Observed duration"),
    ]):
        with col:
            _card(*item)

    a, b, c = st.columns([1.35, .8, .85], gap="small")
    with a:
        _section("Audience growth")
        _line(daily, "day", ["visitors", "sessions"], 310)
    with b:
        _section("Device category")
        _donut(dev, "label", "visitors", 310)
    with c:
        _section("Viewport families")
        _hbar(viewports.sort_values("visitors") if not viewports.empty else viewports, "label", "visitors", 310, "#9c7bff")

    a, b, c, d = st.columns(4, gap="small")
    for col, title, frame, color in [
        (a, "Browsers", browsers, "#1688ff"),
        (b, "Operating systems", osdf, "#2ee5ef"),
        (c, "Countries / regions", countries, "#50df8a"),
        (d, "Languages", languages, "#f2b84b"),
    ]:
        with col:
            _section(title)
            _hbar(frame.sort_values("visitors") if not frame.empty else frame, "label", "visitors", 275, color)



def _acquisition(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    acq = _df(_call(get_v4_acquisition, days, 12, default=[]))
    landing = _df(_call(get_v4_landing_pages, days, 15, default=[]))
    refs = _df(_call(get_referrer_breakdown, 20, default=[]))
    campaigns = _df(_call(get_campaign_breakdown, 25, default=[]))
    _header("Acquisition", "How visitors discover ORBIDENSE and where their sessions begin.", days, ov)

    k = st.columns(4, gap="small")
    direct = _n(acq.loc[acq.get("channel", pd.Series(dtype=str)).eq("Direct"), "visitors"].sum()) if not acq.empty else 0
    organic = _n(acq.loc[acq.get("channel", pd.Series(dtype=str)).eq("Organic Search"), "visitors"].sum()) if not acq.empty else 0
    referral = _n(acq.loc[acq.get("channel", pd.Series(dtype=str)).eq("Referral"), "visitors"].sum()) if not acq.empty else 0
    social = _n(acq.loc[acq.get("channel", pd.Series(dtype=str)).eq("Social"), "visitors"].sum()) if not acq.empty else 0
    for col, item in zip(k, [("Direct", _num(direct), "Visitors"), ("Organic search", _num(organic), "Visitors"), ("Referral", _num(referral), "Visitors"), ("Social", _num(social), "Visitors")]):
        with col:
            _card(*item)

    a, b = st.columns([.85, 1.15], gap="small")
    with a:
        _section("Channel mix")
        _donut(acq, "channel", "visitors", 330)
    with b:
        _section("Landing pages")
        _hbar(landing.sort_values("sessions") if not landing.empty else landing, "page", "sessions", 330)

    a, b = st.columns(2, gap="small")
    with a:
        _section("Referring domains")
        if not refs.empty and "label" in refs and "sessions" in refs:
            _hbar(refs.sort_values("sessions"), "label", "sessions", 300, "#2ee5ef")
        else:
            _empty("No referral traffic recorded.")
    with b:
        _section("Campaign / UTM detail")
        cols = [(c, c.replace("_", " ").title()) for c in ["source", "medium", "campaign", "sessions", "visitors"] if c in campaigns]
        _html_table(campaigns, cols, 12) if cols else _empty("No campaign parameters recorded.")



def _retention(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    ret = _df(_call(get_v4_retention, max(days, 45), default=[]))
    _header("Retention", "Anonymous browser return behavior with D1, D7 and D30 cohorts.", days, ov)

    k = st.columns(4, gap="small")
    latest_d1 = _f(ret.iloc[0].get("d1_pct")) if not ret.empty else 0
    latest_d7 = _f(ret.iloc[0].get("d7_pct")) if not ret.empty else 0
    latest_d30 = _f(ret.iloc[0].get("d30_pct")) if not ret.empty else 0
    for col, item in zip(k, [
        ("Returning visitors", _num(ov.get("returning_visitors")), "Browser-scoped"),
        ("Latest D1", _pct(latest_d1), "Cohort return"),
        ("Latest D7", _pct(latest_d7), "Cohort return"),
        ("Latest D30", _pct(latest_d30), "Cohort return"),
    ]):
        with col:
            _card(*item)

    a, b = st.columns([1.55, .75], gap="small")
    with a:
        _section("Retention cohort heatmap")
        _heatmap_retention(ret, 355)
    with b:
        _section("Identity model")
        _card("Persistent visitor ID", "Active" if persistent_visitor_id_enabled() else "Session fallback", "First-party anonymous browser identifier", state="good" if persistent_visitor_id_enabled() else "warn")
        _card("Identity scope", "Browser / device", "No cross-device person matching", compact=True)
        st.markdown('<div class="pi-muted-note" style="margin-top:10px">A phone and laptop are intentionally treated as separate anonymous visitors unless an authenticated identity exists. Historical sessions created before persistent IDs cannot produce meaningful return cohorts.</div>', unsafe_allow_html=True)



def _content(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    pages = _df(_call(get_v4_content, days, 40, default=[]))
    exits = _df(_call(get_exit_pages, days, 15, default=[]))
    _header("Content", "Page reach, unique visitors, entrances, exits and dwell time.", days, ov)

    views = _n(pd.to_numeric(pages.get("views", pd.Series(dtype=float)), errors="coerce").sum()) if not pages.empty else 0
    avg_dwell = _f(pd.to_numeric(pages.get("avg_dwell_seconds", pd.Series(dtype=float)), errors="coerce").mean()) if not pages.empty else 0
    entrances = _n(pd.to_numeric(pages.get("entrances", pd.Series(dtype=float)), errors="coerce").sum()) if not pages.empty else 0
    exits_total = _n(pd.to_numeric(pages.get("exits", pd.Series(dtype=float)), errors="coerce").sum()) if not pages.empty else 0
    k = st.columns(5, gap="small")
    for col, item in zip(k, [
        ("Page views", _num(views), "Selected period"),
        ("Unique visitors", _num(ov.get("unique_visitors")), "Audience reach"),
        ("Avg dwell", f"{avg_dwell:.0f}s", "Inter-page observed time"),
        ("Entrances", _num(entrances), "First page in session"),
        ("Exits", _num(exits_total), "Last page in session"),
    ]):
        with col:
            _card(*item)

    a, b = st.columns([1.25, .85], gap="small")
    with a:
        _section("Most visited pages")
        _hbar(pages.sort_values("views") if not pages.empty else pages, "page_name", "views", 330)
    with b:
        _section("Exit pages")
        _hbar(exits.sort_values("sessions") if not exits.empty else exits, "label", "sessions", 330, "#f2b84b")

    _section("Content performance detail")
    if not pages.empty:
        p = pages.copy()
        if "views" in p and "exits" in p:
            p["exit_pct"] = (100 * pd.to_numeric(p["exits"], errors="coerce").fillna(0) / pd.to_numeric(p["views"], errors="coerce").replace(0, pd.NA)).fillna(0).round(1)
        cols = [(c, label) for c, label in [
            ("page_name", "Page"), ("views", "Views"), ("unique_visitors", "Visitors"), ("entrances", "Entrances"), ("exits", "Exits"), ("exit_pct", "Exit %"), ("avg_dwell_seconds", "Avg dwell s")
        ] if c in p]
        _html_table(p, cols, 18)
    else:
        _empty("No content telemetry available.")



def _journeys(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    edges = _df(_call(get_journey_edges, days, 40, default=[]))
    depth = _df(_call(get_session_depth_distribution, days, default=[]))
    exits = _df(_call(get_exit_pages, days, 12, default=[]))
    _header("Journeys", "Behavioral flow, session depth and navigation drop-off.", days, ov)

    total_transitions = _n(pd.to_numeric(edges.get("transitions", pd.Series(dtype=float)), errors="coerce").sum()) if not edges.empty else 0
    deep_sessions = _n(depth.loc[depth.get("label", pd.Series(dtype=str)).eq("7+ pages"), "sessions"].sum()) if not depth.empty else 0
    k = st.columns(4, gap="small")
    for col, item in zip(k, [
        ("Transitions", _num(total_transitions), "Observed page-to-page moves"),
        ("Pages / session", f'{_f(ov.get("pages_per_session")):.1f}', "Average depth"),
        ("Deep sessions", _num(deep_sessions), "7+ pages"),
        ("Engagement", _pct(ov.get("engagement_pct")), "Engaged sessions"),
    ]):
        with col:
            _card(*item)

    _section("Top journey flow")
    _sankey(edges, 370)
    a, b = st.columns(2, gap="small")
    with a:
        _section("Session depth")
        _hbar(depth.sort_values("sessions") if not depth.empty else depth, "label", "sessions", 280, "#9c7bff")
    with b:
        _section("Top exit pages")
        _hbar(exits.sort_values("sessions") if not exits.empty else exits, "label", "sessions", 280, "#f2b84b")



def _features(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    adoption = _df(_call(get_v4_feature_adoption, days, 30, default=[]))
    daily = _df(_call(get_v4_feature_daily, days, 8, default=[]))
    _header("Features", "Which product capabilities visitors actually use and return to.", days, ov)

    users = _n(pd.to_numeric(adoption.get("visitors", pd.Series(dtype=float)), errors="coerce").sum()) if not adoption.empty else 0
    events = _n(pd.to_numeric(adoption.get("events", pd.Series(dtype=float)), errors="coerce").sum()) if not adoption.empty else 0
    top_feature = str(adoption.iloc[0].get("feature", "—")) if not adoption.empty else "—"
    top_adoption = _pct(adoption.iloc[0].get("adoption_pct", 0)) if not adoption.empty else "0.0%"
    k = st.columns(4, gap="small")
    for col, item in zip(k, [("Feature users", _num(users), "Sum across features"), ("Feature events", _num(events), "Recorded interactions"), ("Top feature", top_feature, "By unique visitors"), ("Top adoption", top_adoption, "Of period visitors")]):
        with col:
            _card(*item)

    a, b = st.columns([.9, 1.1], gap="small")
    with a:
        _section("Feature adoption")
        _feature_rows(adoption, 14)
    with b:
        _section("Adoption over time")
        if not daily.empty and go is not None and {"day", "feature", "visitors"}.issubset(daily.columns):
            fig = go.Figure()
            palette = ["#1688ff", "#2ee5ef", "#50df8a", "#f2b84b", "#9c7bff", "#ff6b6b", "#5db4ff", "#61e8b4"]
            for i, (name, grp) in enumerate(daily.groupby("feature")):
                fig.add_trace(go.Scatter(x=grp["day"], y=grp["visitors"], mode="lines", name=str(name), line=dict(width=2, color=palette[i % len(palette)])))
            _show(_plot_base(fig, 340, True))
        else:
            _empty("Feature trend data will appear as events accumulate.")
    _section("Feature intelligence detail")
    cols = [(c, label) for c, label in [("feature", "Feature"), ("visitors", "Visitors"), ("events", "Events"), ("adoption_pct", "Adoption %")] if c in adoption]
    _html_table(adoption, cols, 20) if cols else _empty("No feature events available.")



def _performance(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    perf = _call(get_v4_performance_overview, days, default={}) or {}
    ops = _df(_call(get_performance_summary, days, 35, default=[]))
    db = _db_health()
    _header("Performance", "Application, database and external-operation latency from recorded telemetry.", days, ov)

    k = st.columns(6, gap="small")
    for col, item in zip(k, [
        ("DB latency", f'{db["latency_ms"]:.0f} ms', "Live probe"),
        ("Avg response", f'{_f(perf.get("avg_ms")):.0f} ms', "All samples"),
        ("P50", f'{_f(perf.get("p50_ms")):.0f} ms', "Median"),
        ("P95", f'{_f(perf.get("p95_ms")):.0f} ms', "Tail latency"),
        ("P99", f'{_f(perf.get("p99_ms")):.0f} ms', "Extreme tail"),
        ("Success", _pct(perf.get("success_pct"), 2), "Recorded operations"),
    ]):
        with col:
            _card(*item)

    a, b = st.columns([1.15, .85], gap="small")
    with a:
        _section("Slowest operations — P95")
        if not ops.empty:
            d = ops.sort_values("p95_ms").tail(15)
            _hbar(d, "operation", "p95_ms", 390, "#f2b84b")
        else:
            _empty("No performance samples available.")
    with b:
        _section("Latency distribution by operation")
        if not ops.empty and go is not None:
            d = ops.head(24).copy()
            fig = go.Figure(go.Scatter(
                x=pd.to_numeric(d["p95_ms"], errors="coerce"),
                y=pd.to_numeric(d["success_pct"], errors="coerce"),
                mode="markers",
                marker=dict(size=(pd.to_numeric(d["samples"], errors="coerce").fillna(1).clip(lower=1) ** .45) * 6, color=pd.to_numeric(d["avg_ms"], errors="coerce"), colorscale="Turbo", showscale=True, colorbar=dict(title="Avg ms", thickness=8)),
                text=d["operation"],
                hovertemplate="<b>%{text}</b><br>P95 %{x:.0f}ms<br>Success %{y:.1f}%<extra></extra>",
            ))
            fig.update_xaxes(title="P95 latency (ms)")
            fig.update_yaxes(title="Success %", range=[max(0, _f(d["success_pct"].min()) - 5), 101])
            _show(_plot_base(fig, 390, False))
        else:
            _empty("No operation-level performance samples available.")



def _reliability(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    rel = _call(get_v4_reliability_overview, days, default={}) or {}
    groups = _df(_call(get_error_summary, days, 30, default=[]))
    recent = _df(_call(get_recent_errors, 80, default=[]))
    _header("Reliability", "Failures, error groups and operational resilience.", days, ov)

    k = st.columns(5, gap="small")
    for col, item in zip(k, [
        ("Error rate", _pct(rel.get("error_rate_pct"), 2), "Failed performance samples"),
        ("Failed requests", _num(rel.get("failed_requests")), "Recorded failures"),
        ("Recorded errors", _num(rel.get("errors")), "Application error events"),
        ("Error groups", _num(rel.get("error_groups")), "Distinct error hashes"),
        ("Reliability", _pct(max(0, 100 - _f(rel.get("error_rate_pct"))), 2), "Observed success proxy"),
    ]):
        with col:
            _card(*item)

    a, b = st.columns([1, 1.25], gap="small")
    with a:
        _section("Errors by group")
        if not groups.empty:
            g = groups.copy()
            g["group"] = g["component"].astype(str) + " · " + g["error_type"].astype(str)
            _hbar(g.sort_values("occurrences"), "group", "occurrences", 370, "#ff6b6b")
        else:
            _empty("No errors recorded in the selected period.")
    with b:
        _section("Recent redacted errors")
        cols = [(c, label) for c, label in [("recorded_at", "Time"), ("page_name", "Page"), ("component", "Component"), ("operation", "Operation"), ("severity", "Severity"), ("error_type", "Type")] if c in recent]
        _html_table(recent, cols, 14) if cols else _empty("No recent error events.")



def _data_apis(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    api = _df(_call(get_v4_api_sources, days, 40, default=[]))
    quality = _df(_call(get_data_quality_latest, 100, default=[]))
    _header("Data & APIs", "External data services, request volume, latency, success and latest quality checks.", days, ov)

    total = _n(pd.to_numeric(api.get("requests", pd.Series(dtype=float)), errors="coerce").sum()) if not api.empty else 0
    weighted_success = 0.0
    if not api.empty and "requests" in api and "success_pct" in api:
        req = pd.to_numeric(api["requests"], errors="coerce").fillna(0)
        suc = pd.to_numeric(api["success_pct"], errors="coerce").fillna(0)
        weighted_success = float((req * suc).sum() / req.sum()) if req.sum() else 0.0
    slowest = str(api.sort_values("p95_ms", ascending=False).iloc[0].get("source", "—")) if not api.empty and "p95_ms" in api else "—"
    quality_ok = _n((quality.get("status", pd.Series(dtype=str)).astype(str).str.lower() == "ok").sum()) if not quality.empty else 0
    k = st.columns(4, gap="small")
    for col, item in zip(k, [("API requests", _num(total), "Selected period"), ("Weighted success", _pct(weighted_success), "Across data services"), ("Slowest source", slowest, "By P95 latency"), ("Quality checks OK", _num(quality_ok), "Latest checks")]):
        with col:
            _card(*item)

    a, b = st.columns([1.15, .85], gap="small")
    with a:
        _section("Service volume & latency")
        if not api.empty and go is not None:
            d = api.copy()
            fig = go.Figure(go.Scatter(
                x=pd.to_numeric(d["requests"], errors="coerce"),
                y=pd.to_numeric(d["p95_ms"], errors="coerce"),
                mode="markers+text",
                text=d["source"], textposition="top center", textfont=dict(size=9, color="#9cb3c2"),
                marker=dict(size=(pd.to_numeric(d["avg_ms"], errors="coerce").fillna(1).clip(lower=1) ** .3) * 5, color=pd.to_numeric(d["success_pct"], errors="coerce"), colorscale=[[0, "#ff6b6b"], [.7, "#f2b84b"], [1, "#50df8a"]], cmin=0, cmax=100, colorbar=dict(title="Success %", thickness=8)),
                hovertemplate="<b>%{text}</b><br>Requests %{x:,.0f}<br>P95 %{y:.0f}ms<extra></extra>",
            ))
            fig.update_xaxes(title="Requests")
            fig.update_yaxes(title="P95 latency (ms)")
            _show(_plot_base(fig, 370, False))
        else:
            _empty("No data-service telemetry available.")
    with b:
        _section("Source health")
        cols = [(c, label) for c, label in [("source", "Source"), ("requests", "Requests"), ("success_pct", "Success %"), ("avg_ms", "Avg ms"), ("p95_ms", "P95 ms")] if c in api]
        _html_table(api, cols, 14) if cols else _empty("No API source metrics.")

    _section("Latest data-quality checks")
    cols = [(c, label) for c, label in [("source_name", "Source"), ("check_name", "Check"), ("status", "Status"), ("affected_records", "Affected"), ("freshness_seconds", "Freshness s"), ("recorded_at", "Recorded") ] if c in quality]
    _html_table(quality, cols, 18) if cols else _empty("No data-quality checks recorded.")



def _privacy(days: int) -> None:
    ov = _call(get_v4_overview, days, default={}) or {}
    p = _call(get_privacy_summary, default={}) or {}
    _header("Privacy & Governance", "First-party telemetry with explicit data minimization and owner-traffic separation.", days, ov)

    k = st.columns(5, gap="small")
    for col, item in zip(k, [
        ("Tracked sessions", _num(p.get("sessions")), "All-time telemetry"),
        ("DNT sessions", _num(p.get("dnt_sessions")), "Do Not Track observed"),
        ("GPC sessions", _num(p.get("gpc_sessions")), "Global Privacy Control"),
        ("Persistent IDs", _num(p.get("persistent_sessions")), "Anonymous browser IDs"),
        ("Local tracking", "Enabled" if track_local_sessions_enabled() else "Excluded", "Development traffic"),
    ]):
        with col:
            _card(*item)

    st.markdown(
        '''<div class="pi-privacy-grid">
        <div class="pi-privacy-box"><b>Identity</b><span><span class="pi-check">✓</span>Random first-party anonymous visitor ID<br><span class="pi-check">✓</span>Browser/device scoped<br><span class="pi-no">×</span>No cross-device person matching</span></div>
        <div class="pi-privacy-box"><b>Audience context</b><span><span class="pi-check">✓</span>Device category, browser, OS<br><span class="pi-check">✓</span>Language/timezone<br><span class="pi-check">✓</span>Coarse infrastructure country hint only</span></div>
        <div class="pi-privacy-box"><b>Never stored</b><span><span class="pi-no">×</span>Names or email addresses<br><span class="pi-no">×</span>Raw IP addresses<br><span class="pi-no">×</span>Exact GPS coordinates</span></div>
        <div class="pi-privacy-box"><b>Product telemetry</b><span><span class="pi-check">✓</span>Page views and feature events<br><span class="pi-check">✓</span>Referrer / UTM context<br><span class="pi-check">✓</span>Performance and reliability signals</span></div>
        <div class="pi-privacy-box"><b>AI boundary</b><span><span class="pi-check">✓</span>Request category / timing may be measured<br><span class="pi-no">×</span>No raw prompts<br><span class="pi-no">×</span>No conversation contents</span></div>
        <div class="pi-privacy-box"><b>Owner traffic</b><span><span class="pi-check">✓</span>Developer analytics sessions excluded from public audience counts<br><span class="pi-check">✓</span>Analytics remains private behind owner authentication</span></div>
        </div>''',
        unsafe_allow_html=True,
    )


SECTIONS: dict[str, Callable[[int], None]] = {
    "Overview": _overview,
    "Live": _live,
    "Audience": _audience,
    "Acquisition": _acquisition,
    "Retention": _retention,
    "Content": _content,
    "Journeys": _journeys,
    "Features": _features,
    "Performance": _performance,
    "Reliability": _reliability,
    "Data & APIs": _data_apis,
    "Privacy": _privacy,
}


def render_analytics_dashboard_v4() -> None:
    st.markdown(V41_CSS, unsafe_allow_html=True)

    # Persistent period selector across all sections.
    if "pi_v41_period" not in st.session_state:
        st.session_state["pi_v41_period"] = "30d"

    side, main = st.columns([.155, .845], gap="small", vertical_alignment="top")
    with side:
        view = _side_navigation()
    with main:
        tool_left, tool_right = st.columns([4, 2], vertical_alignment="center")
        with tool_left:
            st.markdown('<div class="pi-muted-note">Private analytics · first-party telemetry · owner access only</div>', unsafe_allow_html=True)
        with tool_right:
            period = st.segmented_control("Analysis window", ["24h", "7d", "30d", "90d"], key="pi_v41_period", label_visibility="collapsed")
        days = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}.get(period or "30d", 30)
        renderer = SECTIONS.get(view, _overview)
        renderer(days)
        st.markdown(f'<div class="pi-muted-note" style="margin-top:14px">Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} · live refresh {LIVE_REFRESH_SECONDS}s where applicable</div>', unsafe_allow_html=True)


def render_analytics_dashboard() -> None:
    render_analytics_dashboard_v4()
