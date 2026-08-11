import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox

from src.api.air_quality import get_current_air_quality
from src.api.current_weather import get_current_weather
from src.api.maptiler_search import search_maptiler_places
from src.queries.climate import (
    get_annual_climate_summary,
    get_city_details,
    get_climate_trend,
    get_temperature_anomalies,
)
from src.services.climate_service import (
    ensure_city_history,
    get_history_job_status,
)

load_dotenv()


def get_maptiler_key():
    try:
        if "MAPTILER_KEY" in st.secrets:
            return st.secrets["MAPTILER_KEY"]
    except Exception:
        pass
    return os.getenv("MAPTILER_KEY")


MAPTILER_KEY = get_maptiler_key()

st.set_page_config(
    page_title="ClimatePulse",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --cp-bg: #06101b;
    --cp-card: #0d1b2a;
    --cp-border: rgba(139,179,208,.16);
    --cp-text: #f5f9fc;
    --cp-muted: #92a7b8;
    --cp-blue: #39a9ff;
    --cp-cyan: #36d4e6;
    --cp-green: #43d17b;
    --cp-orange: #ff9f43;
    --cp-red: #ff5b5b;
}
html, body, [class*="css"] {
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp { background: var(--cp-bg); color: var(--cp-text); }
.block-container {
    max-width: 1540px;
    padding-top: 1rem;
    padding-bottom: 2.4rem;
    padding-left: 1.1rem;
    padding-right: 1.1rem;
}
[data-testid="stSidebar"] {
    background: #050d16;
    border-right: 1px solid var(--cp-border);
}
[data-testid="stSidebar"] * { color: #dce7ef; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-baseweb="input"] {
    background: #0b1724 !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 10px !important;
}
[data-baseweb="input"] input { color: #f4f8fb !important; }
.stButton > button {
    border-radius: 10px;
    border: 1px solid var(--cp-border);
    background: #102235;
    color: #f6fbff;
    min-height: 42px;
    font-weight: 650;
}
.stButton > button[kind="primary"] { background: #1677c8; border-color: #2c91e6; }
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: var(--cp-border) !important;
    border-radius: 14px !important;
    background: linear-gradient(145deg, rgba(14,30,46,.94), rgba(8,20,32,.98));
}
[data-testid="stExpander"] {
    border: 1px solid var(--cp-border);
    border-radius: 12px;
    background: #0a1724;
}
.cp-brand { font-weight: 800; font-size: 1.45rem; color: white; margin: 2px 0; }
.cp-brand-sub { color: var(--cp-muted); font-size: .86rem; margin-bottom: 1.15rem; }
.cp-nav { display: grid; gap: 5px; margin: .4rem 0 1.1rem 0; }
.cp-nav a {
    display: block; padding: 9px 11px; border-radius: 9px;
    color: #aebdca !important; text-decoration: none !important; border: 1px solid transparent;
}
.cp-nav a.active { color: #79c9ff !important; background: #0b2236; border-color: rgba(57,169,255,.36); }
.cp-sidebar-title { color: white; font-size: .92rem; font-weight: 700; margin: .65rem 0 .35rem; }
.cp-recent { padding: 7px 0; color: #aebdca; font-size: .88rem; border-bottom: 1px solid rgba(139,179,208,.07); }
.cp-data-box {
    border: 1px solid var(--cp-border); border-radius: 12px; background: #07121d;
    padding: 13px; margin-top: 1rem; color: #9fb0be; font-size: .79rem; line-height: 1.75;
}
.cp-topline { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: .35rem; }
.cp-place-title { color: white; font-size: 1.75rem; font-weight: 800; line-height: 1.15; margin: 0; }
.cp-place-meta { display: flex; flex-wrap: wrap; gap: 14px; color: var(--cp-muted); font-size: .83rem; margin-top: 6px; }
.cp-live-pill {
    display: inline-flex; align-items: center; gap: 6px; background: rgba(67,209,123,.12);
    border: 1px solid rgba(67,209,123,.23); color: #79e9a8; border-radius: 999px; padding: 5px 9px; font-size: .75rem;
}
.cp-section-heading { color: white; font-weight: 750; font-size: 1rem; margin: 0 0 .55rem; }
.cp-current-temp { font-size: 2.45rem; font-weight: 700; color: white; letter-spacing: -1px; margin-top: .2rem; }
.cp-muted { color: var(--cp-muted); }
.cp-mini-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; margin-top: 13px; }
.cp-mini-card { background: #102235; border: 1px solid rgba(139,179,208,.09); border-radius: 9px; padding: 10px; }
.cp-mini-label { color: #89a0b3; font-size: .72rem; margin-bottom: 2px; }
.cp-mini-value { color: #f6fbff; font-size: .95rem; font-weight: 650; }
.cp-aqi {
    margin-top: 11px; padding: 11px; border-radius: 10px; border: 1px solid rgba(139,179,208,.10);
    background: #091724; display: flex; align-items: center; justify-content: space-between;
}
.cp-aqi-value { font-size: 1.35rem; color: #72e59f; font-weight: 750; }
.cp-kpi-grid { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 10px; margin: 12px 0 14px; }
.cp-kpi {
    min-width: 0; background: linear-gradient(145deg,#0f2031,#0a1826);
    border: 1px solid var(--cp-border); border-radius: 12px; padding: 14px 14px 13px;
}
.cp-kpi-label { color: #9eb0bf; font-size: .77rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cp-kpi-value { color: white; font-size: 1.35rem; font-weight: 750; margin-top: 6px; letter-spacing: -.3px; }
.cp-kpi-note { color: #738a9d; font-size: .72rem; margin-top: 6px; }
.cp-blue { color: #55b6ff; } .cp-cyan { color: #47d8e8; } .cp-orange { color: #ffad5b; }
.cp-red { color: #ff7070; } .cp-green { color: #63dc91; }
.cp-landing {
    border: 1px solid var(--cp-border); border-radius: 14px;
    background: linear-gradient(145deg,#0d1d2c,#081521); padding: 20px; margin-top: 12px;
}
.cp-footer { color: #6f8496; font-size: .76rem; text-align: center; padding: 1.2rem 0 .2rem; }
@media (max-width: 1100px) { .cp-kpi-grid { grid-template-columns: repeat(3,minmax(0,1fr)); } }
@media (max-width: 700px) {
    .block-container { padding-left: .65rem; padding-right: .65rem; padding-top: .55rem; }
    .cp-place-title { font-size: 1.38rem; }
    .cp-place-meta { gap: 8px; font-size: .76rem; }
    .cp-kpi-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
    .cp-kpi { padding: 12px; }
    .cp-kpi-value { font-size: 1.15rem; }
    .cp-current-temp { font-size: 2rem; }
}

/* Functional sidebar navigation */
.st-key-main_navigation [role="radiogroup"] {
    gap: 6px;
}

.st-key-main_navigation label {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 8px 10px;
    margin: 0;
}

.st-key-main_navigation label:hover {
    background: #0b1825;
}

.st-key-main_navigation label:has(input:checked) {
    background: #0b2236;
    border-color: rgba(57,169,255,.36);
}

.st-key-main_navigation label:has(input:checked) p {
    color: #79c9ff !important;
}

</style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_STATE = {
    "selected_city_id": None,
    "selected_location": None,
    "selected_country": None,
    "map_lat": 20.0,
    "map_lon": 0.0,
    "map_zoom": 1.35,
    "map_label": "World",
    "recent_searches": [],
    "history_status": None,
    "history_retry_after_seconds": None,
    "main_navigation": "Dashboard",
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def safe_float(value):
    if value is None:
        return None
    return float(value)


def fmt(value, pattern, fallback="N/A"):
    if value is None:
        return fallback
    try:
        return format(float(value), pattern)
    except (TypeError, ValueError):
        return fallback


def stable_maptiler_id(maptiler_id):
    value = str(maptiler_id)
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, byteorder="big", signed=False)
    return number & 0x7FFFFFFFFFFFFFFF


def _first_nonempty(*values):
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _normalized_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def maptiler_english_name(feature):
    """
    Prefer an international/English display name.

    MapTiler returns localized fields when a language is
    requested. We also keep safe fallbacks for older result
    shapes.
    """
    properties = feature.get("properties", {})

    return _first_nonempty(
        feature.get("text_en"),
        feature.get("text"),
        properties.get("text_en"),
        properties.get("name_en"),
        properties.get("name"),
        feature.get("name"),
    ) or "Unknown location"


def maptiler_english_place_name(feature):
    properties = feature.get("properties", {})

    return _first_nonempty(
        feature.get("place_name_en"),
        feature.get("place_name"),
        properties.get("place_name_en"),
        properties.get("place_name"),
        maptiler_english_name(feature),
    ) or "Unknown location"


def maptiler_matching_name(feature):
    """
    Preserve the name/script that matched what the user typed.
    This is useful for Urdu, Chinese, Russian, Arabic, etc.
    """
    return _first_nonempty(
        feature.get("matching_text"),
        feature.get("matching_place_name"),
    )


def maptiler_result_label(feature):
    """
    Human-facing search label:
      English/international name first,
      matched local-script alias second when useful.
    """
    english_label = maptiler_english_place_name(feature)
    matched = maptiler_matching_name(feature)

    if matched:
        english_norm = _normalized_text(english_label)
        matched_norm = _normalized_text(matched)

        if (
            matched_norm
            and matched_norm not in english_norm
            and english_norm not in matched_norm
        ):
            return f"{english_label}  ·  {matched}"

    return english_label


def maptiler_feature_type(feature):
    """
    Normalize MapTiler's richer feature taxonomy.

    Important:
    - A feature administratively typed as a region can still
      be a real city (Berlin/Tokyo-style cases). MapTiler's
      place_designation is used first for this reason.
    - Regions/counties are allowed to produce point-based
      climate analytics at their centroid.
    - Countries remain map-only because one country centroid
      is not representative of national climate.
    """
    properties = feature.get("properties", {})

    place_types = feature.get("place_type", [])

    if isinstance(place_types, str):
        place_types = [place_types]

    place_types = {
        str(value).lower()
        for value in place_types
        if value
    }

    designation = str(
        properties.get("place_designation")
        or feature.get("place_designation")
        or ""
    ).lower()

    inhabited_designations = {
        "city",
        "town",
        "village",
        "hamlet",
        "suburb",
        "neighbourhood",
        "quarter",
        "borough",
        "isolated_dwelling",
        "farm",
        "city_block",
    }

    if designation in inhabited_designations:
        return "place"

    if "country" in place_types:
        return "country"

    if place_types.intersection(
        {
            "municipality",
            "joint_municipality",
            "joint_submunicipality",
            "municipal_district",
            "locality",
            "neighbourhood",
            "place",
            "postal_code",
        }
    ):
        return "place"

    if place_types.intersection(
        {
            "region",
            "subregion",
            "county",
        }
    ):
        return "area"

    if place_types.intersection(
        {
            "address",
            "road",
            "poi",
        }
    ):
        return "local_point"

    return "location"


def maptiler_coordinates(feature):
    """
    Return (longitude, latitude).

    MapTiler can return Point geometries or a centroid for
    polygon/administrative features. Prefer the explicit
    center, then a Point geometry.
    """
    center = feature.get("center")

    if (
        isinstance(center, (list, tuple))
        and len(center) >= 2
        and isinstance(center[0], (int, float))
        and isinstance(center[1], (int, float))
    ):
        return float(center[0]), float(center[1])

    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates")

    if (
        geometry.get("type") == "Point"
        and isinstance(coordinates, (list, tuple))
        and len(coordinates) >= 2
        and isinstance(coordinates[0], (int, float))
        and isinstance(coordinates[1], (int, float))
    ):
        return float(coordinates[0]), float(coordinates[1])

    properties = feature.get("properties", {})

    lon = (
        properties.get("lon")
        or properties.get("longitude")
    )

    lat = (
        properties.get("lat")
        or properties.get("latitude")
    )

    if lon is not None and lat is not None:
        return float(lon), float(lat)

    return None


def _context_name(item):
    properties = item.get("properties", {})

    return _first_nonempty(
        item.get("text_en"),
        item.get("text"),
        properties.get("text_en"),
        properties.get("name_en"),
        properties.get("name"),
        item.get("place_name_en"),
        item.get("place_name"),
    )


def extract_context_value(feature, prefixes):
    """
    Extract hierarchy values using either context IDs or
    MapTiler place types, while preferring English labels.
    """
    for item in feature.get("context", []):
        item_id = str(item.get("id", "")).lower()
        item_types = item.get("place_type", [])

        if isinstance(item_types, str):
            item_types = [item_types]

        item_types = {
            str(value).lower()
            for value in item_types
            if value
        }

        item_properties = item.get("properties", {})

        matches_id = any(
            item_id.startswith(prefix)
            for prefix in prefixes
        )

        matches_type = bool(
            item_types.intersection(
                set(prefixes)
            )
        )

        if matches_id or matches_type:
            name = _context_name(item)

            short_code = _first_nonempty(
                item.get("short_code"),
                item_properties.get("short_code"),
                item_properties.get("country_code"),
            )

            return name, short_code

    return None, None


def maptiler_to_climate_location(feature):
    """
    Convert any climate-capable MapTiler feature to the
    database/service location dictionary.

    For regions/counties, ERA5 represents the selected
    centroid/grid point, NOT an area-average climate.
    """
    properties = feature.get("properties", {})
    coordinates = maptiler_coordinates(feature)

    if not coordinates:
        raise ValueError(
            "Selected MapTiler result has no usable coordinates."
        )

    longitude, latitude = coordinates

    name = maptiler_english_name(feature)

    country_name, country_short_code = extract_context_value(
        feature,
        prefixes=("country",),
    )

    admin1, _ = extract_context_value(
        feature,
        prefixes=(
            "region",
            "subregion",
            "state",
            "province",
        ),
    )

    if not country_name:
        country_name = _first_nonempty(
            properties.get("country_name_en"),
            properties.get("country_name"),
            properties.get("country"),
        )

    # Country features may carry their own country code.
    country_code = _first_nonempty(
        country_short_code,
        properties.get("country_code"),
        properties.get("country_code_alpha_2"),
    )

    if country_code:
        country_code = (
            str(country_code)
            .split("-")[-1]
            .upper()
        )

    if not country_name:
        # Safe final fallback: use the last hierarchy item
        # from the English full label.
        english_full = maptiler_english_place_name(feature)

        if "," in english_full:
            country_name = (
                english_full
                .split(",")[-1]
                .strip()
            )

    external_source_id = (
        feature.get("id")
        or f"{name}|{latitude:.6f}|{longitude:.6f}"
    )

    population = (
        properties.get("population")
        or feature.get("population")
    )

    result_type = maptiler_feature_type(feature)

    return {
        "id": stable_maptiler_id(
            external_source_id
        ),
        "name": name,
        "country": country_name,
        "country_code": country_code,
        "admin1": admin1,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "population": population,

        # UI-only metadata. The database upsert safely
        # ignores these extra fields.
        "result_type": result_type,
        "scope_note": (
            "Climate values represent the selected area's "
            "centroid/grid point, not an area-wide average."
            if result_type == "area"
            else None
        ),
        "matched_name": maptiler_matching_name(feature),
    }


def climate_location_label(location):
    parts = []

    for value in [
        location.get("name"),
        location.get("admin1"),
        location.get("country"),
    ]:
        if (
            value
            and str(value) not in parts
        ):
            parts.append(
                str(value)
            )

    label = ", ".join(parts)

    if location.get("country_code"):
        label += (
            f" - "
            f"{location['country_code']}"
        )

    matched_name = location.get(
        "matched_name"
    )

    if (
        matched_name
        and _normalized_text(matched_name)
        not in _normalized_text(label)
    ):
        label += f"  ·  {matched_name}"

    return label or "Selected location"


def update_map_from_feature(feature):
    coordinates = maptiler_coordinates(
        feature
    )

    if not coordinates:
        return

    longitude, latitude = coordinates
    result_type = maptiler_feature_type(
        feature
    )

    st.session_state.map_lon = longitude
    st.session_state.map_lat = latitude
    st.session_state.map_label = (
        maptiler_result_label(
            feature
        )
    )

    zoom_by_type = {
        "country": 4.0,
        "area": 6.5,
        "place": 9.5,
        "local_point": 13.0,
        "location": 10.0,
    }

    st.session_state.map_zoom = (
        zoom_by_type.get(
            result_type,
            9.0,
        )
    )


def add_recent(label):
    recent = list(st.session_state.recent_searches)
    if label in recent:
        recent.remove(label)
    recent.insert(0, label)
    st.session_state.recent_searches = recent[:5]


def aqi_note(aqi):
    if aqi is None:
        return "AQI unavailable"
    try:
        value = float(aqi)
    except (TypeError, ValueError):
        return "AQI unavailable"
    if value <= 20:
        return "Very good"
    if value <= 40:
        return "Good"
    if value <= 60:
        return "Moderate"
    if value <= 80:
        return "Poor"
    if value <= 100:
        return "Very poor"
    return "Extremely poor"


def map_style_url(style_name):
    if style_name == "Street":
        return "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    if style_name == "Dark":
        return "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    if MAPTILER_KEY:
        return f"https://api.maptiler.com/maps/satellite/style.json?key={MAPTILER_KEY}"
    return "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


def build_map(style_name):
    df = pd.DataFrame({
        "label": [st.session_state.map_label],
        "latitude": [st.session_state.map_lat],
        "longitude": [st.session_state.map_lon],
    })
    marker = pdk.Layer(
        "ScatterplotLayer", data=df, get_position=["longitude", "latitude"],
        get_radius=120, radius_min_pixels=7, radius_max_pixels=16,
        get_fill_color=[255,82,82,235], get_line_color=[255,255,255,240],
        line_width_min_pixels=2, stroked=True, filled=True, pickable=True,
    )
    view = pdk.ViewState(
        latitude=st.session_state.map_lat, longitude=st.session_state.map_lon,
        zoom=st.session_state.map_zoom, pitch=0, bearing=0,
    )
    return pdk.Deck(
        map_style=map_style_url(style_name), initial_view_state=view, layers=[marker],
        tooltip={"html": "<b>{label}</b>", "style": {"backgroundColor": "#07111c", "color": "#ffffff"}},
    )


@st.fragment
def render_map_fragment():
    """
    Map-style changes rerun only this fragment instead
    of re-executing SQL, weather, AQI, and charts.
    """
    with st.container(border=True):
        map_style_name = st.segmented_control(
            "Map style",
            options=[
                "Street",
                "Dark",
                "Satellite",
            ],
            default="Street",
            key="map_style_selector",
            label_visibility="collapsed",
        ) or "Street"

        st.pydeck_chart(
            build_map(map_style_name),
            width="stretch",
            height=330,
        )


def style_plotly(fig, height=290, y_title=None):
    fig.update_layout(
        height=height,
        margin=dict(l=15, r=12, t=16, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#aebdca", size=11),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        xaxis=dict(title=None, gridcolor="rgba(160,190,210,.10)", zeroline=False),
        yaxis=dict(title=y_title, gridcolor="rgba(160,190,210,.10)", zeroline=False),
    )
    return fig


@st.cache_data(
    ttl=21600,
    max_entries=128,
    show_spinner=False,
)
def cached_dashboard_data(city_id):
    """
    Load the four PostgreSQL dashboard datasets in parallel
    and keep the result cached for six hours.

    Historical ERA5 analytics change very rarely, so a long
    cache dramatically reduces repeat Neon round trips.
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        city_future = executor.submit(
            get_city_details,
            city_id,
        )
        summary_future = executor.submit(
            get_annual_climate_summary,
            city_id,
        )
        anomaly_future = executor.submit(
            get_temperature_anomalies,
            city_id,
        )
        trend_future = executor.submit(
            get_climate_trend,
            city_id,
        )

        city = city_future.result()
        summary = summary_future.result()
        anomalies = anomaly_future.result()
        trend = trend_future.result()

    return city, summary, anomalies, trend


@st.cache_data(
    ttl=600,
    max_entries=128,
    show_spinner=False,
)
def cached_live_environment(
    latitude,
    longitude,
    timezone,
):
    """
    Fetch current weather and air quality concurrently.

    Both calls are independent, so running them together
    reduces the waiting time for live conditions.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        weather_future = executor.submit(
            get_current_weather,
            latitude,
            longitude,
            timezone=timezone,
        )

        air_future = executor.submit(
            get_current_air_quality,
            latitude,
            longitude,
            timezone=timezone,
        )

        weather_data = weather_future.result()
        air_data = air_future.result()

    return {
        "weather": weather_data,
        "air": air_data,
    }


@st.cache_data(
    ttl=3600,
    max_entries=256,
    show_spinner=False,
)
def cached_maptiler_search(query):
    """
    Cache autocomplete results for one hour.
    MapTiler is asked to return English/international names,
    while matching_* fields preserve local-script matches.
    """
    return search_maptiler_places(
        query,
        limit=10,
        language="en",
    )


def _search_priority(feature):
    result_type = maptiler_feature_type(
        feature
    )

    return {
        "place": 0.18,
        "area": 0.12,
        "local_point": 0.08,
        "country": 0.05,
        "location": 0.00,
    }.get(
        result_type,
        0.00,
    )


def _feature_search_score(
    feature,
    query,
):
    relevance = safe_float(
        feature.get("relevance")
    ) or 0.0

    score = relevance + _search_priority(
        feature
    )

    query_norm = _normalized_text(
        query
    )

    candidates = [
        maptiler_english_name(feature),
        maptiler_matching_name(feature),
        feature.get("matching_place_name"),
    ]

    for candidate in candidates:
        candidate_norm = _normalized_text(
            candidate
        )

        if not candidate_norm:
            continue

        if candidate_norm == query_norm:
            score += 0.30

        elif (
            candidate_norm.startswith(
                query_norm
            )
            or query_norm.startswith(
                candidate_norm
            )
        ):
            score += 0.15

    return score


def global_search(search_term):
    """
    Fast multilingual autocomplete with international
    English display labels.

    Small settlements and administrative areas are retained
    instead of being discarded solely because they are not
    typed as a major city.
    """
    query = search_term.strip()

    if len(query) < 2:
        return []

    try:
        features = cached_maptiler_search(
            query
        )

    except Exception as error:
        print(
            "MapTiler search error:",
            error,
        )
        return []

    ranked = []
    seen = set()

    for feature in features:
        coordinates = maptiler_coordinates(
            feature
        )

        if not coordinates:
            continue

        longitude, latitude = coordinates

        result = dict(feature)

        result["result_type"] = (
            maptiler_feature_type(
                feature
            )
        )

        result["map_lon"] = longitude
        result["map_lat"] = latitude

        label = maptiler_result_label(
            feature
        )

        # Deduplicate repeated hierarchy variants.
        dedupe_key = (
            _normalized_text(label),
            round(latitude, 5),
            round(longitude, 5),
        )

        if dedupe_key in seen:
            continue

        seen.add(
            dedupe_key
        )

        ranked.append(
            (
                _feature_search_score(
                    feature,
                    query,
                ),
                label,
                result,
            )
        )

    ranked.sort(
        key=lambda row: row[0],
        reverse=True,
    )

    return [
        (label, result)
        for _, label, result in ranked[:10]
    ]


with st.sidebar:

    st.markdown(
        """
<div class="cp-brand">🌍 ClimatePulse</div>
<div class="cp-brand-sub">Global Climate Intelligence</div>
        """,
        unsafe_allow_html=True,
    )

    nav_view = st.radio(
        "Navigation",
        options=[
            "Dashboard",
            "Map Explorer",
            "Climate Trends",
            "Data & Methods",
        ],
        key="main_navigation",
        label_visibility="collapsed",
        width="stretch",
        format_func=lambda value: {
            "Dashboard": "⌂   Dashboard",
            "Map Explorer": "▧   Map Explorer",
            "Climate Trends": "↗   Climate Trends",
            "Data & Methods": "▤   Data & Methods",
        }[value],
    )

    st.markdown(
        '<div class="cp-sidebar-title">Recent searches</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.recent_searches:
        for recent in st.session_state.recent_searches:
            st.markdown(
                f'<div class="cp-recent">📍 {recent}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption(
            "Your recently selected places will appear here."
        )

    st.markdown(
        """
<div class="cp-data-box">
<b style="color:#eaf4fb;">Data &amp; Models</b><br>
Weather: Open-Meteo<br>
Climate: ERA5 reanalysis<br>
Analytics: PostgreSQL / Neon<br>
Maps: CARTO + MapTiler
</div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# TOP SEARCH BAR
# =========================================================

st.markdown(
    '<div id="dashboard"></div>',
    unsafe_allow_html=True,
)

search_col, status_col = st.columns(
    [4.8, 1.2],
    vertical_alignment="center",
)

with search_col:
    selected_search_result = st_searchbox(
        global_search,
        key="global_place_search",
        label="Search",
        placeholder="Search any city, place or country...",
        debounce=300,
        edit_after_submit="option",
        clear_on_submit=False,
    )

with status_col:
    st.markdown(
        """
        <div style="text-align:right;">
            <span class="cp-live-pill">
                ● All systems normal
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# HANDLE SEARCH RESULT
# =========================================================

pending_location = None

if selected_search_result:

    result_type = selected_search_result.get(
        "result_type",
        "location",
    )

    # The map always follows a valid search selection.
    update_map_from_feature(
        selected_search_result
    )

    selected_label = (
        maptiler_result_label(
            selected_search_result
        )
    )

    add_recent(
        selected_label
    )

    # -----------------------------------------------------
    # COUNTRY
    # -----------------------------------------------------
    # Countries remain map-only. A single country centroid
    # would be scientifically misleading as "the climate of
    # the country".
    if result_type == "country":

        st.session_state.selected_country = (
            selected_search_result
        )

        st.session_state.selected_city_id = None
        st.session_state.selected_location = None
        st.session_state.history_status = None
        st.session_state.history_retry_after_seconds = None

    # -----------------------------------------------------
    # PLACE / AREA / LOCAL POINT
    # -----------------------------------------------------
    # Cities, towns, villages, hamlets, neighbourhoods,
    # municipalities, regions/counties, addresses and POIs
    # can all be represented by a coordinate for point-based
    # weather/reanalysis.
    else:

        try:
            pending_location = (
                maptiler_to_climate_location(
                    selected_search_result
                )
            )

        except Exception as error:
            st.error(
                "Location conversion failed: "
                f"{error}"
            )


# =========================================================
# AUTO-LOAD SELECTED LOCATION
# =========================================================

if pending_location:

    pending_id = pending_location.get(
        "id"
    )

    current_loaded_location = (
        st.session_state.get(
            "selected_location"
        )
    )

    current_loaded_id = None

    if current_loaded_location:
        current_loaded_id = (
            current_loaded_location.get(
                "id"
            )
        )

    if pending_id != current_loaded_id:

        try:
            result = ensure_city_history(
                pending_location
            )

            st.session_state.selected_city_id = (
                result["city_id"]
            )

            st.session_state.selected_location = (
                pending_location
            )

            st.session_state.selected_country = None

            st.session_state.history_status = (
                result.get(
                    "history_status",
                    "loading",
                )
            )

            st.session_state.history_retry_after_seconds = None

            st.rerun()

        except Exception:
            st.session_state.history_status = (
                "unavailable"
            )


# =========================================================
# CITY DATA
# =========================================================

city = None
summary = None
anomalies = None
trend = None
current_weather = {}
current_air = {}

if st.session_state.selected_city_id is not None:
    city_id = st.session_state.selected_city_id

    try:
        (
            city,
            summary,
            anomalies,
            trend,
        ) = cached_dashboard_data(
            city_id
        )
    except Exception as error:
        st.error(
            "Unable to load climate analytics: "
            f"{error}"
        )
        city = None
        summary = None
        anomalies = None
        trend = None

    if city is not None:

        if summary is not None and not summary.empty:
            for column in [
                "avg_temperature_c",
                "avg_max_temperature_c",
                "avg_min_temperature_c",
                "hottest_day_c",
                "coldest_day_c",
                "annual_precipitation_mm",
                "hot_days_30c",
                "extreme_hot_days_35c",
            ]:
                if column in summary.columns:
                    summary[column] = pd.to_numeric(
                        summary[column],
                        errors="coerce",
                    )

        if anomalies is not None and not anomalies.empty:
            for column in [
                "annual_temperature_c",
                "baseline_temperature_c",
                "anomaly_c",
            ]:
                if column in anomalies.columns:
                    anomalies[column] = pd.to_numeric(
                        anomalies[column],
                        errors="coerce",
                    )

        try:
            live_environment = cached_live_environment(
                city["latitude"],
                city["longitude"],
                city["timezone"],
            )

            current_weather = (
                live_environment
                .get("weather", {})
                .get("current", {})
            )

            current_air = (
                live_environment
                .get("air", {})
                .get("current", {})
            )

        except Exception:
            current_weather = {}
            current_air = {}



@st.fragment(
    run_every=5,
)
def render_history_progress(
    city_id,
):
    """
    Poll one background ERA5 import without rerunning the
    whole app every five seconds.
    """
    status = get_history_job_status(
        city_id
    )

    state = status.get(
        "status",
        "not_started",
    )

    completed = int(
        status.get(
            "completed_years",
            0,
        )
    )

    total = max(
        int(
            status.get(
                "total_years",
                36,
            )
        ),
        1,
    )

    if state == "ready":

        if (
            st.session_state.get(
                "history_status"
            )
            != "ready"
        ):
            st.session_state.history_status = (
                "ready"
            )

            cached_dashboard_data.clear()

            st.rerun()

        return

    if state in {
        "queued",
        "running",
        "waiting",
        "partial",
        "paused",
    }:

        progress = min(
            max(
                completed / total,
                0.0,
            ),
            1.0,
        )

        st.progress(
            progress,
            text=status.get(
                "message",
                "Preparing historical climate...",
            ),
        )

        if state in {
            "paused",
            "partial",
        }:
            st.caption(
                "ClimatePulse will resume this location's "
                "missing years the next time it is opened."
            )

    elif state == "error":
        st.caption(
            "Historical climate is temporarily unavailable. "
            "Live conditions remain available."
        )


if city is not None:
    title = f"{city['city_name']}, {city['country_name']}"

    live_timezone = None

    try:
        live_timezone = (
            live_environment
            .get("weather", {})
            .get("timezone")
        )
    except Exception:
        live_timezone = None

    timezone_label = (
        live_timezone
        or (
            "Local timezone"
            if city["timezone"] == "auto"
            else city["timezone"]
        )
    )

    selected_scope_note = None

    if st.session_state.selected_location:
        selected_scope_note = (
            st.session_state.selected_location
            .get("scope_note")
        )

    scope_html = (
        f"<span>◌ Point-based ERA5 at selected centroid</span>"
        if selected_scope_note
        else ""
    )

    meta = (
        f"◈ {city['latitude']:.4f}°, {city['longitude']:.4f}°"
        f"<span>◉ {timezone_label}</span>"
        f"<span>ERA5 1990–2025</span>"
        f"{scope_html}"
    )
elif st.session_state.selected_country:
    title = maptiler_result_label(st.session_state.selected_country)
    meta = "Country view • select a city to load detailed climate analytics"
else:
    title = "Global Climate Intelligence"
    meta = "Search any city, place or country to explore climate conditions and long-term trends"

st.markdown(
    f"""
<div class="cp-topline"><div>
<div class="cp-place-title">{title}</div>
<div class="cp-place-meta">{meta}</div>
</div></div>
    """,
    unsafe_allow_html=True,
)

if nav_view in {"Dashboard", "Map Explorer"}:
    st.markdown('<div id="map-explorer"></div>', unsafe_allow_html=True)
    map_col, current_col = st.columns([1.55, 1], gap="medium")
    with map_col:
        render_map_fragment()

    with current_col:
        with st.container(border=True):
            if city is not None:
                temperature = current_weather.get("temperature_2m")
                feels_like = current_weather.get("apparent_temperature")
                humidity = current_weather.get("relative_humidity_2m")
                wind = current_weather.get("wind_speed_10m")
                precipitation_now = current_weather.get("precipitation")
                aqi = current_air.get("european_aqi")
                pm25 = current_air.get("pm2_5")
                st.markdown(
                    f"""
    <div class="cp-section-heading">☁️ &nbsp; Current Conditions <span class="cp-live-pill" style="float:right;">● Live</span></div>
    <div class="cp-current-temp">{fmt(temperature, '.1f')}°C</div>
    <div class="cp-muted">Feels like {fmt(feels_like, '.1f')}°C</div>
    <div class="cp-mini-grid">
    <div class="cp-mini-card"><div class="cp-mini-label">Humidity</div><div class="cp-mini-value">💧 {fmt(humidity, '.0f')}%</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Wind</div><div class="cp-mini-value">➤ {fmt(wind, '.1f')} km/h</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Precipitation</div><div class="cp-mini-value">🌧 {fmt(precipitation_now, '.1f')} mm</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">PM2.5</div><div class="cp-mini-value">{fmt(pm25, '.1f')} µg/m³</div></div>
    </div>
    <div class="cp-aqi"><div><div class="cp-mini-label">European Air Quality Index</div><div class="cp-mini-value">{aqi_note(aqi)}</div></div><div class="cp-aqi-value">{fmt(aqi, '.0f')}</div></div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
    <div class="cp-section-heading">ClimatePulse Explorer</div>
    <div class="cp-current-temp">Explore anywhere.</div>
    <div class="cp-muted">Search above to move the map instantly. Cities, towns, villages, neighbourhoods and many administrative areas can load point-based weather, air quality and ERA5 climate analytics.</div>
    <div class="cp-mini-grid" style="margin-top:18px;">
    <div class="cp-mini-card"><div class="cp-mini-label">Climate history</div><div class="cp-mini-value">1990–2025</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Database</div><div class="cp-mini-value">PostgreSQL / Neon</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Weather</div><div class="cp-mini-value">Open-Meteo</div></div>
    <div class="cp-mini-card"><div class="cp-mini-label">Climate</div><div class="cp-mini-value">ERA5</div></div>
    </div>
                    """,
                    unsafe_allow_html=True,
                )


if nav_view == "Map Explorer":
    if city is not None and st.session_state.get("history_status") != "ready":
        render_history_progress(city["city_id"])
    st.markdown('<div class="cp-footer">ClimatePulse • Map Explorer</div>', unsafe_allow_html=True)
    st.stop()


if nav_view == "Data & Methods":

    st.markdown(
        "### Data & Methods"
    )

    st.markdown(
        """
**Historical climate:** ERA5 reanalysis accessed through
Open-Meteo and stored in PostgreSQL/Neon.

**Historical period:** 1990–2025.

**Reference period:** 1991–2020.

**Temperature anomaly:** annual mean temperature minus the
1991–2020 mean for the selected ERA5 grid point.

**Warming trend:** least-squares regression slope calculated
in PostgreSQL and expressed in °C per decade.

**Spatial meaning:** ERA5 is gridded reanalysis. For cities,
towns, neighbourhoods and administrative areas, ClimatePulse
shows the grid point nearest the selected coordinate or
centroid rather than a boundary-wide average.
        """
    )

    if (
        summary is not None
        and not summary.empty
    ):
        tab1, tab2 = st.tabs(
            [
                "Annual climate data",
                "Temperature anomalies",
            ]
        )

        with tab1:
            st.dataframe(
                summary,
                width="stretch",
                hide_index=True,
            )

        with tab2:
            st.dataframe(
                anomalies,
                width="stretch",
                hide_index=True,
            )

    elif city is not None:
        render_history_progress(
            city["city_id"]
        )

        st.info(
            "Historical tables will appear automatically "
            "when this location's background import finishes."
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Data & Methods</div>',
        unsafe_allow_html=True,
    )

    st.stop()


if (
    city is None
    or summary is None
    or summary.empty
    or anomalies is None
    or anomalies.empty
):

    if city is not None:

        render_history_progress(
            city["city_id"]
        )

        st.markdown(
            """
<div class="cp-landing">
<b>Live conditions are ready</b><br>
<span class="cp-muted">
ClimatePulse is preparing the 1990–2025 ERA5 history in the
background. You can continue using the map and live conditions;
historical charts appear automatically when the import completes.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
<div class="cp-landing">
<b>Start exploring</b><br>
<span class="cp-muted">
Search for any city, town, village, neighbourhood or place.
The map follows your selection immediately.
</span>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="cp-footer">ClimatePulse • Global Climate Intelligence</div>',
        unsafe_allow_html=True,
    )

    st.stop()

if nav_view == "Climate Trends":
    st.markdown("### Climate Trends")

latest = summary.iloc[-1]
latest_anomaly = anomalies.iloc[-1]
latest_year = int(latest["year"])
warming_rate = safe_float(trend.get("warming_rate_c_per_decade")) if trend else None
warming_text = f"{warming_rate:+.2f}°C/decade" if warming_rate is not None else "N/A"

st.markdown(
    f"""
<div class="cp-kpi-grid">
<div class="cp-kpi"><div class="cp-kpi-label">🌡 Mean Temp ({latest_year})</div><div class="cp-kpi-value cp-cyan">{latest['avg_temperature_c']:.1f}°C</div><div class="cp-kpi-note">Annual mean</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">↗ Temperature Anomaly</div><div class="cp-kpi-value cp-red">{latest_anomaly['anomaly_c']:+.2f}°C</div><div class="cp-kpi-note">vs 1991–2020</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">⌁ Warming Trend</div><div class="cp-kpi-value cp-blue">{warming_text}</div><div class="cp-kpi-note">Linear trend</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">☀ Days ≥30°C</div><div class="cp-kpi-value cp-orange">{int(latest['hot_days_30c'])}</div><div class="cp-kpi-note">Hot days</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">🔥 Days ≥35°C</div><div class="cp-kpi-value cp-red">{int(latest['extreme_hot_days_35c'])}</div><div class="cp-kpi-note">Extreme heat</div></div>
<div class="cp-kpi"><div class="cp-kpi-label">🌧 Precipitation ({latest_year})</div><div class="cp-kpi-value cp-blue">{latest['annual_precipitation_mm']:.0f} mm</div><div class="cp-kpi-note">Annual total</div></div>
</div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div id="climate-trends"></div>', unsafe_allow_html=True)
chart1, chart2, chart3 = st.columns(3, gap="medium")
with chart1:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Average Temperature Trend</div>', unsafe_allow_html=True)
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=summary["year"], y=summary["avg_temperature_c"], mode="lines+markers", name="Annual mean",
            line=dict(color="#42d5e6", width=2), marker=dict(color="#42d5e6", size=4),
        ))
        baseline = anomalies["baseline_temperature_c"].dropna() if "baseline_temperature_c" in anomalies.columns else pd.Series(dtype=float)
        if not baseline.empty:
            fig_temp.add_hline(y=float(baseline.iloc[-1]), line_dash="dash", line_color="#9aa9b5")
        style_plotly(fig_temp, height=280, y_title="°C")
        st.plotly_chart(fig_temp, width="stretch", config={"displayModeBar": False, "responsive": True})

with chart2:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Extreme Heat Days</div>', unsafe_allow_html=True)
        fig_heat = go.Figure()
        fig_heat.add_trace(go.Bar(x=summary["year"], y=summary["hot_days_30c"], name="≥30°C", marker_color="#ff9f43"))
        fig_heat.add_trace(go.Bar(x=summary["year"], y=summary["extreme_hot_days_35c"], name="≥35°C", marker_color="#ff5b5b"))
        fig_heat.update_layout(barmode="overlay")
        style_plotly(fig_heat, height=280, y_title="Days")
        st.plotly_chart(fig_heat, width="stretch", config={"displayModeBar": False, "responsive": True})

with chart3:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Total Precipitation</div>', unsafe_allow_html=True)
        fig_rain = go.Figure()
        fig_rain.add_trace(go.Scatter(
            x=summary["year"], y=summary["annual_precipitation_mm"], mode="lines+markers", name="Annual precipitation",
            line=dict(color="#4da8ff", width=2), marker=dict(color="#4da8ff", size=4),
            fill="tozeroy", fillcolor="rgba(77,168,255,.10)",
        ))
        style_plotly(fig_rain, height=280, y_title="mm")
        st.plotly_chart(fig_rain, width="stretch", config={"displayModeBar": False, "responsive": True})

secondary1, secondary2 = st.columns([1.15, 1], gap="medium")
with secondary1:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Temperature Anomaly</div>', unsafe_allow_html=True)
        colors = ["#ff6666" if value >= 0 else "#3aa7ff" for value in anomalies["anomaly_c"]]
        fig_anomaly = go.Figure(go.Bar(x=anomalies["year"], y=anomalies["anomaly_c"], marker_color=colors, name="Anomaly"))
        fig_anomaly.add_hline(y=0, line_width=1, line_color="#8597a6")
        style_plotly(fig_anomaly, height=255, y_title="°C")
        fig_anomaly.update_layout(showlegend=False)
        st.plotly_chart(fig_anomaly, width="stretch", config={"displayModeBar": False, "responsive": True})

with secondary2:
    with st.container(border=True):
        st.markdown('<div class="cp-section-heading">Climate Snapshot</div>', unsafe_allow_html=True)
        hottest_year_row = summary.loc[summary["avg_temperature_c"].idxmax()]
        coldest_year_row = summary.loc[summary["avg_temperature_c"].idxmin()]
        most_extreme_heat_row = summary.loc[summary["extreme_hot_days_35c"].idxmax()]
        st.markdown(
            f"""
<div class="cp-mini-grid">
<div class="cp-mini-card"><div class="cp-mini-label">Hottest year</div><div class="cp-mini-value">{int(hottest_year_row['year'])}</div><div class="cp-kpi-note">{hottest_year_row['avg_temperature_c']:.2f}°C mean</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Coolest year</div><div class="cp-mini-value">{int(coldest_year_row['year'])}</div><div class="cp-kpi-note">{coldest_year_row['avg_temperature_c']:.2f}°C mean</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Most ≥35°C days</div><div class="cp-mini-value">{int(most_extreme_heat_row['extreme_hot_days_35c'])} days</div><div class="cp-kpi-note">{int(most_extreme_heat_row['year'])}</div></div>
<div class="cp-mini-card"><div class="cp-mini-label">Hottest daily maximum</div><div class="cp-mini-value">{summary['hottest_day_c'].max():.1f}°C</div><div class="cp-kpi-note">1990–2025 record</div></div>
</div>
            """,
            unsafe_allow_html=True,
        )

if nav_view == "Dashboard":
    st.markdown('<div id="data-methods"></div>', unsafe_allow_html=True)
    with st.expander("Technical Details & Data"):
        st.markdown(
            """
    **Climate source:** ERA5 reanalysis accessed programmatically through Open-Meteo.

    **Historical period:** 1990–2025.

    **Climate reference period:** 1991–2020.

    **Temperature anomaly:** annual mean temperature minus the city's 1991–2020 ERA5 mean.

    **Warming trend:** least-squares regression slope calculated in PostgreSQL using annual mean temperatures and expressed in °C per decade.

    **Extreme heat indicators:** number of days where daily maximum temperature is at least 30°C and 35°C.

    ERA5 represents gridded reanalysis conditions around the selected coordinates rather than a single physical weather station.
            """
        )
        tab1, tab2 = st.tabs(["Annual climate data", "Temperature anomalies"])
        with tab1:
            st.dataframe(summary, width="stretch", hide_index=True)
        with tab2:
            st.dataframe(anomalies, width="stretch", hide_index=True)


st.markdown(
    '<div class="cp-footer">ClimatePulse • Python + PostgreSQL + Neon + MapTiler + CARTO + Open-Meteo + ERA5 + Streamlit</div>',
    unsafe_allow_html=True,
)