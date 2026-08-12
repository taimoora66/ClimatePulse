from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    get_analytics_summary,
    get_browser_breakdown,
    get_campaign_breakdown,
    get_country_hint_breakdown,
    get_daily_traffic,
    get_entry_pages,
    get_device_breakdown,
    get_hourly_activity,
    get_language_breakdown,
    get_live_sessions,
    get_os_breakdown,
    get_popular_pages,
    get_recent_activity,
    get_recent_events,
    get_referrer_breakdown,
    get_search_destinations,
    get_theme_breakdown,
    get_timezone_breakdown,
    get_top_events,
)


def _style_figure(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=25, r=20, t=28, b=34),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfe0ea"),
        xaxis=dict(
            gridcolor="rgba(139,179,208,.08)",
            zerolinecolor="rgba(139,179,208,.10)",
        ),
        yaxis=dict(
            gridcolor="rgba(139,179,208,.08)",
            zerolinecolor="rgba(139,179,208,.10)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
        ),
        hoverlabel=dict(
            bgcolor="#081722",
            font_color="#f5fbff",
        ),
    )
    return fig


def _bar_from_rows(
    rows,
    *,
    label_column: str = "label",
    value_column: str = "sessions",
    title: str,
    height: int = 330,
) -> None:
    if not rows:
        st.info("No data recorded yet.")
        return

    frame = pd.DataFrame(rows)
    fig = go.Figure(
        go.Bar(
            x=frame[value_column],
            y=frame[label_column],
            orientation="h",
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    _style_figure(fig, height=height)
    st.plotly_chart(
        fig,
        width="stretch",
        config={"displayModeBar": False, "responsive": True},
    )


def _analytics_css() -> None:
    st.html(
        """
<style>
.cp-admin-hero {
    background:
        radial-gradient(circle at 88% 14%, rgba(61, 210, 237, .12), transparent 27%),
        linear-gradient(135deg, rgba(13, 38, 55, .98), rgba(5, 19, 30, .99));
    border: 1px solid rgba(73, 214, 246, .18);
    border-radius: 18px;
    padding: 23px 24px;
    margin: 7px 0 16px;
}
.cp-admin-kicker {
    color: #58d7f3;
    font-size: .66rem;
    font-weight: 850;
    letter-spacing: .15em;
}
.cp-admin-title {
    color: #fff;
    font-size: 1.7rem;
    font-weight: 850;
    margin-top: 6px;
}
.cp-admin-copy {
    color: #8fa8b8;
    font-size: .78rem;
    line-height: 1.55;
    max-width: 900px;
    margin-top: 8px;
}
.cp-admin-live {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-top: 13px;
    padding: 7px 11px;
    border-radius: 999px;
    border: 1px solid rgba(83, 225, 160, .22);
    background: rgba(83, 225, 160, .08);
    color: #8cf0bd;
    font-size: .72rem;
    font-weight: 750;
}
.cp-admin-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #59e7a1;
    box-shadow: 0 0 10px rgba(89,231,161,.8);
}
.cp-admin-note {
    margin-top: 12px;
    color: #6f899a;
    font-size: .69rem;
    line-height: 1.55;
}
.cp-admin-section {
    color: #ffffff;
    font-size: 1.02rem;
    font-weight: 780;
    margin: 4px 0 10px;
}
</style>
        """
    )


def render_analytics_dashboard() -> None:
    _analytics_css()
    summary = get_analytics_summary()

    st.html(
        f"""
<div class="cp-admin-hero">
    <div class="cp-admin-kicker">CLIMATEPULSE / DEVELOPER ANALYTICS</div>
    <div class="cp-admin-title">Audience & Product Intelligence</div>
    <div class="cp-admin-copy">
        Private first-party analytics stored in PostgreSQL / Neon. This dashboard
        is designed for the developer and is not exposed in the normal public navigation.
    </div>
    <div class="cp-admin-live">
        <span class="cp-admin-dot"></span>
        {summary['active_now']:,} active now
    </div>
    <div class="cp-admin-note">
        Privacy mode: session-scoped anonymous identifiers. Native Streamlit session
        context is used instead of a custom browser component. The tracker avoids names,
        email addresses, raw IP addresses, precise GPS coordinates, raw user-agent
        strings, advertising IDs and AI message contents.
    </div>
</div>
        """
    )

    row1 = st.columns(5, gap="small")
    row1[0].metric("Active now", f"{summary['active_now']:,}")
    row1[1].metric("Visitors today", f"{summary['visitors_today']:,}")
    row1[2].metric("Last 7 days", f"{summary['visitors_7d']:,}")
    row1[3].metric("Last 30 days", f"{summary['visitors_30d']:,}")
    row1[4].metric("Anonymous visitors", f"{summary['unique_visitors']:,}")

    row2 = st.columns(5, gap="small")
    row2[0].metric("Sessions", f"{summary['total_sessions']:,}")
    row2[1].metric("Page views", f"{summary['total_pageviews']:,}")
    row2[2].metric("Tracked events", f"{summary['total_events']:,}")
    row2[3].metric("Avg session", f"{summary['avg_session_minutes']:.1f} min")
    row2[4].metric("Pages / session", f"{summary['avg_pages_per_session']:.2f}")

    row3 = st.columns(3, gap="small")
    row3[0].metric("Events / session", f"{summary['avg_events_per_session']:.2f}")
    row3[1].metric("Single-page sessions", f"{summary['single_page_rate_pct']:.1f}%")
    row3[2].metric("Identity model", "Session-scoped")

    overview_tab, acquisition_tab, audience_tab, engagement_tab, live_tab, data_tab = st.tabs(
        [
            "Overview",
            "Acquisition",
            "Audience",
            "Engagement",
            "Live",
            "Data dictionary",
        ]
    )

    with overview_tab:
        st.markdown("### Traffic over time")
        period = st.segmented_control(
            "Period",
            options=[7, 30, 90, 365],
            default=30,
            format_func=lambda value: f"{value} days",
            key="analytics_period_selector_v36",
            label_visibility="collapsed",
        ) or 30

        traffic = get_daily_traffic(period)
        if traffic:
            frame = pd.DataFrame(traffic)
            frame["date"] = pd.to_datetime(frame["date"])

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=frame["date"], y=frame["visitors"], mode="lines+markers", name="Visitors"))
            fig.add_trace(go.Scatter(x=frame["date"], y=frame["sessions"], mode="lines+markers", name="Sessions"))
            fig.add_trace(go.Scatter(x=frame["date"], y=frame["pageviews"], mode="lines+markers", name="Page views"))
            fig.add_trace(go.Scatter(x=frame["date"], y=frame["events"], mode="lines+markers", name="Events"))
            fig.update_layout(hovermode="x unified")
            _style_figure(fig, height=410)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True})
        else:
            st.info("Traffic history will appear as visitors use ClimatePulse.")

        left, right = st.columns(2, gap="medium")
        with left:
            st.markdown("### Most viewed pages")
            pages = get_popular_pages(15)
            if pages:
                page_df = pd.DataFrame(pages)
                fig = go.Figure(
                    go.Bar(
                        x=page_df["pageviews"],
                        y=page_df["page_name"],
                        orientation="h",
                        customdata=page_df[["visitors", "sessions"]].values,
                        hovertemplate=(
                            "<b>%{y}</b><br>Views: %{x}<br>"
                            "Visitors: %{customdata[0]}<br>"
                            "Sessions: %{customdata[1]}<extra></extra>"
                        ),
                    )
                )
                fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=False)
                _style_figure(fig, height=390)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("No page views yet.")

        with right:
            st.markdown("### Activity by hour")
            hourly = get_hourly_activity()
            if hourly:
                hourly_df = pd.DataFrame(hourly)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=hourly_df["hour"], y=hourly_df["pageviews"], name="Page views"))
                fig.add_trace(go.Scatter(x=hourly_df["hour"], y=hourly_df["visitors"], mode="lines+markers", name="Visitors"))
                fig.update_xaxes(dtick=1, title="Hour of day (database timezone)")
                _style_figure(fig, height=390)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("No hourly activity yet.")

        st.markdown("### Entry pages")
        _bar_from_rows(
            get_entry_pages(15),
            title="Sessions by entry page",
        )

    with acquisition_tab:
        left, right = st.columns(2, gap="medium")

        with left:
            st.markdown("### Referrers")
            _bar_from_rows(
                get_referrer_breakdown(15),
                title="Sessions by referring domain",
            )

        with right:
            st.markdown("### Campaign attribution")
            campaigns = get_campaign_breakdown(30)
            if campaigns:
                campaign_df = pd.DataFrame(campaigns)
                st.dataframe(
                    campaign_df.rename(
                        columns={
                            "source": "Source",
                            "medium": "Medium",
                            "campaign": "Campaign",
                            "sessions": "Sessions",
                            "visitors": "Visitors",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No campaign/UTM traffic yet.")

        st.markdown("### Most selected search destinations")
        destinations = get_search_destinations(30)
        if destinations:
            st.dataframe(
                pd.DataFrame(destinations).rename(
                    columns={
                        "label": "Selected place",
                        "result_type": "Type",
                        "selections": "Selections",
                    }
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("Search selections will appear after visitors use global search.")

    with audience_tab:
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("### Device category")
            _bar_from_rows(get_device_breakdown(), title="Sessions by device")
        with c2:
            st.markdown("### Browser family")
            _bar_from_rows(get_browser_breakdown(), title="Sessions by browser")

        c3, c4 = st.columns(2, gap="medium")
        with c3:
            st.markdown("### Operating system")
            _bar_from_rows(get_os_breakdown(), title="Sessions by OS")
        with c4:
            st.markdown("### Browser language")
            _bar_from_rows(get_language_breakdown(), title="Sessions by language")

        geo_col, theme_col = st.columns(2, gap="medium")
        with geo_col:
            st.markdown("### Country hint")
            _bar_from_rows(
                get_country_hint_breakdown(20),
                title="Sessions by hosting-provided country hint",
            )

        with theme_col:
            st.markdown("### Theme")
            _bar_from_rows(
                get_theme_breakdown(),
                title="Sessions by Streamlit theme",
            )

        st.markdown("### Timezone distribution")
        timezone_rows = get_timezone_breakdown(20)
        if timezone_rows:
            st.dataframe(
                pd.DataFrame(timezone_rows).rename(
                    columns={"label": "Timezone", "sessions": "Sessions"}
                ),
                hide_index=True,
                width="stretch",
            )

    with engagement_tab:
        left, right = st.columns(2, gap="medium")

        with left:
            st.markdown("### Top product events")
            events = get_top_events(30)
            if events:
                st.dataframe(
                    pd.DataFrame(events).rename(
                        columns={
                            "event_name": "Event",
                            "event_category": "Category",
                            "event_count": "Count",
                            "visitors": "Visitors",
                            "sessions": "Sessions",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No product events recorded yet.")

        with right:
            st.markdown("### Popular pages")
            pages = get_popular_pages(20)
            if pages:
                st.dataframe(
                    pd.DataFrame(pages).rename(
                        columns={
                            "page_name": "Page",
                            "pageviews": "Views",
                            "visitors": "Visitors",
                            "sessions": "Sessions",
                        }
                    ),
                    hide_index=True,
                    width="stretch",
                )

        st.markdown("### Recent product events")
        recent_events = get_recent_events(75)
        if recent_events:
            event_df = pd.DataFrame(recent_events)
            event_df = event_df.rename(
                columns={
                    "event_at": "Time",
                    "page_name": "Page",
                    "event_name": "Event",
                    "event_category": "Category",
                    "metadata": "Metadata",
                }
            )
            st.dataframe(event_df, hide_index=True, width="stretch")
        else:
            st.info("No event stream yet.")

    with live_tab:
        st.markdown("### Active sessions")
        live_rows = get_live_sessions(75)
        if live_rows:
            live_df = pd.DataFrame(live_rows).rename(
                columns={
                    "current_page": "Current page",
                    "started_at": "Started",
                    "last_seen": "Last active",
                    "pageviews": "Views",
                    "events": "Events",
                    "device_category": "Device",
                    "browser_family": "Browser",
                    "os_family": "OS",
                    "language": "Language",
                    "timezone": "Timezone",
                    "country_hint": "Country hint",
                }
            )
            st.dataframe(live_df, hide_index=True, width="stretch")
        else:
            st.info("No sessions are active in the last two minutes.")

        st.markdown("### Recent sessions")
        recent = get_recent_activity(100)
        if recent:
            recent_df = pd.DataFrame(recent)
            # Session IDs are internal identifiers; do not surface them in the UI.
            recent_df = recent_df.drop(columns=["session_id"], errors="ignore")
            recent_df = recent_df.rename(
                columns={
                    "current_page": "Current page",
                    "entry_page": "Entry page",
                    "started_at": "Started",
                    "last_seen": "Last active",
                    "duration_minutes": "Duration (min)",
                    "pageviews": "Views",
                    "events": "Events",
                    "device_category": "Device",
                    "browser_family": "Browser",
                    "os_family": "OS",
                    "language": "Language",
                    "timezone": "Timezone",
                    "timezone_offset_minutes": "TZ offset (min)",
                    "theme_type": "Theme",
                    "is_embedded": "Embedded",
                    "app_host": "App host",
                    "country_hint": "Country hint",
                    "referrer_domain": "Referrer",
                    "utm_source": "UTM source",
                    "utm_medium": "UTM medium",
                    "utm_campaign": "UTM campaign",
                }
            )
            st.dataframe(recent_df, hide_index=True, width="stretch")

    with data_tab:
        st.markdown("### What ClimatePulse tracks")
        st.markdown(
            """
**Audience / session**
- Anonymous visitor and session identifiers
- First seen / last active
- Session count, page views, event count
- Entry page, current page, approximate session duration
- Active-now heartbeat

**Acquisition**
- Referring domain only (not the full referring URL)
- UTM source, medium, campaign, content and term

**Browser / environment context**
- Coarse device category: desktop / tablet / mobile
- Browser family and operating-system family (parsed without storing raw user-agent text)
- Browser locale, timezone and timezone offset from Streamlit's native session context
- Streamlit light/dark theme and embedded-app status
- App host/domain
- Optional coarse country hint only when the hosting/CDN already supplies one

**Product usage**
- Navigation/page views
- Selected search destinations and result type
- Browser-location feature usage without storing the coordinates
- Compare Places configuration
- Global Rankings scenario/period selections
- Climate Passport generation
- Additional events can be added with `track_event()` without changing the database schema

**Intentionally not collected**
- Names, email addresses or account identities
- Raw IP addresses
- Exact GPS coordinates
- Raw user-agent strings or device fingerprints
- AI prompts / conversation text
- Passwords, API keys or other secrets
            """
        )

        st.warning(
            "Analytics configuration is not a substitute for a privacy notice or legal review. "
            "This build deliberately does not create a persistent cross-visit fingerprint."
        )
