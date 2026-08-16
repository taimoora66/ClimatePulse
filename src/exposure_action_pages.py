from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.population_exposure_v7 import render_population_exposure_v7

CYAN="#2FE1F2"; BLUE="#49A8FF"; GREEN="#59D88C"; YELLOW="#F4C64C"; ORANGE="#FF9C4A"; RED="#FF5D62"; PURPLE="#A77BFF"


def _read(paths):
    for p in paths:
        if p.exists():
            try:
                return (pd.read_parquet(p) if p.suffix=='.parquet' else pd.read_csv(p)), p
            except Exception:
                pass
    return None, None


def _layout(fig,h=390,y=None,legend=True):
    fig.update_layout(height=h,margin=dict(l=10,r=10,t=42,b=10),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(5,17,27,.62)',font=dict(color='#cfe0e9',family='Inter, sans-serif'),hoverlabel=dict(bgcolor='#0b1d2b'),legend=dict(orientation='h',y=1.08,x=0),showlegend=legend)
    fig.update_xaxes(showgrid=False,zeroline=False,color='#7890a2'); fig.update_yaxes(gridcolor='rgba(121,181,207,.11)',zeroline=False,color='#7890a2',title=y)
    return fig


def _card(label,value,note='',accent=CYAN):
    st.markdown(f'''<div class="orb-card" style="border-top:2px solid {accent}"><small>{label}</small><div class="orb-big">{value}</div><div class="orb-note">{note}</div></div>''',unsafe_allow_html=True)


def _num(v):
    try: v=float(v)
    except: return '—'
    if not math.isfinite(v): return '—'
    if abs(v)>=1e9: return f'{v/1e9:.2f}B'
    if abs(v)>=1e6: return f'{v/1e6:.2f}M'
    if abs(v)>=1e3: return f'{v/1e3:.1f}k'
    return f'{v:.1f}'


def render_population_exposure_tab(
    *,
    iso3: str,
    country: str,
    scenario: str,
    period: str,
    statistic: str,
) -> None:
    render_population_exposure_v7(
        iso3=iso3,
        country=country,
        scenario=scenario,
        period=period,
        statistic=statistic,
    )

def render_climate_action_full(*,iso3,country):
    ec,pc=_read([Path('data/climate_intelligence/edgar_country_emissions.parquet'),Path('data/climate_intelligence/edgar_country_emissions.csv')])
    es,ps=_read([Path('data/climate_intelligence/edgar_sector_emissions.parquet'),Path('data/climate_intelligence/edgar_sector_emissions.csv')])
    tg,pt=_read([Path('data/climate_intelligence/climatewatch_targets.parquet'),Path('data/climate_intelligence/climatewatch_targets.csv')])
    cat,pca=_read([Path('data/climate_intelligence/cat_country_ratings.parquet'),Path('data/climate_intelligence/cat_country_ratings.csv')])
    tabs=st.tabs(['Overview','Emissions','Targets','Sectors','Policy'])
    if ec is None:
        with tabs[0]:
            st.markdown('''<div class="orb-hero"><div class="orb-section-title">Climate Action production data is not built yet</div><div class="orb-sub">Build EDGAR first. Targets and policy ratings remain separate because their accounting scopes can differ from EDGAR totals.</div></div>''',unsafe_allow_html=True)
            st.code('python .\\scripts\\build_edgar_action.py\npython .\\scripts\\validate_climate_action.py',language='powershell')
        return
    ec=ec.copy(); ec['iso3']=ec.iso3.astype(str).str.upper(); ec['year']=pd.to_numeric(ec.year,errors='coerce'); ec['value_mtco2e']=pd.to_numeric(ec.value_mtco2e,errors='coerce'); c=ec[ec.iso3.eq(iso3.upper())].dropna(subset=['year','value_mtco2e']).sort_values('year')
    if c.empty:
        with tabs[0]:st.info(f'No EDGAR emissions for {country} ({iso3}).')
        return
    latest=c.iloc[-1]; y1990=c[c.year.eq(1990)]; pct=None if y1990.empty or float(y1990.iloc[0].value_mtco2e)==0 else (float(latest.value_mtco2e)/float(y1990.iloc[0].value_mtco2e)-1)*100
    sector=pd.DataFrame()
    if es is not None:
        es=es.copy(); es['iso3']=es.iso3.astype(str).str.upper(); es['year']=pd.to_numeric(es.year,errors='coerce'); es['value_mtco2e']=pd.to_numeric(es.value_mtco2e,errors='coerce'); sector=es[es.iso3.eq(iso3.upper())].dropna(subset=['year','value_mtco2e'])
    targets=pd.DataFrame() if tg is None else tg[tg.iso3.astype(str).str.upper().eq(iso3.upper())].copy() if 'iso3' in tg.columns else pd.DataFrame()
    cats=pd.DataFrame() if cat is None else cat[cat.iso3.astype(str).str.upper().eq(iso3.upper())].copy() if 'iso3' in cat.columns else pd.DataFrame()
    with tabs[0]:
        cols=st.columns(4,gap='small')
        vals=[('Latest GHG emissions',f'{float(latest.value_mtco2e):,.1f} MtCO₂e',f'EDGAR · {int(latest.year)} · excl. LULUCF',CYAN),('Change since 1990','—' if pct is None else f'{pct:+.1f}%','EDGAR total GHG',GREEN if pct is not None and pct<0 else RED),('NDC / target records',str(len(targets)) if not targets.empty else 'Source pending','Climate Watch quantifications',YELLOW),('Policy assessment',str(cats.iloc[-1].get('overall_rating','Available')) if not cats.empty else 'Source pending','CAT where entity is assessed',ORANGE)]
        for col,v in zip(cols,vals):
            with col:_card(*v)
        left,right=st.columns([1.55,.85],gap='medium')
        with left:
            fig=go.Figure(go.Scatter(x=c.year,y=c.value_mtco2e,mode='lines',line=dict(color=CYAN,width=3),fill='tozeroy',fillcolor='rgba(47,225,242,.06)',hovertemplate='%{x:.0f}<br>%{y:.1f} MtCO₂e<extra></extra>')); fig.update_layout(title=f'GHG emissions pathway · {country}')
            st.plotly_chart(_layout(fig,420,'MtCO₂e'),width='stretch',config={'displayModeBar':False})
        with right:
            if not sector.empty:
                yy=int(sector.year.max()); ss=sector[sector.year.eq(yy)].sort_values('value_mtco2e',ascending=False).head(8)
                fig=go.Figure(go.Pie(labels=ss.sector,values=ss.value_mtco2e,hole=.62,marker=dict(colors=[RED,ORANGE,YELLOW,CYAN,BLUE,GREEN,PURPLE,'#8FA6B5']),textinfo='percent',hovertemplate='<b>%{label}</b><br>%{value:.1f} MtCO₂e<br>%{percent}<extra></extra>')); fig.add_annotation(text=f'{yy}<br>sectors',x=.5,y=.5,showarrow=False,font=dict(size=15,color='#fff')); fig.update_layout(title='Sector composition')
                st.plotly_chart(_layout(fig,420,None,False),width='stretch',config={'displayModeBar':False})
            else:st.info('Sector emissions appear after the EDGAR sector table is built.')
        if not sector.empty:
            yy=int(sector.year.max()); base=2005 if 2005 in set(sector.year.dropna().astype(int)) else int(sector.year.min()); a=sector[sector.year.eq(yy)][['sector','value_mtco2e']].rename(columns={'value_mtco2e':'latest'}); b=sector[sector.year.eq(base)][['sector','value_mtco2e']].rename(columns={'value_mtco2e':'base'}); ch=a.merge(b,on='sector'); ch['change']=ch.latest-ch.base; ch=ch.reindex(ch.change.abs().sort_values(ascending=False).index).head(10)
            fig=go.Figure(go.Bar(x=ch.change,y=ch.sector,orientation='h',marker=dict(color=[GREEN if v<0 else RED for v in ch.change]),text=[f'{v:+.1f}' for v in ch.change],textposition='outside')); fig.update_layout(title=f'Sector change · {base} → {yy}',yaxis=dict(autorange='reversed'),showlegend=False)
            st.plotly_chart(_layout(fig,360,'Change in MtCO₂e',False),width='stretch',config={'displayModeBar':False})
    with tabs[1]:
        fig=go.Figure(go.Scatter(x=c.year,y=c.value_mtco2e,mode='lines+markers',line=dict(color=CYAN,width=2.5),marker=dict(size=4))); fig.update_layout(title=f'EDGAR total GHG · {country} · 1970–2024')
        st.plotly_chart(_layout(fig,480,'MtCO₂e'),width='stretch',config={'displayModeBar':False}); st.caption(f'EDGAR 2025 GHG · total GHG CO₂e AR5 · excluding LULUCF · {pc}')
    with tabs[2]:
        if targets.empty:st.info('No Climate Watch quantification records installed for this entity yet.')
        else:
            st.dataframe(targets,width='stretch',hide_index=True); st.warning('ORBIDENSE does not automatically subtract a target from EDGAR totals. A target gap is only valid after gas, sector, LULUCF, base-year and conditionality scopes are confirmed compatible.')
    with tabs[3]:
        if sector.empty:st.info('No EDGAR sector table installed for this entity.')
        else:
            yy=st.select_slider('Sector year',options=sorted(sector.year.dropna().astype(int).unique().tolist()),value=int(sector.year.max()),key='action_sector_year'); ss=sector[sector.year.eq(yy)].sort_values('value_mtco2e')
            fig=go.Figure(go.Bar(x=ss.value_mtco2e,y=ss.sector,orientation='h',marker=dict(color=CYAN),hovertemplate='%{y}<br>%{x:.1f} MtCO₂e<extra></extra>')); fig.update_layout(title=f'Sector emissions · {yy}',showlegend=False)
            st.plotly_chart(_layout(fig,520,'MtCO₂e',False),width='stretch',config={'displayModeBar':False}); st.caption(f'EDGAR 2025 sector-country series · {ps}')
    with tabs[4]:
        if cats.empty:st.info('CAT country-ratings dataset not installed for this entity. ORBIDENSE will not invent a national CAT rating where CAT only assesses a regional entity.')
        else:st.dataframe(cats,width='stretch',hide_index=True)
