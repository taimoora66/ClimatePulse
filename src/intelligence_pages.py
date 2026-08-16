from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.exposure_action_pages import render_population_exposure_tab, render_climate_action_full

# ORBIDENSE V3 LOCAL CCKP HELPERS
# Self-contained on purpose: avoids coupling the visual layer to older/newer
# helper APIs in src.climate_projection_store.py.
from functools import lru_cache

SCENARIO_LABELS = {
    "ssp126": "SSP1–2.6 · Low emissions",
    "ssp245": "SSP2–4.5 · Intermediate",
    "ssp370": "SSP3–7.0 · High",
    "ssp585": "SSP5–8.5 · Very high",
}
PERIODS = ("2020-2039", "2040-2059", "2060-2079", "2080-2099")
STATS = ("p10", "median", "p90")


@lru_cache(maxsize=2)
def _read_cckp_file(path_string: str) -> pd.DataFrame:
    path = Path(path_string)
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    else:
        frame = pd.read_csv(path)

    required = {
        "iso3", "country", "indicator", "scenario", "period",
        "statistic", "value_type", "value", "unit"
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "CCKP production dataset is missing required columns: "
            + ", ".join(sorted(missing))
        )

    frame = frame.copy()
    frame["iso3"] = frame["iso3"].astype(str).str.upper().str.strip()
    frame["country"] = frame["country"].astype(str).str.strip()
    frame["indicator"] = frame["indicator"].astype(str).str.lower().str.strip()
    frame["scenario"] = frame["scenario"].astype(str).str.lower().str.strip()
    frame["period"] = frame["period"].astype(str).str.strip()
    frame["statistic"] = frame["statistic"].astype(str).str.lower().str.strip()
    frame["value_type"] = frame["value_type"].astype(str).str.lower().str.strip()
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame


def load_cckp():
    candidates = [
        Path("data/climate_intelligence/cckp_country_projections.parquet"),
        Path("data/climate_intelligence/cckp_country_projections.csv"),
    ]
    for path in candidates:
        if path.exists():
            return _read_cckp_file(str(path.resolve())), path
    raise FileNotFoundError(
        "Validated CCKP production dataset not found. Expected "
        "data/climate_intelligence/cckp_country_projections.parquet "
        "or CSV fallback."
    )


def country_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame[["iso3", "country"]]
        .drop_duplicates()
        .sort_values(["country", "iso3"])
        .reset_index(drop=True)
    )


def resolve_default_iso3(frame: pd.DataFrame, preferred_iso3=None) -> str:
    catalog = country_catalog(frame)
    available = set(catalog["iso3"])
    if preferred_iso3:
        code = str(preferred_iso3).upper().strip()
        if code in available:
            return code
    if "ITA" in available:
        return "ITA"
    return str(catalog.iloc[0]["iso3"])


def select_slice(
    frame: pd.DataFrame,
    *,
    iso3=None,
    indicator=None,
    scenario=None,
    period=None,
    statistic=None,
    value_type=None,
) -> pd.DataFrame:
    out = frame
    if iso3 is not None:
        codes = [iso3] if isinstance(iso3, str) else list(iso3)
        codes = [str(x).upper() for x in codes]
        out = out[out["iso3"].isin(codes)]
    if indicator is not None:
        out = out[out["indicator"].eq(str(indicator).lower())]
    if scenario is not None:
        out = out[out["scenario"].eq(str(scenario).lower())]
    if period is not None:
        out = out[out["period"].eq(str(period))]
    if statistic is not None:
        out = out[out["statistic"].eq(str(statistic).lower())]
    if value_type is not None:
        out = out[out["value_type"].eq(str(value_type).lower())]
    return out.copy()


def triplet(
    frame: pd.DataFrame,
    *,
    iso3: str,
    indicator: str,
    scenario: str,
    period: str,
    value_type: str,
):
    subset = select_slice(
        frame,
        iso3=iso3,
        indicator=indicator,
        scenario=scenario,
        period=period,
        value_type=value_type,
    )
    result = {"p10": None, "median": None, "p90": None}
    for stat in result:
        values = subset.loc[subset["statistic"].eq(stat), "value"]
        if not values.empty:
            result[stat] = float(values.iloc[0])
    return result


def trajectory(
    frame: pd.DataFrame,
    *,
    iso3: str,
    indicator: str,
    scenario: str,
    value_type: str,
) -> pd.DataFrame:
    subset = select_slice(
        frame,
        iso3=iso3,
        indicator=indicator,
        scenario=scenario,
        value_type=value_type,
    )
    if subset.empty:
        return pd.DataFrame(columns=["period", "p10", "median", "p90"])

    pivot = (
        subset.pivot_table(
            index="period",
            columns="statistic",
            values="value",
            aggfunc="first",
        )
        .reset_index()
    )
    order = {p: i for i, p in enumerate(PERIODS)}
    pivot["_order"] = pivot["period"].map(order)
    return pivot.sort_values("_order").drop(columns="_order")


# Kept local so the visual layer is compatible with the existing
# production climate_projection_store.py.
SCENARIO_LABELS = {
    "ssp126": "SSP1–2.6 · Low emissions",
    "ssp245": "SSP2–4.5 · Intermediate",
    "ssp370": "SSP3–7.0 · High",
    "ssp585": "SSP5–8.5 · Very high",
}
PERIODS = ("2020-2039", "2040-2059", "2060-2079", "2080-2099")
STATS = ("p10", "median", "p90")

BG = "#04101a"
TEXT = "#F5FBFF"
CYAN = "#2FE1F2"
BLUE = "#49A8FF"
GREEN = "#59D88C"
YELLOW = "#F4C64C"
ORANGE = "#FF9C4A"
RED = "#FF5D62"
PURPLE = "#A77BFF"


def inject_intelligence_theme() -> None:
    st.markdown(
        '''
<style>
[data-testid="stAppViewContainer"]{background:
radial-gradient(circle at 80% 8%,rgba(23,87,111,.13),transparent 31%),
linear-gradient(180deg,#04101a 0%,#030b13 100%);}
.orb-kicker{font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#55dff0;font-size:.7rem}
.orb-h1{font-size:2.05rem;line-height:1.04;font-weight:900;color:#f7fbff;letter-spacing:-.03em;margin:.35rem 0 .4rem}
.orb-sub{color:#91a8b8;font-size:.92rem;line-height:1.5;max-width:980px}
.orb-section-title{font-size:1.05rem;font-weight:850;color:#eef8fc;margin:.2rem 0 .6rem}
.orb-card{background:linear-gradient(145deg,rgba(11,33,50,.97),rgba(6,21,33,.97));
border:1px solid rgba(121,181,207,.16);border-radius:16px;padding:15px 16px;
box-shadow:0 16px 36px rgba(0,0,0,.16);height:100%;}
.orb-card small{display:block;color:#819aaa;text-transform:uppercase;letter-spacing:.08em;font-weight:800;font-size:.68rem}
.orb-big{font-size:1.8rem;line-height:1.05;font-weight:900;color:#fff;margin:.35rem 0}
.orb-note{font-size:.72rem;color:#8299a8;line-height:1.4}
.orb-live{display:inline-flex;align-items:center;gap:6px;padding:5px 9px;border-radius:999px;
border:1px solid rgba(89,216,140,.2);background:rgba(89,216,140,.08);color:#78e4a7;font-size:.69rem;font-weight:800}
.orb-dot{width:7px;height:7px;border-radius:50%;background:#59d88c;box-shadow:0 0 12px rgba(89,216,140,.7)}
.orb-hero{border:1px solid rgba(121,181,207,.16);border-radius:18px;padding:18px;
background:linear-gradient(145deg,rgba(10,31,47,.98),rgba(4,16,26,.98));box-shadow:0 20px 55px rgba(0,0,0,.18)}
.orb-source{margin-top:.6rem;padding:10px 12px;border:1px solid rgba(121,181,207,.12);border-radius:12px;
color:#819aaa;background:rgba(3,13,21,.56);font-size:.71rem;line-height:1.45}
.orb-table-head{display:grid;grid-template-columns:1.3fr repeat(4,1fr);gap:8px;color:#7e96a7;font-size:.67rem;
font-weight:800;text-transform:uppercase;letter-spacing:.06em;padding:8px 10px}
.orb-table-row{display:grid;grid-template-columns:1.3fr repeat(4,1fr);gap:8px;align-items:center;padding:10px;
border-top:1px solid rgba(121,181,207,.09);color:#e9f3f8;font-size:.78rem}
.orb-passport-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.orb-passport-panel{border:1px solid rgba(121,181,207,.14);border-radius:14px;padding:14px;
background:linear-gradient(145deg,rgba(11,33,50,.97),rgba(7,22,34,.97))}
.orb-creator{border:1px solid rgba(47,225,242,.17);border-radius:16px;padding:18px;
background:linear-gradient(140deg,rgba(13,42,58,.95),rgba(6,18,29,.97))}
.orb-creator-name{font-size:1.25rem;font-weight:900;color:#fff}
.orb-creator-role{color:#70dfee;font-size:.78rem;font-weight:800;margin-top:3px}
@media(max-width:900px){
.orb-h1{font-size:1.6rem}.orb-table-head,.orb-table-row{grid-template-columns:1.2fr 1fr 1fr}
.orb-table-head>:nth-child(n+4),.orb-table-row>:nth-child(n+4){display:none}.orb-passport-grid{grid-template-columns:1fr}}
</style>
        ''',
        unsafe_allow_html=True,
    )


def _header(kicker, title, sub, live=False):
    live_html = '<span class="orb-live"><span class="orb-dot"></span> LIVE</span>' if live else ""
    st.markdown(
        f'''<div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:14px">
        <div><div class="orb-kicker">{kicker}</div><div class="orb-h1">{title}</div><div class="orb-sub">{sub}</div></div>
        <div>{live_html}</div></div>''',
        unsafe_allow_html=True,
    )


def _fmt(v, unit, signed=False):
    if v is None:
        return "—"
    try:
        v=float(v)
        if not math.isfinite(v): return "—"
    except Exception:
        return "—"
    pre="+" if signed and v>0 else ""
    if unit=="degC": return f"{pre}{v:.2f}°C"
    if unit=="days": return f"{v:.1f} days"
    if unit=="mm": return f"{pre}{v:,.0f} mm"
    if unit=="pct": return f"{pre}{v:.0f}%"
    return f"{pre}{v:,.1f}"


def _card(label, value, note="", accent=CYAN):
    st.markdown(
        f'''<div class="orb-card" style="border-top:2px solid {accent}">
        <small>{label}</small><div class="orb-big">{value}</div><div class="orb-note">{note}</div></div>''',
        unsafe_allow_html=True,
    )


def _layout(fig, height=390, ytitle=None, showlegend=True):
    fig.update_layout(
        height=height, margin=dict(l=12,r=12,t=42,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(5,17,27,.62)",
        font=dict(color="#cfe0e9",family="Inter, sans-serif"),
        hoverlabel=dict(bgcolor="#0b1d2b"),
        legend=dict(orientation="h",y=1.08,x=0),
        showlegend=showlegend,
    )
    fig.update_xaxes(showgrid=False,zeroline=False,color="#7890a2")
    fig.update_yaxes(gridcolor="rgba(121,181,207,.11)",zeroline=False,color="#7890a2",title=ytitle)
    return fig


def _country_select(frame, preferred, key):
    cat=country_catalog(frame)
    default=resolve_default_iso3(frame,preferred)
    labels=[f"{r.country} · {r.iso3}" for r in cat.itertuples(index=False)]
    mapping={f"{r.country} · {r.iso3}":r.iso3 for r in cat.itertuples(index=False)}
    default_label=next((x for x in labels if x.endswith(f"· {default}")),labels[0])
    label=st.selectbox("Country / territory",labels,index=labels.index(default_label),key=key)
    iso=mapping[label]
    name=cat.loc[cat.iso3.eq(iso),"country"].iloc[0]
    return iso,str(name)


def _map(frame, indicator, typ, scenario, period, stat, title, unit, selected_iso=None, height=430):
    x=select_slice(frame,indicator=indicator,value_type=typ,scenario=scenario,period=period,statistic=stat)
    fig=go.Figure()
    fig.add_trace(go.Choropleth(
        locations=x.iso3,z=x.value,text=x.country,locationmode="ISO-3",
        colorscale="Turbo" if indicator in {"tas","hd30","hd35"} else "BrBG",
        zmid=0 if typ=="anomaly" else None,
        marker_line_color="rgba(255,255,255,.14)",marker_line_width=.3,
        colorbar=dict(title=unit,thickness=12,len=.72),
        hovertemplate="<b>%{text}</b><br>%{z:.2f}<extra></extra>"
    ))
    if selected_iso:
        sel=x[x.iso3.eq(selected_iso)]
        if not sel.empty:
            fig.add_trace(go.Choropleth(
                locations=sel.iso3,z=[1]*len(sel),text=sel.country,locationmode="ISO-3",
                colorscale=[[0,"rgba(255,255,255,0)"],[1,"rgba(255,255,255,.01)"]],
                showscale=False,marker_line_color="#ffffff",marker_line_width=1.8,hoverinfo="skip"
            ))
    fig.update_geos(projection_type="natural earth",showframe=False,showcoastlines=False,
                    bgcolor="rgba(0,0,0,0)",landcolor="#0b1d2b")
    fig.update_layout(title=title)
    st.plotly_chart(_layout(fig,height=height,showlegend=False),width="stretch",config={"displayModeBar":False})


def render_climate_outlook(preferred_iso3=None):
    inject_intelligence_theme()
    _header("02 · CLIMATE OUTLOOK","What’s happening to the climate?",
            "Historical context, future pathways, extremes and uncertainty—organized around one selected country.")
    try:
        frame,source_path=load_cckp()
    except Exception as e:
        st.error(str(e)); return

    c1,c2,c3,c4=st.columns([1.6,1.15,1.05,.95],gap="small")
    with c1: iso,country=_country_select(frame,preferred_iso3,"v3_outlook_country")
    with c2: scenario=st.selectbox("Scenario",list(SCENARIO_LABELS),index=1,format_func=lambda x:SCENARIO_LABELS[x],key="v3_outlook_s")
    with c3: period=st.selectbox("Time period",PERIODS,index=1,key="v3_outlook_p")
    with c4: stat=st.selectbox("Statistic",STATS,index=1,format_func=lambda x:{"p10":"P10","median":"Median","p90":"P90"}[x],key="v3_outlook_stat")

    tabs=st.tabs(["Overview","Temperature","Precipitation","Extreme Heat","Population Exposure"])
    tab_over,tab_temp,tab_pr,tab_heat,tab_exposure=tabs

    with tab_over:
        left,right=st.columns([1.65,.85],gap="medium")
        with left:
            _map(frame,"tas","anomaly",scenario,period,stat,
                 f"Projected temperature change · {period} · {SCENARIO_LABELS[scenario]}","°C",iso,430)
        with right:
            t=triplet(frame,iso3=iso,indicator="tas",scenario=scenario,period=period,value_type="anomaly")
            h30=triplet(frame,iso3=iso,indicator="hd30",scenario=scenario,period=period,value_type="climatology")
            h35=triplet(frame,iso3=iso,indicator="hd35",scenario=scenario,period=period,value_type="climatology")
            pr=triplet(frame,iso3=iso,indicator="pr",scenario=scenario,period=period,value_type="anomaly")
            st.markdown(f"<div class='orb-section-title'>{country}</div>",unsafe_allow_html=True)
            _card("Projected temperature change",_fmt(t.get(stat),"degC",True),f"{period} · {SCENARIO_LABELS[scenario]}",RED)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            _card("Ensemble spread",f"{_fmt(t.get('p10'),'degC',True)} → {_fmt(t.get('p90'),'degC',True)}","P10 to P90 · not a confidence interval",CYAN)

        tr=trajectory(frame,iso3=iso,indicator="tas",scenario=scenario,value_type="anomaly")
        fig=go.Figure()
        if not tr.empty and {"p10","median","p90"}.issubset(tr.columns):
            fig.add_trace(go.Scatter(x=list(tr.period)+list(tr.period)[::-1],y=list(tr.p90)+list(tr.p10)[::-1],
                                     fill="toself",fillcolor="rgba(255,93,98,.13)",line=dict(color="rgba(0,0,0,0)"),
                                     name="P10–P90 spread",hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=tr.period,y=tr["median"],mode="lines+markers",
                                     line=dict(color=RED,width=3),marker=dict(size=7),name="Median"))
        for sc,color in [("ssp126",GREEN),("ssp245",CYAN),("ssp370",ORANGE),("ssp585",RED)]:
            med=trajectory(frame,iso3=iso,indicator="tas",scenario=sc,value_type="anomaly")
            if not med.empty and "median" in med.columns:
                fig.add_trace(go.Scatter(x=med.period,y=med["median"],mode="lines",
                                         line=dict(color=color,width=1.35,dash="dot"),opacity=.68,
                                         name=SCENARIO_LABELS[sc].split(" · ")[0]))
        fig.update_layout(title=f"Climate pathway · {country}")
        st.plotly_chart(_layout(fig,410,"Temperature change (°C)"),width="stretch",config={"displayModeBar":False})

        k1,k2,k3,k4=st.columns(4,gap="small")
        with k1:_card("Hot days >30°C",_fmt(h30.get(stat),"days"),"annual climatology",ORANGE)
        with k2:_card("Very hot days >35°C",_fmt(h35.get(stat),"days"),"annual climatology",RED)
        with k3:_card("Precipitation change",_fmt(pr.get(stat),"mm",True),"annual anomaly",BLUE)
        with k4:
            delta_end=select_slice(frame,iso3=iso,indicator="tas",value_type="anomaly",period="2080-2099",statistic="median")
            p=delta_end.pivot_table(index="iso3",columns="scenario",values="value",aggfunc="first")
            div=None
            if not p.empty and {"ssp126","ssp585"}.issubset(p.columns):
                div=float(p.iloc[0]["ssp585"]-p.iloc[0]["ssp126"])
            _card("Scenario divergence",_fmt(div,"degC",True),"SSP5-8.5 minus SSP1-2.6 · 2080–2099",PURPLE)

    with tab_temp:
        _map(frame,"tas","anomaly",scenario,period,stat,"Global projected temperature change","°C",iso,520)
    with tab_pr:
        _map(frame,"pr","anomaly",scenario,period,stat,"Global projected precipitation change","mm/year",iso,520)
    with tab_heat:
        a,b=st.columns(2,gap="medium")
        with a:_map(frame,"hd30","climatology",scenario,period,stat,"Hot days >30°C","days/year",iso,440)
        with b:_map(frame,"hd35","climatology",scenario,period,stat,"Very hot days >35°C","days/year",iso,440)
    with tab_exposure:
        render_population_exposure_tab(iso3=iso,country=country,scenario=scenario,period=period,statistic=stat)

    with st.expander("Method & sources ⓘ"):
        st.markdown(
            f"**World Bank CCKP / CMIP6** · `{source_path}`  \\n"
            "P10 / median / P90 are ensemble percentiles. Country aggregation is area-aware; "
            "microstates use the validated fractional-overlap fallback."
        )


def _load_action_data():
    candidates=[
        Path("data/climate_intelligence/climate_action_country.parquet"),
        Path("data/climate_intelligence/climate_action_country.csv"),
        Path("data/climate_intelligence/country_action.parquet"),
        Path("data/climate_intelligence/country_action.csv"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return (pd.read_parquet(p) if p.suffix==".parquet" else pd.read_csv(p)),p
            except Exception:
                pass
    return None,None


def render_climate_action(preferred_iso3=None):
    inject_intelligence_theme()
    _header("03 · CLIMATE ACTION","What is the country doing about it?",
            "Track emissions, targets, policy progress and sector transitions without hiding the implementation gap.")
    try:
        climate,_=load_cckp(); iso,country=_country_select(climate,preferred_iso3,"v3_action_country")
    except Exception:
        iso=preferred_iso3 or "ITA"; country=iso

    render_climate_action_full(iso3=iso, country=country)
    return
    action,path=_load_action_data()
    tabs=st.tabs(["Overview","Emissions","Targets","Sectors","Policy","Finance"])
    if action is None:
        with tabs[0]:
            st.markdown("<div class='orb-hero'><div class='orb-section-title'>Climate Action data pipeline is not installed yet</div>"
                        "<div class='orb-sub'>The final visual layout is ready for EDGAR historical/sector emissions, UNFCCC / Climate Watch targets, and Climate Action Tracker policy assessment. No illustrative target gaps or CAT ratings are shown as real data.</div></div>",unsafe_allow_html=True)
            a,b,c,d=st.columns(4,gap="small")
            with a:_card("Historical emissions","Waiting for source","EDGAR",CYAN)
            with b:_card("2030 target","Waiting for source","UNFCCC / Climate Watch",YELLOW)
            with c:_card("Current policies","Waiting for source","CAT",ORANGE)
            with d:_card("Policy gap","Waiting for source","derived after comparable accounting",RED)
        for t in tabs[1:]:
            with t:
                st.caption("This panel activates automatically once the normalized Climate Action dataset is installed.")
        return

    d=action.copy()
    d["iso3"]=d["iso3"].astype(str).str.upper()
    d=d[d.iso3.eq(iso)]
    if d.empty:
        with tabs[0]: st.info(f"No normalized Climate Action records available for {country} ({iso}).")
        return
    if not {"metric","value"}.issubset(d.columns):
        with tabs[0]: st.error(f"{path} must contain at least `metric` and `value`.")
        return
    d["value"]=pd.to_numeric(d["value"],errors="coerce")
    if "year" in d.columns: d["year"]=pd.to_numeric(d["year"],errors="coerce")
    def metric(name): return d[d.metric.eq(name)].dropna(subset=["value"]).copy()
    hist=metric("ghg_total"); policy=metric("current_policy"); target=metric("ndc_target")
    sectors=d[d.metric.str.startswith("sector_",na=False)].dropna(subset=["value"]).copy()
    cat=metric("cat_rating"); nz=metric("net_zero_year"); ren=metric("renewable_share")

    with tabs[0]:
        left,right=st.columns([1.6,.8],gap="medium")
        with left:
            fig=go.Figure()
            if not hist.empty and "year" in hist.columns:
                fig.add_trace(go.Scatter(x=hist.year,y=hist.value,mode="lines",line=dict(color="#DDE7EC",width=2),name="Historical"))
            if not policy.empty and "year" in policy.columns:
                fig.add_trace(go.Scatter(x=policy.year,y=policy.value,mode="lines+markers",line=dict(color=RED,width=2.5),name="Current policies"))
            if not target.empty and "year" in target.columns:
                fig.add_trace(go.Scatter(x=target.year,y=target.value,mode="lines+markers",line=dict(color=YELLOW,width=2.5,dash="dash"),name="NDC / target"))
            fig.update_layout(title=f"Emissions pathway · {country}")
            st.plotly_chart(_layout(fig,410,"MtCO₂e"),width="stretch",config={"displayModeBar":False})
        with right:
            latest=float(hist.sort_values("year").iloc[-1].value) if not hist.empty and "year" in hist.columns else None
            t2030=target[target.year.eq(2030)] if "year" in target.columns else pd.DataFrame()
            p2030=policy[policy.year.eq(2030)] if "year" in policy.columns else pd.DataFrame()
            tv=float(t2030.value.iloc[-1]) if not t2030.empty else None
            pv=float(p2030.value.iloc[-1]) if not p2030.empty else None
            gap=(pv-tv) if pv is not None and tv is not None else None
            _card("Latest emissions",_fmt(latest,""),"latest available",CYAN)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            _card("2030 target",_fmt(tv,""),"target accounting must match pathway",YELLOW)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            _card("Implementation gap",_fmt(gap,"",True),"current policies minus target",RED)
        a,b=st.columns([1.25,.75],gap="medium")
        with a:
            if not sectors.empty:
                s=sectors.groupby("metric",as_index=False)["value"].last().sort_values("value")
                fig=go.Figure(go.Bar(x=s.value,y=s.metric.str.replace("sector_","",regex=False).str.title(),
                                     orientation="h",marker=dict(color=[BLUE,CYAN,GREEN,YELLOW,ORANGE,RED][:len(s)])))
                fig.update_layout(title="Sector emissions / shares",showlegend=False)
                st.plotly_chart(_layout(fig,330),width="stretch",config={"displayModeBar":False})
            else: st.caption("Sector data not available for this country.")
        with b:
            _card("CAT assessment",str(cat.value.iloc[-1]) if not cat.empty else "—","independent assessment",RED)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            _card("Net-zero target",str(int(float(nz.value.iloc[-1]))) if not nz.empty else "—","reported target year",GREEN)
            st.markdown("<div style='height:8px'></div>",unsafe_allow_html=True)
            _card("Renewable share",_fmt(float(ren.value.iloc[-1]),"pct") if not ren.empty else "—","latest available",CYAN)
    for tab,name in zip(tabs[1:],["emission","target","sector","policy","finance"]):
        with tab:
            q=d[d.metric.str.contains(name,case=False,na=False)]
            st.dataframe(q,width="stretch",hide_index=True)


def render_compare(preferred_iso3=None):
    inject_intelligence_theme()
    _header("04 · COMPARE","Compare countries & places.",
            "One scenario, one time horizon and one statistic across every place—so the comparison stays scientifically fair.")
    try: frame,_=load_cckp()
    except Exception as e: st.error(str(e)); return
    cat=country_catalog(frame); allcodes=set(cat.iso3)
    preferred=resolve_default_iso3(frame,preferred_iso3)
    defaults=[preferred]+[x for x in ("FRA","DEU","ESP") if x in allcodes and x!=preferred]
    labels=[f"{r.country} · {r.iso3}" for r in cat.itertuples(index=False)]
    codefor={f"{r.country} · {r.iso3}":r.iso3 for r in cat.itertuples(index=False)}
    def label_for(c): return next((x for x in labels if x.endswith(f"· {c}")),labels[0])
    selected=st.multiselect("Locations · choose 2–4",labels,default=[label_for(x) for x in defaults[:4]],max_selections=4,key="v3_compare_locations")
    if len(selected)<2: st.info("Choose at least two locations."); return
    codes=[codefor[x] for x in selected]
    c1,c2,c3,c4=st.columns(4,gap="small")
    with c1: indicator=st.selectbox("Indicator",["Temperature Change","Hot Days >30°C","Very Hot Days >35°C","Precipitation Change"],key="v3_cmp_i")
    with c2: scenario=st.selectbox("Scenario",list(SCENARIO_LABELS),index=1,format_func=lambda x:SCENARIO_LABELS[x],key="v3_cmp_s")
    with c3: period=st.selectbox("Period",PERIODS,index=1,key="v3_cmp_p")
    with c4: stat=st.selectbox("Statistic",STATS,index=1,format_func=lambda x:x.upper() if x!="median" else "Median",key="v3_cmp_stat")
    mapping={
        "Temperature Change":("tas","anomaly","degC",True),
        "Hot Days >30°C":("hd30","climatology","days",False),
        "Very Hot Days >35°C":("hd35","climatology","days",False),
        "Precipitation Change":("pr","anomaly","mm",True),
    }
    ind,typ,unit,signed=mapping[indicator]
    x=select_slice(frame,iso3=codes,indicator=ind,value_type=typ,scenario=scenario,period=period,statistic=stat)
    order={c:i for i,c in enumerate(codes)}; x["_o"]=x.iso3.map(order); x=x.sort_values("_o")
    palette=[RED,BLUE,GREEN,YELLOW]
    fig=go.Figure(go.Bar(x=x.country,y=x.value,marker=dict(color=palette[:len(x)]),
                         text=[_fmt(v,unit,signed) for v in x.value],textposition="outside"))
    fig.update_layout(title=f"{indicator} · {period}",showlegend=False)
    st.plotly_chart(_layout(fig,365,indicator),width="stretch",config={"displayModeBar":False})
    metrics=[("Temperature","tas","anomaly","degC",True),
             ("Hot days >30°C","hd30","climatology","days",False),
             ("Hot days >35°C","hd35","climatology","days",False),
             ("Precipitation change","pr","anomaly","mm",True)]
    header="<div class='orb-table-head'><div>Indicator</div>"+''.join(f"<div>{cat.loc[cat.iso3.eq(c),'country'].iloc[0]}</div>" for c in codes)+"</div>"
    rows=[]
    for lab,ii,tt,uu,ss in metrics:
        cells=[]
        for c in codes:
            q=select_slice(frame,iso3=c,indicator=ii,value_type=tt,scenario=scenario,period=period,statistic=stat)
            cells.append(_fmt(float(q.value.iloc[0]) if not q.empty else None,uu,ss))
        rows.append("<div class='orb-table-row'><div style='font-weight:800'>"+lab+"</div>"+''.join(f"<div>{v}</div>" for v in cells)+"</div>")
    st.markdown(header+''.join(rows),unsafe_allow_html=True)
    st.markdown("#### Compare maps")
    mapcols=st.columns(len(codes),gap="small")
    for col,c in zip(mapcols,codes):
        with col:
            name=cat.loc[cat.iso3.eq(c),"country"].iloc[0]
            _map(frame,ind,typ,scenario,period,stat,name,unit,c,250)


def render_global_insights():
    inject_intelligence_theme()
    _header("05 · GLOBAL INSIGHTS","Global patterns, leaders & hotspots.",
            "Discover where climate indicators are largest, how futures diverge, and which patterns deserve deeper investigation.")
    try: frame,_=load_cckp()
    except Exception as e: st.error(str(e)); return
    c1,c2,c3,c4=st.columns(4,gap="small")
    with c1: indicator=st.selectbox("Indicator",["Projected warming","Hot days >30°C","Hot days >35°C","Precipitation change"],key="v3_gl_i")
    with c2: scenario=st.selectbox("Scenario",list(SCENARIO_LABELS),index=1,format_func=lambda x:SCENARIO_LABELS[x],key="v3_gl_s")
    with c3: period=st.selectbox("Period",PERIODS,index=1,key="v3_gl_p")
    with c4: stat=st.selectbox("Statistic",STATS,index=1,format_func=lambda x:x.upper() if x!="median" else "Median",key="v3_gl_st")
    meta={"Projected warming":("tas","anomaly","degC",True),
          "Hot days >30°C":("hd30","climatology","days",False),
          "Hot days >35°C":("hd35","climatology","days",False),
          "Precipitation change":("pr","anomaly","mm",True)}
    ind,typ,unit,signed=meta[indicator]
    left,right=st.columns([1.7,.75],gap="medium")
    with left:_map(frame,ind,typ,scenario,period,stat,f"{indicator} · {period}",unit,None,480)
    with right:
        x=select_slice(frame,indicator=ind,value_type=typ,scenario=scenario,period=period,statistic=stat).nlargest(10,"value")
        st.markdown("<div class='orb-section-title'>Top 10 countries</div>",unsafe_allow_html=True)
        for rank,row in enumerate(x.itertuples(index=False),1):
            st.markdown(f"<div class='orb-table-row' style='grid-template-columns:32px 1fr .7fr'><div>{rank:02d}</div><div><b>{row.country}</b></div><div>{_fmt(row.value,unit,signed)}</div></div>",unsafe_allow_html=True)
    a,b,c,d=st.columns(4,gap="small")
    full=select_slice(frame,indicator=ind,value_type=typ,scenario=scenario,period=period,statistic=stat)
    with a:
        r=full.nlargest(1,"value").iloc[0];_card("Highest selected value",str(r.country),_fmt(r.value,unit,signed),RED)
    with b:
        r=full.nsmallest(1,"value").iloc[0];_card("Lowest selected value",str(r.country),_fmt(r.value,unit,signed),BLUE)
    with c:
        if ind=="tas":
            e=select_slice(frame,indicator="tas",value_type="anomaly",period="2080-2099",statistic="median")
            p=e.pivot_table(index=["iso3","country"],columns="scenario",values="value",aggfunc="first").dropna()
            p["d"]=p["ssp585"]-p["ssp126"]; r=p.nlargest(1,"d").reset_index().iloc[0]
            _card("Largest scenario divergence",str(r.country),_fmt(r.d,"degC",True),PURPLE)
        else:_card("Scenario divergence","Temperature layer","available under Projected warming",PURPLE)
    with d:_card("Coverage","245 entities","validated production CCKP layer",GREEN)


def render_climate_passport(preferred_iso3=None):
    inject_intelligence_theme()
    _header("06 · CLIMATE PASSPORT","One-page country summary.",
            "A compact, share-ready profile of the most important climate facts—without replacing the full analytical pages.")
    try: frame,_=load_cckp()
    except Exception as e: st.error(str(e)); return
    c1,c2,c3=st.columns([1.7,1.2,1.05],gap="small")
    with c1: iso,country=_country_select(frame,preferred_iso3,"v3_passport_country")
    with c2: scenario=st.selectbox("Scenario",list(SCENARIO_LABELS),index=1,format_func=lambda x:SCENARIO_LABELS[x],key="v3_pass_s")
    with c3: period=st.selectbox("Period",PERIODS,index=1,key="v3_pass_p")
    def med(ind,typ):
        q=select_slice(frame,iso3=iso,indicator=ind,value_type=typ,scenario=scenario,period=period,statistic="median")
        return None if q.empty else float(q.value.iloc[0])
    t=med("tas","anomaly"); h30=med("hd30","climatology"); h35=med("hd35","climatology"); pr=med("pr","anomaly")
    st.markdown(f"<div class='orb-hero'><div class='orb-kicker'>{country} · {iso}</div><div class='orb-h1' style='font-size:1.65rem'>Climate Passport</div><div class='orb-sub'>{SCENARIO_LABELS[scenario]} · {period}</div></div>",unsafe_allow_html=True)
    a,b,c,d=st.columns(4,gap="small")
    with a:_card("Projected warming",_fmt(t,"degC",True),"median",RED)
    with b:_card("Hot days >30°C",_fmt(h30,"days"),"annual",ORANGE)
    with c:_card("Hot days >35°C",_fmt(h35,"days"),"annual",RED)
    with d:_card("Precipitation change",_fmt(pr,"mm",True),"annual anomaly",BLUE)
    st.markdown("<div class='orb-passport-grid' style='margin-top:12px'><div class='orb-passport-panel'><b style='color:#fff'>Climate Outlook</b><div class='orb-note' style='margin-top:8px'>Scenario-conditioned physical climate summary from the validated CCKP country projection layer.</div></div><div class='orb-passport-panel'><b style='color:#fff'>Climate Action</b><div class='orb-note' style='margin-top:8px'>Action metrics appear when normalized EDGAR / target / policy data are installed.</div></div></div>",unsafe_allow_html=True)


def render_about_science():
    inject_intelligence_theme()
    _header("07 · ABOUT","Science, methods & transparency.",
            "ORBIDENSE AI connects Earth data, climate projections, emissions evidence and policy intelligence while keeping provenance visible.")
    tabs=st.tabs(["Overview","Science & Methodology","Data Sources","Coverage","Limitations","References"])
    with tabs[0]:
        left,right=st.columns([1.3,.7],gap="medium")
        with left:
            st.markdown("### ORBIDENSE AI")
            st.write("An independent environmental and climate-data project built to turn complex Earth-system data into clear, comparable and scientifically traceable intelligence.")
            st.markdown("#### Integrated framework")
            st.markdown("**Live Earth → Climate Outlook → Climate Action → Compare → Global Insights**")
        with right:
            st.markdown('''<div class="orb-creator"><div class="orb-kicker">Project creator</div>
<div class="orb-creator-name">Taimoor Ahmad</div>
<div class="orb-creator-role">MSc · Environmental Change & Global Sustainability</div>
<div class="orb-note" style="margin-top:8px">University of Milan · Independent environmental and climate-data project</div></div>''',unsafe_allow_html=True)
        a,b,c,d=st.columns(4,gap="small")
        with a:_card("Coverage","245+","countries & territories",CYAN)
        with b:_card("Future pathways","4 SSPs","scenario-conditioned",PURPLE)
        with c:_card("Core climate indicators","4","tas · pr · HD30 · HD35",GREEN)
        with d:_card("Principle","Transparent","no fake composite score",YELLOW)
    with tabs[1]:
        st.markdown(
            "**Weather ≠ climate. Reanalysis ≠ projection. Hazard ≠ risk.**  \\n"
            "P10 / median / P90 are ensemble percentiles rather than confidence intervals. "
            "Future values are conditional on SSP pathways."
        )
    with tabs[2]:
        st.markdown(
            "**Current / operational:** Open-Meteo and configured live providers.  \\n"
            "**Historical:** ERA5 / CRU.  \\n"
            "**Future climate:** World Bank CCKP / CMIP6.  \\n"
            "**Action pipeline:** EDGAR, UNFCCC / Climate Watch, Climate Action Tracker.  \\n"
            "**Risk / exposure roadmap:** SSP population and INFORM."
        )
    with tabs[3]:
        st.markdown("The validated CCKP layer covers 245 country/territory entities, four scenarios, four future periods and P10/median/P90 ensemble statistics.")
    with tabs[4]:
        st.markdown(
            "- Country averages suppress subnational variability.\\n"
            "- Ensemble spread does not represent every uncertainty source.\\n"
            "- Live weather at a point is not a national climate average.\\n"
            "- Policy datasets update asynchronously and require source dates."
        )
    with tabs[5]:
        st.markdown("Production references are retained in dataset metadata and project documentation so charts can remain clean while methods stay inspectable.")
