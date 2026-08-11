from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from src.profile import (
    BUILDER_BIO,
    BUILDER_HEADLINE,
    BUILDER_NAME,
    GITHUB_URL,
    LINKEDIN_URL,
    PROFILE_PHOTO_PATH,
)


def _data_uri(path_value: str) -> str | None:
    path = Path(path_value)

    if not path.exists():
        return None

    suffix = path.suffix.lower()

    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(
        suffix,
        "image/jpeg",
    )

    encoded = base64.b64encode(
        path.read_bytes()
    ).decode("ascii")

    return f"data:{mime};base64,{encoded}"


def _safe(value: str) -> str:
    return html.escape(
        str(value or "")
    )


def render_about_page() -> None:
    """
    Render the ClimatePulse About page.

    This page intentionally uses st.html rather than st.markdown for the
    visual cards. That prevents Streamlit from displaying the HTML source
    as code blocks.
    """

    portrait_uri = _data_uri(
        PROFILE_PHOTO_PATH
    )

    earth_uri = _data_uri(
        "assets/about_earth.jpg"
    )

    css = """
    <style>
    .cp-about-page {
        width: 100%;
        color: #eef7ff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                     BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .cp-about-page * {
        box-sizing: border-box;
    }

    .cp-a-card {
        background:
            linear-gradient(
                145deg,
                rgba(11, 29, 45, .98),
                rgba(7, 20, 32, .98)
            );
        border: 1px solid rgba(104, 169, 211, .22);
        border-radius: 14px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .13);
    }

    /* HERO */
    .cp-a-hero {
        position: relative;
        overflow: hidden;
        min-height: 272px;
        padding: 28px 34px;
        display: flex;
        align-items: center;
        margin-bottom: 14px;
    }

    .cp-a-hero-bg {
        position: absolute;
        inset: 0 0 0 43%;
        background-position: center right;
        background-repeat: no-repeat;
        background-size: cover;
        opacity: .95;
    }

    .cp-a-hero-shade {
        position: absolute;
        inset: 0;
        background:
            linear-gradient(
                90deg,
                rgba(7, 20, 32, .99) 0%,
                rgba(7, 20, 32, .98) 38%,
                rgba(7, 20, 32, .69) 61%,
                rgba(7, 20, 32, .20) 100%
            );
    }

    .cp-a-hero-content {
        position: relative;
        z-index: 2;
        width: 49%;
        min-width: 420px;
    }

    .cp-a-kicker {
        color: #60c8ff;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .cp-a-hero h1 {
        color: #ffffff;
        font-size: 37px;
        line-height: 1.06;
        font-weight: 850;
        margin: 0;
    }

    .cp-a-hero-tag {
        color: #5ec8ff;
        font-size: 19px;
        line-height: 1.34;
        font-weight: 730;
        margin-top: 14px;
        max-width: 530px;
    }

    .cp-a-hero-copy {
        color: #d2deE7;
        font-size: 14px;
        line-height: 1.55;
        margin-top: 14px;
        max-width: 520px;
    }

    /* ABOUT / CREATOR */
    .cp-a-profile-grid {
        display: grid;
        grid-template-columns: 1.05fr .70fr 1.55fr;
        min-height: 265px;
        margin-bottom: 17px;
        overflow: hidden;
    }

    .cp-a-about-copy,
    .cp-a-created {
        padding: 28px 30px;
    }

    .cp-a-photo-cell {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px 12px;
        border-left: 1px solid rgba(104, 169, 211, .17);
        border-right: 1px solid rgba(104, 169, 211, .17);
        background:
            linear-gradient(
                180deg,
                rgba(11, 29, 45, .58),
                rgba(8, 22, 35, .42)
            );
    }

    .cp-a-photo {
        width: 185px;
        height: 226px;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid rgba(131, 183, 216, .22);
        background: #eef0f2;
        box-shadow: 0 10px 25px rgba(0,0,0,.18);
    }

    .cp-a-photo img {
        width: 100%;
        height: 100%;
        display: block;
        object-fit: cover;
        object-position: center 16%;
    }

    .cp-a-photo-placeholder {
        width: 185px;
        height: 226px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        border: 1px dashed rgba(131, 183, 216, .30);
        border-radius: 10px;
        color: #7f9db0;
        font-size: 12px;
        padding: 18px;
    }

    .cp-a-section-label {
        color: #61c9ff;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: .11em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .cp-a-about-copy p {
        color: #e1eaf0;
        font-size: 14px;
        line-height: 1.60;
        margin: 0;
        max-width: 360px;
    }

    .cp-a-created h2 {
        color: #ffffff;
        font-size: 28px;
        line-height: 1.12;
        margin: 0;
        font-weight: 850;
    }

    .cp-a-role {
        color: #64cbff;
        font-size: 14px;
        font-weight: 720;
        margin-top: 8px;
    }

    .cp-a-school {
        color: #d4e1e9;
        font-size: 13px;
        margin-top: 5px;
    }

    .cp-a-divider {
        width: 45px;
        height: 2px;
        background: #4aaee8;
        border-radius: 999px;
        margin: 14px 0 12px;
    }

    .cp-a-created p {
        color: #d7e2e9;
        font-size: 14px;
        line-height: 1.55;
        margin: 0;
        max-width: 505px;
    }

    .cp-a-links {
        display: flex;
        gap: 10px;
        margin-top: 13px;
        flex-wrap: wrap;
    }

    .cp-a-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 118px;
        height: 38px;
        padding: 0 14px;
        color: #eaf6ff !important;
        text-decoration: none !important;
        background: rgba(14, 40, 61, .88);
        border: 1px solid rgba(97, 189, 240, .52);
        border-radius: 8px;
        font-size: 13px;
        font-weight: 700;
    }

    .cp-a-link:hover {
        background: rgba(29, 73, 104, .88);
        border-color: rgba(112, 204, 255, .80);
    }

    /* FEATURES */
    .cp-a-heading {
        color: #a7c5d8;
        font-size: 13px;
        letter-spacing: .10em;
        text-transform: uppercase;
        font-weight: 800;
        margin: 8px 0 10px;
    }

    .cp-a-feature-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 11px;
        margin-bottom: 13px;
    }

    .cp-a-feature {
        min-height: 105px;
        padding: 15px 16px;
        display: grid;
        grid-template-columns: 50px 1fr;
        gap: 12px;
        align-items: center;
    }

    .cp-a-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
            linear-gradient(
                145deg,
                rgba(38, 106, 174, .75),
                rgba(18, 55, 103, .72)
            );
        border: 1px solid rgba(92, 190, 255, .55);
        color: #c6ecff;
        font-size: 22px;
        font-weight: 800;
    }

    .cp-a-feature-title {
        color: #ffffff;
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .cp-a-feature-copy {
        color: #c3d0d9;
        font-size: 12px;
        line-height: 1.45;
    }

    /* BOTTOM */
    .cp-a-bottom {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 11px;
        margin-top: 5px;
    }

    .cp-a-data,
    .cp-a-method {
        min-height: 92px;
        padding: 18px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .cp-a-data-icon,
    .cp-a-method-icon {
        color: #6fbfff;
        font-size: 29px;
        line-height: 1;
        flex: 0 0 auto;
    }

    .cp-a-data-title,
    .cp-a-method-title {
        color: #64cbff;
        font-size: 13px;
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .cp-a-data-row {
        color: #ecf6fb;
        font-size: 13px;
        font-weight: 700;
        word-spacing: 7px;
    }

    .cp-a-method {
        justify-content: space-between;
    }

    .cp-a-method-main {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .cp-a-method-title {
        color: #ffffff;
        text-transform: none;
        letter-spacing: 0;
        font-size: 14px;
        margin-bottom: 4px;
    }

    .cp-a-method-copy {
        color: #8ea7b8;
        font-size: 12px;
    }

    .cp-a-chevron {
        color: #79c8f3;
        font-size: 25px;
    }

    .cp-a-footer {
        color: #708b9d;
        text-align: center;
        font-size: 11px;
        margin: 17px 0 2px;
    }

    @media (max-width: 1100px) {
        .cp-a-hero-content {
            width: 58%;
            min-width: 0;
        }

        .cp-a-profile-grid {
            grid-template-columns: 1fr .65fr 1.35fr;
        }

        .cp-a-feature-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 820px) {
        .cp-a-hero {
            min-height: 310px;
        }

        .cp-a-hero-bg {
            inset: 0;
            opacity: .45;
        }

        .cp-a-hero-shade {
            background: rgba(7, 20, 32, .72);
        }

        .cp-a-hero-content {
            width: 100%;
        }

        .cp-a-profile-grid {
            grid-template-columns: 1fr;
        }

        .cp-a-photo-cell {
            border: 0;
            border-top: 1px solid rgba(104,169,211,.15);
            border-bottom: 1px solid rgba(104,169,211,.15);
        }

        .cp-a-bottom {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 540px) {
        .cp-a-hero {
            padding: 22px;
        }

        .cp-a-hero h1 {
            font-size: 30px;
        }

        .cp-a-hero-tag {
            font-size: 16px;
        }

        .cp-a-feature-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """

    st.html(css)

    earth_style = (
        f'background-image: url("{earth_uri}");'
        if earth_uri
        else ""
    )

    hero = f"""
    <div class="cp-about-page">
      <section class="cp-a-hero cp-a-card">
        <div class="cp-a-hero-bg" style='{earth_style}'></div>
        <div class="cp-a-hero-shade"></div>
        <div class="cp-a-hero-content">
          <div class="cp-a-kicker">ClimatePulse</div>
          <h1>Global Climate Intelligence</h1>
          <div class="cp-a-hero-tag">
            Understand how climate is changing —<br>
            from local conditions to long-term projections.
          </div>
          <div class="cp-a-hero-copy">
            ClimatePulse brings historical climate data, live environmental
            conditions and future climate projections together in one
            interactive platform for exploring and comparing environmental
            change across places.
          </div>
        </div>
      </section>
    </div>
    """

    st.html(hero)

    portrait = (
        f'<div class="cp-a-photo"><img src="{portrait_uri}" '
        f'alt="{_safe(BUILDER_NAME)}"></div>'
        if portrait_uri
        else (
            '<div class="cp-a-photo-placeholder">'
            'Add your portrait as<br><b>assets/profile.jpg</b>'
            '</div>'
        )
    )

    linkedin = (
        f'<a class="cp-a-link" href="{_safe(LINKEDIN_URL)}" '
        f'target="_blank" rel="noopener noreferrer">in&nbsp;&nbsp;LinkedIn ↗</a>'
        if LINKEDIN_URL
        else ""
    )

    github = (
        f'<a class="cp-a-link" href="{_safe(GITHUB_URL)}" '
        f'target="_blank" rel="noopener noreferrer">◉&nbsp;&nbsp;GitHub ↗</a>'
        if GITHUB_URL
        else ""
    )

    profile_block = f"""
    <div class="cp-about-page">
      <section class="cp-a-profile-grid cp-a-card">

        <div class="cp-a-about-copy">
          <div class="cp-a-section-label">About ClimatePulse</div>
          <p>
            ClimatePulse combines observed climate data, current
            environmental conditions and climate-model projections in one
            interactive platform for exploring and comparing environmental
            change across places.
          </p>
        </div>

        <div class="cp-a-photo-cell">
          {portrait}
        </div>

        <div class="cp-a-created">
          <div class="cp-a-section-label">Created by</div>
          <h2>{_safe(BUILDER_NAME)}</h2>
          <div class="cp-a-role">{_safe(BUILDER_HEADLINE)}</div>
          <div class="cp-a-school">University of Milan</div>
          <div class="cp-a-divider"></div>
          <p>{_safe(BUILDER_BIO)}</p>
          <div class="cp-a-links">
            {linkedin}
            {github}
          </div>
        </div>

      </section>
    </div>
    """

    st.html(profile_block)

    st.html(
        """
        <div class="cp-about-page">
          <div class="cp-a-heading">Explore ClimatePulse</div>

          <section class="cp-a-feature-grid">

            <div class="cp-a-feature cp-a-card">
              <div class="cp-a-icon">☁</div>
              <div>
                <div class="cp-a-feature-title">Live Conditions</div>
                <div class="cp-a-feature-copy">
                  Current weather, air quality and environmental conditions.
                </div>
              </div>
            </div>

            <div class="cp-a-feature cp-a-card">
              <div class="cp-a-icon">▥</div>
              <div>
                <div class="cp-a-feature-title">Historical Climate</div>
                <div class="cp-a-feature-copy">
                  Explore past climate trends, extremes and variability.
                </div>
              </div>
            </div>

            <div class="cp-a-feature cp-a-card">
              <div class="cp-a-icon">⌁</div>
              <div>
                <div class="cp-a-feature-title">Future Climate</div>
                <div class="cp-a-feature-copy">
                  Climate-model projections and future scenarios.
                </div>
              </div>
            </div>

            <div class="cp-a-feature cp-a-card">
              <div class="cp-a-icon">◎</div>
              <div>
                <div class="cp-a-feature-title">Compare Places</div>
                <div class="cp-a-feature-copy">
                  Compare cities and countries across past, present and future.
                </div>
              </div>
            </div>

          </section>

          <section class="cp-a-bottom">

            <div class="cp-a-data cp-a-card">
              <div class="cp-a-data-icon">◇</div>
              <div>
                <div class="cp-a-data-title">Data & Methods</div>
                <div class="cp-a-data-row">
                  ERA5 • CRU • CMIP6 • Open-Meteo • PostgreSQL • MapTiler
                </div>
              </div>
            </div>

            <div class="cp-a-method cp-a-card">
              <div class="cp-a-method-main">
                <div class="cp-a-method-icon">▤</div>
                <div>
                  <div class="cp-a-method-title">
                    Methodology, sources & limitations
                  </div>
                  <div class="cp-a-method-copy">
                    Learn how data is collected, processed and interpreted.
                  </div>
                </div>
              </div>
              <div class="cp-a-chevron">⌄</div>
            </div>

          </section>

          <div class="cp-a-footer">
            ClimatePulse &nbsp;•&nbsp; Independent climate-data exploration project
            &nbsp;•&nbsp; Built by Taimoor Ahmad
          </div>
        </div>
        """
    )

    with st.expander(
        "Methodology, sources & limitations",
        expanded=False,
    ):
        st.markdown(
            """
**Live conditions** provide local weather and air-quality context.

**Historical city/place climate** is point-based and is kept distinct from
country-level spatial averages.

**Country climate** uses national spatial aggregates where available,
rather than treating one centroid as representative of an entire country.

**Future climate** uses climate-model projections and communicates model
spread where the underlying dataset provides it.

ClimatePulse is an independent informational and exploratory project. It
is not an official meteorological service and should not replace
professional climate-risk assessment.
            """
        )