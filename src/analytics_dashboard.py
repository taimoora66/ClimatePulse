from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Callable

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:
    px = None

from src.analytics import (
    get_analytics_summary,
    get_daily_traffic,
    get_popular_pages,
    get_top_events,
    get_device_breakdown,
    get_browser_breakdown,
    get_os_breakdown,
    get_language_breakdown,
    get_timezone_breakdown,
    get_country_hint_breakdown,
    get_theme_breakdown,
    get_entry_pages,
    get_referrer_breakdown,
    get_campaign_breakdown,
    get_hourly_activity,
    get_recent_events,
    get_search_destinations,
    get_live_sessions,
    get_journey_edges,
    get_exit_pages,
    get_session_depth_distribution,
    get_feature_usage,
    get_performance_summary,
    get_error_summary,
    get_recent_errors,
    get_ai_usage_summary,
    get_ai_category_breakdown,
    get_data_quality_latest,
    get_privacy_summary,
    track_local_sessions_enabled,
)
from src.db import get_connection

try:
    from src.developer_analytics_gate import (
        close_developer_analytics,
        exit_developer_mode,
        logout_analytics,
    )
except Exception:
    close_developer_analytics = None
    exit_developer_mode = None
    logout_analytics = None

LIVE_REFRESH_SECONDS = 15


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


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _fmt_int(value: Any) -> str:
    return f"{_int(value):,}"


def _fmt_float(value: Any, digits: int = 2) -> str:
    return f"{_float(value):,.{digits}f}"


def _fmt_pct(value: Any, digits: int = 1) -> str:
    return f"{_float(value):.{digits}f}%"


def _clean_display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            sample = out[col].dropna().head(200)
            kinds = {type(v) for v in sample}
            if len(kinds) > 1 or any(t in kinds for t in (dict, list, tuple, set)):
                out[col] = out[col].map(lambda v: "" if v is None else str(v)).astype("string")
    return out


def _table(df: pd.DataFrame, height: int | None = None) -> None:
    if df.empty:
        st.caption("No data available for the selected period.")
        return
    kwargs = {"width": "stretch", "hide_index": True}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(_clean_display_df(df), **kwargs)


def _bar(df: pd.DataFrame, x: str, y: str, title: str = "", height: int = 360) -> None:
    if df.empty:
        st.caption("No data available.")
        return
    if px is None:
        _table(df)
        return
    fig = px.bar(df, x=x, y=y, orientation="h", title=title)
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=46 if title else 20, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def _line(df: pd.DataFrame, x: str, ys: list[str], title: str = "", height: int = 370) -> None:
    if df.empty:
        st.caption("No data available.")
        return
    available = [c for c in ys if c in df.columns]
    if not available:
        _table(df)
        return
    if px is None:
        _table(df)
        return
    long_df = df.melt(id_vars=[x], value_vars=available, var_name="metric", value_name="value")
    fig = px.line(long_df, x=x, y="value", color="metric", markers=True, title=title)
    fig.update_traces(line=dict(width=3))
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=46 if title else 20, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})


def _section(title: str, caption: str | None = None) -> None:
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)


def _db_health() -> dict[str, Any]:
    result = {
        "connected": False,
        "latency_ms": None,
        "connections": None,
        "active_connections": None,
        "size_mb": None,
        "cache_hit_pct": None,
    }
    started = time.perf_counter()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
                result["connected"] = True
                result["latency_ms"] = (time.perf_counter() - started) * 1000.0

                try:
                    cur.execute("""
                        SELECT COUNT(*) AS connections,
                               COUNT(*) FILTER (WHERE state = 'active') AS active_connections
                        FROM pg_stat_activity
                        WHERE datname = current_database();
                    """)
                    row = cur.fetchone() or {}
                    if isinstance(row, dict):
                        result["connections"] = row.get("connections")
                        result["active_connections"] = row.get("active_connections")
                    else:
                        result["connections"] = row[0] if row else None
                        result["active_connections"] = row[1] if len(row) > 1 else None
                except Exception:
                    pass

                try:
                    cur.execute("SELECT pg_database_size(current_database()) / 1024.0 / 1024.0 AS size_mb;")
                    row = cur.fetchone() or {}
                    result["size_mb"] = row.get("size_mb") if isinstance(row, dict) else (row[0] if row else None)
                except Exception:
                    pass

                try:
                    cur.execute("""
                        SELECT CASE
                                 WHEN SUM(blks_hit + blks_read) = 0 THEN NULL
                                 ELSE 100.0 * SUM(blks_hit)::float / SUM(blks_hit + blks_read)
                               END AS cache_hit_pct
                        FROM pg_stat_database
                        WHERE datname = current_database();
                    """)
                    row = cur.fetchone() or {}
                    result["cache_hit_pct"] = row.get("cache_hit_pct") if isinstance(row, dict) else (row[0] if row else None)
                except Exception:
                    pass
    except Exception:
        pass
    return result


def _render_header() -> None:
    left, right = st.columns([4.4, 1.6], vertical_alignment="center")
    with left:
        st.markdown("# Developer Analytics")
        st.caption("Private ORBIDENSE product intelligence • live audience • performance • reliability • privacy-safe first-party telemetry")
    with right:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Back to site", width="stretch", key="analytics_back_to_site_v3"):
                if close_developer_analytics:
                    close_developer_analytics()
                st.session_state["main_navigation"] = "Home"
                st.rerun()
        with c2:
            if st.button("Lock", width="stretch", key="analytics_lock_v3"):
                if logout_analytics:
                    logout_analytics()
                if close_developer_analytics:
                    close_developer_analytics()
                st.session_state["main_navigation"] = "Home"
                st.rerun()

    with st.expander("Developer access & privacy", expanded=False):
        a, b, c = st.columns(3)
        with a:
            st.caption("Owner entry")
            st.code("?owner=1")
        with b:
            st.caption("Local analytics")
            st.write("Enabled" if track_local_sessions_enabled() else "Excluded")
        with c:
            if st.button("Exit developer mode", width="stretch", key="analytics_exit_dev_v3"):
                if exit_developer_mode:
                    exit_developer_mode()
                st.session_state["main_navigation"] = "Home"
                st.rerun()


@st.fragment(run_every=LIVE_REFRESH_SECONDS)
def _render_live_viewers() -> None:
    summary = _call(get_analytics_summary, default={}) or {}
    live = _df(_call(get_live_sessions, 50, default=[]))
    now_utc = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

    _section("Live viewers", f"Automatically refreshes every {LIVE_REFRESH_SECONDS}s • last refresh {now_utc}")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Active now", _fmt_int(summary.get("active_now")))
    with k2:
        st.metric("Live sessions listed", _fmt_int(len(live)))
    with k3:
        active_pages = live["current_page"].nunique() if "current_page" in live.columns and not live.empty else 0
        st.metric("Pages active", _fmt_int(active_pages))
    with k4:
        countries = live["country_hint"].nunique() if "country_hint" in live.columns and not live.empty else 0
        st.metric("Country hints", _fmt_int(countries))

    if live.empty:
        st.info("No sessions are currently inside the active window.")
        return

    preferred = [
        "current_page", "entry_page", "last_seen", "pageviews", "events",
        "device_category", "browser_family", "os_family", "language",
        "timezone", "country_hint",
    ]
    cols = [c for c in preferred if c in live.columns]
    view = live[cols].copy()
    if "last_seen" in view.columns:
        view["last_seen"] = view["last_seen"].astype("string")
    _table(view, height=330)


def _overview(days: int) -> None:
    summary = _call(get_analytics_summary, default={}) or {}
    db = _db_health()
    _section("Executive overview", "Product reach, engagement and infrastructure health.")

    cards = st.columns(8)
    metrics = [
        ("Active now", _fmt_int(summary.get("active_now"))),
        ("Visitors today", _fmt_int(summary.get("visitors_today"))),
        (f"Visitors {days}d", _fmt_int(summary.get("visitors_7d") if days <= 7 else summary.get("visitors_30d"))),
        ("Total sessions", _fmt_int(summary.get("total_sessions"))),
        ("Total pageviews", _fmt_int(summary.get("total_pageviews"))),
        ("Pages / session", _fmt_float(summary.get("avg_pages_per_session"), 2)),
        ("Avg session", f'{_fmt_float(summary.get("avg_session_minutes"), 1)} min'),
        ("DB latency", f'{_fmt_float(db.get("latency_ms"), 0)} ms'),
    ]
    for c, (label, value) in zip(cards, metrics):
        with c:
            st.metric(label, value)

    daily = _df(_call(get_daily_traffic, max(days, 7), default=[]))
    if not daily.empty:
        _line(daily, "date", ["pageviews", "visitors", "sessions", "events"], "Traffic and engagement trend", 390)

    left, right = st.columns([1.4, 1])
    with left:
        pages = _df(_call(get_popular_pages, 12, default=[]))
        if not pages.empty:
            _section("Top product areas")
            _bar(pages.sort_values("pageviews").tail(12), "pageviews", "page_name", height=390)

    with right:
        _section("Platform health")
        rows = [
            {"Metric": "Database connected", "Value": "Yes" if db.get("connected") else "No"},
            {"Metric": "DB latency", "Value": f'{_fmt_float(db.get("latency_ms"), 1)} ms'},
            {"Metric": "Connections", "Value": _fmt_int(db.get("connections"))},
            {"Metric": "Active connections", "Value": _fmt_int(db.get("active_connections"))},
            {"Metric": "Database size", "Value": f'{_fmt_float(db.get("size_mb"), 1)} MB'},
            {"Metric": "Cache hit", "Value": f'{_fmt_float(db.get("cache_hit_pct"), 1)}%'},
            {"Metric": "Single-page rate", "Value": _fmt_pct(summary.get("single_page_rate_pct"))},
            {"Metric": "Events / session", "Value": _fmt_float(summary.get("avg_events_per_session"), 2)},
        ]
        platform = pd.DataFrame(rows).astype({"Metric": "string", "Value": "string"})
        _table(platform, height=390)


def _audience(days: int) -> None:
    _section("Audience", "Anonymous browser/session context. No names, emails, raw IP addresses or exact GPS.")
    sets = [
        ("Device mix", get_device_breakdown),
        ("Browser mix", get_browser_breakdown),
        ("Operating systems", get_os_breakdown),
        ("Languages", get_language_breakdown),
        ("Time zones", get_timezone_breakdown),
        ("Country hints", get_country_hint_breakdown),
    ]
    for i in range(0, len(sets), 2):
        cols = st.columns(2)
        for c, (title, fn) in zip(cols, sets[i:i+2]):
            with c:
                data = _df(_call(fn, default=[]))
                _section(title)
                if not data.empty:
                    value_col = "sessions" if "sessions" in data.columns else ("visitors" if "visitors" in data.columns else data.columns[-1])
                    label_col = "label" if "label" in data.columns else data.columns[0]
                    _bar(data.sort_values(value_col).tail(12), value_col, label_col, height=335)
                else:
                    st.caption("No audience data available.")
    theme = _df(_call(get_theme_breakdown, default=[]))
    if not theme.empty:
        _section("Theme usage")
        _table(theme)


def _content(days: int) -> None:
    _section("Content & feature adoption")
    pages = _df(_call(get_popular_pages, 25, default=[]))
    features = _df(_call(get_feature_usage, days, 30, default=[]))
    searches = _df(_call(get_search_destinations, 25, default=[]))
    c1, c2 = st.columns(2)
    with c1:
        _section("Most visited pages")
        if not pages.empty:
            _bar(pages.sort_values("pageviews").tail(15), "pageviews", "page_name", height=430)
    with c2:
        _section("Feature usage")
        if not features.empty:
            value = "events" if "events" in features.columns else features.columns[-1]
            label = "feature" if "feature" in features.columns else features.columns[0]
            _bar(features.sort_values(value).tail(15), value, label, height=430)
        else:
            st.info("Feature events are not yet broadly instrumented.")
    _section("Search destinations")
    _table(searches)


def _journeys(days: int) -> None:
    _section("Journeys & funnels", "Navigation transitions, entry/exit behavior and session depth.")
    edges = _df(_call(get_journey_edges, days, 40, default=[]))
    exits = _df(_call(get_exit_pages, days, 15, default=[]))
    entries = _df(_call(get_entry_pages, 15, default=[]))
    depth = _df(_call(get_session_depth_distribution, days, default=[]))
    if not edges.empty and {"source", "target", "transitions"} <= set(edges.columns):
        edges["transition"] = edges["source"].astype(str) + " → " + edges["target"].astype(str)
        _section("Top navigation transitions")
        _bar(edges.sort_values("transitions").tail(18), "transitions", "transition", height=470)
    c1, c2, c3 = st.columns(3)
    with c1:
        _section("Entry pages")
        _table(entries, height=310)
    with c2:
        _section("Exit pages")
        _table(exits, height=310)
    with c3:
        _section("Session depth")
        _table(depth, height=310)


def _events(days: int) -> None:
    _section("Events & interactions")
    top = _df(_call(get_top_events, 25, default=[]))
    recent = _df(_call(get_recent_events, 80, default=[]))
    if not top.empty:
        value = "event_count" if "event_count" in top.columns else top.columns[-1]
        _bar(top.sort_values(value).tail(18), value, "event_name", "Most frequent events", 455)
    _section("Recent event stream")
    if not recent.empty and "metadata" in recent.columns:
        recent["metadata"] = recent["metadata"].map(lambda x: str(x)[:220])
    _table(recent, height=380)


def _acquisition(days: int) -> None:
    _section("Acquisition")
    refs = _df(_call(get_referrer_breakdown, 20, default=[]))
    campaigns = _df(_call(get_campaign_breakdown, 25, default=[]))
    hours = _df(_call(get_hourly_activity, default=[]))
    c1, c2 = st.columns(2)
    with c1:
        _section("Referrers")
        if not refs.empty:
            _bar(refs.sort_values("sessions").tail(15), "sessions", "label", height=390)
    with c2:
        _section("Hourly activity")
        _line(hours, "hour", ["pageviews", "visitors"], height=390)
    _section("Campaigns")
    _table(campaigns)


def _performance(days: int) -> None:
    _section("Application performance", "True telemetry from analytics_performance; not inferred from pageviews.")
    db = _db_health()
    perf = _df(_call(get_performance_summary, days, 40, default=[]))

    cards = st.columns(6)
    values = [
        ("DB latency", f'{_fmt_float(db.get("latency_ms"), 0)} ms'),
        ("DB cache hit", f'{_fmt_float(db.get("cache_hit_pct"), 1)}%'),
        ("DB connections", _fmt_int(db.get("connections"))),
        ("Active DB", _fmt_int(db.get("active_connections"))),
        ("DB size", f'{_fmt_float(db.get("size_mb"), 1)} MB'),
        ("Perf samples", _fmt_int(perf["samples"].sum() if "samples" in perf.columns else 0)),
    ]
    for c, (label, value) in zip(cards, values):
        with c:
            st.metric(label, value)

    if perf.empty:
        st.info("Performance storage is ready but has no samples yet. Use record_performance() around route rendering, database queries and external API calls.")
        return

    _section("Latency by operation")
    _table(perf, height=430)
    if "operation" in perf.columns and "p95_ms" in perf.columns:
        chart = perf.copy()
        chart["p95_ms"] = pd.to_numeric(chart["p95_ms"], errors="coerce")
        _bar(chart.sort_values("p95_ms").tail(20), "p95_ms", "operation", "Slowest operations by P95", 470)


def _reliability(days: int) -> None:
    _section("Reliability & errors", "Redacted operational failures only.")
    summary = _df(_call(get_error_summary, days, 40, default=[]))
    recent = _df(_call(get_recent_errors, 100, default=[]))
    total = int(summary["occurrences"].sum()) if "occurrences" in summary.columns else len(recent)
    unique = len(summary)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Error occurrences", _fmt_int(total))
    with c2:
        st.metric("Unique error groups", _fmt_int(unique))
    with c3:
        critical = int(summary["severity"].astype(str).str.lower().isin(["critical", "fatal"]).sum()) if "severity" in summary.columns else 0
        st.metric("Critical groups", _fmt_int(critical))
    if not summary.empty:
        _section("Grouped failures")
        _table(summary, height=360)
    if not recent.empty:
        if "metadata" in recent.columns:
            recent["metadata"] = recent["metadata"].map(lambda x: str(x)[:180])
        if "message_redacted" in recent.columns:
            recent["message_redacted"] = recent["message_redacted"].astype("string").str.slice(0, 220)
        _section("Recent redacted errors")
        _table(recent, height=380)
    elif summary.empty:
        st.success("No recorded application errors in the selected period.")


def _ai_data(days: int) -> None:
    _section("AI & data quality")
    ai = _call(get_ai_usage_summary, days, default={}) or {}
    cats = _df(_call(get_ai_category_breakdown, days, 20, default=[]))
    quality = _df(_call(get_data_quality_latest, 100, default=[]))
    cards = st.columns(6)
    metrics = [
        ("AI requests", _fmt_int(ai.get("requests") or ai.get("total_requests"))),
        ("AI failures", _fmt_int(ai.get("failed"))),
        ("AI avg latency", f'{_fmt_float(ai.get("avg_ms"), 0)} ms'),
        ("AI P95", f'{_fmt_float(ai.get("p95_ms"), 0)} ms'),
        ("Input chars", _fmt_int(ai.get("input_chars"))),
        ("Output chars", _fmt_int(ai.get("output_chars"))),
    ]
    for c, (label, value) in zip(cards, metrics):
        with c:
            st.metric(label, value)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        _section("AI categories")
        _table(cats, height=350)
    with c2:
        _section("Latest data-quality checks")
        _table(quality, height=350)


def _privacy(days: int) -> None:
    _section("Privacy & telemetry health")
    privacy = _call(get_privacy_summary, default={}) or {}
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Tracked sessions", _fmt_int(privacy.get("sessions")))
    with c2:
        st.metric("DNT sessions", _fmt_int(privacy.get("dnt_sessions")))
    with c3:
        st.metric("GPC sessions", _fmt_int(privacy.get("gpc_sessions")))
    with c4:
        st.metric("Persistent IDs", _fmt_int(privacy.get("persistent_sessions")))

    st.info("ORBIDENSE currently uses session-scoped anonymous visitor identifiers, so this console does not present true cross-visit user retention as if it were available.")
    st.markdown("""
**Privacy boundary**

- No names or email addresses
- No raw IP addresses
- No exact GPS coordinates
- No advertising identifiers
- No raw AI prompts or conversation contents
- Error messages are redacted before storage
- Browser context is used only for coarse product analytics
    """)


def render_analytics_dashboard() -> None:
    _render_header()

    period = st.segmented_control(
        "Analysis window",
        options=["24h", "7d", "30d", "90d"],
        default="30d",
        key="developer_analytics_period_v3",
        label_visibility="collapsed",
    )
    days = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}.get(period or "30d", 30)

    tabs = st.tabs([
        "Overview", "Live", "Audience", "Content", "Journeys", "Events",
        "Acquisition", "Performance", "Reliability", "AI & Data", "Privacy"
    ])

    with tabs[0]:
        _overview(days)
    with tabs[1]:
        _render_live_viewers()
    with tabs[2]:
        _audience(days)
    with tabs[3]:
        _content(days)
    with tabs[4]:
        _journeys(days)
    with tabs[5]:
        _events(days)
    with tabs[6]:
        _acquisition(days)
    with tabs[7]:
        _performance(days)
    with tabs[8]:
        _reliability(days)
    with tabs[9]:
        _ai_data(days)
    with tabs[10]:
        _privacy(days)

    st.caption(f"Private analytics • live refresh {LIVE_REFRESH_SECONDS}s • generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
