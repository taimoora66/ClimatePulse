from __future__ import annotations

from pathlib import Path
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path("data/climate_intelligence/population_exposure.parquet")

CYAN = "#2FE1F2"
BLUE = "#49A8FF"
GREEN = "#59D88C"
YELLOW = "#F4C64C"
ORANGE = "#FF9C4A"
RED = "#FF5D62"
PURPLE = "#A77BFF"

SCENARIO_LABELS = {
    "ssp126": "SSP1–2.6 · Low emissions",
    "ssp245": "SSP2–4.5 · Intermediate",
    "ssp370": "SSP3–7.0 · High",
    "ssp585": "SSP5–8.5 · Very high",
}
PERIODS = ("2020-2039", "2040-2059", "2060-2079", "2080-2099")
STAT_LABELS = {"p10": "P10", "median": "Median", "p90": "P90"}
HAZARD_LABELS = {"hd30": "Hot days >30°C", "hd35": "Very hot days >35°C"}


@st.cache_data(show_spinner=False)
def _load_exposure() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(DATA_PATH)
    d = pd.read_parquet(DATA_PATH).copy()
    d["iso3"] = d["iso3"].astype(str).str.upper()
    d["scenario"] = d["scenario"].astype(str).str.lower()
    d["statistic"] = d["statistic"].astype(str).str.lower()
    d["hazard"] = d["hazard"].astype(str).str.lower()
    for col in ["threshold_days","population_total","population_exposed","exposed_share_pct","population_year"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    return d


def _inject_css() -> None:
    st.markdown("""
<style>
.exp-shell{border:1px solid rgba(121,181,207,.14);border-radius:18px;padding:16px 16px 10px;
background:linear-gradient(145deg,rgba(8,27,42,.97),rgba(4,16,26,.98));box-shadow:0 18px 45px rgba(0,0,0,.18)}
.exp-eyebrow{color:#55dff0;font-size:.68rem;font-weight:850;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.25rem}
.exp-title{color:#f6fbff;font-size:1.45rem;font-weight:900;letter-spacing:-.025em}
.exp-sub{color:#8fa7b8;font-size:.78rem;line-height:1.45;margin-top:.25rem}
.exp-kpi{height:100%;border:1px solid rgba(121,181,207,.14);border-radius:15px;padding:13px 14px;
background:linear-gradient(145deg,rgba(10,31,47,.96),rgba(6,20,31,.96))}
.exp-kpi-label{color:#819aaa;text-transform:uppercase;font-size:.63rem;font-weight:850;letter-spacing:.08em}
.exp-kpi-value{color:white;font-size:1.55rem;font-weight:900;line-height:1.05;margin-top:.3rem}
.exp-kpi-note{color:#819aaa;font-size:.68rem;line-height:1.35;margin-top:.25rem}
.exp-rail-row{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;
padding:8px 2px;border-bottom:1px solid rgba(121,181,207,.08)}
.exp-rank{color:#6fdfea;font-size:.7rem;font-weight:900}
.exp-country{color:#edf8fc;font-size:.76rem;font-weight:800}
.exp-value{color:#9eb3c1;font-size:.72rem}
.exp-note{border:1px solid rgba(121,181,207,.12);border-radius:12px;padding:10px 12px;
background:rgba(3,13,21,.48);color:#8299a8;font-size:.7rem;line-height:1.5}
.exp-pill{display:inline-flex;padding:5px 8px;border-radius:999px;margin-right:5px;border:1px solid rgba(47,225,242,.18);
background:rgba(47,225,242,.07);color:#7ce9f4;font-size:.66rem;font-weight:800}
</style>
""", unsafe_allow_html=True)


def _layout(fig, height=390, ytitle=None, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=10,r=10,t=44,b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(5,17,27,.60)",
        font=dict(color="#cfe0e9",family="Inter, sans-serif"),
        hoverlabel=dict(bgcolor="#0b1d2b"),
        legend=dict(orientation="h",y=1.08,x=0), showlegend=legend,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color="#7890a2")
    fig.update_yaxes(gridcolor="rgba(121,181,207,.10)", zeroline=False, color="#7890a2", title=ytitle)
    return fig


def _human(v):
    if v is None or not math.isfinite(float(v)):
        return "—"
    v=float(v)
    if abs(v)>=1_000_000_000: return f"{v/1_000_000_000:.2f}B"
    if abs(v)>=1_000_000: return f"{v/1_000_000:.2f}M"
    if abs(v)>=1_000: return f"{v/1_000:.1f}k"
    return f"{v:,.0f}"


def _kpi(label, value, note, accent):
    st.markdown(f"""
<div class="exp-kpi" style="border-top:2px solid {accent}">
  <div class="exp-kpi-label">{label}</div>
  <div class="exp-kpi-value">{value}</div>
  <div class="exp-kpi-note">{note}</div>
</div>""", unsafe_allow_html=True)


def _current_row(d, iso3, scenario, period, stat, hazard, threshold):
    q=d[
        d["iso3"].eq(iso3)&d["scenario"].eq(scenario)&d["period"].eq(period)&
        d["statistic"].eq(stat)&d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
    ]
    return None if q.empty else q.iloc[0]


def _country_name(d, iso3):
    q=d.loc[d["iso3"].eq(iso3),"country"]
    return iso3 if q.empty else str(q.iloc[0])


def render_population_exposure_v7(*, iso3: str, country: str, scenario: str, period: str, statistic: str) -> None:
    _inject_css()
    d=_load_exposure()

    iso3=iso3.upper()
    if iso3 not in set(d["iso3"]):
        iso3="ITA" if "ITA" in set(d["iso3"]) else str(d["iso3"].iloc[0])
        country=_country_name(d,iso3)

    st.markdown("""
<div class="exp-shell">
  <div class="exp-eyebrow">Population Exposure Explorer</div>
  <div class="exp-title">How many people live inside future climate hazards?</div>
  <div class="exp-sub">
    Explore population exposed to extreme-heat frequency thresholds across scenarios, future periods and ensemble percentiles.
    Every value is precomputed from the common 0.25° climate–population grid before country aggregation.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    c1,c2,c3,c4,c5=st.columns([1.55,1.25,1.0,.9,1.2],gap="small")

    catalog=d[["iso3","country"]].drop_duplicates().sort_values(["country","iso3"]).reset_index(drop=True)
    labels=[f"{r.country} · {r.iso3}" for r in catalog.itertuples(index=False)]
    label_to_iso={f"{r.country} · {r.iso3}":r.iso3 for r in catalog.itertuples(index=False)}
    default_label=next((x for x in labels if x.endswith(f"· {iso3}")),labels[0])

    with c1:
        selected_label=st.selectbox("Country / territory",labels,index=labels.index(default_label),key="exp_v7_country")
        iso3=label_to_iso[selected_label]
        country=_country_name(d,iso3)

    with c2:
        scenario=st.selectbox("Scenario",list(SCENARIO_LABELS),
            index=list(SCENARIO_LABELS).index(scenario) if scenario in SCENARIO_LABELS else 1,
            format_func=lambda x:SCENARIO_LABELS[x],key="exp_v7_scenario")
    with c3:
        period=st.selectbox("Period",PERIODS,index=PERIODS.index(period) if period in PERIODS else 1,key="exp_v7_period")
    with c4:
        statistic=st.selectbox("Statistic",list(STAT_LABELS),
            index=list(STAT_LABELS).index(statistic) if statistic in STAT_LABELS else 1,
            format_func=lambda x:STAT_LABELS[x],key="exp_v7_stat")
    with c5:
        hazard=st.segmented_control("Hazard",["hd30","hd35"],default="hd30",
            format_func=lambda x:HAZARD_LABELS[x],key="exp_v7_hazard") or "hd30"

    threshold_options=sorted(d.loc[d["hazard"].eq(hazard),"threshold_days"].dropna().unique().tolist())
    default_threshold=60 if hazard=="hd30" else 10
    if default_threshold not in threshold_options:
        default_threshold=threshold_options[len(threshold_options)//2]

    threshold=st.select_slider(
        "Exposure threshold · minimum number of hazard days per year",
        options=threshold_options,value=default_threshold,key="exp_v7_threshold"
    )

    row=_current_row(d,iso3,scenario,period,statistic,hazard,threshold)
    if row is None:
        st.warning("No exposure record exists for the current selection.")
        return

    near=_current_row(d,iso3,scenario,"2020-2039",statistic,hazard,threshold)
    delta_pp=None if near is None else float(row["exposed_share_pct"])-float(near["exposed_share_pct"])

    k1,k2,k3,k4=st.columns(4,gap="small")
    with k1:_kpi("People exposed",_human(row["population_exposed"]),f"{HAZARD_LABELS[hazard]} · ≥ {threshold:g} days/year",ORANGE)
    with k2:_kpi("Share exposed",f"{float(row['exposed_share_pct']):.1f}%","of projected population",RED)
    with k3:_kpi("Change vs 2020–2039","—" if delta_pp is None else f"{delta_pp:+.1f} pp","percentage-point change",PURPLE)
    with k4:_kpi("Projected population",_human(row["population_total"]),f"population year {int(row['population_year'])}",CYAN)

    st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)

    map_col,rail_col=st.columns([1.72,.68],gap="medium")

    with map_col:
        map_mode=st.segmented_control("Map layer",["Exposure share","People exposed","Projected population"],
            default="Exposure share",key="exp_v7_map_mode") or "Exposure share"
        world=d[
            d["scenario"].eq(scenario)&d["period"].eq(period)&d["statistic"].eq(statistic)&
            d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
        ].copy()

        if map_mode=="Exposure share":
            z=world["exposed_share_pct"]; title="Exposed %"; colorscale="YlOrRd"; zmin,zmax=0,100
            hover="<b>%{text}</b><br>%{z:.1f}% exposed<extra></extra>"
        elif map_mode=="People exposed":
            z=world["population_exposed"]; title="People"; colorscale="Turbo"; zmin,zmax=None,None
            hover="<b>%{text}</b><br>%{z:,.0f} people exposed<extra></extra>"
        else:
            z=world["population_total"]; title="Population"; colorscale="Viridis"; zmin,zmax=None,None
            hover="<b>%{text}</b><br>%{z:,.0f} projected population<extra></extra>"

        fig=go.Figure(go.Choropleth(
            locations=world["iso3"],z=z,text=world["country"],locationmode="ISO-3",
            colorscale=colorscale,zmin=zmin,zmax=zmax,
            marker_line_color="rgba(255,255,255,.12)",marker_line_width=.25,
            colorbar=dict(title=title,thickness=12,len=.72),hovertemplate=hover
        ))
        selected=world[world["iso3"].eq(iso3)]
        if not selected.empty:
            fig.add_trace(go.Choropleth(
                locations=selected["iso3"],z=[1],text=selected["country"],locationmode="ISO-3",
                colorscale=[[0,"rgba(255,255,255,0)"],[1,"rgba(255,255,255,.01)"]],
                showscale=False,marker_line_color="#ffffff",marker_line_width=2,hoverinfo="skip"
            ))
        fig.update_geos(projection_type="natural earth",showframe=False,showcoastlines=False,
            bgcolor="rgba(0,0,0,0)",landcolor="#0b1d2b")
        fig.update_layout(title=f"{map_mode} · {HAZARD_LABELS[hazard]} ≥ {threshold:g} days/year · {period}")
        st.plotly_chart(_layout(fig,500,None,False),width="stretch",config={"displayModeBar":False})

    with rail_col:
        ranking_mode=st.radio("Hotspot ranking",["Exposed population","Exposed share","Increase vs near term"],key="exp_v7_ranking")
        if ranking_mode=="Exposed population":
            rank=world.nlargest(10,"population_exposed"); values=[_human(v) for v in rank["population_exposed"]]
        elif ranking_mode=="Exposed share":
            rank=world.nlargest(10,"exposed_share_pct"); values=[f"{v:.1f}%" for v in rank["exposed_share_pct"]]
        else:
            near_world=d[
                d["scenario"].eq(scenario)&d["period"].eq("2020-2039")&
                d["statistic"].eq(statistic)&d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
            ][["iso3","exposed_share_pct"]].rename(columns={"exposed_share_pct":"near_share"})
            rank=world.merge(near_world,on="iso3",how="left")
            rank["increase_pp"]=rank["exposed_share_pct"]-rank["near_share"]
            rank=rank.nlargest(10,"increase_pp"); values=[f"{v:+.1f} pp" for v in rank["increase_pp"]]

        st.markdown('<div class="exp-eyebrow">Global hotspots</div>',unsafe_allow_html=True)
        for i,(r,val) in enumerate(zip(rank.itertuples(index=False),values),start=1):
            st.markdown(f"""<div class="exp-rail-row"><div class="exp-rank">{i:02d}</div>
<div class="exp-country">{r.country}</div><div class="exp-value">{val}</div></div>""",unsafe_allow_html=True)

    left,right=st.columns([1.35,.65],gap="medium")

    with left:
        curve_mode=st.segmented_control("Curve mode",["Selected scenario","Compare scenarios"],
            default="Selected scenario",key="exp_v7_curve_mode") or "Selected scenario"
        fig=go.Figure()
        if curve_mode=="Selected scenario":
            curve=d[
                d["iso3"].eq(iso3)&d["scenario"].eq(scenario)&d["period"].eq(period)&
                d["statistic"].eq(statistic)&d["hazard"].eq(hazard)
            ].sort_values("threshold_days")
            fig.add_trace(go.Scatter(x=curve["threshold_days"],y=curve["exposed_share_pct"],mode="lines+markers",
                line=dict(color=CYAN,width=3),marker=dict(size=7),fill="tozeroy",fillcolor="rgba(47,225,242,.08)",
                name=SCENARIO_LABELS[scenario],hovertemplate="≥ %{x:.0f} days/year<br>%{y:.1f}% exposed<extra></extra>"))
        else:
            colors={"ssp126":GREEN,"ssp245":CYAN,"ssp370":ORANGE,"ssp585":RED}
            for sc in SCENARIO_LABELS:
                curve=d[
                    d["iso3"].eq(iso3)&d["scenario"].eq(sc)&d["period"].eq(period)&
                    d["statistic"].eq(statistic)&d["hazard"].eq(hazard)
                ].sort_values("threshold_days")
                fig.add_trace(go.Scatter(x=curve["threshold_days"],y=curve["exposed_share_pct"],mode="lines+markers",
                    line=dict(color=colors[sc],width=2.3),marker=dict(size=6),
                    name=SCENARIO_LABELS[sc].split(" · ")[0],
                    hovertemplate="≥ %{x:.0f} days/year<br>%{y:.1f}% exposed<extra></extra>"))
        fig.add_vline(x=threshold,line_dash="dot",line_color=YELLOW,annotation_text=f"Selected: {threshold:g}",annotation_position="top")
        fig.update_layout(title=f"Exposure curve · {country}")
        st.plotly_chart(_layout(fig,390,"Population exposed (%)"),width="stretch",config={"displayModeBar":False})

    with right:
        exposed=float(row["population_exposed"]); total=float(row["population_total"]); unexposed=max(total-exposed,0.0)
        fig=go.Figure(go.Pie(values=[exposed,unexposed],labels=["Exposed","Not exposed"],hole=.72,
            marker=dict(colors=[RED,"rgba(121,181,207,.14)"]),textinfo="none",
            hovertemplate="%{label}<br>%{value:,.0f}<extra></extra>"))
        fig.add_annotation(text=f"<b>{float(row['exposed_share_pct']):.1f}%</b><br><span style='font-size:12px'>{_human(exposed)} exposed</span>",
            x=.5,y=.5,showarrow=False,font=dict(size=20,color="#ffffff"))
        fig.update_layout(title="Population exposure ring")
        st.plotly_chart(_layout(fig,390,None,False),width="stretch",config={"displayModeBar":False})

    st.markdown("#### Exposure through the century")
    timeline=d[
        d["iso3"].eq(iso3)&d["scenario"].eq(scenario)&d["statistic"].eq(statistic)&
        d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
    ].copy()
    order={p:i for i,p in enumerate(PERIODS)}
    timeline["_order"]=timeline["period"].map(order)
    timeline=timeline.sort_values("_order")
    fig=go.Figure(go.Bar(
        x=timeline["period"],y=timeline["exposed_share_pct"],
        marker=dict(color=timeline["exposed_share_pct"],colorscale="YlOrRd",cmin=0,cmax=100),
        text=[f"{s:.1f}%<br>{_human(p)}" for s,p in zip(timeline["exposed_share_pct"],timeline["population_exposed"])],
        textposition="outside"
    ))
    fig.update_layout(title=f"{SCENARIO_LABELS[scenario]} · {HAZARD_LABELS[hazard]} ≥ {threshold:g} days/year")
    st.plotly_chart(_layout(fig,330,"Population exposed (%)",False),width="stretch",config={"displayModeBar":False})

    st.markdown("#### Scenario divergence")
    low=_current_row(d,iso3,"ssp126",period,statistic,hazard,threshold)
    high=_current_row(d,iso3,"ssp585",period,statistic,hazard,threshold)

    d1,d2=st.columns([.72,1.28],gap="medium")
    with d1:
        if low is not None and high is not None:
            diff_people=float(high["population_exposed"])-float(low["population_exposed"])
            diff_share=float(high["exposed_share_pct"])-float(low["exposed_share_pct"])
            _kpi("SSP5-8.5 minus SSP1-2.6",_human(diff_people),f"{diff_share:+.1f} percentage points exposed · {period}",PURPLE)

    with d2:
        low_world=d[
            d["scenario"].eq("ssp126")&d["period"].eq(period)&d["statistic"].eq(statistic)&
            d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
        ][["iso3","country","exposed_share_pct"]].rename(columns={"exposed_share_pct":"low"})
        high_world=d[
            d["scenario"].eq("ssp585")&d["period"].eq(period)&d["statistic"].eq(statistic)&
            d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
        ][["iso3","exposed_share_pct"]].rename(columns={"exposed_share_pct":"high"})
        divergence=low_world.merge(high_world,on="iso3",how="inner")
        divergence["delta"]=divergence["high"]-divergence["low"]
        fig=go.Figure(go.Choropleth(
            locations=divergence["iso3"],z=divergence["delta"],text=divergence["country"],locationmode="ISO-3",
            colorscale="RdPu",marker_line_color="rgba(255,255,255,.12)",marker_line_width=.25,
            colorbar=dict(title="Δ exposed pp",thickness=12),
            hovertemplate="<b>%{text}</b><br>%{z:+.1f} pp<extra></extra>"
        ))
        fig.update_geos(projection_type="natural earth",showframe=False,showcoastlines=False,
            bgcolor="rgba(0,0,0,0)",landcolor="#0b1d2b")
        fig.update_layout(title="Global exposure difference · SSP5-8.5 − SSP1-2.6")
        st.plotly_chart(_layout(fig,390,None,False),width="stretch",config={"displayModeBar":False})

    st.markdown("#### Explore further")
    b1,b2,b3=st.columns(3,gap="small")
    with b1:
        current_slice=d[
            d["scenario"].eq(scenario)&d["period"].eq(period)&d["statistic"].eq(statistic)&
            d["hazard"].eq(hazard)&d["threshold_days"].eq(threshold)
        ].copy()
        st.download_button("Download current exposure layer",
            data=current_slice.to_csv(index=False).encode("utf-8"),
            file_name=f"orbidense_exposure_{scenario}_{period}_{statistic}_{hazard}_{int(threshold)}.csv",
            mime="text/csv",width="stretch")
    with b2:
        if st.button("Explain this view with ORBIDENSE",width="stretch"):
            st.session_state["orbidense_ai_context_hint"]={
                "section":"Population Exposure","country":country,"iso3":iso3,
                "scenario":scenario,"period":period,"statistic":statistic,
                "hazard":hazard,"threshold_days":float(threshold),
                "population_total":float(row["population_total"]),
                "population_exposed":float(row["population_exposed"]),
                "exposed_share_pct":float(row["exposed_share_pct"]),
            }
            st.success("Exposure context prepared for ORBIDENSE.")
    with b3:
        st.markdown("""<div class="exp-note"><b style="color:#fff">Validated production layer</b><br>
129,360 rows · 245 entities · 0 duplicate keys · 245/245 coverage</div>""",unsafe_allow_html=True)

    with st.expander("Methodology & interpretation"):
        st.markdown(f"""
**Population exposure definition**

For the selected hazard and threshold, a grid cell is classified as exposed when its projected annual
hazard frequency is at least the selected number of days. Population in qualifying cells is summed
before country aggregation.

- Country: **{country} ({iso3})**
- Scenario: **{SCENARIO_LABELS[scenario]}**
- Period: **{period}**
- Ensemble statistic: **{STAT_LABELS[statistic]}**
- Hazard: **{HAZARD_LABELS[hazard]}**
- Threshold: **≥ {threshold:g} days/year**

World Bank CCKP `pop-x0.25` population projections are aligned to CCKP CMIP6 0.25° HD30/HD35 grids.
Small entities without a grid-cell centre use the validated fractional-overlap fallback. This is a
**population exposure** metric, not a full climate-risk score.
""")
