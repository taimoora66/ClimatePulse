from __future__ import annotations

from pathlib import Path
import base64, math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.orbidense_router import request_route

CCKP=Path('data/climate_intelligence/cckp_country_projections.parquet')
EXPOSURE=Path('data/climate_intelligence/population_exposure.parquet')
EDGAR=Path('data/climate_intelligence/edgar_country_emissions.parquet')
HERO=Path('assets/orbidense_earth_hero.png')
SCENARIO='ssp245'; PERIOD='2040-2059'; STATISTIC='median'
CYAN='#25C8FF'; ORANGE='#FF9C3A'; RED='#FF5842'

@st.cache_data(show_spinner=False)
def _read(path:str)->pd.DataFrame:
    p=Path(path); return pd.read_parquet(p) if p.exists() else pd.DataFrame()

@st.cache_data(show_spinner=False)
def _hero_uri()->str:
    if not HERO.exists(): return ''
    return 'data:image/png;base64,'+base64.b64encode(HERO.read_bytes()).decode('ascii')

def _human(v,decimals=1):
    try:v=float(v)
    except Exception:return '—'
    if not math.isfinite(v):return '—'
    if abs(v)>=1_000_000_000:return f'{v/1_000_000_000:.{decimals}f}B'
    if abs(v)>=1_000_000:return f'{v/1_000_000:.{decimals}f}M'
    if abs(v)>=1_000:return f'{v/1_000:.{decimals}f}k'
    return f'{v:,.0f}'

def _button(label, route_label, key, target=None, primary=False):
    st.button(
        label,
        key=key,
        width="stretch",
        type="primary" if primary else "secondary",
        on_click=request_route,
        args=(route_label, target),
    )


def _css():
    hero=_hero_uri()
    st.markdown(f'''
<style>
.home-final-hero{{position:relative;overflow:hidden;min-height:280px;padding:30px 34px;border:1px solid rgba(55,155,219,.20);border-radius:19px;background:linear-gradient(90deg,rgba(2,12,23,.99) 0%,rgba(2,12,23,.91) 42%,rgba(2,12,23,.12) 72%,rgba(2,12,23,.18) 100%),url("{hero}") right center / 63% 123% no-repeat,radial-gradient(circle at 70% 45%,rgba(30,140,255,.19),transparent 27%),linear-gradient(135deg,#061728,#020e19)}}
.hf-kicker{{color:#49e7d5;font-size:.65rem;font-weight:900;letter-spacing:.13em;text-transform:uppercase}}.hf-title{{max-width:700px;color:#fff;font-size:clamp(2rem,3.5vw,3.4rem);font-weight:950;line-height:1.03;letter-spacing:-.045em;margin:8px 0 12px}}.hf-title b{{color:#18e39a}}.hf-copy{{max-width:640px;color:#a0b3c0;font-size:.92rem;line-height:1.52}}
.hf-signal{{position:absolute;top:15px;right:17px;width:285px;border-radius:15px;padding:13px;border:1px solid rgba(67,167,223,.27);background:rgba(4,20,36,.89);backdrop-filter:blur(7px)}}.hf-signal h4{{margin:0;color:#fff;font-size:.84rem}}.hf-signal-sub{{color:#8098aa;font-size:.61rem;margin:3px 0 9px}}.hf-signal-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}.hf-signal-card{{border:1px solid rgba(69,165,213,.16);border-radius:11px;padding:9px;background:rgba(7,27,44,.88)}}.hf-signal-card .v{{font-size:1.03rem;color:#fff;font-weight:950}}.hf-signal-card .l{{font-size:.57rem;color:#8199aa;line-height:1.34;margin-top:3px}}
.hf-metrics{{display:grid;grid-template-columns:repeat(5,1fr);border-radius:16px;overflow:hidden;border:1px solid rgba(55,155,219,.22);background:linear-gradient(180deg,rgba(5,27,46,.99),rgba(4,18,31,.99));margin-top:9px}}.hf-metric{{padding:13px 17px;border-right:1px solid rgba(71,159,202,.12);min-height:72px}}.hf-metric:last-child{{border-right:0}}.hf-metric .v{{font-size:1.25rem;font-weight:950;color:#fff}}.hf-metric .l{{font-size:.61rem;color:#859cac;line-height:1.34;margin-top:4px}}
.hf-section{{margin:12px 0 3px;color:#f2f9fd;font-size:1rem;font-weight:900}}.hf-sub{{color:#8199aa;font-size:.64rem;margin-bottom:7px}}.hf-panel{{height:100%;border:1px solid rgba(55,155,219,.19);border-radius:16px;padding:12px;background:linear-gradient(145deg,rgba(7,27,43,.98),rgba(3,15,26,.99))}}.hf-panel h4{{margin:0;color:#fff;font-size:.83rem}}.hf-panel .sub{{color:#8098aa;font-size:.61rem;margin-top:2px}}.hf-hot{{display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:center;padding:8px 2px;border-bottom:1px solid rgba(80,160,200,.09)}}.hf-rank{{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:rgba(39,113,240,.17);color:#d1e3ff;font-size:.63rem;font-weight:900}}.hf-place{{color:#e9f4f9;font-size:.67rem}}.hf-val{{color:#ffbd75;font-size:.66rem;font-weight:900}}.hf-big{{font-size:2rem;color:#fff;font-weight:950;line-height:1;margin-top:9px}}.hf-note{{color:#8da4b3;font-size:.65rem;line-height:1.4;margin-top:4px}}
.hf-question{{height:100%;border-radius:15px;padding:14px;border:1px solid rgba(74,169,213,.18);background:linear-gradient(145deg,rgba(7,27,43,.98),rgba(4,16,27,.99))}}.hf-question .t{{font-size:.80rem;color:#fff;font-weight:900}}.hf-question .c{{font-size:.64rem;color:#839bab;line-height:1.42;margin-top:5px}}.hf-question.outlook{{border-color:rgba(42,177,255,.58);background:linear-gradient(135deg,rgba(4,52,103,.83),rgba(5,25,45,.97))}}.hf-question.exposure{{border-color:rgba(0,230,211,.50);background:linear-gradient(135deg,rgba(4,69,80,.78),rgba(5,26,41,.97))}}.hf-question.action{{border-color:rgba(24,229,139,.48);background:linear-gradient(135deg,rgba(3,72,54,.72),rgba(4,25,36,.97))}}.hf-question.compare{{border-color:rgba(166,99,255,.58);background:linear-gradient(135deg,rgba(58,30,112,.80),rgba(17,19,49,.98))}}.hf-question.insights{{border-color:rgba(93,106,255,.50);background:linear-gradient(135deg,rgba(25,47,116,.72),rgba(11,24,52,.98))}}
.hf-sources{{display:flex;gap:23px;flex-wrap:wrap;align-items:center;margin-top:10px;border-top:1px solid rgba(70,160,201,.11);padding:10px 2px 2px;color:#8399a9;font-size:.60rem}}.hf-source-lead{{color:#a2b4bf;font-weight:800}}.hf-footer{{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;border-top:1px solid rgba(70,160,201,.11);margin-top:10px;padding:10px 2px;color:#718899;font-size:.58rem}}.hf-back{{position:fixed;right:22px;bottom:24px;z-index:40}}.hf-back a{{display:grid;place-items:center;width:44px;height:44px;border-radius:50%;border:1px solid #19dff1;background:rgba(4,31,50,.94);color:#39e6ef;text-decoration:none;font-size:1.35rem;box-shadow:0 0 24px rgba(25,223,241,.18)}}
@media(max-width:1100px){{.hf-signal{{position:relative;top:auto;right:auto;width:auto;margin-top:14px}}.hf-metrics{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:700px){{.home-final-hero{{padding:20px 16px 150px;min-height:auto;background:linear-gradient(180deg,rgba(2,12,23,.99) 0%,rgba(2,12,23,.96) 54%,rgba(2,12,23,.13) 78%),url("{hero}") center bottom / 118% auto no-repeat,linear-gradient(135deg,#061728,#020e19)}}.hf-title{{font-size:2rem}}.hf-copy{{font-size:.82rem}}.hf-metrics{{grid-template-columns:repeat(2,1fr)}}.hf-metric:last-child{{grid-column:1/-1}}.hf-back{{right:13px;bottom:14px}}}}
</style>
''',unsafe_allow_html=True)

def _layer(d,indicator,value_type):
    req={'indicator','scenario','period','statistic','value_type','value','iso3','country'}
    if d.empty or not req.issubset(d.columns):return pd.DataFrame()
    x=d[d['indicator'].astype(str).str.lower().eq(indicator)&d['scenario'].astype(str).str.lower().eq(SCENARIO)&d['period'].astype(str).eq(PERIOD)&d['statistic'].astype(str).str.lower().eq(STATISTIC)&d['value_type'].astype(str).str.lower().eq(value_type)].copy();x['value']=pd.to_numeric(x['value'],errors='coerce');return x.dropna(subset=['value'])

def _exp_total(d,period):
    req={'scenario','period','statistic','hazard','threshold_days','population_exposed'}
    if d.empty or not req.issubset(d.columns):return None
    x=d[d['scenario'].astype(str).str.lower().eq(SCENARIO)&d['period'].astype(str).eq(period)&d['statistic'].astype(str).str.lower().eq(STATISTIC)&d['hazard'].astype(str).str.lower().eq('hd30')&pd.to_numeric(d['threshold_days'],errors='coerce').eq(60)]
    if x.empty:return None
    return float(pd.to_numeric(x['population_exposed'],errors='coerce').fillna(0).sum())

def render_home_v2():
    st.markdown('''
<style>
/* HOME CTA BUTTONS FINAL */
[class*="st-key-hf_"] button{
  background:#0a2236!important;
  border:1px solid rgba(47,174,225,.31)!important;
  color:#e8f7fd!important;
  border-radius:12px!important;
  min-height:42px!important;
  font-size:.70rem!important;
  font-weight:800!important;
  box-shadow:none!important;
}
[class*="st-key-hf_"] button:hover{
  background:#0d2c45!important;
  border-color:#20dfea!important;
  color:#46eee7!important;
}
.st-key-hf_cta_outlook button{
  background:linear-gradient(90deg,#16c8f4,#18e598)!important;
  color:#03131d!important;
  border-color:transparent!important;
}
.st-key-hf_q1 button{border-color:rgba(42,177,255,.55)!important}
.st-key-hf_q2 button{border-color:rgba(0,230,211,.48)!important}
.st-key-hf_q3 button{border-color:rgba(24,229,139,.46)!important}
.st-key-hf_q4 button{border-color:rgba(166,99,255,.53)!important}
.st-key-hf_q5 button{border-color:rgba(93,106,255,.48)!important}
</style>
''', unsafe_allow_html=True)
    _css();cckp=_read(str(CCKP));exposure=_read(str(EXPOSURE));edgar=_read(str(EDGAR));temp=_layer(cckp,'tas','anomaly');precip=_layer(cckp,'pr','anomaly')
    entities=int(cckp['iso3'].nunique()) if (not cckp.empty and 'iso3' in cckp.columns) else None;scenarios=int(cckp['scenario'].nunique()) if (not cckp.empty and 'scenario' in cckp.columns) else None;periods=int(cckp['period'].nunique()) if (not cckp.empty and 'period' in cckp.columns) else None;exp_rows=len(exposure) if not exposure.empty else None;latest=int(pd.to_numeric(edgar['year'],errors='coerce').max()) if (not edgar.empty and 'year' in edgar.columns) else None;tmed=float(temp['value'].median()) if not temp.empty else None;pmed=float(precip['value'].median()) if not precip.empty else None;expmid=_exp_total(exposure,PERIOD)
    st.markdown(f'''<div class="home-final-hero"><div class="hf-kicker">EARTH INTELLIGENCE · BETTER DECISIONS</div><div class="hf-title">Understand. Anticipate.<br>Act for a <b>Resilient Planet.</b></div><div class="hf-copy">Turning global climate, exposure and emissions data into clear insights for smarter, evidence-based decisions.</div><div class="hf-signal"><h4>Global Climate Signal</h4><div class="hf-signal-sub">SSP2–4.5 · 2040–2059 · Median</div><div class="hf-signal-grid"><div class="hf-signal-card"><div class="v">{'—' if tmed is None else f'{tmed:+.2f}°C'}</div><div class="l">Median warming across covered entities</div></div><div class="hf-signal-card"><div class="v">{_human(expmid) if expmid is not None else '—'}</div><div class="l">People exposed to ≥60 hot days/year</div></div><div class="hf-signal-card"><div class="v">{'—' if pmed is None else f'{pmed:+.0f} mm'}</div><div class="l">Median precipitation change</div></div><div class="hf-signal-card"><div class="v">{latest or '—'}</div><div class="l">Latest emissions year (EDGAR)</div></div></div></div></div>''',unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,.85,1],gap='small')
    with c1:_button('Explore Climate Outlook  →','Climate Outlook','hf_cta_outlook',primary=True)
    with c2:_button('Compare Places  →','Compare','hf_cta_compare')
    with c3:_button('View Global Insights  →','Global Insights','hf_cta_insights')
    st.markdown(f'''<div class="hf-metrics"><div class="hf-metric"><div class="v">◎ {entities or '—'}</div><div class="l">Countries & Territories</div></div><div class="hf-metric"><div class="v">▱ {scenarios or '—'}</div><div class="l">CMIP6 SSP Scenarios</div></div><div class="hf-metric"><div class="v">▣ {periods or '—'}</div><div class="l">Future Periods<br>(2020–2099)</div></div><div class="hf-metric"><div class="v">♙ {_human(exp_rows) if exp_rows else '—'}</div><div class="l">Exposure Rows Validated</div></div><div class="hf-metric"><div class="v">◇ {latest or '—'}</div><div class="l">Latest Emissions Year<br>(EDGAR)</div></div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="hf-section">Global Projected Warming</div>',unsafe_allow_html=True);st.markdown('<div class="hf-sub">SSP2–4.5 · 2040–2059 · Median</div>',unsafe_allow_html=True)
    a,b,c=st.columns([1.15,1.0,1.08],gap='medium')
    with a:
        st.markdown('<div class="hf-panel">',unsafe_allow_html=True)
        if not temp.empty:
            fig=go.Figure(go.Choropleth(locations=temp['iso3'],z=temp['value'],text=temp['country'],locationmode='ISO-3',colorscale=[[0,'#2153d4'],[.25,'#18b6ff'],[.47,'#38e388'],[.67,'#ffe14d'],[.84,'#ff9824'],[1,'#ff351f']],marker_line_color='rgba(255,255,255,.08)',marker_line_width=.2,colorbar=dict(title='°C',thickness=8,len=.58),hovertemplate='<b>%{text}</b><br>%{z:+.2f}°C<extra></extra>'));fig.update_geos(projection_type='natural earth',showframe=False,showcoastlines=False,bgcolor='rgba(0,0,0,0)',landcolor='#0a1b28');fig.update_layout(height=280,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',font=dict(color='#cfe0e9'));st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
        else:st.info('Temperature projection layer unavailable.')
        st.markdown('</div>',unsafe_allow_html=True);_button('Explore maps  →','Climate Outlook','hf_maps')
    with b:
        st.markdown('<div class="hf-panel"><h4>Top Warming Hotspots</h4><div class="sub">2040–2059</div>',unsafe_allow_html=True)
        if not temp.empty:
            for i,r in enumerate(temp.nlargest(5,'value').itertuples(index=False),1):st.markdown(f'<div class="hf-hot"><div class="hf-rank">{i}</div><div class="hf-place">{r.country}</div><div class="hf-val">{float(r.value):+.2f}°C</div></div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True);_button('View Global Insights  →','Global Insights','hf_hot')
    with c:
        vals=[_exp_total(exposure,p) for p in ['2020-2039','2040-2059','2060-2079','2080-2099']];late=next((v for v in reversed(vals) if v is not None),None);st.markdown('<div class="hf-panel"><h4>People Exposure to Extreme Heat</h4><div class="sub">SSP2–4.5 · median · HD30 ≥60 days/year</div>',unsafe_allow_html=True);st.markdown(f'<div class="hf-big">{_human(late) if late is not None else "—"}</div><div class="hf-note">people globally in the selected late-century layer</div>',unsafe_allow_html=True)
        if any(v is not None for v in vals):
            fig=go.Figure(go.Bar(x=['2020s','2040s','2060s','2080s'],y=[0 if v is None else v for v in vals],marker_color=[CYAN,'#5CADFF',ORANGE,RED],hovertemplate='%{x}<br>%{y:,.0f} people<extra></extra>'));fig.update_layout(height=145,margin=dict(l=0,r=0,t=6,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',showlegend=False,font=dict(color='#8fa5b5',size=10));fig.update_xaxes(showgrid=False);fig.update_yaxes(visible=False,showgrid=False);st.plotly_chart(fig,width='stretch',config={'displayModeBar':False})
        st.markdown('</div>',unsafe_allow_html=True);_button('Explore Population Exposure  →','Climate Outlook','hf_exposure',target='Population Exposure')
    st.markdown('<div class="hf-section">Explore by question</div>',unsafe_allow_html=True)
    qs=st.columns(5,gap='small');cards=[('outlook','Climate Outlook','How could temperature, precipitation and extremes evolve?','Open Outlook  →','Climate Outlook',None),('exposure','Population Exposure','How many people may live inside future heat hazards?','Open Exposure  →','Climate Outlook','Population Exposure'),('action','Climate Action','How are emissions and sectors actually changing?','Open Action  →','Climate Action',None),('compare','Compare Places','Where do places diverge and where are the hotspots?','Open Compare  →','Compare',None),('insights','Global Insights','Discover global hotspots, trends and patterns.','Open Insights  →','Global Insights',None)]
    for i,(cls,title,copy,label,route,target) in enumerate(cards):
        with qs[i]:st.markdown(f'<div class="hf-question {cls}"><div class="t">{title}</div><div class="c">{copy}</div></div>',unsafe_allow_html=True);_button(label,route,f'hf_q{i}',target=target)
    st.markdown('<div class="hf-sources"><span class="hf-source-lead">Trusted data. Transparent methods.</span><span>◉ Copernicus Climate Data</span><span>◎ World Bank CCKP</span><span>▱ EDGAR Emissions</span><span>◌ UNFCCC / Climate Watch</span><span>♙ WorldPop / population layers</span></div>',unsafe_allow_html=True)
    ac,_=st.columns([.24,.76]);
    with ac:_button('About ORBIDENSE  →','About','hf_about')
    st.markdown('<div class="hf-footer"><span>© 2026 ORBIDENSE. All rights reserved.</span><span>Earth Intelligence. Better Decisions.</span><span>Data Sources · Methodology · Transparency · Privacy · Contact</span></div><div class="hf-back"><a href="#top" title="Back to top">↑</a></div>',unsafe_allow_html=True)
