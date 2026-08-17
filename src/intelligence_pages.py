from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.orbidense_theme import get_theme_tokens, inject_global_theme

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
        """
<style>
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(circle at 82% 7%,rgba(22,102,130,.11),transparent 28%),
    linear-gradient(180deg,#04101A 0%,#020A11 100%);
}

/* ---------- TYPOGRAPHIC HIERARCHY ---------- */
.orb-kicker{
  font-weight:900;letter-spacing:.15em;text-transform:uppercase;
  color:#56E8EF;font-size:.68rem
}
.orb-h1{
  font-size:clamp(1.75rem,2.7vw,2.35rem);
  line-height:1.03;font-weight:950;color:#F7FBFF;
  letter-spacing:-.035em;margin:.40rem 0 .46rem
}
.orb-sub{
  color:#9AB0BF;font-size:.91rem;line-height:1.55;
  max-width:980px
}
.orb-section-title{
  font-size:1.02rem;font-weight:900;color:#EEF8FC;
  margin:.2rem 0 .50rem
}
.orb-section-eyebrow{
  font-size:.64rem;font-weight:850;letter-spacing:.10em;
  text-transform:uppercase;color:#6E8A9C;margin-bottom:.2rem
}

/* ---------- CARDS ---------- */
.orb-card{
  position:relative;overflow:hidden;
  background:linear-gradient(145deg,rgba(10,31,48,.98),rgba(5,18,30,.99));
  border:1px solid rgba(121,181,207,.16);
  border-radius:16px;padding:15px 16px;
  box-shadow:0 14px 32px rgba(0,0,0,.14);height:100%
}
.orb-card small{
  display:block;color:#8DA6B6;text-transform:uppercase;
  letter-spacing:.09em;font-weight:850;font-size:.64rem
}
.orb-big{
  font-size:1.72rem;line-height:1.06;font-weight:950;
  color:#FFF;margin:.34rem 0
}
.orb-note{font-size:.70rem;color:#8198A8;line-height:1.42}
.orb-live{
  display:inline-flex;align-items:center;gap:6px;padding:5px 9px;
  border-radius:999px;border:1px solid rgba(89,216,140,.22);
  background:rgba(89,216,140,.08);color:#7DE4A9;
  font-size:.67rem;font-weight:850
}
.orb-dot{
  width:7px;height:7px;border-radius:50%;background:#59D88C;
  box-shadow:0 0 12px rgba(89,216,140,.7)
}

/* ---------- ANALYTICAL SUMMARY ---------- */
.orb-signal-grid{
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;margin:10px 0 15px
}
.orb-signal{
  min-height:108px;border-radius:15px;padding:14px 15px;
  background:linear-gradient(145deg,rgba(9,30,47,.98),rgba(4,17,28,.99));
  border:1px solid rgba(108,173,204,.15)
}
.orb-signal .label{
  color:#819BAC;font-size:.62rem;font-weight:900;letter-spacing:.10em;
  text-transform:uppercase
}
.orb-signal .value{
  color:#FFF;font-size:1.55rem;font-weight:950;line-height:1.06;
  margin:.38rem 0 .24rem
}
.orb-signal .context{color:#8299A9;font-size:.68rem;line-height:1.38}

.orb-story{
  border:1px solid rgba(47,225,242,.17);
  border-radius:16px;padding:16px 17px;
  background:
    linear-gradient(135deg,rgba(10,43,58,.94),rgba(5,20,31,.98));
}
.orb-story-title{
  font-size:.68rem;font-weight:900;letter-spacing:.10em;
  text-transform:uppercase;color:#50DFE9
}
.orb-story-copy{
  color:#D7E5EC;font-size:.84rem;line-height:1.56;margin-top:.45rem
}

/* ---------- COMPARISON MATRIX ---------- */
.orb-matrix{
  border:1px solid rgba(121,181,207,.14);
  border-radius:16px;overflow:hidden;
  background:rgba(4,16,26,.72)
}
.orb-table-head{
  display:grid;grid-template-columns:1.35fr repeat(4,1fr);
  gap:8px;color:#90A7B6;font-size:.64rem;font-weight:900;
  text-transform:uppercase;letter-spacing:.07em;padding:11px 12px;
  background:rgba(10,31,47,.86)
}
.orb-table-row{
  display:grid;grid-template-columns:1.35fr repeat(4,1fr);
  gap:8px;align-items:center;padding:11px 12px;
  border-top:1px solid rgba(121,181,207,.08);
  color:#EAF4F8;font-size:.76rem
}
.orb-matrix-cell{
  display:inline-flex;align-items:center;justify-content:center;
  min-height:31px;padding:4px 8px;border-radius:9px;
  background:rgba(21,53,72,.48);font-weight:760
}

/* ---------- RANKING ---------- */
.orb-rank-row{
  display:grid;grid-template-columns:30px minmax(0,1fr) auto;
  gap:9px;align-items:center;padding:9px 2px;
  border-bottom:1px solid rgba(121,181,207,.08)
}
.orb-rank-num{
  width:27px;height:27px;border-radius:8px;display:grid;place-items:center;
  background:rgba(54,130,239,.14);color:#BED8FF;font-size:.62rem;font-weight:900
}
.orb-rank-name{color:#EAF3F8;font-size:.72rem;font-weight:760}
.orb-rank-value{color:#FFBE76;font-size:.70rem;font-weight:900}

/* ---------- TABS / INPUTS ---------- */
/* ---------- OUTLOOK ANALYTICAL CONTROLS ---------- */
/* The former st.tabs navigation was too faint and, in this app shell,
   its active panels were intermittently rendering blank. V4.1 uses a
   segmented control and renders exactly one analytical section in normal
   page flow. */

.st-key-v41_outlook_section_main,
.st-key-v41_outlook_section_exposure{
  margin:.55rem 0 .85rem!important;
}

.st-key-v41_outlook_section_main [data-testid="stSegmentedControl"],
.st-key-v41_outlook_section_exposure [data-testid="stSegmentedControl"]{
  width:100%!important;
}

.st-key-v41_outlook_section_main button,
.st-key-v41_outlook_section_exposure button{
  min-height:44px!important;
  border:1px solid rgba(91,160,194,.22)!important;
  background:linear-gradient(180deg,rgba(10,32,49,.96),rgba(6,22,35,.98))!important;
  color:#BFD0DB!important;
  font-weight:820!important;
  font-size:.78rem!important;
  padding:.45rem .80rem!important;
  transition:all .15s ease!important;
}

.st-key-v41_outlook_section_main button:hover,
.st-key-v41_outlook_section_exposure button:hover{
  color:#F5FDFF!important;
  border-color:rgba(47,225,242,.55)!important;
  background:linear-gradient(180deg,rgba(15,54,70,.98),rgba(7,30,44,.98))!important;
}

.st-key-v41_outlook_section_main button[aria-pressed="true"],
.st-key-v41_outlook_section_exposure button[aria-pressed="true"]{
  color:#70FFF3!important;
  border-color:#32DFE8!important;
  background:linear-gradient(180deg,rgba(17,68,82,.98),rgba(8,36,50,.98))!important;
  box-shadow:inset 0 -3px 0 #2FE7EE,0 8px 22px rgba(30,218,231,.10)!important;
}

/* Make the four analytical selectors part of the dark interface instead
   of looking like white browser forms pasted on top of the dashboard. */
div[data-testid="stSelectbox"] label p{
  color:#91A9B8!important;
  font-size:.72rem!important;
  font-weight:780!important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"]>div{
  min-height:48px!important;
  background:linear-gradient(180deg,#0A2030 0%,#071925 100%)!important;
  border:1px solid rgba(90,159,192,.30)!important;
  border-radius:11px!important;
  color:#EAF4F8!important;
  box-shadow:0 8px 24px rgba(0,0,0,.08)!important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"]>div:hover{
  border-color:rgba(47,225,242,.55)!important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] span{
  color:#EAF4F8!important;
}
div[data-testid="stSelectbox"] svg{
  fill:#9EB5C3!important;
}

/* Visible analytical canvas around maps/charts. */
.orb-viz-shell{
  border:1px solid rgba(100,171,203,.16);
  border-radius:17px;
  padding:11px 12px 5px;
  background:linear-gradient(145deg,rgba(7,25,39,.88),rgba(3,14,23,.90));
  box-shadow:0 14px 34px rgba(0,0,0,.10);
  margin:.35rem 0 .75rem;
}
.orb-viz-heading{
  color:#EAF6FB;font-size:.98rem;font-weight:900;margin:.15rem 0 .15rem;
}
.orb-viz-sub{
  color:#819AA9;font-size:.70rem;line-height:1.45;margin-bottom:.25rem;
}

@media(max-width:850px){
  .st-key-v41_outlook_section_main button,
  .st-key-v41_outlook_section_exposure button{
    font-size:.70rem!important;
    padding:.35rem .42rem!important;
  }
}

/* ---------- LEGACY SUPPORT ---------- */
.orb-hero{
  border:1px solid rgba(121,181,207,.16);border-radius:18px;padding:18px;
  background:linear-gradient(145deg,rgba(10,31,47,.98),rgba(4,16,26,.98));
  box-shadow:0 20px 55px rgba(0,0,0,.18)
}
.orb-source{
  margin-top:.6rem;padding:10px 12px;border:1px solid rgba(121,181,207,.12);
  border-radius:12px;color:#819AAA;background:rgba(3,13,21,.56);
  font-size:.71rem;line-height:1.45
}
.orb-passport-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.orb-passport-panel{
  border:1px solid rgba(121,181,207,.14);border-radius:14px;padding:14px;
  background:linear-gradient(145deg,rgba(11,33,50,.97),rgba(7,22,34,.97))
}
.orb-creator{
  border:1px solid rgba(47,225,242,.17);border-radius:16px;padding:18px;
  background:linear-gradient(140deg,rgba(13,42,58,.95),rgba(6,18,29,.97))
}
.orb-creator-name{font-size:1.25rem;font-weight:900;color:#FFF}
.orb-creator-role{color:#70DFEE;font-size:.78rem;font-weight:800;margin-top:3px}

@media(max-width:1000px){
  .orb-signal-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .orb-table-head,.orb-table-row{grid-template-columns:1.2fr repeat(2,1fr)}
  .orb-table-head>:nth-child(n+4),.orb-table-row>:nth-child(n+4){display:none}
}
@media(max-width:700px){
  .orb-h1{font-size:1.65rem}
  .orb-signal-grid{grid-template-columns:1fr 1fr}
  .orb-passport-grid{grid-template-columns:1fr}
}
</style>
        """,
        unsafe_allow_html=True,
    )
    inject_global_theme()




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
    t = get_theme_tokens()

    fig.update_layout(
        height=height,
        margin=dict(l=26, r=20, t=62, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=t["chart_bg"],
        font=dict(color=t["text"], family="Inter, sans-serif", size=11),
        title=dict(
            font=dict(size=15, color=t["text"]),
            x=0.01,
            xanchor="left",
        ),
        hoverlabel=dict(
            bgcolor=t["surface_2"],
            bordercolor=t["border"],
            font=dict(color=t["text"], size=11),
        ),
        legend=dict(
            orientation="h",
            y=1.11,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=t["muted"], size=10),
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        showlegend=showlegend,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        color=t["chart_axis"],
        linecolor=t["border_soft"],
        tickfont=dict(size=10, color=t["chart_axis"]),
        ticks="outside",
        ticklen=4,
    )
    fig.update_yaxes(
        gridcolor=t["chart_grid"],
        gridwidth=1,
        zeroline=False,
        color=t["chart_axis"],
        title=ytitle,
        tickfont=dict(size=10, color=t["chart_axis"]),
        ticks="outside",
        ticklen=4,
    )
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


def _map(
    frame,
    indicator,
    value_type,
    scenario,
    period,
    statistic,
    title,
    unit,
    selected_iso=None,
    height=430,
):
    t = get_theme_tokens()

    data = select_slice(
        frame,
        indicator=indicator,
        value_type=value_type,
        scenario=scenario,
        period=period,
        statistic=statistic,
    ).copy()

    if data.empty:
        st.info("No map data are available for the selected climate layer.")
        return

    data = data.dropna(subset=["value"])
    if data.empty:
        st.info("The selected climate layer contains no valid values.")
        return

    # Scientific colour semantics remain stable across UI themes.
    if indicator == "tas":
        colorscale = [
            [0.00, "#2457D6"],
            [0.20, "#21A6F3"],
            [0.40, "#36D4C1"],
            [0.58, "#F0D95D"],
            [0.76, "#F99A3E"],
            [1.00, "#E74432"],
        ]
    elif indicator in {"hd30", "hd35"}:
        colorscale = [
            [0.00, "#16385F"],
            [0.25, "#2176B8"],
            [0.48, "#43C3C9"],
            [0.68, "#F3CE62"],
            [0.84, "#F18A38"],
            [1.00, "#E33D32"],
        ]
    elif indicator == "pr":
        colorscale = [
            [0.00, "#8C4E2F"],
            [0.18, "#C77C47"],
            [0.38, "#E9C89B"],
            [0.50, "#E8ECE7"],
            [0.62, "#A8D5C6"],
            [0.82, "#43A7A2"],
            [1.00, "#176B72"],
        ]
    else:
        colorscale = "Viridis"

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            locations=data["iso3"],
            z=data["value"],
            text=data["country"],
            locationmode="ISO-3",
            colorscale=colorscale,
            zmid=0 if value_type == "anomaly" else None,
            marker=dict(
                line=dict(
                    color="rgba(255,255,255,0.12)",
                    width=0.35,
                )
            ),
            colorbar=dict(
                title=dict(
                    text=unit,
                    font=dict(
                        color=t["muted"],
                        size=10,
                    ),
                ),
                thickness=10,
                len=0.62,
                outlinewidth=0,
                tickfont=dict(
                    color=t["muted"],
                    size=9,
                ),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>%{z:.2f} "
                + unit
                + "<extra></extra>"
            ),
        )
    )

    if selected_iso:
        selected = data[data["iso3"] == selected_iso]
        if not selected.empty:
            fig.add_trace(
                go.Choropleth(
                    locations=selected["iso3"],
                    z=[1] * len(selected),
                    text=selected["country"],
                    locationmode="ISO-3",
                    colorscale=[
                        [0.0, "rgba(255,255,255,0.00)"],
                        [1.0, "rgba(255,255,255,0.01)"],
                    ],
                    showscale=False,
                    marker=dict(
                        line=dict(
                            color="#FFFFFF" if t["mode"] == "dark" else "#102A3A",
                            width=2.2,
                        )
                    ),
                    hoverinfo="skip",
                )
            )

    fig.update_geos(
        projection_type="natural earth",
        showframe=False,
        showcoastlines=False,
        bgcolor="rgba(0,0,0,0)",
        landcolor=t["map_land"],
        lakecolor=t["map_water"],
        showlakes=False,
    )

    fig.update_layout(
        title=dict(
            text=title,
            x=0.01,
            xanchor="left",
            font=dict(
                size=14,
                color=t["text"],
            ),
        ),
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"]),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
            "responsive": True,
        },
    )






def render_climate_outlook(preferred_iso3=None):
    """
    Country climate intelligence.

    V4.1 intentionally avoids st.tabs for the analytical sub-pages. The
    production data were never removed: the Overview cards proved CCKP was
    loaded, while the other tab panels could appear blank in the current
    Streamlit/app-shell combination. A segmented control now selects one
    section and that section is rendered directly in normal page flow.
    """
    inject_intelligence_theme()
    _header(
        "02 · CLIMATE OUTLOOK",
        "What’s happening to the climate?",
        "A country-first view of warming, precipitation, heat extremes and uncertainty—then the global context behind it.",
    )

    try:
        frame, source_path = load_cckp()
    except Exception as e:
        st.error(str(e))
        return

    c1, c2, c3, c4 = st.columns([1.55, 1.16, 1.02, .90], gap="small")
    with c1:
        iso, country = _country_select(frame, preferred_iso3, "v41_outlook_country")
    with c2:
        scenario = st.selectbox(
            "Scenario",
            list(SCENARIO_LABELS),
            index=1,
            format_func=lambda x: SCENARIO_LABELS[x],
            key="v41_outlook_s",
        )
    with c3:
        period = st.selectbox("Time period", PERIODS, index=1, key="v41_outlook_p")
    with c4:
        stat = st.selectbox(
            "Statistic",
            STATS,
            index=1,
            format_func=lambda x: {"p10": "P10", "median": "Median", "p90": "P90"}[x],
            key="v41_outlook_stat",
        )

    options = [
        "Overview",
        "Temperature",
        "Precipitation",
        "Extreme Heat",
        "Population Exposure",
    ]

    exposure_target = (
        st.session_state.get("orbidense_outlook_target") == "Population Exposure"
    )
    default_section = "Population Exposure" if exposure_target else "Overview"

    # Separate widget identities mean the top-level Climate Outlook and
    # Population Exposure routes each remember a sensible local state without
    # modifying the working public router.
    section_key = (
        "v41_outlook_section_exposure"
        if exposure_target
        else "v41_outlook_section_main"
    )

    section = st.segmented_control(
        "Climate intelligence section",
        options,
        selection_mode="single",
        default=default_section,
        key=section_key,
        label_visibility="collapsed",
        width="stretch",
    ) or default_section

    # Shared metrics for Overview and contextual summaries.
    t = triplet(
        frame,
        iso3=iso,
        indicator="tas",
        scenario=scenario,
        period=period,
        value_type="anomaly",
    )
    h30 = triplet(
        frame,
        iso3=iso,
        indicator="hd30",
        scenario=scenario,
        period=period,
        value_type="climatology",
    )
    h35 = triplet(
        frame,
        iso3=iso,
        indicator="hd35",
        scenario=scenario,
        period=period,
        value_type="climatology",
    )
    pr = triplet(
        frame,
        iso3=iso,
        indicator="pr",
        scenario=scenario,
        period=period,
        value_type="anomaly",
    )

    if section == "Overview":
        layer = select_slice(
            frame,
            indicator="tas",
            value_type="anomaly",
            scenario=scenario,
            period=period,
            statistic=stat,
        ).dropna(subset=["value"])

        rank = None
        percentile = None
        if not layer.empty:
            ranked = layer.sort_values("value", ascending=False).reset_index(drop=True)
            match = ranked.index[ranked.iso3.eq(iso)].tolist()
            if match:
                rank = match[0] + 1
                percentile = 100 * (
                    1 - (rank - 1) / max(len(ranked) - 1, 1)
                )

        delta_end = select_slice(
            frame,
            iso3=iso,
            indicator="tas",
            value_type="anomaly",
            period="2080-2099",
            statistic="median",
        )
        pivot = delta_end.pivot_table(
            index="iso3",
            columns="scenario",
            values="value",
            aggfunc="first",
        )
        divergence = None
        if not pivot.empty and {"ssp126", "ssp585"}.issubset(pivot.columns):
            divergence = float(
                pivot.iloc[0]["ssp585"] - pivot.iloc[0]["ssp126"]
            )

        st.markdown(
            f"""
<div class="orb-section-eyebrow">{country} · {period} · {SCENARIO_LABELS[scenario]}</div>
<div class="orb-signal-grid">
  <div class="orb-signal">
    <div class="label">Projected warming</div>
    <div class="value">{_fmt(t.get(stat), "degC", True)}</div>
    <div class="context">{stat.upper() if stat != "median" else "Median"} temperature anomaly</div>
  </div>
  <div class="orb-signal">
    <div class="label">Hot days &gt;30°C</div>
    <div class="value">{_fmt(h30.get(stat), "days")}</div>
    <div class="context">Expected annual climatology</div>
  </div>
  <div class="orb-signal">
    <div class="label">Very hot days &gt;35°C</div>
    <div class="value">{_fmt(h35.get(stat), "days")}</div>
    <div class="context">Expected annual climatology</div>
  </div>
  <div class="orb-signal">
    <div class="label">Precipitation change</div>
    <div class="value">{_fmt(pr.get(stat), "mm", True)}</div>
    <div class="context">Annual anomaly</div>
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

        map_col, story_col = st.columns([1.55, .72], gap="medium")
        with map_col:
            st.markdown(
                """
<div class="orb-viz-shell">
  <div class="orb-viz-heading">Spatial context</div>
  <div class="orb-viz-sub">Selected country outlined in white; all countries use the same scenario, period and statistic.</div>
</div>
                """,
                unsafe_allow_html=True,
            )
            _map(
                frame, "tas", "anomaly", scenario, period, stat,
                f"Projected warming · {period}", "°C", iso, 400
            )

        with story_col:
            _card(
                "Ensemble spread",
                f"{_fmt(t.get('p10'),'degC',True)} → {_fmt(t.get('p90'),'degC',True)}",
                "P10 to P90 · ensemble range, not a confidence interval",
                CYAN,
            )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            _card(
                "Global warming position",
                f"#{rank}" if rank else "—",
                (
                    f"Approx. {percentile:.0f}th percentile of covered entities"
                    if percentile is not None
                    else "Comparable global layer"
                ),
                ORANGE,
            )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            _card(
                "Late-century divergence",
                _fmt(divergence, "degC", True),
                "SSP5-8.5 minus SSP1-2.6 · 2080–2099",
                PURPLE,
            )

        st.markdown(
            """
<div class="orb-viz-shell" style="margin-top:12px">
  <div class="orb-viz-heading">How the pathways diverge</div>
  <div class="orb-viz-sub">The selected scenario is emphasized. Other SSPs are muted context; the uncertainty ribbon applies only to the selected pathway.</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        selected_tr = trajectory(
            frame,
            iso3=iso,
            indicator="tas",
            scenario=scenario,
            value_type="anomaly",
        )

        fig = go.Figure()
        if (
            not selected_tr.empty
            and {"p10", "median", "p90"}.issubset(selected_tr.columns)
        ):
            fig.add_trace(
                go.Scatter(
                    x=list(selected_tr.period) + list(selected_tr.period)[::-1],
                    y=list(selected_tr.p90) + list(selected_tr.p10)[::-1],
                    fill="toself",
                    fillcolor="rgba(24,213,231,.16)",
                    line=dict(color="rgba(24,213,231,.18)", width=1),
                    name="Selected P10–P90",
                    hoverinfo="skip",
                )
            )

        scenario_colors = {
            "ssp126": "#2FBF71",
            "ssp245": "#18D5E7",
            "ssp370": "#F3A33C",
            "ssp585": "#F05A52",
        }
        for sc in ("ssp126", "ssp245", "ssp370", "ssp585"):
            med = trajectory(
                frame,
                iso3=iso,
                indicator="tas",
                scenario=sc,
                value_type="anomaly",
            )
            if med.empty or "median" not in med.columns:
                continue

            selected = sc == scenario
            dash_map = {
                "ssp126": "dash",
                "ssp245": "solid",
                "ssp370": "dot",
                "ssp585": "dashdot",
            }
            symbol_map = {
                "ssp126": "circle",
                "ssp245": "circle",
                "ssp370": "diamond",
                "ssp585": "square",
            }

            fig.add_trace(
                go.Scatter(
                    x=med.period,
                    y=med["median"],
                    mode="lines+markers",
                    line=dict(
                        color=scenario_colors[sc],
                        width=4.2 if selected else 2.4,
                        dash="solid" if selected else dash_map[sc],
                    ),
                    marker=dict(
                        size=8 if selected else 5,
                        symbol=symbol_map[sc],
                        color=scenario_colors[sc],
                        line=dict(
                            color="#FFFFFF",
                            width=1.1 if selected else .6,
                        ),
                    ),
                    opacity=1.0 if selected else .82,
                    name=(
                        SCENARIO_LABELS[sc].split(" · ")[0]
                        + (" · selected" if selected else "")
                    ),
                    hovertemplate="%{x}<br><b>%{y:+.2f}°C</b><extra></extra>",
                )
            )

        fig.update_layout(title=f"Climate pathways · {country}")
        st.plotly_chart(
            _layout(fig, 390, "Temperature change (°C)"),
            width="stretch",
            key="v41_outlook_pathways",
            config={"displayModeBar": False},
        )

        st.markdown(
            f"""
<div class="orb-story">
  <div class="orb-story-title">How to read this layer</div>
  <div class="orb-story-copy">
    Under <b>{SCENARIO_LABELS[scenario].split(" · ")[0]}</b> in <b>{period}</b>,
    {country} is projected at <b>{_fmt(t.get(stat), "degC", True)}</b>,
    with about <b>{_fmt(h30.get(stat), "days")}</b> above 30°C per year
    and an annual precipitation anomaly of
    <b>{_fmt(pr.get(stat), "mm", True)}</b>.
    Read the ensemble range and alternative SSPs together rather than as a
    single deterministic forecast.
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )

    elif section == "Temperature":
        st.markdown(
            """
<div class="orb-viz-shell">
  <div class="orb-viz-heading">Temperature change</div>
  <div class="orb-viz-sub">Spatial distribution of projected temperature anomaly under the selected climate layer.</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        _map(
            frame, "tas", "anomaly", scenario, period, stat,
            f"Global projected temperature change · {period}", "°C", iso, 520
        )

        m1, m2, m3 = st.columns(3, gap="small")
        with m1:
            _card(
                "Selected country",
                _fmt(t.get(stat), "degC", True),
                country,
                RED,
            )
        with m2:
            _card(
                "P10",
                _fmt(t.get("p10"), "degC", True),
                "Lower ensemble percentile",
                BLUE,
            )
        with m3:
            _card(
                "P90",
                _fmt(t.get("p90"), "degC", True),
                "Upper ensemble percentile",
                ORANGE,
            )

    elif section == "Precipitation":
        st.markdown(
            """
<div class="orb-viz-shell">
  <div class="orb-viz-heading">Precipitation change</div>
  <div class="orb-viz-sub">Annual precipitation anomaly. Diverging colours separate drying from wetter conditions.</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        _map(
            frame, "pr", "anomaly", scenario, period, stat,
            f"Global projected precipitation change · {period}",
            "mm/year", iso, 520
        )

        p1, p2, p3 = st.columns(3, gap="small")
        with p1:
            _card(
                "Selected country",
                _fmt(pr.get(stat), "mm", True),
                country,
                BLUE,
            )
        with p2:
            _card(
                "P10",
                _fmt(pr.get("p10"), "mm", True),
                "Lower ensemble percentile",
                CYAN,
            )
        with p3:
            _card(
                "P90",
                _fmt(pr.get("p90"), "mm", True),
                "Upper ensemble percentile",
                GREEN,
            )

    elif section == "Extreme Heat":
        st.markdown(
            """
<div class="orb-viz-shell">
  <div class="orb-viz-heading">Extreme heat</div>
  <div class="orb-viz-sub">Two thresholds separate frequent hot conditions from more severe heat exposure.</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        a, b = st.columns(2, gap="medium")
        with a:
            _map(
                frame, "hd30", "climatology", scenario, period, stat,
                "Hot days >30°C", "days/year", iso, 420
            )
        with b:
            _map(
                frame, "hd35", "climatology", scenario, period, stat,
                "Very hot days >35°C", "days/year", iso, 420
            )

        h1, h2 = st.columns(2, gap="small")
        with h1:
            _card(
                "Hot days >30°C",
                _fmt(h30.get(stat), "days"),
                f"{country} · annual climatology",
                ORANGE,
            )
        with h2:
            _card(
                "Very hot days >35°C",
                _fmt(h35.get(stat), "days"),
                f"{country} · annual climatology",
                RED,
            )

    elif section == "Population Exposure":
        st.markdown(
            """
<div class="orb-viz-shell">
  <div class="orb-viz-heading">Population exposure</div>
  <div class="orb-viz-sub">Population living inside projected heat-hazard conditions. This view uses the validated exposure dataset rather than substituting climate hazard for human exposure.</div>
</div>
            """,
            unsafe_allow_html=True,
        )
        render_population_exposure_tab(
            iso3=iso,
            country=country,
            scenario=scenario,
            period=period,
            statistic=stat,
        )

    with st.expander("Method & sources ⓘ"):
        st.markdown(
            f"**World Bank CCKP / CMIP6** · `{source_path}`  \n"
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
    _header(
        "04 · COMPARE",
        "Compare countries & places.",
        "A precision-first comparison: one climate layer, one scale and one definition across every selected place.",
    )

    try:
        frame, _ = load_cckp()
    except Exception as e:
        st.error(str(e))
        return

    cat = country_catalog(frame)
    allcodes = set(cat.iso3)
    preferred = resolve_default_iso3(frame, preferred_iso3)

    defaults = [preferred] + [
        x for x in ("FRA", "DEU", "ESP") if x in allcodes and x != preferred
    ]

    labels = [f"{r.country} · {r.iso3}" for r in cat.itertuples(index=False)]
    codefor = {f"{r.country} · {r.iso3}": r.iso3 for r in cat.itertuples(index=False)}

    def label_for(c):
        return next((x for x in labels if x.endswith(f"· {c}")), labels[0])

    selected = st.multiselect(
        "Locations · choose 2–4",
        labels,
        default=[label_for(x) for x in defaults[:4]],
        max_selections=4,
        key="v4_compare_locations",
    )
    if len(selected) < 2:
        st.info("Choose at least two locations.")
        return

    codes = [codefor[x] for x in selected]

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        indicator = st.selectbox(
            "Indicator",
            [
                "Temperature Change",
                "Hot Days >30°C",
                "Very Hot Days >35°C",
                "Precipitation Change",
            ],
            key="v4_cmp_i",
        )
    with c2:
        scenario = st.selectbox(
            "Scenario",
            list(SCENARIO_LABELS),
            index=1,
            format_func=lambda x: SCENARIO_LABELS[x],
            key="v4_cmp_s",
        )
    with c3:
        period = st.selectbox("Period", PERIODS, index=1, key="v4_cmp_p")
    with c4:
        stat = st.selectbox(
            "Statistic",
            STATS,
            index=1,
            format_func=lambda x: x.upper() if x != "median" else "Median",
            key="v4_cmp_stat",
        )

    mapping = {
        "Temperature Change": ("tas", "anomaly", "degC", True),
        "Hot Days >30°C": ("hd30", "climatology", "days", False),
        "Very Hot Days >35°C": ("hd35", "climatology", "days", False),
        "Precipitation Change": ("pr", "anomaly", "mm", True),
    }
    ind, typ, unit, signed = mapping[indicator]

    x = select_slice(
        frame,
        iso3=codes,
        indicator=ind,
        value_type=typ,
        scenario=scenario,
        period=period,
        statistic=stat,
    ).dropna(subset=["value"])

    if x.empty:
        st.info("No comparable records are available for the selected layer.")
        return

    # Respect selection order for matrix, but sort analytical ranking by value.
    selection_order = {c: i for i, c in enumerate(codes)}
    x["_selection_order"] = x.iso3.map(selection_order)
    x_matrix = x.sort_values("_selection_order")
    x_rank = x.sort_values("value", ascending=True).copy()

    vmax = float(x.value.max())
    vmin = float(x.value.min())
    spread = vmax - vmin
    highest = x.loc[x.value.idxmax()]
    lowest = x.loc[x.value.idxmin()]
    mean_value = float(x.value.mean())

    # Compact analytical headline instead of a giant chart first.
    s1, s2, s3 = st.columns(3, gap="small")
    with s1:
        _card(
            "Highest selected value",
            str(highest.country),
            _fmt(highest.value, unit, signed),
            RED if ind != "pr" else ORANGE,
        )
    with s2:
        _card(
            "Lowest selected value",
            str(lowest.country),
            _fmt(lowest.value, unit, signed),
            BLUE,
        )
    with s3:
        _card(
            "Spread across selections",
            _fmt(spread, unit, False),
            f"{period} · {SCENARIO_LABELS[scenario].split(' · ')[0]}",
            PURPLE,
        )

    st.markdown(
        "<div class='orb-section-title' style='margin-top:14px'>Relative position</div>"
        "<div class='orb-note' style='margin-bottom:4px'>"
        "Dots show the exact values on one common scale. The dashed line is the selected-place mean."
        "</div>",
        unsafe_allow_html=True,
    )

    # Precision-oriented horizontal dot/lollipop plot.
    fig = go.Figure()

    for row in x_rank.itertuples(index=False):
        fig.add_trace(
            go.Scatter(
                x=[vmin, row.value],
                y=[row.country, row.country],
                mode="lines",
                line=dict(color="rgba(91,153,185,.28)", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    dot_colors = [CYAN if i == len(x_rank) - 1 else "#7AA7BD" for i in range(len(x_rank))]
    fig.add_trace(
        go.Scatter(
            x=x_rank.value,
            y=x_rank.country,
            mode="markers+text",
            marker=dict(
                size=15,
                color=dot_colors,
                line=dict(color="rgba(255,255,255,.35)", width=.8),
            ),
            text=[_fmt(v, unit, signed) for v in x_rank.value],
            textposition="middle right",
            textfont=dict(color="#E8F3F8", size=11),
            hovertemplate="<b>%{y}</b><br>%{x:.2f}<extra></extra>",
            showlegend=False,
        )
    )

    fig.add_vline(
        x=mean_value,
        line_width=1,
        line_dash="dash",
        line_color="rgba(167,123,255,.65)",
        annotation_text="Selected mean",
        annotation_position="top",
        annotation_font_color="#BCA4FF",
    )

    pad = max(abs(spread) * .22, .15 if unit == "degC" else 1)
    fig.update_xaxes(range=[vmin - pad, vmax + pad * 2.0])
    fig.update_layout(title=f"{indicator} · {period}")

    st.plotly_chart(
        _layout(fig, 320, indicator, showlegend=False),
        width="stretch",
        config={"displayModeBar": False},
    )

    # Multi-indicator comparison matrix.
    st.markdown(
        "<div class='orb-section-title'>Climate comparison matrix</div>"
        "<div class='orb-note' style='margin-bottom:6px'>"
        "One row per decision-relevant indicator. Values use the same scenario, period and statistic selected above."
        "</div>",
        unsafe_allow_html=True,
    )

    metrics = [
        ("Temperature", "tas", "anomaly", "degC", True),
        ("Hot days >30°C", "hd30", "climatology", "days", False),
        ("Hot days >35°C", "hd35", "climatology", "days", False),
        ("Precipitation change", "pr", "anomaly", "mm", True),
    ]

    names = [cat.loc[cat.iso3.eq(c), "country"].iloc[0] for c in codes]
    header = (
        "<div class='orb-matrix'><div class='orb-table-head'><div>Indicator</div>"
        + "".join(f"<div>{name}</div>" for name in names)
        + "</div>"
    )

    rows = []
    for lab, ii, tt, uu, ss in metrics:
        cells = []
        for c in codes:
            q = select_slice(
                frame,
                iso3=c,
                indicator=ii,
                value_type=tt,
                scenario=scenario,
                period=period,
                statistic=stat,
            )
            val = float(q.value.iloc[0]) if not q.empty else None
            cells.append(_fmt(val, uu, ss))

        rows.append(
            "<div class='orb-table-row'>"
            f"<div style='font-weight:850;color:#EAF4F8'>{lab}</div>"
            + "".join(f"<div><span class='orb-matrix-cell'>{v}</span></div>" for v in cells)
            + "</div>"
        )

    st.markdown(header + "".join(rows) + "</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='orb-section-title' style='margin-top:16px'>Spatial context</div>"
        "<div class='orb-note' style='margin-bottom:6px'>"
        "Small multiples preserve the same map scale so geographic context can be checked without dominating the comparison."
        "</div>",
        unsafe_allow_html=True,
    )

    mapcols = st.columns(len(codes), gap="small")
    for col, c in zip(mapcols, codes):
        with col:
            name = cat.loc[cat.iso3.eq(c), "country"].iloc[0]
            _map(frame, ind, typ, scenario, period, stat, name, unit, c, 235)




def render_global_insights():
    inject_intelligence_theme()
    _header(
        "05 · GLOBAL INSIGHTS",
        "Global patterns, leaders & hotspots.",
        "Scan the whole climate layer first, then use rankings and outliers to decide where deeper analysis is warranted.",
    )

    try:
        frame, _ = load_cckp()
    except Exception as e:
        st.error(str(e))
        return

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        indicator = st.selectbox(
            "Indicator",
            [
                "Projected warming",
                "Hot days >30°C",
                "Hot days >35°C",
                "Precipitation change",
            ],
            key="v4_gl_i",
        )
    with c2:
        scenario = st.selectbox(
            "Scenario",
            list(SCENARIO_LABELS),
            index=1,
            format_func=lambda x: SCENARIO_LABELS[x],
            key="v4_gl_s",
        )
    with c3:
        period = st.selectbox("Period", PERIODS, index=1, key="v4_gl_p")
    with c4:
        stat = st.selectbox(
            "Statistic",
            STATS,
            index=1,
            format_func=lambda x: x.upper() if x != "median" else "Median",
            key="v4_gl_st",
        )

    meta = {
        "Projected warming": ("tas", "anomaly", "degC", True),
        "Hot days >30°C": ("hd30", "climatology", "days", False),
        "Hot days >35°C": ("hd35", "climatology", "days", False),
        "Precipitation change": ("pr", "anomaly", "mm", True),
    }
    ind, typ, unit, signed = meta[indicator]

    full = select_slice(
        frame,
        indicator=ind,
        value_type=typ,
        scenario=scenario,
        period=period,
        statistic=stat,
    ).dropna(subset=["value"])

    if full.empty:
        st.info("No global records are available for this layer.")
        return

    high = full.nlargest(1, "value").iloc[0]
    low = full.nsmallest(1, "value").iloc[0]
    median_value = float(full.value.median())

    divergence_name = "—"
    divergence_value = None
    if ind == "tas":
        e = select_slice(
            frame,
            indicator="tas",
            value_type="anomaly",
            period="2080-2099",
            statistic="median",
        )
        p = e.pivot_table(
            index=["iso3", "country"],
            columns="scenario",
            values="value",
            aggfunc="first",
        ).dropna()
        if not p.empty and {"ssp585", "ssp126"}.issubset(p.columns):
            p["d"] = p["ssp585"] - p["ssp126"]
            r = p.nlargest(1, "d").reset_index().iloc[0]
            divergence_name = str(r.country)
            divergence_value = float(r.d)

    # Headline signals before the map.
    a, b, c, d = st.columns(4, gap="small")
    with a:
        _card(
            "Highest value",
            str(high.country),
            _fmt(high.value, unit, signed),
            RED,
        )
    with b:
        _card(
            "Global median",
            _fmt(median_value, unit, signed),
            f"{len(full)} covered entities",
            CYAN,
        )
    with c:
        _card(
            "Lowest value",
            str(low.country),
            _fmt(low.value, unit, signed),
            BLUE,
        )
    with d:
        if ind == "tas":
            _card(
                "Largest SSP divergence",
                divergence_name,
                _fmt(divergence_value, "degC", True),
                PURPLE,
            )
        else:
            _card(
                "Coverage",
                f"{len(full)} entities",
                "validated production CCKP layer",
                GREEN,
            )

    left, right = st.columns([1.58, .72], gap="medium")
    with left:
        st.markdown(
            "<div class='orb-section-title' style='margin-top:12px'>Global distribution</div>"
            "<div class='orb-note' style='margin-bottom:5px'>"
            "Use the map for spatial pattern; use the ranking beside it for exact ordering."
            "</div>",
            unsafe_allow_html=True,
        )
        _map(
            frame,
            ind,
            typ,
            scenario,
            period,
            stat,
            f"{indicator} · {period}",
            unit,
            None,
            455,
        )

    with right:
        st.markdown(
            "<div class='orb-section-title' style='margin-top:12px'>Top hotspots</div>"
            "<div class='orb-note' style='margin-bottom:4px'>Highest values under the selected layer.</div>",
            unsafe_allow_html=True,
        )
        top = full.nlargest(8, "value")
        for rank, row in enumerate(top.itertuples(index=False), 1):
            st.markdown(
                f"""
<div class="orb-rank-row">
  <div class="orb-rank-num">{rank}</div>
  <div class="orb-rank-name">{row.country}</div>
  <div class="orb-rank-value">{_fmt(row.value, unit, signed)}</div>
</div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
<div class="orb-story" style="margin-top:12px">
  <div class="orb-story-title">Interpretation guardrail</div>
  <div class="orb-story-copy">
    Rankings describe the selected climate indicator only. They are not a composite
    risk score and should not be interpreted as overall national vulnerability,
    exposure or preparedness.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )




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
            "ORBIDENSE connects Earth data, climate projections, emissions evidence and policy intelligence while keeping provenance visible.")
    tabs=st.tabs(["Overview","Science & Methodology","Data Sources","Coverage","Limitations","References"])
    with tabs[0]:
        left,right=st.columns([1.3,.7],gap="medium")
        with left:
            st.markdown("### ORBIDENSE")
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
