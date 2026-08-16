from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui_v27 import style_plotly_v27
from src.api.country_rankings import CCKP_SCENARIOS, get_country_scenario_trajectory
from src.api.future_climate import get_midcentury_ensemble
from .data_clients import (
    get_cat_rating,
    get_cat_sector_benchmarks,
    get_cdp_city_profile,
    get_climate_policy_timeline,
    get_climate_watch_emissions,
    get_edgar_country_sector_snapshot,
    get_ndc_quantifications,
)
from .logic import (
    latest_total_emissions,
    linear_trend_per_decade,
    parse_target_candidates,
    percent_change,
    sector_shares,
)


def _inject_css():
    st.markdown(
        """
<style>
.ci-hero{border:1px solid rgba(66,211,230,.18);background:linear-gradient(120deg,rgba(8,28,44,.92),rgba(5,18,29,.92));border-radius:22px;padding:22px 24px;margin:6px 0 18px;position:relative;overflow:hidden}
.ci-eyebrow{font-size:.72rem;text-transform:uppercase;letter-spacing:.16em;color:#38d6e8;font-weight:800;margin-bottom:7px}
.ci-title{font-size:1.65rem;font-weight:850;line-height:1.15;color:#f7fbff;margin-bottom:6px}.ci-sub{color:#9cb3c4;font-size:.92rem;max-width:980px}
.ci-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 18px}.ci-card{border:1px solid rgba(139,179,208,.14);background:#0b1a28;border-radius:16px;padding:14px 15px;min-height:96px}.ci-label{font-size:.68rem;color:#7f9aab;text-transform:uppercase;letter-spacing:.08em;font-weight:750}.ci-value{font-size:1.32rem;color:#f7fbff;font-weight:820;margin-top:7px}.ci-note{font-size:.73rem;color:#7f9aab;margin-top:4px}
.ci-ribbon{display:flex;gap:7px;flex-wrap:wrap;margin:2px 0 14px}.ci-badge{display:inline-flex;align-items:center;border:1px solid rgba(53,206,229,.20);background:rgba(15,53,70,.55);color:#9bd9e4;border-radius:999px;padding:5px 9px;font-size:.70rem}.ci-good{color:#73e5a4}.ci-warn{color:#ffc46b}.ci-danger{color:#ff8d8d}
.ci-section{font-size:1.05rem;font-weight:800;color:#f6fbff;margin:22px 0 5px}.ci-help{font-size:.79rem;color:#849eaf;margin-bottom:12px}.ci-callout{border-left:3px solid #35d2e5;background:rgba(10,34,48,.74);padding:12px 14px;border-radius:10px;color:#b6c9d5;margin:10px 0 16px}.ci-source{font-size:.72rem;color:#698597;margin-top:6px}.ci-empty{border:1px dashed rgba(139,179,208,.20);border-radius:15px;padding:14px 16px;color:#8ba4b5;background:rgba(9,24,36,.5)}
.ci-deadline{display:grid;grid-template-columns:90px 1fr;gap:12px;align-items:start;padding:10px 0;border-bottom:1px solid rgba(139,179,208,.10)}.ci-year{font-weight:850;color:#38d6e8}.ci-event{color:#dbe7ee;font-weight:650}.ci-event-note{color:#7692a5;font-size:.76rem;margin-top:3px}
@media(max-width:1000px){.ci-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.ci-grid{grid-template-columns:1fr}.ci-title{font-size:1.35rem}}
</style>
        """,
        unsafe_allow_html=True,
    )


def _fmt(value, pattern=".1f", suffix=""):
    try:
        return f"{float(value):{pattern}}{suffix}"
    except Exception:
        return "—"


def _country_display(country_feature: dict | None, iso3: str | None) -> str:
    if country_feature:
        for key in ("place_name", "name", "text", "country", "label"):
            value = country_feature.get(key)
            if value:
                return str(value).split(",")[0]
    return iso3 or "Select a country"


def _selected_place_name(point_location: dict | None) -> str | None:
    if not point_location:
        return None
    for key in ("place_name", "name", "city_name", "display_name", "label"):
        if point_location.get(key):
            return str(point_location[key]).split(",")[0]
    return None


def _historical_country_metrics(country_national: pd.DataFrame | None):
    result = {"trend": None, "latest_temp": None, "latest_precip": None, "period": None}
    if country_national is None or country_national.empty:
        return result
    frame = country_national.copy()
    year_col = "year" if "year" in frame else None
    temp_col = next((c for c in ("mean_temperature_c", "avg_temperature_c", "temperature_c") if c in frame), None)
    precip_col = next((c for c in ("annual_precipitation_mm", "precipitation_mm") if c in frame), None)
    if year_col and temp_col:
        temp_frame = frame[[year_col, temp_col]].rename(columns={temp_col: "value"})
        result["trend"] = linear_trend_per_decade(temp_frame)
        latest = frame.sort_values(year_col).iloc[-1]
        result["latest_temp"] = latest.get(temp_col)
        result["period"] = f"{int(pd.to_numeric(frame[year_col], errors='coerce').min())}–{int(pd.to_numeric(frame[year_col], errors='coerce').max())}"
        if precip_col:
            result["latest_precip"] = latest.get(precip_col)
    return result


def _projection_chart(trajectory: pd.DataFrame, scenario_label: str):
    if trajectory is None or trajectory.empty:
        return None
    frame = trajectory.copy()
    frame["period_mid"] = frame["period"].astype(str).str.extract(r"(\d{4})")[0].astype(float) + 9.5
    fig = go.Figure()
    p10 = pd.to_numeric(frame.get("p10_c"), errors="coerce")
    p90 = pd.to_numeric(frame.get("p90_c"), errors="coerce")
    median = pd.to_numeric(frame.get("median_c"), errors="coerce")
    if p10.notna().any() and p90.notna().any():
        fig.add_trace(go.Scatter(x=frame["period_mid"], y=p90, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=frame["period_mid"], y=p10, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(56,214,232,.12)", name="P10–P90 model spread", hovertemplate="%{y:.2f}°C<extra>Model spread</extra>"))
    fig.add_trace(go.Scatter(x=frame["period_mid"], y=median, mode="lines+markers", name="Median warming", line=dict(width=3), marker=dict(size=8), hovertemplate="%{x:.0f}: +%{y:.2f}°C<extra></extra>"))
    fig.update_layout(height=390, margin=dict(l=18,r=18,t=42,b=28), title=dict(text=f"Projected temperature anomaly · {scenario_label}", font=dict(size=16)), xaxis_title="Period midpoint", yaxis_title="Temperature anomaly (°C)", legend=dict(orientation="h", y=1.02, x=0))
    return style_plotly_v27(fig)


def _historical_chart(country_national: pd.DataFrame | None):
    if country_national is None or country_national.empty or "year" not in country_national:
        return None
    frame = country_national.copy()
    temp_col = next((c for c in ("mean_temperature_c", "avg_temperature_c", "temperature_c") if c in frame), None)
    if not temp_col:
        return None
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame[temp_col] = pd.to_numeric(frame[temp_col], errors="coerce")
    frame = frame.dropna(subset=["year", temp_col])
    if frame.empty:
        return None
    baseline = frame[(frame["year"] >= 1991) & (frame["year"] <= 2020)][temp_col].mean()
    frame["anomaly"] = frame[temp_col] - baseline if pd.notna(baseline) else pd.NA
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame["year"], y=frame["anomaly"], mode="lines", name="Observed anomaly", line=dict(width=2.4), hovertemplate="%{x:.0f}: %{y:+.2f}°C<extra></extra>"))
    fig.add_hline(y=0, line_width=1, line_dash="dot")
    fig.update_layout(height=340, margin=dict(l=18,r=18,t=40,b=25), title=dict(text="Observed annual temperature anomaly", font=dict(size=16)), xaxis_title="Year", yaxis_title="Anomaly vs 1991–2020 (°C)", showlegend=False)
    return style_plotly_v27(fig)


def render_country_climate_outlook(*, country_feature, country_iso3, country_national, point_location=None):
    _inject_css()
    country = _country_display(country_feature, country_iso3)
    place = _selected_place_name(point_location)
    st.markdown(f"""<div class="ci-hero"><div class="ci-eyebrow">Country climate outlook</div><div class="ci-title">{country} · past → present → future</div><div class="ci-sub">Observed national climate and transparent CMIP6 scenario projections are kept separate. City/place searches receive a point-based local lens; national metrics remain country aggregates.</div></div>""", unsafe_allow_html=True)

    if not country_iso3:
        st.markdown('<div class="ci-empty">Search for a country above to load national climate history and projections. A city search can still provide a local physical-climate lens once its country mapping is available.</div>', unsafe_allow_html=True)
        return

    hist = _historical_country_metrics(country_national)
    scenario_label = st.selectbox("Projection pathway", options=list(CCKP_SCENARIOS.keys()), index=1, key="ci_outlook_scenario", help="One pathway is loaded at a time to preserve speed. P10–P90 shows climate-model spread, not probability.")
    scenario = CCKP_SCENARIOS[scenario_label]
    with st.spinner("Loading country projection…"):
        try:
            trajectory = get_country_scenario_trajectory(country_iso3, scenario)
        except Exception:
            trajectory = pd.DataFrame()
    mid = None
    late = None
    if trajectory is not None and not trajectory.empty:
        mid_row = trajectory[trajectory["period"].astype(str).str.contains("2040-2059")]
        late_row = trajectory[trajectory["period"].astype(str).str.contains("2080-2099")]
        if not mid_row.empty:
            mid = mid_row.iloc[0].get("median_c")
        if not late_row.empty:
            late = late_row.iloc[0].get("median_c")

    st.markdown(f"""<div class="ci-grid">
<div class="ci-card"><div class="ci-label">Observed warming trend</div><div class="ci-value">{_fmt(hist['trend'], '+.2f', '°C/decade')}</div><div class="ci-note">National observed series</div></div>
<div class="ci-card"><div class="ci-label">Latest annual mean</div><div class="ci-value">{_fmt(hist['latest_temp'], '.1f', '°C')}</div><div class="ci-note">Historical source period {hist['period'] or '—'}</div></div>
<div class="ci-card"><div class="ci-label">2040–2059 warming</div><div class="ci-value">{_fmt(mid, '+.2f', '°C')}</div><div class="ci-note">CMIP6 ensemble median</div></div>
<div class="ci-card"><div class="ci-label">2080–2099 warming</div><div class="ci-value">{_fmt(late, '+.2f', '°C')}</div><div class="ci-note">CMIP6 ensemble median</div></div>
</div>""", unsafe_allow_html=True)
    st.markdown('<div class="ci-ribbon"><span class="ci-badge">Observed: World Bank CCKP / CRU</span><span class="ci-badge">Projection: CCKP CMIP6</span><span class="ci-badge">Baseline: 1991–2020 where applicable</span><span class="ci-badge">Uncertainty shown explicitly</span></div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left:
        fig = _historical_chart(country_national)
        if fig:
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        else:
            st.markdown('<div class="ci-empty">Observed national time series is not available for this selection.</div>', unsafe_allow_html=True)
    with right:
        fig = _projection_chart(trajectory, scenario_label)
        if fig:
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        else:
            st.markdown('<div class="ci-empty">The CCKP projection service did not return a usable trajectory. ORBIDENSE does not fabricate missing projections.</div>', unsafe_allow_html=True)

    if place and point_location:
        st.markdown('<div class="ci-section">City / place climate lens</div>', unsafe_allow_html=True)
        st.markdown('<div class="ci-help">Physical climate projections can be produced for a point even when city policy reporting is unavailable.</div>', unsafe_allow_html=True)
        try:
            lat = float(point_location.get("latitude"))
            lon = float(point_location.get("longitude"))
            local_future = get_midcentury_ensemble(lat, lon, model_names=("CMCC_CM2_VHR4", "MRI_AGCM3_2_S", "EC_Earth3P_HR", "MPI_ESM1_2_XR"))
        except Exception:
            local_future = {}
        cdp = get_cdp_city_profile(place, country_iso3)
        c1, c2, c3 = st.columns(3)
        c1.metric("Place", place)
        c2.metric("2041–2049 local mean", _fmt(local_future.get("temperature_median_c"), '.1f', '°C'))
        c3.metric("CDP policy reporting", "Available" if cdp else "Not synced / not reported")
        if cdp:
            st.markdown(f"<div class='ci-callout'><b>City reporting:</b> target year {cdp.get('target_year','—')} · reported progress {cdp.get('target_progress_pct','—')}% · main reported risk {cdp.get('primary_risk','—')}.</div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="ci-empty">Phase 2 is coverage-aware: city policy indicators appear only for cities present in the preprocessed CDP public dataset. No country value is substituted for a missing city disclosure.</div>', unsafe_allow_html=True)

    with st.expander("Data, methods & interpretation"):
        st.markdown("""
**Observed national climate:** World Bank Climate Change Knowledge Portal historical country aggregates (CRU/CCKP pipeline already used by ORBIDENSE).

**Future national climate:** World Bank CCKP CMIP6 country aggregates. The selected SSP is a forcing/emissions pathway; P10/median/P90 expresses model-ensemble spread.

**Local city/place lens:** point-based Open-Meteo Climate / CMIP6 HighResMIP ensemble. It is not a city-boundary average.

**Interpretation rule:** observed weather, observed climate, mitigation targets and future projections are never mixed into one score.
        """)


def _emissions_chart(frame: pd.DataFrame):
    if frame is None or frame.empty:
        return None
    data = frame.copy()
    total_mask = data["sector"].astype(str).str.lower().str.contains("total|all sectors")
    if total_mask.any():
        data = data[total_mask]
    else:
        # Sum sectors by year only when the provider did not supply an explicit total.
        data = data.groupby("year", as_index=False).agg(value=("value", "sum"), unit=("unit", "first"))
    data = data.groupby("year", as_index=False)["value"].sum().sort_values("year")
    fig = go.Figure(go.Scatter(x=data["year"], y=data["value"], mode="lines", line=dict(width=2.5), name="Historical emissions", hovertemplate="%{x}: %{y:,.1f}<extra></extra>"))
    fig.update_layout(height=355, margin=dict(l=18,r=18,t=42,b=28), title=dict(text="Historical greenhouse-gas emissions", font=dict(size=16)), xaxis_title="Year", yaxis_title="Reported dataset unit", showlegend=False)
    return style_plotly_v27(fig)


def _sector_chart(sectors: pd.DataFrame):
    if sectors is None or sectors.empty:
        return None
    data = sectors.sort_values("share_pct", ascending=True)
    fig = go.Figure(go.Bar(x=data["share_pct"], y=data["sector"], orientation="h", text=data["share_pct"].map(lambda x: f"{x:.1f}%"), textposition="outside", hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.update_layout(height=max(320, 54 * len(data)), margin=dict(l=18,r=45,t=42,b=25), title=dict(text="Largest emitting sectors · latest available year", font=dict(size=16)), xaxis_title="Share of represented sectors (%)", yaxis_title="", showlegend=False)
    return style_plotly_v27(fig)


def render_climate_action_progress(*, country_feature, country_iso3, country_national=None, point_location=None):
    _inject_css()
    country = _country_display(country_feature, country_iso3)
    st.markdown(f"""<div class="ci-hero"><div class="ci-eyebrow">Climate action & progress</div><div class="ci-title">{country} · targets → emissions → implementation</div><div class="ci-sub">Official NDC commitments, independent CAT assessment where covered, emissions evidence and sector structure are shown as separate evidence layers. ORBIDENSE does not turn them into a black-box climate score.</div></div>""", unsafe_allow_html=True)
    if not country_iso3:
        st.markdown('<div class="ci-empty">Search for a country above. Mitigation progress is a country-policy product and is not inferred from a city centroid or current weather.</div>', unsafe_allow_html=True)
        return

    cat = get_cat_rating(country_iso3)
    try:
        ndc_records = get_ndc_quantifications(country_iso3)
    except Exception:
        ndc_records = []
    targets = parse_target_candidates(ndc_records)
    try:
        emissions = get_climate_watch_emissions(country_iso3)
    except Exception:
        emissions = pd.DataFrame()
    latest_year, latest_value, latest_unit = latest_total_emissions(emissions)
    trend = None
    if emissions is not None and not emissions.empty:
        total = emissions.copy()
        total_mask = total["sector"].astype(str).str.lower().str.contains("total|all sectors")
        if total_mask.any():
            total = total[total_mask]
        else:
            total = total.groupby("year", as_index=False)["value"].sum()
        trend = percent_change(total.sort_values("year").iloc[0]["value"], total.sort_values("year").iloc[-1]["value"]) if len(total) >= 2 else None

    target_years = [t.get("year") for t in targets if t.get("year")]
    next_target = min([y for y in target_years if y >= 2026], default=None)
    next_target_record = next((t for t in targets if t.get("year") == next_target), None)
    target_text = "—"
    if next_target_record:
        if next_target_record.get("reduction_pct") is not None:
            target_text = f"{next_target_record['reduction_pct']:.0f}% reduction"
        elif next_target_record.get("target_emissions") is not None:
            target_text = f"{next_target_record['target_emissions']:,.0f} target emissions"
        else:
            target_text = str(next_target_record.get("label") or "Target")

    cat_rating = cat.get("rating") if cat else "Not covered by CAT snapshot"
    cat_update = cat.get("update_date") if cat else "—"
    st.markdown(f"""<div class="ci-grid">
<div class="ci-card"><div class="ci-label">Next quantified target</div><div class="ci-value">{next_target or '—'}</div><div class="ci-note">{target_text}</div></div>
<div class="ci-card"><div class="ci-label">Latest emissions</div><div class="ci-value">{_fmt(latest_value, ',.0f')}</div><div class="ci-note">{latest_year or '—'} · {latest_unit or 'dataset unit'}</div></div>
<div class="ci-card"><div class="ci-label">Historical change</div><div class="ci-value">{_fmt(trend, '+.1f', '%')}</div><div class="ci-note">First to latest available observation</div></div>
<div class="ci-card"><div class="ci-label">Climate Action Tracker</div><div class="ci-value" style="font-size:1.05rem">{cat_rating}</div><div class="ci-note">Independent assessment · {cat_update}</div></div>
</div>""", unsafe_allow_html=True)
    st.markdown('<div class="ci-ribbon"><span class="ci-badge">Official NDC documents: UNFCCC Registry</span><span class="ci-badge">Structured targets: Climate Watch / WRI</span><span class="ci-badge">Independent assessment: CAT where covered</span><span class="ci-badge">Emissions: Climate Watch/CAIT + EDGAR sector fallback</span></div>', unsafe_allow_html=True)

    left, right = st.columns([1.25, .75], gap="medium")
    with left:
        fig = _emissions_chart(emissions)
        if fig:
            st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        else:
            st.markdown('<div class="ci-empty">Historical emissions could not be retrieved from the structured Climate Watch endpoint. The page remains available and does not invent an emissions path.</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="ci-section" style="margin-top:0">Target deadlines</div>', unsafe_allow_html=True)
        if targets:
            for item in targets[:8]:
                year = item.get("year") or "—"
                details = []
                if item.get("reduction_pct") is not None:
                    details.append(f"{item['reduction_pct']:.0f}% reduction")
                if item.get("target_emissions") is not None:
                    details.append(f"target emissions {item['target_emissions']:,.0f}")
                st.markdown(f"<div class='ci-deadline'><div class='ci-year'>{year}</div><div><div class='ci-event'>{item.get('label') or 'NDC target'}</div><div class='ci-event-note'>{' · '.join(details) or 'Structured NDC target record'}</div></div></div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="ci-empty">No structured target fields were returned. Use the UNFCCC Registry as the authoritative document source.</div>', unsafe_allow_html=True)

    st.markdown('<div class="ci-section">Sector structure</div>', unsafe_allow_html=True)
    st.markdown('<div class="ci-help">ORBIDENSE first attempts the current EDGAR 2025 workbook; if unavailable at runtime, sector composition can fall back to available structured emissions data.</div>', unsafe_allow_html=True)
    edgar = get_edgar_country_sector_snapshot(country_iso3, country)
    sectors = sector_shares(edgar)
    if sectors.empty and emissions is not None and not emissions.empty:
        latest = emissions[emissions["year"] == emissions["year"].max()]
        sectors = sector_shares(latest)
    fig = _sector_chart(sectors)
    if fig:
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        top = sectors.sort_values("share_pct", ascending=False).iloc[0]
        st.markdown(f"<div class='ci-callout'><b>Largest represented sector:</b> {top['sector']} ({top['share_pct']:.1f}% of the represented sector total). This is descriptive emissions accounting, not a causal statement about policy effectiveness.</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="ci-empty">Sector-level emissions are not available for this country in the current runtime cache. The sync/backtest utilities flag this as a coverage gap rather than substituting another country or sector.</div>', unsafe_allow_html=True)

    benchmarks = get_cat_sector_benchmarks(country_iso3)
    st.markdown('<div class="ci-section">Phase 3 · sector transition benchmarks</div>', unsafe_allow_html=True)
    if not benchmarks.empty:
        display_cols = [c for c in ("sector", "indicator", "current_value", "benchmark_2030", "unit", "status") if c in benchmarks.columns]
        st.dataframe(benchmarks[display_cols], width="stretch", hide_index=True)
    else:
        st.markdown('<div class="ci-empty">CAT 1.5°C sector benchmark data is intentionally shown only after the downloadable CAT sector dataset has been synced and provenance-checked. This prevents fabricated benchmark values.</div>', unsafe_allow_html=True)

    try:
        timeline = get_climate_policy_timeline(country_iso3)
    except Exception:
        timeline = []
    if timeline:
        with st.expander("Policy / NDC event timeline"):
            st.dataframe(pd.DataFrame(timeline), width="stretch", hide_index=True)

    with st.expander("Data, methods & interpretation"):
        st.markdown("""
**Targets:** official legal/Paris-Agreement status remains anchored to the UNFCCC NDC Registry. Climate Watch/WRI is used for structured machine-readable target fields where available.

**Independent mitigation assessment:** Climate Action Tracker rating snapshot is displayed only for countries it covers and includes its update date.

**Historical emissions:** machine-readable Climate Watch/CAIT endpoint; EDGAR/JRC is used for sector accounting when the current workbook can be parsed.

**No composite score:** physical climate risk, emissions, target ambition and policy implementation are analytically distinct and are not collapsed into one opaque number.
        """)
