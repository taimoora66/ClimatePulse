from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from src.profile import (
    ABOUT_EARTH_PATH,
    BUILDER_BIO,
    BUILDER_DEGREE,
    BUILDER_HEADLINE,
    BUILDER_INTERESTS,
    BUILDER_MISSION,
    BUILDER_NAME,
    BUILDER_UNIVERSITY,
    GITHUB_URL,
    LINKEDIN_URL,
    PROFILE_PHOTO_PATH,
    PROJECT_MOTIVATION,
)


def _safe(value) -> str:
    return html.escape(str(value or ""))


def _data_uri(path_value: str) -> str | None:
    path = Path(path_value)
    if not path.exists():
        return None
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render_about_page() -> None:
    portrait = _data_uri(PROFILE_PHOTO_PATH)
    earth = _data_uri(ABOUT_EARTH_PATH)

    st.markdown("""
<style>
.cpab{--b:rgba(149,204,227,.24);--txt:#f6fbfd;--mut:#9db2c0;--cyan:#62e8ef;--blue:#76d3ff;max-width:1450px;margin:0 auto;color:var(--txt)}
.cpab *{box-sizing:border-box}.cpab-card{position:relative;overflow:hidden;border:1px solid var(--b);border-radius:18px;background:radial-gradient(circle at 90% 10%,rgba(66,224,234,.08),transparent 28%),linear-gradient(145deg,#102434,#081722);box-shadow:0 16px 36px rgba(0,0,0,.2)}
.cpab-top{display:flex;justify-content:space-between;align-items:center;gap:14px;margin:0 0 15px}.cpab-top h1{margin:0;font-size:clamp(24px,2.6vw,36px);letter-spacing:-.03em}.cpab-status{display:flex;align-items:center;gap:7px;border:1px solid rgba(91,224,173,.27);background:rgba(31,104,77,.12);padding:8px 11px;border-radius:999px;color:#c8f3df;font-size:10px;font-weight:700}.cpab-dot{width:7px;height:7px;border-radius:50%;background:#67e5a8;box-shadow:0 0 10px rgba(103,229,168,.75)}
.cpab-grid{display:grid;grid-template-columns:1.48fr .82fr;gap:12px}.cpab-main{min-height:455px;padding:27px 29px}.cpab-globe{width:215px;height:215px;border-radius:50%;background-size:cover;background-position:center;border:1px solid rgba(116,219,242,.28);box-shadow:0 0 0 11px rgba(71,219,232,.03),0 0 38px rgba(71,219,232,.14);margin-bottom:24px}.cpab-main-title{font-size:clamp(38px,4.4vw,59px);font-weight:850;line-height:1;letter-spacing:-.04em}.cpab-main-title span{color:var(--blue)}.cpab-sub{font-size:15px;color:#79d4e8;font-weight:700;margin-top:14px}.cpab-copy{font-size:12px;color:#c6d5de;line-height:1.7;margin-top:11px;max-width:760px}
.cpab-creator{min-height:455px;padding:23px 20px;text-align:center}.cpab-label{text-align:left;color:#88a5b5;font-size:10px;font-weight:800;letter-spacing:.13em}.cpab-avatar{width:195px;height:195px;margin:24px auto 17px;overflow:hidden;clip-path:polygon(25% 4%,75% 4%,98% 50%,75% 96%,25% 96%,2% 50%);background:#e8ecef;border:1px solid rgba(114,219,240,.36);box-shadow:0 0 30px rgba(66,220,232,.15)}.cpab-avatar img{width:100%;height:100%;object-fit:cover;object-position:center 14%}.cpab-name{font-size:27px;font-weight:830}.cpab-degree{font-size:11px;line-height:1.45;color:#dbe6eb;margin-top:7px}.cpab-uni{font-size:10px;color:#9fb5c2;margin-top:3px}.cpab-headline{font-size:9px;color:#72dce9;margin-top:8px}.cpab-socials{display:flex;justify-content:center;gap:9px;flex-wrap:wrap;margin-top:17px}.cpab-social{display:inline-flex;align-items:center;gap:6px;padding:0 14px;min-height:37px;border-radius:999px;border:1px solid rgba(78,225,234,.55);background:rgba(16,61,78,.7);color:#f2fcff!important;text-decoration:none!important;font-size:10px;font-weight:750}
.cpab-second{display:grid;grid-template-columns:1.48fr .82fr;gap:12px;margin-top:12px}.cpab-about,.cpab-focus{min-height:320px;padding:24px 25px}.cpab-kicker{color:#7fd9e8;font-size:10px;font-weight:820;letter-spacing:.13em}.cpab-section-title{font-size:22px;font-weight:800;line-height:1.15;margin-top:8px}.cpab-aboutcopy{width:52%;position:relative;z-index:2}.cpab-wave{position:absolute;right:0;bottom:0;width:62%;height:80%;opacity:.85;background:radial-gradient(ellipse at 65% 66%,rgba(73,223,233,.14),transparent 40%)}.cpab-wave:before{content:"";position:absolute;left:4%;right:-6%;top:45%;height:2px;background:linear-gradient(90deg,transparent,#5de5ed,transparent);transform:rotate(-10deg);box-shadow:0 -18px 0 rgba(93,229,237,.20),0 18px 0 rgba(93,229,237,.16),0 36px 0 rgba(93,229,237,.10)}.cpab-focuslist{display:grid;gap:8px;margin-top:15px}.cpab-chip{display:flex;align-items:center;gap:8px;width:max-content;max-width:100%;padding:9px 11px;border:1px solid rgba(75,224,233,.38);border-radius:10px;background:rgba(17,63,80,.62);font-size:10px;font-weight:700}.cpab-mission{margin-top:19px;padding-top:15px;border-top:1px solid rgba(139,188,212,.13);font-size:11px;line-height:1.55;color:#d0dde4}
.cpab-research{margin-top:12px;padding:22px 24px}.cpab-rgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-top:15px}.cpab-ritem{padding:14px;border:1px solid rgba(130,187,212,.12);border-radius:11px;background:rgba(9,28,41,.72);min-height:118px}.cpab-ritem b{font-size:11px}.cpab-ritem p{font-size:9px;line-height:1.5;color:#8099a7;margin:5px 0 0}
.cpab-explore-title{margin:22px 2px 11px;color:#9bb2c0;font-size:10px;font-weight:820;letter-spacing:.13em}.cpab-explore{display:grid;grid-template-columns:1fr 1fr;gap:10px}.cpab-explore-card{display:grid;grid-template-columns:50px 1fr;gap:13px;align-items:center;padding:16px 18px;min-height:108px}.cpab-icon{width:47px;height:47px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:1px solid rgba(79,224,233,.25);background:rgba(31,89,107,.3);color:#91eaf2;font-size:17px}.cpab-explore-card b{font-size:11px}.cpab-explore-card p{font-size:9px;color:#8099a8;line-height:1.45;margin:4px 0 0}
.cpab-bottom{display:grid;grid-template-columns:1.04fr .96fr;gap:10px;margin-top:10px}.cpab-data,.cpab-method{padding:16px 18px;min-height:105px}.cpab-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.cpab-tag{padding:5px 7px;border-radius:6px;background:rgba(106,164,190,.1);border:1px solid rgba(108,174,202,.1);font-size:9px;color:#acc4d0}.cpab-method{display:grid;grid-template-columns:40px 1fr;gap:11px;align-items:center}.cpab-method-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:rgba(40,116,146,.14);color:#72dce9;border:1px solid rgba(81,201,224,.16)}
@media(max-width:700px){.cpab-grid,.cpab-second{grid-template-columns:1.2fr .8fr;gap:8px}.cpab-main,.cpab-creator{min-height:385px;padding:15px}.cpab-globe{width:120px;height:120px;margin-bottom:16px}.cpab-main-title{font-size:27px}.cpab-sub{font-size:10px}.cpab-copy{font-size:8px}.cpab-avatar{width:100px;height:100px;margin-top:20px}.cpab-name{font-size:16px}.cpab-degree,.cpab-uni,.cpab-headline{font-size:7.5px}.cpab-social{font-size:7.5px;min-height:29px;padding:0 8px}.cpab-about,.cpab-focus{min-height:275px;padding:15px}.cpab-aboutcopy{width:67%}.cpab-section-title{font-size:15px}.cpab-chip{font-size:7.5px;padding:7px}.cpab-rgrid{grid-template-columns:1fr}.cpab-explore{gap:8px}.cpab-explore-card{grid-template-columns:35px 1fr;min-height:88px;padding:11px}.cpab-icon{width:34px;height:34px}.cpab-bottom{gap:8px}}
@media(max-width:470px){.cpab-grid,.cpab-second,.cpab-explore,.cpab-bottom{grid-template-columns:1fr}.cpab-main,.cpab-creator{min-height:auto}.cpab-aboutcopy{width:70%}}
</style>
        """,
        unsafe_allow_html=True,
    )

    earth_style = (
        f'background-image:url("{earth}");'
        if earth
        else "background:radial-gradient(circle,#227d96,#12394e 45%,#06101b 75%);"
    )

    avatar_html = (
        f'<img src="{portrait}" alt="{_safe(BUILDER_NAME)}">'
        if portrait
        else '<div style="padding:70px 20px;color:#708b9b;font-size:10px;">Add assets/profile.jpg</div>'
    )

    interests = "".join(
        f'<div class="cpab-chip">✦ {_safe(item)}</div>'
        for item in BUILDER_INTERESTS
    )

    socials = []
    if LINKEDIN_URL:
        socials.append(
            f'<a class="cpab-social" href="{_safe(LINKEDIN_URL)}" target="_blank">in LinkedIn</a>'
        )
    if GITHUB_URL:
        socials.append(
            f'<a class="cpab-social" href="{_safe(GITHUB_URL)}" target="_blank">◉ GitHub</a>'
        )

    st.html(
        f"""
<div class="cpab">
  <div class="cpab-top">
    <h1>GLOBAL CLIMATE INTELLIGENCE</h1>
    <div class="cpab-status"><span class="cpab-dot"></span>All systems normal <span style="opacity:.55;">· Live Earth online</span></div>
  </div>

  <div class="cpab-grid">
    <section class="cpab-card cpab-main">
      <div class="cpab-globe" style='{earth_style}'></div>
      <div class="cpab-main-title">Global Climate <span>Intelligence</span></div>
      <div class="cpab-sub">Historical climate · live environmental telemetry · predictive climate models</div>
      <div class="cpab-copy">
        ClimatePulse is an advanced environmental-intelligence platform harmonizing
        current conditions, observed climate records and future climate-model
        projections in one coherent, data-driven interface.
      </div>
      <div class="cpab-copy" style="color:#8fa5b4;font-size:10px;">
        Built to support exploration and comparison while keeping point weather,
        reanalysis, national climate indicators and future model projections
        scientifically distinct.
      </div>
    </section>

    <section class="cpab-card cpab-creator">
      <div class="cpab-label">THE CREATOR:</div>
      <div class="cpab-avatar">{avatar_html}</div>
      <div class="cpab-name">{_safe(BUILDER_NAME)}</div>
      <div class="cpab-degree">{_safe(BUILDER_DEGREE)}</div>
      <div class="cpab-uni">{_safe(BUILDER_UNIVERSITY)}</div>
      <div class="cpab-headline">{_safe(BUILDER_HEADLINE)}</div>
      <div class="cpab-socials">{''.join(socials)}</div>
    </section>
  </div>

  <div class="cpab-second">
    <section class="cpab-card cpab-about">
      <div class="cpab-aboutcopy">
        <div class="cpab-kicker">ABOUT CLIMATEPULSE</div>
        <div class="cpab-section-title">Environmental change in one connected workspace</div>
        <div class="cpab-copy">{_safe(PROJECT_MOTIVATION)}</div>
      </div>
      <div class="cpab-wave"></div>
    </section>

    <section class="cpab-card cpab-focus">
      <div class="cpab-kicker">CORE FOCUS</div>
      <div class="cpab-focuslist">{interests}</div>
      <div class="cpab-mission">
        <div class="cpab-kicker">MISSION STATEMENT</div>
        <div style="margin-top:8px;">{_safe(BUILDER_MISSION)}</div>
      </div>
    </section>
  </div>

  <section class="cpab-card cpab-research">
    <div class="cpab-kicker">RESEARCH & DEVELOPMENT DIRECTION</div>
    <div class="cpab-section-title">Climate science, environmental risk and responsible AI</div>
    <div class="cpab-copy" style="max-width:1050px;">
      {_safe(BUILDER_BIO)}
      A central development interest is the responsible integration of AI with
      climate and environmental information — using AI to support discovery,
      interpretation and decision support while keeping source data, uncertainty
      and methodological limitations visible.
    </div>
    <div class="cpab-rgrid">
      <div class="cpab-ritem"><b>Data-grounded AI</b><p>AI-supported interpretation should remain tied to traceable environmental datasets instead of replacing primary evidence.</p></div>
      <div class="cpab-ritem"><b>Risk & uncertainty</b><p>Environmental intelligence should communicate spatial scope, hazard, exposure, vulnerability and model uncertainty.</p></div>
      <div class="cpab-ritem"><b>Probabilistic decision support</b><p>Longer-term interest in probabilistic and data-driven decision support for climate adaptation and environmental-risk applications.</p></div>
    </div>
  </section>

  <div class="cpab-explore-title">EXPLORE CLIMATEPULSE</div>

  <div class="cpab-explore">
    <section class="cpab-card cpab-explore-card"><div class="cpab-icon">☁</div><div><b>Live Conditions</b><p>Current weather, air quality and environmental conditions.</p></div></section>
    <section class="cpab-card cpab-explore-card"><div class="cpab-icon">▥</div><div><b>Historical Climate</b><p>Explore observed climate trends, anomalies, extremes and variability.</p></div></section>
    <section class="cpab-card cpab-explore-card"><div class="cpab-icon">⌁</div><div><b>Future Climate</b><p>Climate-model projections, future scenarios and model spread.</p></div></section>
    <section class="cpab-card cpab-explore-card"><div class="cpab-icon">◉</div><div><b>Compare Places</b><p>Compare cities and countries across present, historical and future context.</p></div></section>
  </div>

  <div class="cpab-bottom">
    <section class="cpab-card cpab-data">
      <div class="cpab-kicker">DATA & METHODS</div>
      <div class="cpab-tags">
        <span class="cpab-tag">ERA5</span><span class="cpab-tag">CRU</span>
        <span class="cpab-tag">CMIP6</span><span class="cpab-tag">Open-Meteo</span>
        <span class="cpab-tag">PostgreSQL / Neon</span><span class="cpab-tag">MapTiler</span>
      </div>
    </section>

    <section class="cpab-card cpab-method">
      <div class="cpab-method-icon">▤</div>
      <div>
        <b style="font-size:10px;">Methodology, sources & limitations</b>
        <div style="font-size:9px;color:#829aaa;line-height:1.45;margin-top:4px;">
          Learn how data are collected, processed and interpreted while preserving
          the distinction between point, national and model-based climate information.
        </div>
      </div>
    </section>
  </div>
</div>
        """
    )

    with st.expander("Methodology, data sources & limitations", expanded=False):
        st.markdown(
            """
**Live conditions** are coordinate-based. A country live-weather point is a
representative location and is not a national spatial-average weather value.

**Historical place climate** uses point-based reanalysis and is kept separate
from country-level spatial aggregates.

**Country climate** uses national spatial-average datasets where available.

**Future climate** uses climate-model projections and communicates scenario or
model spread where supported by the underlying source.

**AI features** are intended as an interface to environmental information and
decision support, not as a replacement for primary scientific datasets or
professional risk assessment.

ClimatePulse is an independent informational and exploratory project. It is not
an official meteorological service.
            """
        )