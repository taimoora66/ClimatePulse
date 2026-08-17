from __future__ import annotations

from pathlib import Path
import base64
import html

import streamlit as st

try:
    from src.profile import (
        BUILDER_NAME,
        BUILDER_HEADLINE,
        BUILDER_BIO,
        BUILDER_INTERESTS,
        BUILDER_DEGREE,
        BUILDER_UNIVERSITY,
        PROFILE_PHOTO_PATH,
        LINKEDIN_URL,
        GITHUB_URL,
    )
except ImportError:
    from src.profile import (
        BUILDER_NAME,
        BUILDER_HEADLINE,
        BUILDER_BIO,
        PROFILE_PHOTO_PATH,
        LINKEDIN_URL,
        GITHUB_URL,
    )
    BUILDER_INTERESTS = (
        "Climate Data",
        "Environmental Risk Analysis",
        "AI for Climate & Environment",
        "Probabilistic Decision Support",
        "Scientific Data Engineering",
    )
    BUILDER_DEGREE = "MSc Environmental Change & Global Sustainability"
    BUILDER_UNIVERSITY = "University of Milan"


FUTURE_UPDATES = (
    "City-Scale Climate Digital Twin",
    "High-Resolution Downscaled Climate Projections",
    "Satellite & Remote-Sensing Intelligence",
    "Probabilistic Climate-Risk & Adaptation Decision Support",
    "Infrastructure & Asset Exposure Analytics",
    "Real-Time Environmental Alerts & Public API",
)

METHODOLOGY_ITEMS = (
    (
        "Climate projections",
        "Future climate values are scenario-conditioned CMIP6 projections from the validated World Bank CCKP country layer. "
        "P10, median and P90 are model-ensemble percentiles rather than forecast probabilities or confidence intervals.",
    ),
    (
        "Climate-action evidence",
        "Historical national and sector greenhouse-gas evidence is kept analytically separate from SSP projections. "
        "Action indicators are interpreted from their own source years and accounting definitions.",
    ),
    (
        "Exposure",
        "Population exposure reports people located within modeled heat-hazard conditions. "
        "ORBIDENSE does not label exposure alone as vulnerability or full climate risk.",
    ),
    (
        "Comparison",
        "Country comparisons use the same indicator, scenario, future period and statistic so that the displayed values share one definition and scale.",
    ),
)

LIMITATIONS = (
    "Country averages suppress important sub-national variability and should not be used as neighbourhood-scale estimates.",
    "Model-ensemble spread does not represent every source of climate uncertainty.",
    "Current weather at a point is not interchangeable with national historical climate or future climate projections.",
    "Exposure does not by itself measure vulnerability, adaptive capacity, health impact or economic damage.",
    "Policy, target and emissions datasets update on different schedules and must be interpreted with their source year and accounting basis.",
    "ORBIDENSE is an analytical information platform, not an official warning service or a substitute for specialist climate-risk assessment.",
)

REFERENCES = (
    ("World Bank Climate Change Knowledge Portal (CCKP) / CMIP6", "Future country climate projections"),
    ("ECMWF ERA5 and CRU", "Historical / reanalysis climate context used by the wider project"),
    ("Open-Meteo and configured operational providers", "Current environmental and weather context"),
    ("EDGAR", "National and sector greenhouse-gas emissions"),
    ("UNFCCC / Climate Watch", "Targets and nationally determined contribution data where installed"),
    ("Climate Action Tracker", "Policy-assessment evidence where the relevant entity is assessed"),
    ("SSP population / INFORM", "Exposure and broader risk-roadmap sources where supported by installed datasets"),
)


def _safe(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _find_creator_photo() -> Path | None:
    for path in (
        Path(PROFILE_PHOTO_PATH),
        Path("assets/profile.jpg"),
        Path("assets/profile.png"),
        Path("assets/creator.jpg"),
    ):
        if path.exists():
            return path
    return None


def _image_uri(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    return f"data:image/{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _css() -> None:
    st.markdown(
        """
<style>
.orb-about{max-width:1500px;margin:0 auto;color:var(--orb-text)}
.orb-about-hero,.orb-about-card,.orb-science-card{
  border:1px solid var(--orb-border-soft);
  background:linear-gradient(145deg,var(--orb-surface),var(--orb-surface-2));
  box-shadow:var(--orb-shadow);
}
.orb-about-hero{overflow:hidden;border-radius:20px;padding:clamp(24px,3.1vw,46px);
background:radial-gradient(circle at 88% 18%,var(--orb-primary-soft),transparent 27%),
linear-gradient(135deg,var(--orb-surface),var(--orb-surface-2))}
.orb-about-eyebrow,.orb-about-label{color:var(--orb-primary);font-size:.72rem;font-weight:950;letter-spacing:.14em;text-transform:uppercase}
.orb-about-title{margin:.45rem 0 .58rem;color:var(--orb-text);font-size:clamp(2.25rem,4vw,4.15rem);font-weight:950;line-height:.99;letter-spacing:-.05em}
.orb-about-title span{color:var(--orb-secondary)}
.orb-about-lead{max-width:900px;color:var(--orb-muted);font-size:clamp(.98rem,1.15vw,1.13rem);line-height:1.66}
.orb-about-grid{display:grid;grid-template-columns:.92fr 1.45fr;gap:14px;margin-top:14px}
.orb-about-card{border-radius:17px}
.orb-about-portrait{padding:16px;display:flex;align-items:center;justify-content:center}
.orb-about-portrait img{width:100%;max-width:310px;aspect-ratio:4/5;object-fit:cover;border-radius:15px;border:1px solid var(--orb-border)}
.orb-about-profile{padding:clamp(20px,2.4vw,34px)}
.orb-about-name{color:var(--orb-text);font-size:clamp(1.75rem,2.6vw,2.75rem);font-weight:950;letter-spacing:-.035em;margin-top:.28rem}
.orb-about-degree{color:var(--orb-primary);font-size:1rem;font-weight:820;margin-top:.30rem}
.orb-about-uni,.orb-about-bio{color:var(--orb-muted)}
.orb-about-uni{font-size:.92rem;margin-top:.15rem}
.orb-about-bio{font-size:.96rem;line-height:1.64;margin-top:1rem}
.orb-about-divider{height:1px;background:var(--orb-border-soft);margin:1.1rem 0}
.orb-chip-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:.65rem}
.orb-chip{border:1px solid var(--orb-border);border-radius:999px;padding:7px 10px;background:var(--orb-primary-soft);color:var(--orb-text);font-size:.78rem;font-weight:780}
.orb-about-heading{margin:25px 2px 11px;color:var(--orb-text);font-size:1.22rem;font-weight:930;letter-spacing:-.02em}
.orb-roadmap{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.orb-roadmap-item{min-height:88px;display:flex;align-items:center;gap:11px;border:1px solid var(--orb-border-soft);
border-radius:14px;padding:13px 14px;background:linear-gradient(145deg,var(--orb-surface),var(--orb-surface-2))}
.orb-roadmap-no{width:35px;height:35px;flex:0 0 35px;display:grid;place-items:center;border-radius:10px;color:var(--orb-primary);
border:1px solid var(--orb-border);background:var(--orb-primary-soft);font-size:.70rem;font-weight:950}
.orb-roadmap-name{color:var(--orb-text);font-size:.89rem;font-weight:830;line-height:1.40}
.orb-collab{display:grid;grid-template-columns:1.35fr .65fr;gap:14px;margin-top:10px;padding:clamp(18px,2.2vw,30px)}
.orb-collab h3{margin:0 0 .45rem;color:var(--orb-text);font-size:1.38rem}
.orb-collab p{margin:0;color:var(--orb-muted);font-size:.94rem;line-height:1.64}
.orb-socials{display:flex;flex-direction:column;gap:8px;justify-content:center}
.orb-social{display:flex;justify-content:center;align-items:center;min-height:47px;border-radius:11px;text-decoration:none!important;
font-size:.86rem;font-weight:870;color:var(--orb-text)!important;background:var(--orb-primary-soft);border:1px solid var(--orb-border);transition:.16s ease}
.orb-social:hover{transform:translateY(-1px);border-color:var(--orb-primary);background:var(--orb-surface-3)}
.orb-science-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.orb-science-card{border-radius:14px;padding:16px}
.orb-science-title{color:var(--orb-primary);font-size:.70rem;font-weight:950;letter-spacing:.10em;text-transform:uppercase}
.orb-science-copy{color:var(--orb-muted);font-size:.90rem;line-height:1.62;margin-top:6px}
.orb-limit-list{display:grid;gap:8px}
.orb-limit{border-left:3px solid var(--orb-accent);padding:10px 12px;border-radius:0 10px 10px 0;
background:var(--orb-surface);color:var(--orb-muted);font-size:.90rem;line-height:1.55}
.orb-ref-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.orb-ref{border:1px solid var(--orb-border-soft);border-radius:12px;padding:12px 13px;background:var(--orb-surface)}
.orb-ref b{color:var(--orb-text);font-size:.88rem}.orb-ref span{display:block;color:var(--orb-muted);font-size:.80rem;line-height:1.45;margin-top:3px}
.orb-about-foot{color:var(--orb-muted-2);text-align:center;font-size:.77rem;padding:20px 0 4px}
@media(max-width:900px){.orb-about-grid{grid-template-columns:1fr}.orb-roadmap{grid-template-columns:repeat(2,minmax(0,1fr))}
.orb-collab{grid-template-columns:1fr}.orb-science-grid,.orb-ref-grid{grid-template-columns:1fr}}
@media(max-width:600px){.orb-roadmap{grid-template-columns:1fr}.orb-about-hero{padding:22px 18px}.orb-about-profile{padding:20px 17px}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_professional_about() -> None:
    _css()

    portrait_uri = _image_uri(_find_creator_photo())
    portrait_html = (
        f'<img src="{portrait_uri}" alt="{_safe(BUILDER_NAME)}">'
        if portrait_uri
        else '<div style="color:var(--orb-muted);padding:60px 15px;text-align:center">Creator portrait</div>'
    )

    interests = "".join(
        f'<span class="orb-chip">{_safe(item)}</span>'
        for item in BUILDER_INTERESTS
    )
    roadmap = "".join(
        f'<div class="orb-roadmap-item"><div class="orb-roadmap-no">{i:02d}</div><div class="orb-roadmap-name">{_safe(name)}</div></div>'
        for i, name in enumerate(FUTURE_UPDATES, 1)
    )
    methodology = "".join(
        f'<div class="orb-science-card"><div class="orb-science-title">{_safe(title)}</div><div class="orb-science-copy">{_safe(copy)}</div></div>'
        for title, copy in METHODOLOGY_ITEMS
    )
    limitations = "".join(
        f'<div class="orb-limit">{_safe(item)}</div>'
        for item in LIMITATIONS
    )
    references = "".join(
        f'<div class="orb-ref"><b>{_safe(source)}</b><span>{_safe(role)}</span></div>'
        for source, role in REFERENCES
    )

    linkedin = _safe(LINKEDIN_URL or "#")
    github = _safe(GITHUB_URL or "https://github.com/taimoora66/ORBIDENSE-AI")

    st.markdown(
        f"""
<div class="orb-about">
  <section class="orb-about-hero">
    <div class="orb-about-eyebrow">ABOUT ORBIDENSE</div>
    <div class="orb-about-title">Earth intelligence.<br><span>Built to become decision infrastructure.</span></div>
    <div class="orb-about-lead">
      ORBIDENSE brings climate projections, population exposure, emissions evidence and transparent analytical
      context into one coherent environment. It is designed to make complex Earth data easier to investigate
      without hiding uncertainty, provenance or scientific limitations.
    </div>
  </section>

  <section class="orb-about-grid">
    <div class="orb-about-card orb-about-portrait">{portrait_html}</div>
    <div class="orb-about-card orb-about-profile">
      <div class="orb-about-label">CREATED BY</div>
      <div class="orb-about-name">{_safe(BUILDER_NAME)}</div>
      <div class="orb-about-degree">{_safe(BUILDER_DEGREE)}</div>
      <div class="orb-about-uni">{_safe(BUILDER_UNIVERSITY)}</div>
      <div class="orb-about-divider"></div>
      <div class="orb-about-bio">{_safe(BUILDER_BIO)}</div>
      <div class="orb-about-divider"></div>
      <div class="orb-about-label">INTERESTS</div>
      <div class="orb-chip-row">{interests}</div>
    </div>
  </section>

  <div class="orb-about-heading">Future updates</div>
  <section class="orb-roadmap">{roadmap}</section>

  <div class="orb-about-heading">Collaboration, feedback & improvement</div>
  <section class="orb-about-card orb-collab">
    <div>
      <h3>Open to building ORBIDENSE with others.</h3>
      <p>
        Research collaboration, scientific review, data partnerships, responsible engineering contributions,
        interface feedback and improvement ideas are welcome—especially from people working across climate science,
        environmental data, geospatial systems, risk analysis, statistics, software engineering and decision support.
      </p>
    </div>
    <div class="orb-socials">
      <a class="orb-social" href="{linkedin}" target="_blank" rel="noopener noreferrer">in&nbsp;&nbsp;LinkedIn ↗</a>
      <a class="orb-social" href="{github}" target="_blank" rel="noopener noreferrer">◉&nbsp;&nbsp;GitHub ↗</a>
    </div>
  </section>

  <div class="orb-about-heading">Science & methodology</div>
  <section class="orb-science-grid">{methodology}</section>

  <div class="orb-about-heading">Limitations</div>
  <section class="orb-limit-list">{limitations}</section>

  <div class="orb-about-heading">References & data provenance</div>
  <section class="orb-ref-grid">{references}</section>

  <div class="orb-about-foot">
    ORBIDENSE · Earth intelligence for clearer environmental decisions.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
