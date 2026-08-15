from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    get_analytics_summary,
    get_ai_category_breakdown,
    get_ai_usage_summary,
    get_browser_breakdown,
    get_campaign_breakdown,
    get_country_hint_breakdown,
    get_daily_traffic,
    get_data_quality_latest,
    get_device_breakdown,
    get_entry_pages,
    get_error_summary,
    get_exit_pages,
    get_feature_usage,
    get_hourly_activity,
    get_journey_edges,
    get_language_breakdown,
    get_live_sessions,
    get_os_breakdown,
    get_performance_summary,
    get_popular_pages,
    get_privacy_summary,
    get_recent_activity,
    get_recent_errors,
    get_recent_events,
    get_referrer_breakdown,
    get_search_destinations,
    get_session_depth_distribution,
    get_theme_breakdown,
    get_timezone_breakdown,
    get_top_events,
)


def _style_figure(fig, height=350):
    fig.update_layout(
        height=height,
        margin=dict(l=24, r=18, t=38, b=34),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d6e6ef"),
        xaxis=dict(gridcolor="rgba(139,179,208,.08)", zeroline=False),
        yaxis=dict(gridcolor="rgba(139,179,208,.08)", zeroline=False),
        hoverlabel=dict(bgcolor="#061520", font_color="#f7fbff"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    return fig


def _bar(rows, label, value, title, height=330):
    if not rows:
        st.caption("No records yet.")
        return
    df = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(x=df[value], y=df[label], orientation="h"))
    fig.update_layout(title=title, yaxis=dict(autorange="reversed"), showlegend=False)
    st.plotly_chart(_style_figure(fig, height), width="stretch", config={"displayModeBar": False})


def _console_css():
    st.html("""
<style>
.orb-admin-hero{background:radial-gradient(circle at 88% 10%,rgba(47,225,198,.13),transparent 29%),linear-gradient(135deg,#0a2231,#05131e);border:1px solid rgba(73,214,246,.18);border-radius:20px;padding:24px 26px;margin:4px 0 16px;box-shadow:0 18px 48px rgba(0,0,0,.22)}
.orb-admin-kicker{font-size:.65rem;font-weight:900;letter-spacing:.17em;color:#54e3d2;text-transform:uppercase}
.orb-admin-title{font-size:1.75rem;font-weight:900;color:#fff;margin-top:5px}.orb-admin-copy{font-size:.76rem;line-height:1.55;color:#8fa8b8;max-width:980px;margin-top:8px}
.orb-admin-private{display:inline-flex;align-items:center;gap:7px;margin-top:12px;border:1px solid rgba(84,227,210,.18);background:rgba(84,227,210,.06);color:#a3f3e7;border-radius:999px;padding:7px 11px;font-size:.68rem;font-weight:800}
.orb-admin-section{font-size:1rem;font-weight:850;color:#fff;margin:4px 0 10px}.orb-admin-note{font-size:.69rem;line-height:1.55;color:#7892a3}
[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(9,31,44,.88),rgba(5,18,28,.92));border:1px solid rgba(114,175,207,.12);padding:12px 14px;border-radius:15px}
</style>
""")


def render_analytics_dashboard() -> None:
    _console_css()
    summary = get_analytics_summary()

    st.html("""
<div class="orb-admin-hero">
  <div class="orb-admin-kicker">ORBIDENSE AI / PRIVATE DEVELOPER CONSOLE</div>
  <div class="orb-admin-title">Product Intelligence & Observability</div>
  <div class="orb-admin-copy">Private first-party analytics, user-journey intelligence, performance telemetry, technical errors, AI usage and data-quality monitoring. This console is available only after the developer gate and password are validated.</div>
  <div class="orb-admin-private">● Developer-only · no public system status or technical diagnostics</div>
</div>
""")

    c = st.columns(6, gap="small")
    c[0].metric("Active now", f"{summary['active_now']:,}")
    c[1].metric("Sessions", f"{summary['total_sessions']:,}")
    c[2].metric("Page views", f"{summary['total_pageviews']:,}")
    c[3].metric("Events", f"{summary['total_events']:,}")
    c[4].metric("Avg session", f"{summary['avg_session_minutes']:.1f} min")
    c[5].metric("Pages / session", f"{summary['avg_pages_per_session']:.2f}")

    tabs = st.tabs([
        "Overview", "Live", "Journeys", "Features", "Search", "Audience",
        "AI", "Performance", "Errors", "Data Quality", "Privacy"
    ])

    with tabs[0]:
        period = st.segmented_control("Period", [7, 30, 90, 365], default=30, format_func=lambda x:f"{x} days", label_visibility="collapsed", key="orb_analytics_period_v2") or 30
        traffic = get_daily_traffic(period)
        if traffic:
            df = pd.DataFrame(traffic); df['date']=pd.to_datetime(df['date'])
            fig=go.Figure()
            for col,name in [("visitors","Visitors"),("sessions","Sessions"),("pageviews","Page views"),("events","Events")]:
                fig.add_trace(go.Scatter(x=df['date'], y=df[col], mode='lines', name=name))
            st.plotly_chart(_style_figure(fig,390), width="stretch", config={"displayModeBar":False})
        a,b=st.columns(2)
        with a: _bar(get_popular_pages(12), 'page_name','pageviews','Most viewed pages')
        with b: _bar(get_session_depth_distribution(period),'label','sessions','Session depth')
        st.markdown("#### Exit pages")
        st.dataframe(pd.DataFrame(get_exit_pages(period,15)), width="stretch", hide_index=True)

    with tabs[1]:
        live=get_live_sessions(100)
        st.metric("Active sessions", len(live))
        st.dataframe(pd.DataFrame(live), width="stretch", hide_index=True)
        st.markdown("#### Recent activity")
        st.dataframe(pd.DataFrame(get_recent_activity(100)), width="stretch", hide_index=True)

    with tabs[2]:
        days=st.selectbox("Journey window", [7,30,90,365], index=1, key="journey_window_v2")
        edges=get_journey_edges(days,50)
        if edges:
            df=pd.DataFrame(edges)
            labels=list(dict.fromkeys(df['source'].tolist()+df['target'].tolist()))
            ix={v:i for i,v in enumerate(labels)}
            fig=go.Figure(go.Sankey(node=dict(label=labels,pad=16,thickness=14),link=dict(source=[ix[x] for x in df['source']],target=[ix[x] for x in df['target']],value=df['transitions'].tolist())))
            fig.update_layout(title="Common navigation paths")
            st.plotly_chart(_style_figure(fig,520), width="stretch", config={"displayModeBar":False})
            st.dataframe(df, width="stretch", hide_index=True)
        else: st.caption("Journey data will appear as page-view history accumulates.")

    with tabs[3]:
        days=st.selectbox("Feature window", [7,30,90,365], index=1, key="feature_window_v2")
        usage=get_feature_usage(days,50)
        _bar(usage,'feature','events','Feature / event adoption',420)
        st.markdown("#### Event taxonomy")
        st.dataframe(pd.DataFrame(get_top_events(100)), width="stretch", hide_index=True)
        st.markdown("#### Recent events")
        st.dataframe(pd.DataFrame(get_recent_events(100)), width="stretch", hide_index=True)

    with tabs[4]:
        _bar(get_search_destinations(30),'label','selections','Most selected destinations',430)
        st.caption("Search analytics store selected destination labels/types, not typed private messages.")

    with tabs[5]:
        c1,c2=st.columns(2)
        with c1:
            _bar(get_device_breakdown(),'label','sessions','Device classes')
            _bar(get_os_breakdown(),'label','sessions','Operating systems')
            _bar(get_language_breakdown(),'label','sessions','Languages')
        with c2:
            _bar(get_browser_breakdown(),'label','sessions','Browsers')
            _bar(get_country_hint_breakdown(),'label','sessions','Coarse infrastructure country hints')
            _bar(get_timezone_breakdown(),'label','sessions','Time zones')
        st.markdown("#### Acquisition")
        ac1,ac2=st.columns(2)
        with ac1: _bar(get_referrer_breakdown(),'label','sessions','Referrers')
        with ac2: _bar(get_entry_pages(),'label','sessions','Entry pages')
        st.dataframe(pd.DataFrame(get_campaign_breakdown(50)), width="stretch", hide_index=True)

    with tabs[6]:
        ai=get_ai_usage_summary(30)
        c=st.columns(5)
        c[0].metric("Requests", int(ai.get('requests') or 0)); c[1].metric("Successful", int(ai.get('successful') or 0)); c[2].metric("Failed", int(ai.get('failed') or 0)); c[3].metric("Avg latency", f"{float(ai.get('avg_ms') or 0):.0f} ms"); c[4].metric("P95 latency", f"{float(ai.get('p95_ms') or 0):.0f} ms")
        _bar(get_ai_category_breakdown(30,30),'label','requests','AI request categories',420)
        st.caption("Prompts and assistant responses are not stored by this analytics layer.")

    with tabs[7]:
        perf=get_performance_summary(7,100)
        if perf:
            st.dataframe(pd.DataFrame(perf), width="stretch", hide_index=True)
            _bar(perf,'operation','p95_ms','Slowest operations by P95 latency',430)
        else: st.caption("Performance telemetry will appear after instrumented operations run.")

    with tabs[8]:
        errs=get_error_summary(7,100)
        e1,e2,e3=st.columns(3)
        total=sum(int(x.get('occurrences') or 0) for x in errs)
        e1.metric("Errors / 7d", total); e2.metric("Unique signatures", len(errs)); e3.metric("Public technical errors", "Hidden")
        st.dataframe(pd.DataFrame(errs), width="stretch", hide_index=True)
        with st.expander("Recent redacted diagnostics", expanded=False):
            st.dataframe(pd.DataFrame(get_recent_errors(200)), width="stretch", hide_index=True)

    with tabs[9]:
        dq=get_data_quality_latest(200)
        if dq: st.dataframe(pd.DataFrame(dq), width="stretch", hide_index=True)
        else: st.caption("No data-quality checks recorded yet.")

    with tabs[10]:
        p=get_privacy_summary()
        c=st.columns(4)
        c[0].metric("Sessions", p.get('sessions',0)); c[1].metric("DNT", p.get('dnt_sessions',0)); c[2].metric("GPC", p.get('gpc_sessions',0)); c[3].metric("Persistent IDs", p.get('persistent_sessions',0))
        st.markdown("""
#### Privacy architecture
- First-party PostgreSQL / Neon storage.
- Session-scoped anonymous identifiers; no cross-site fingerprinting.
- No names, emails, raw IP addresses, exact GPS coordinates, advertising IDs or raw user-agent strings.
- AI prompt/response text is not stored by analytics.
- DNT/GPC requests disable audience tracking.
- Technical errors are redacted before storage and are visible only here.
- Public users do not see analytics, system-health cards, stack traces or developer diagnostics.
""")
