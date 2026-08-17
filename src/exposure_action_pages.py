from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.orbidense_theme import get_theme_tokens

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
    t=get_theme_tokens()
    fig.update_layout(
        template=t.get("plot_template","plotly_dark"),
        height=h,
        margin=dict(l=24,r=18,t=54,b=28),
        paper_bgcolor=t["chart_bg"],
        plot_bgcolor=t["chart_bg"],
        font=dict(color=t["text"],family="Inter, Arial, sans-serif",size=12),
        colorway=t.get("colorway"),
        hoverlabel=dict(bgcolor=t["surface"],bordercolor=t["border"],font=dict(color=t["text"],size=12)),
        legend=dict(orientation="h",y=1.08,x=0,bgcolor="rgba(0,0,0,0)",font=dict(color=t["muted"],size=11)),
        showlegend=legend,
    )
    fig.update_xaxes(showgrid=False,zeroline=False,color=t["chart_axis"],linecolor=t["border_soft"],tickfont=dict(color=t["chart_axis"],size=11))
    fig.update_yaxes(gridcolor=t["chart_grid"],zeroline=False,color=t["chart_axis"],linecolor=t["border_soft"],tickfont=dict(color=t["chart_axis"],size=11),title=y,title_font=dict(color=t["chart_axis"],size=12))
    return fig



def _card(label,value,note='',accent=CYAN):
    st.markdown(
        f"""<div class="orb-card" style="
          border-top:2px solid {accent};
          background:linear-gradient(145deg,var(--orb-surface),var(--orb-surface-2));
          border-color:var(--orb-border-soft);
          box-shadow:var(--orb-shadow);
        ">
          <small style="color:var(--orb-muted-2)">{label}</small>
          <div class="orb-big" style="color:var(--orb-text)">{value}</div>
          <div class="orb-note" style="color:var(--orb-muted)">{note}</div>
        </div>""",
        unsafe_allow_html=True
    )



def _num(v):
    try: v=float(v)
    except: return '—'
    if not math.isfinite(v): return '—'
    if abs(v)>=1e9: return f'{v/1e9:.2f}B'
    if abs(v)>=1e6: return f'{v/1e6:.2f}M'
    if abs(v)>=1e3: return f'{v/1e3:.1f}k'
    return f'{v:.1f}'


def render_population_exposure_tab(*,iso3,country,scenario,period,statistic):
    d,p=_read([Path('data/climate_intelligence/population_exposure.parquet'),Path('data/climate_intelligence/population_exposure.csv')])
    if d is None:
        st.markdown('''<div class="orb-hero"><div class="orb-section-title">Population Exposure data is not built yet</div><div class="orb-sub">Run the supplied population-exposure builder. It overlays CCKP population and HD30/HD35 grids before country aggregation; ORBIDENSE does not multiply national population by a national mean hazard.</div></div>''',unsafe_allow_html=True)
        st.code('python .\\scripts\\build_population_exposure.py --scenarios ssp245 --periods 2040-2059 --stats median --hazards hd30\npython .\\scripts\\validate_population_exposure.py',language='powershell')
        return
    for c in ['iso3','scenario','period','statistic','hazard']:
        d[c]=d[c].astype(str)
    d['iso3']=d.iso3.str.upper(); d['scenario']=d.scenario.str.lower(); d['statistic']=d.statistic.str.lower(); d['hazard']=d.hazard.str.lower()
    for c in ['threshold_days','population_total','population_exposed','exposed_share_pct']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    hazard=st.radio('Exposure hazard',['hd30','hd35'],horizontal=True,format_func=lambda x:'Hot days >30°C' if x=='hd30' else 'Very hot days >35°C',key='exp_hazard')
    ths=sorted(d.loc[d.hazard.eq(hazard),'threshold_days'].dropna().unique())
    if not ths: st.info('No thresholds available.'); return
    default=min(ths,key=lambda x:abs(x-(60 if hazard=='hd30' else 10)))
    threshold=st.select_slider('Exposure threshold · annual hazard days',options=ths,value=default,key='exp_threshold')
    q=d[(d.iso3.eq(iso3.upper()))&(d.scenario.eq(scenario.lower()))&(d.period.eq(period))&(d.statistic.eq(statistic.lower()))&(d.hazard.eq(hazard))&(d.threshold_days.eq(threshold))]
    if q.empty: st.warning('No exposure record for this exact selection.'); return
    r=q.iloc[0]
    near=d[(d.iso3.eq(iso3.upper()))&(d.scenario.eq(scenario.lower()))&(d.period.eq('2020-2039'))&(d.statistic.eq(statistic.lower()))&(d.hazard.eq(hazard))&(d.threshold_days.eq(threshold))]
    delta=None if near.empty else float(r.exposed_share_pct)-float(near.iloc[0].exposed_share_pct)
    cols=st.columns(4,gap='small')
    vals=[('Projected population',_num(r.population_total),f'{period} · scenario-aligned',CYAN),('People exposed',_num(r.population_exposed),f'{hazard.upper()} ≥ {threshold:g} days/yr',ORANGE),('Share exposed',f'{float(r.exposed_share_pct):.1f}%','of projected population',RED),('Change vs 2020–2039','—' if delta is None else f'{delta:+.1f} pp','percentage points',PURPLE)]
    for col,(a,b,c,ac) in zip(cols,vals):
        with col:_card(a,b,c,ac)
    left,right=st.columns([1.45,.85],gap='medium')
    with left:
        curve=d[(d.iso3.eq(iso3.upper()))&(d.scenario.eq(scenario.lower()))&(d.period.eq(period))&(d.statistic.eq(statistic.lower()))&(d.hazard.eq(hazard))].sort_values('threshold_days')
        fig=go.Figure(go.Scatter(x=curve.threshold_days,y=curve.exposed_share_pct,mode='lines+markers',line=dict(color=CYAN,width=3),fill='tozeroy',fillcolor='rgba(47,225,242,.09)',hovertemplate='≥ %{x:.0f} days/yr<br>%{y:.1f}% exposed<extra></extra>'))
        fig.add_vline(x=threshold,line_dash='dot',line_color=ORANGE); fig.update_layout(title=f'Exposure curve · {country} · {period}')
        st.plotly_chart(_layout(fig,390,'Population exposed (%)',False),width='stretch',config={'displayModeBar':False})
    with right:
        pp=d[(d.iso3.eq(iso3.upper()))&(d.scenario.eq(scenario.lower()))&(d.statistic.eq(statistic.lower()))&(d.hazard.eq(hazard))&(d.threshold_days.eq(threshold))].copy(); order={'2020-2039':0,'2040-2059':1,'2060-2079':2,'2080-2099':3}; pp['_o']=pp.period.map(order); pp=pp.sort_values('_o')
        fig=go.Figure(go.Bar(x=pp.period,y=pp.exposed_share_pct,marker=dict(color=[BLUE,CYAN,ORANGE,RED][:len(pp)]),text=[f'{v:.1f}%' for v in pp.exposed_share_pct],textposition='outside')); fig.update_layout(title='Exposure through the century',showlegend=False)
        st.plotly_chart(_layout(fig,390,'Exposed (%)',False),width='stretch',config={'displayModeBar':False})
    world=d[(d.scenario.eq(scenario.lower()))&(d.period.eq(period))&(d.statistic.eq(statistic.lower()))&(d.hazard.eq(hazard))&(d.threshold_days.eq(threshold))]
    fig=go.Figure(go.Choropleth(locations=world.iso3,z=world.exposed_share_pct,text=world.country,locationmode='ISO-3',colorscale='YlOrRd',zmin=0,zmax=100,marker_line_color='rgba(255,255,255,.12)',marker_line_width=.25,colorbar=dict(title='Exposed %',thickness=12),hovertemplate='<b>%{text}</b><br>%{z:.1f}% exposed<extra></extra>'))
    fig.update_geos(projection_type='natural earth',showframe=False,showcoastlines=False,bgcolor='rgba(0,0,0,0)',landcolor='#0b1d2b'); fig.update_layout(title=f'Global exposure · {hazard.upper()} ≥ {threshold:g} days/year · {period}')
    st.plotly_chart(_layout(fig,470,None,False),width='stretch',config={'displayModeBar':False})
    st.caption(f'Source: World Bank CCKP pop-x0.25 + CCKP CMIP6 {hazard.upper()} grids. Grid overlay precedes country aggregation. Dataset: {p}')


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
