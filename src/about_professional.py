from __future__ import annotations

from pathlib import Path
import streamlit as st


def _find_creator_photo() -> Path | None:
    for path in [
        Path('assets/creator.jpg'),
        Path('assets/creator.jpeg'),
        Path('assets/creator.png'),
        Path('assets/taimoor.jpg'),
        Path('assets/taimoor.jpeg'),
        Path('assets/taimoor.png'),
        Path('assets/profile.jpg'),
        Path('assets/profile.png'),
    ]:
        if path.exists():
            return path
    return None


def _css() -> None:
    st.markdown('''
<style>
.about-eyebrow{color:#5bdff0;font-size:.72rem;font-weight:850;letter-spacing:.15em;text-transform:uppercase;margin-bottom:.45rem}
.about-title{color:#f7fbff;font-size:2.25rem;font-weight:900;line-height:1.02;letter-spacing:-.035em;margin-bottom:.55rem}
.about-lead{color:#91a8b8;font-size:.98rem;line-height:1.6;max-width:930px}
.about-card{height:100%;border:1px solid rgba(121,181,207,.16);border-radius:18px;padding:18px;background:linear-gradient(145deg,rgba(11,33,50,.96),rgba(5,18,29,.98));box-shadow:0 16px 38px rgba(0,0,0,.17)}
.about-card h3{color:#f5fbff;font-size:1.05rem;margin:0 0 .45rem}.about-card p,.about-card li{color:#92a9b9;font-size:.82rem;line-height:1.55}
.about-chip{display:inline-flex;margin:4px 5px 4px 0;padding:6px 9px;border:1px solid rgba(47,225,242,.2);border-radius:999px;color:#8debf5;background:rgba(47,225,242,.07);font-size:.7rem;font-weight:750}
.about-section{color:#f4fbff;font-size:1.22rem;font-weight:900;margin:1.35rem 0 .7rem}
.about-stat{border:1px solid rgba(121,181,207,.14);border-radius:15px;padding:14px 15px;background:rgba(8,24,38,.86)}
.about-stat-label{color:#7f98aa;text-transform:uppercase;font-size:.65rem;font-weight:800;letter-spacing:.08em}.about-stat-value{color:#fff;font-size:1.42rem;font-weight:900;margin-top:.3rem}.about-stat-note{color:#7f98aa;font-size:.7rem;margin-top:.2rem}
.about-photo-frame{border:1px solid rgba(47,225,242,.2);border-radius:20px;padding:8px;background:linear-gradient(145deg,rgba(13,42,58,.95),rgba(5,18,28,.97));box-shadow:0 18px 42px rgba(0,0,0,.22)}
.about-quote{border-left:3px solid #42d8ec;padding:13px 15px;border-radius:0 12px 12px 0;background:rgba(47,225,242,.055);color:#b7cad5;line-height:1.6;font-size:.86rem}
</style>
''', unsafe_allow_html=True)


def render_professional_about() -> None:
    _css()
    st.markdown('''
<div class="about-eyebrow">ABOUT ORBIDENSE AI</div>
<div class="about-title">Earth data. Climate intelligence. Better decisions.</div>
<div class="about-lead">ORBIDENSE AI is an independent environmental and climate-intelligence project built to make complex Earth-system information easier to explore, compare and interpret without hiding scientific uncertainty or data provenance.</div>
''', unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    left, right = st.columns([0.78, 1.35], gap='large')

    with left:
        photo = _find_creator_photo()
        if photo:
            st.markdown('<div class="about-photo-frame">', unsafe_allow_html=True)
            st.image(str(photo), width='stretch')
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('''<div class="about-card"><h3>Creator portrait</h3><p>Add your portrait as <b>assets/creator.jpg</b> or <b>assets/creator.png</b>. The page detects it automatically.</p></div>''', unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown('''
<div class="about-card">
<div class="about-eyebrow">PROJECT CREATOR</div><h3>Taimoor Ahmad</h3>
<p><b style="color:#d8edf4">MSc · Environmental Change & Global Sustainability</b><br>University of Milan</p>
<p>Independent environmental-data builder focused on climate science, environmental risk, sustainability analytics and decision-oriented digital tools.</p>
</div>
''', unsafe_allow_html=True)

    with right:
        st.markdown('''
<div class="about-card"><div class="about-eyebrow">WHY ORBIDENSE AI</div>
<h3>Turning fragmented environmental data into usable intelligence</h3>
<p>Climate information is often split across weather APIs, reanalysis archives, climate-model products, emissions databases, policy trackers and risk frameworks. ORBIDENSE AI brings these layers into one coherent experience while preserving the distinction between observed conditions, historical climate, future projections, exposure, vulnerability and policy action.</p>
<div class="about-quote">The goal is not another dashboard full of disconnected numbers. The goal is a transparent Earth-intelligence environment where users can understand what is happening, what may happen, how places differ, and whether climate action is keeping pace.</div></div>
''', unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown('''
<div class="about-card"><div class="about-eyebrow">FOCUS AREAS</div>
<span class="about-chip">Climate change</span><span class="about-chip">Global sustainability</span><span class="about-chip">Environmental risk</span><span class="about-chip">Climate projections</span><span class="about-chip">Climate extremes</span><span class="about-chip">Emissions & transition</span><span class="about-chip">Probabilistic modelling</span><span class="about-chip">Bayesian reasoning</span><span class="about-chip">Environmental data engineering</span><span class="about-chip">Scientific visualization</span><span class="about-chip">Decision support</span><span class="about-chip">Earth-data platforms</span>
</div>
''', unsafe_allow_html=True)

    st.markdown('<div class="about-section">What the platform is built to answer</div>', unsafe_allow_html=True)
    cols = st.columns(4, gap='small')
    content = [
        ('NOW','Live Earth','What is happening right now?'),
        ('OUTLOOK','Future climate','How could conditions change?'),
        ('ACTION','Transition','Are policies and targets aligned?'),
        ('GLOBAL','Patterns','Where are hotspots and divergences?'),
    ]
    for col,(lab,val,note) in zip(cols,content):
        with col:
            st.markdown(f'<div class="about-stat"><div class="about-stat-label">{lab}</div><div class="about-stat-value">{val}</div><div class="about-stat-note">{note}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="about-section">Research & technical interests</div>', unsafe_allow_html=True)
    a,b,c = st.columns(3, gap='small')
    with a:
        st.markdown('''<div class="about-card"><h3>Climate & environmental science</h3><ul><li>Observed and projected climate change</li><li>Extreme heat and precipitation</li><li>Exposure, vulnerability and climate risk</li><li>Climate mitigation and transition pathways</li><li>Environmental change and sustainability</li></ul></div>''', unsafe_allow_html=True)
    with b:
        st.markdown('''<div class="about-card"><h3>Quantitative modelling</h3><ul><li>Probabilistic environmental prediction</li><li>Bayesian statistics and graphical models</li><li>Uncertainty-aware analysis</li><li>Scenario comparison</li><li>Decision-oriented risk interpretation</li></ul></div>''', unsafe_allow_html=True)
    with c:
        st.markdown('''<div class="about-card"><h3>Data & product engineering</h3><ul><li>Environmental data pipelines</li><li>Geospatial and gridded climate data</li><li>Scientific web visualization</li><li>Database-backed environmental analytics</li><li>Human-readable climate intelligence</li></ul></div>''', unsafe_allow_html=True)

    st.markdown('<div class="about-section">Science & transparency</div>', unsafe_allow_html=True)
    tabs = st.tabs(['Methodology','Data Sources','Coverage','Limitations','References'])
    with tabs[0]:
        st.markdown('''- Current weather is not climate.\n- Historical/reanalysis climate is not a future projection.\n- A model projection is conditional on a scenario rather than a deterministic forecast.\n- Hazard is not equivalent to risk.\n- P10 / median / P90 represent ensemble percentiles, not formal confidence intervals.\n- Country averages hide subnational variability.''')
    with tabs[1]:
        st.markdown('''**Current / operational:** Open-Meteo and configured live providers.  \n**Historical climate:** ERA5 / CRU.  \n**Future climate:** World Bank Climate Change Knowledge Portal / CMIP6.  \n**Climate action roadmap:** EDGAR, UNFCCC / Climate Watch, Climate Action Tracker.  \n**Risk / exposure roadmap:** population-exposure layers and INFORM where appropriate.''')
    with tabs[2]:
        st.markdown('The validated climate-projection layer currently covers **245 countries and territories** across four SSP pathways, four future periods and P10/median/P90 ensemble statistics.')
    with tabs[3]:
        st.markdown('''- Country-level climate aggregates suppress local spatial differences.\n- Model ensemble spread does not represent every source of uncertainty.\n- Live conditions can be point-based rather than area-wide.\n- Climate-action datasets update at different intervals.\n- Composite risk metrics should not be created without explicit hazard, exposure and vulnerability methodology.''')
    with tabs[4]:
        st.markdown('ORBIDENSE AI keeps detailed references and processing notes in project documentation and dataset metadata so visual pages can remain readable while scientific provenance stays auditable.')
