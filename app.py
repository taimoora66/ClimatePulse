import hashlib
import os

import pandas as pd
import plotly.express as px
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
from src.services.climate_service import ensure_city_history


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

def get_maptiler_key():

    try:
        if "MAPTILER_KEY" in st.secrets:
            return st.secrets["MAPTILER_KEY"]
    except Exception:
        pass

    return os.getenv(
        "MAPTILER_KEY"
    )


MAPTILER_KEY = get_maptiler_key()


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ClimatePulse",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background:
        radial-gradient(
            circle at 15% 0%,
            #16384a 0%,
            #07151e 28%,
            #02070b 72%
        );
    color: #f7fbfd;
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

[data-testid="stSidebar"] {
    background: #041017;
    border-right: 1px solid rgba(180, 225, 240, 0.14);
}

[data-testid="stSidebar"] * {
    color: #edf8fb;
}

[data-testid="stMetric"] {
    background:
        linear-gradient(
            145deg,
            rgba(18, 55, 70, 0.98),
            rgba(5, 22, 30, 0.98)
        );
    border: 1px solid rgba(130, 220, 235, 0.18);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
}

[data-testid="stMetricLabel"] {
    color: #a9c9d3 !important;
}

[data-testid="stMetricValue"] {
    color: #ffffff !important;
}

.hero-card {
    background:
        linear-gradient(
            120deg,
            #113547 0%,
            #08222d 58%,
            #06141b 100%
        );
    border: 1px solid rgba(128, 225, 241, 0.18);
    border-radius: 22px;
    padding: 28px;
    color: #ffffff;
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.25);
    margin-bottom: 24px;
}

.hero-title {
    color: #ffffff;
    font-size: 2.35rem;
    font-weight: 800;
    line-height: 1.1;
}

.hero-subtitle {
    color: #c9e2ea;
    margin-top: 10px;
    font-size: 1.02rem;
}

.section-title {
    color: #f8fcfd;
    font-size: 1.6rem;
    font-weight: 700;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}

h1,
h2,
h3 {
    color: #f8fcfd !important;
}

p,
label {
    color: #d7e9ee;
}

[data-testid="stHeader"] {
    background: transparent;
}

[data-testid="stToolbar"] {
    display: none;
}

[data-testid="stDecoration"] {
    display: none;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

</style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "selected_city_id" not in st.session_state:
    st.session_state.selected_city_id = None

if "selected_location" not in st.session_state:
    st.session_state.selected_location = None

if "selected_country" not in st.session_state:
    st.session_state.selected_country = None

if "map_lat" not in st.session_state:
    st.session_state.map_lat = 20.0

if "map_lon" not in st.session_state:
    st.session_state.map_lon = 0.0

if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 1.4

if "map_label" not in st.session_state:
    st.session_state.map_label = "World"


# =========================================================
# HELPERS
# =========================================================

def safe_float(value):
    if value is None:
        return None
    return float(value)


def stable_maptiler_id(maptiler_id):
    """
    Convert a MapTiler string ID such as
    'municipality.52052' into a stable positive BIGINT.
    """
    value = str(maptiler_id)

    digest = hashlib.blake2b(
        value.encode("utf-8"),
        digest_size=8,
    ).digest()

    number = int.from_bytes(
        digest,
        byteorder="big",
        signed=False,
    )

    return number & 0x7FFFFFFFFFFFFFFF


def maptiler_result_label(feature):
    """
    Return the best readable label from a MapTiler feature.
    """
    properties = feature.get("properties", {})

    candidates = [
        feature.get("place_name"),
        properties.get("place_name"),
        feature.get("text"),
        properties.get("name"),
        feature.get("name"),
    ]

    for candidate in candidates:
        if candidate:
            return str(candidate)

    return "Unknown location"


def maptiler_feature_type(feature):
    """
    Normalize MapTiler result type.
    """
    properties = feature.get("properties", {})

    place_types = feature.get("place_type", [])

    if isinstance(place_types, str):
        place_types = [place_types]

    feature_type = (
        properties.get("feature_type")
        or properties.get("type")
        or ""
    )

    combined = " ".join(
        str(value).lower()
        for value in place_types
    )

    combined += " " + str(feature_type).lower()

    if "country" in combined:
        return "country"

    if "region" in combined:
        return "region"

    if any(
        word in combined
        for word in [
            "place",
            "city",
            "municipality",
            "locality",
            "town",
            "village",
        ]
    ):
        return "place"

    return "location"


def maptiler_coordinates(feature):
    """
    Extract longitude/latitude from a MapTiler feature.
    """
    geometry = feature.get("geometry", {})

    coordinates = geometry.get("coordinates")

    if (
        isinstance(coordinates, (list, tuple))
        and len(coordinates) >= 2
        and isinstance(coordinates[0], (int, float))
        and isinstance(coordinates[1], (int, float))
    ):
        return float(coordinates[0]), float(coordinates[1])

    center = feature.get("center")

    if (
        isinstance(center, (list, tuple))
        and len(center) >= 2
    ):
        return float(center[0]), float(center[1])

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


def extract_context_value(feature, prefixes):
    """
    Extract a named parent object from MapTiler context.
    """
    context = feature.get("context", [])

    for item in context:
        item_id = str(item.get("id", "")).lower()
        item_properties = item.get("properties", {})

        if any(
            item_id.startswith(prefix)
            for prefix in prefixes
        ):
            name = (
                item.get("text")
                or item_properties.get("name")
                or item.get("place_name")
            )

            short_code = (
                item.get("short_code")
                or item_properties.get("short_code")
                or item_properties.get("country_code")
            )

            return name, short_code

    return None, None


def maptiler_to_climate_location(feature):
    """
    Convert MapTiler's feature structure into the location
    dictionary expected by ClimatePulse services/database.
    """
    properties = feature.get("properties", {})

    coordinates = maptiler_coordinates(feature)

    if not coordinates:
        raise ValueError(
            "Selected MapTiler result has no usable coordinates."
        )

    longitude, latitude = coordinates

    display_label = maptiler_result_label(feature)

    # Prefer explicit local name over the long place label.
    name = (
        feature.get("text")
        or properties.get("name")
        or feature.get("name")
    )

    if not name:
        # Fallback: first part of "Milano, Italia"
        name = display_label.split(",")[0].strip()

    country_name, country_short_code = extract_context_value(
        feature,
        prefixes=("country",),
    )

    admin1, _ = extract_context_value(
        feature,
        prefixes=("region", "state", "province"),
    )

    # MapTiler may expose parent metadata directly.
    if not country_name:
        country_name = (
            properties.get("country")
            or properties.get("country_name")
        )

    country_code = (
        country_short_code
        or properties.get("country_code")
        or properties.get("country_code_alpha_2")
    )

    if country_code:
        country_code = (
            str(country_code)
            .split("-")[-1]
            .upper()
        )

    # If context parsing still fails, infer country from the
    # last part of the readable place label.
    if not country_name and "," in display_label:
        country_name = display_label.split(",")[-1].strip()

    external_source_id = feature.get("id")

    if not external_source_id:
        external_source_id = (
            f"{name}|{latitude:.6f}|{longitude:.6f}"
        )

    population = (
        properties.get("population")
        or feature.get("population")
    )

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
    }


def climate_location_label(location):
    parts = []

    name = location.get("name")
    admin1 = location.get("admin1")
    country = location.get("country")
    country_code = location.get("country_code")

    if name:
        parts.append(str(name))

    if admin1 and admin1 not in parts:
        parts.append(str(admin1))

    if country and country not in parts:
        parts.append(str(country))

    label = ", ".join(parts)

    if country_code:
        label += f" - {country_code}"

    return label or "Selected location"


def update_map_from_feature(feature):
    coordinates = maptiler_coordinates(feature)

    if not coordinates:
        return

    longitude, latitude = coordinates

    result_type = maptiler_feature_type(feature)

    st.session_state.map_lon = longitude
    st.session_state.map_lat = latitude
    st.session_state.map_label = maptiler_result_label(feature)

    if result_type == "country":
        st.session_state.map_zoom = 4.0
    elif result_type == "region":
        st.session_state.map_zoom = 6.0
    elif result_type == "place":
        st.session_state.map_zoom = 9.0
    else:
        st.session_state.map_zoom = 12.0


# =========================================================
# CACHED DATA
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def cached_annual_summary(city_id):
    return get_annual_climate_summary(city_id)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_temperature_anomalies(city_id):
    return get_temperature_anomalies(city_id)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_city_details(city_id):
    return get_city_details(city_id)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_climate_trend(city_id):
    return get_climate_trend(city_id)


@st.cache_data(ttl=600, show_spinner=False)
def cached_current_weather(latitude, longitude, timezone):
    return get_current_weather(
        latitude,
        longitude,
        timezone=timezone,
    )


@st.cache_data(ttl=600, show_spinner=False)
def cached_air_quality(latitude, longitude, timezone):
    return get_current_air_quality(
        latitude,
        longitude,
        timezone=timezone,
    )


# =========================================================
# MAPTILER SEARCH
# =========================================================

def global_search(search_term):
    """
    One MapTiler autocomplete for countries, regions,
    cities and locations.
    """
    query = search_term.strip()

    if len(query) < 2:
        return []

    try:
        features = search_maptiler_places(
            query,
            limit=10,
        )
    except Exception as error:
        print(
            "MapTiler search error:",
            error,
        )
        return []

    results = []

    for feature in features:
        coordinates = maptiler_coordinates(feature)

        if not coordinates:
            continue

        result = dict(feature)

        result["result_type"] = maptiler_feature_type(
            feature
        )

        result["map_lon"] = coordinates[0]
        result["map_lat"] = coordinates[1]

        label = maptiler_result_label(
            feature
        )

        results.append(
            (
                label,
                result,
            )
        )

    return results


# =========================================================
# SIDEBAR SEARCH
# =========================================================

st.sidebar.markdown("## 🌍 ClimatePulse")
st.sidebar.caption("Global Climate Intelligence")
st.sidebar.divider()

with st.sidebar:
    selected_search_result = st_searchbox(
        global_search,
        key="global_place_search",
        label="Search city, place or country",
        placeholder="Milan, Pakistan, Tokyo, Italy...",
        debounce=350,
        edit_after_submit="option",
        clear_on_submit=False,
    )


# =========================================================
# HANDLE SELECTED SEARCH RESULT
# =========================================================

if selected_search_result:

    result_type = selected_search_result.get(
        "result_type",
        "location",
    )

    # Always move the permanent map immediately.
    update_map_from_feature(
        selected_search_result
    )

    selected_label = maptiler_result_label(
        selected_search_result
    )

    # -----------------------------------------------------
    # COUNTRY
    # -----------------------------------------------------

    if result_type == "country":

        st.session_state.selected_country = (
            selected_search_result
        )

        st.session_state.selected_city_id = None
        st.session_state.selected_location = None

        st.sidebar.caption(
            "Selected country"
        )

        st.sidebar.success(
            f"🌐 {selected_label}"
        )

    # -----------------------------------------------------
    # PLACE / CITY / MUNICIPALITY
    # -----------------------------------------------------

    elif result_type == "place":

        try:
            selected_location = maptiler_to_climate_location(
                selected_search_result
            )
        except Exception as error:
            selected_location = None
            st.sidebar.error(
                f"Location conversion failed: {error}"
            )

        if selected_location:

            st.sidebar.caption(
                "Selected location"
            )

            st.sidebar.success(
                f"📍 {climate_location_label(selected_location)}"
            )

            if st.sidebar.button(
                "Load climate dashboard",
                type="primary",
                width="stretch",
                key="load_city_dashboard",
            ):

                try:
                    with st.spinner(
                        "Preparing climate history..."
                    ):
                        result = ensure_city_history(
                            selected_location
                        )

                    st.session_state.selected_city_id = (
                        result["city_id"]
                    )

                    st.session_state.selected_location = (
                        selected_location
                    )

                    st.session_state.selected_country = None

                    # Refresh cached SQL views/data.
                    cached_city_details.clear()
                    cached_annual_summary.clear()
                    cached_temperature_anomalies.clear()
                    cached_climate_trend.clear()

                    if result["downloaded"]:
                        st.sidebar.success(
                            f"Imported "
                            f"{result['records_saved']:,} "
                            f"daily ERA5 records."
                        )
                    else:
                        st.sidebar.success(
                            "Climate history loaded "
                            "from PostgreSQL."
                        )

                except Exception as error:
                    st.sidebar.error(
                        "Unable to load climate data: "
                        f"{error}"
                    )

    # -----------------------------------------------------
    # REGION / ADDRESS / OTHER MAP LOCATION
    # -----------------------------------------------------

    else:

        st.session_state.selected_city_id = None
        st.session_state.selected_location = None
        st.session_state.selected_country = None

        st.sidebar.caption(
            "Selected map location"
        )

        st.sidebar.success(
            f"🗺 {selected_label}"
        )


st.sidebar.divider()
st.sidebar.caption(
    "Historical climate: ERA5 reanalysis"
)
st.sidebar.caption(
    "Analytics engine: PostgreSQL"
)


# =========================================================
# PERMANENT INTERACTIVE MAP
# =========================================================

st.markdown(
    '<div class="section-title">🗺 Explore the World</div>',
    unsafe_allow_html=True,
)

map_control_1, map_control_2 = st.columns(
    [2, 1]
)

with map_control_1:
    map_style_name = st.radio(
        "Map appearance",
        [
            "Street",
            "Dark",
            "Satellite",
        ],
        horizontal=True,
        key="permanent_map_style",
    )

with map_control_2:
    map_pitch = st.slider(
        "3D tilt",
        min_value=0,
        max_value=60,
        value=20,
        step=5,
        key="permanent_map_pitch",
    )


if not MAPTILER_KEY:

    st.warning(
        "MapTiler key is missing. "
        "Check MAPTILER_KEY in your .env file."
    )

else:

    if map_style_name == "Street":
        map_style = (
            "https://api.maptiler.com/"
            "maps/streets-v4/style.json"
            f"?key={MAPTILER_KEY}"
        )

    elif map_style_name == "Dark":
        # Reliable fallback style.
        map_style = (
            "https://basemaps.cartocdn.com/"
            "gl/dark-matter-gl-style/style.json"
        )

    else:
        map_style = (
            "https://api.maptiler.com/"
            "maps/satellite/style.json"
            f"?key={MAPTILER_KEY}"
        )

    map_dataframe = pd.DataFrame(
        {
            "label": [
                st.session_state.map_label
            ],
            "latitude": [
                st.session_state.map_lat
            ],
            "longitude": [
                st.session_state.map_lon
            ],
        }
    )

    marker_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_dataframe,
        get_position=[
            "longitude",
            "latitude",
        ],
        get_radius=12000,
        radius_min_pixels=7,
        radius_max_pixels=18,
        get_fill_color=[
            35,
            200,
            225,
            220,
        ],
        get_line_color=[
            255,
            255,
            255,
            230,
        ],
        line_width_min_pixels=2,
        stroked=True,
        filled=True,
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=st.session_state.map_lat,
        longitude=st.session_state.map_lon,
        zoom=st.session_state.map_zoom,
        pitch=map_pitch,
        bearing=0,
    )

    deck = pdk.Deck(
        map_style=map_style,
        initial_view_state=view_state,
        layers=[
            marker_layer
        ],
        tooltip={
            "html": "<b>{label}</b>",
            "style": {
                "backgroundColor": "#071117",
                "color": "#ffffff",
            },
        },
    )

    st.pydeck_chart(
        deck,
        width="stretch",
        height=520,
    )


# =========================================================
# LANDING / COUNTRY MODE
# =========================================================

if st.session_state.selected_city_id is None:

    if st.session_state.selected_country:

        country_label = maptiler_result_label(
            st.session_state.selected_country
        )

        st.markdown(
            f"""
<div class="hero-card">
<div class="hero-title">{country_label}</div>
<div class="hero-subtitle">Country selected. The map above follows your search immediately. Select a city or municipality to load detailed climate analytics.</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            """
<div class="hero-card">
<div class="hero-title">Global Climate Intelligence</div>
<div class="hero-subtitle">Search countries, regions and cities. The map is always available; detailed ERA5 and PostgreSQL analytics load only when you choose a city.</div>
</div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()


# =========================================================
# LOAD SQL DATA
# =========================================================

city_id = st.session_state.selected_city_id

city = cached_city_details(
    city_id
)

if city is None:
    st.error(
        "The selected city could not be found."
    )
    st.stop()


summary = cached_annual_summary(
    city_id
)

anomalies = cached_temperature_anomalies(
    city_id
)

trend = cached_climate_trend(
    city_id
)


if summary.empty:
    st.error(
        "No climate records are available."
    )
    st.stop()


if anomalies.empty:
    st.error(
        "No temperature anomaly records are available."
    )
    st.stop()


# =========================================================
# LIVE DATA
# =========================================================

current_weather_data = cached_current_weather(
    city["latitude"],
    city["longitude"],
    city["timezone"],
)

air_quality_data = cached_air_quality(
    city["latitude"],
    city["longitude"],
    city["timezone"],
)

current_weather = current_weather_data.get(
    "current",
    {},
)

current_air = air_quality_data.get(
    "current",
    {},
)


# =========================================================
# CONVERT NUMERIC COLUMNS
# =========================================================

summary_numeric_columns = [
    "avg_temperature_c",
    "avg_max_temperature_c",
    "avg_min_temperature_c",
    "hottest_day_c",
    "coldest_day_c",
    "annual_precipitation_mm",
    "hot_days_30c",
    "extreme_hot_days_35c",
]

for column in summary_numeric_columns:
    if column in summary.columns:
        summary[column] = pd.to_numeric(
            summary[column],
            errors="coerce",
        )


anomaly_numeric_columns = [
    "annual_temperature_c",
    "baseline_temperature_c",
    "anomaly_c",
]

for column in anomaly_numeric_columns:
    if column in anomalies.columns:
        anomalies[column] = pd.to_numeric(
            anomalies[column],
            errors="coerce",
        )


latest = summary.iloc[-1]
latest_anomaly = anomalies.iloc[-1]

warming_rate = None

if trend:
    warming_rate = safe_float(
        trend.get(
            "warming_rate_c_per_decade"
        )
    )


# =========================================================
# HERO HEADER
# =========================================================

st.markdown(
    f"""
<div class="hero-card">
<div class="hero-title">{city['city_name']}, {city['country_name']}</div>
<div class="hero-subtitle">{city['latitude']:.4f}° • {city['longitude']:.4f}° &nbsp;•&nbsp; {city['timezone']} &nbsp;•&nbsp; ERA5 climate record 1990–2025</div>
</div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# LIVE ENVIRONMENT
# =========================================================

st.markdown(
    '<div class="section-title">⚡ Live Environment</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Current weather and air-quality conditions "
    "for the selected location."
)

live1, live2, live3, live4 = st.columns(
    4
)

with live1:
    temperature = current_weather.get(
        "temperature_2m"
    )

    feels_like = current_weather.get(
        "apparent_temperature"
    )

    temperature_text = (
        f"{temperature:.1f} °C"
        if temperature is not None
        else "N/A"
    )

    feels_text = (
        f"Feels like {feels_like:.1f} °C"
        if feels_like is not None
        else None
    )

    st.metric(
        "Current Temperature",
        temperature_text,
        feels_text,
    )


with live2:
    humidity = current_weather.get(
        "relative_humidity_2m"
    )

    st.metric(
        "Humidity",
        (
            f"{humidity:.0f}%"
            if humidity is not None
            else "N/A"
        ),
    )


with live3:
    wind = current_weather.get(
        "wind_speed_10m"
    )

    st.metric(
        "Wind Speed",
        (
            f"{wind:.1f} km/h"
            if wind is not None
            else "N/A"
        ),
    )


with live4:
    precipitation = current_weather.get(
        "precipitation"
    )

    st.metric(
        "Current Precipitation",
        (
            f"{precipitation:.1f} mm"
            if precipitation is not None
            else "N/A"
        ),
    )


# =========================================================
# AIR QUALITY
# =========================================================

st.markdown(
    '<div class="section-title">🌫 Air Quality</div>',
    unsafe_allow_html=True,
)

air1, air2, air3, air4, air5 = st.columns(
    5
)

with air1:
    aqi = current_air.get(
        "european_aqi"
    )

    st.metric(
        "European AQI",
        (
            f"{aqi:.0f}"
            if aqi is not None
            else "N/A"
        ),
    )


with air2:
    pm25 = current_air.get(
        "pm2_5"
    )

    st.metric(
        "PM2.5",
        (
            f"{pm25:.1f} µg/m³"
            if pm25 is not None
            else "N/A"
        ),
    )


with air3:
    pm10 = current_air.get(
        "pm10"
    )

    st.metric(
        "PM10",
        (
            f"{pm10:.1f} µg/m³"
            if pm10 is not None
            else "N/A"
        ),
    )


with air4:
    no2 = current_air.get(
        "nitrogen_dioxide"
    )

    st.metric(
        "NO₂",
        (
            f"{no2:.1f} µg/m³"
            if no2 is not None
            else "N/A"
        ),
    )


with air5:
    ozone = current_air.get(
        "ozone"
    )

    st.metric(
        "O₃",
        (
            f"{ozone:.1f} µg/m³"
            if ozone is not None
            else "N/A"
        ),
    )


st.divider()


# =========================================================
# HISTORICAL KPI CARDS
# =========================================================

k1, k2, k3, k4, k5 = st.columns(
    5
)

with k1:
    st.metric(
        "2025 Mean Temperature",
        f"{latest['avg_temperature_c']:.1f} °C",
    )

with k2:
    st.metric(
        "2025 Anomaly",
        f"{latest_anomaly['anomaly_c']:+.2f} °C",
    )

with k3:
    trend_text = (
        f"{warming_rate:+.2f} °C/decade"
        if warming_rate is not None
        else "N/A"
    )

    st.metric(
        "Linear Warming Trend",
        trend_text,
    )

with k4:
    st.metric(
        "Days ≥ 30°C",
        int(
            latest[
                "hot_days_30c"
            ]
        ),
    )

with k5:
    st.metric(
        "2025 Precipitation",
        f"{latest['annual_precipitation_mm']:.0f} mm",
    )


# =========================================================
# TEMPERATURE EVOLUTION
# =========================================================

st.markdown(
    '<div class="section-title">🌡 Temperature Evolution</div>',
    unsafe_allow_html=True,
)

fig_temp = go.Figure()

fig_temp.add_trace(
    go.Scatter(
        x=summary["year"],
        y=summary[
            "avg_temperature_c"
        ],
        mode="lines+markers",
        name="Annual mean",
        line=dict(
            width=3
        ),
        marker=dict(
            size=6
        ),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Mean temperature: %{y:.2f} °C"
            "<extra></extra>"
        ),
    )
)

fig_temp.update_layout(
    template="plotly_dark",
    height=430,
    margin=dict(
        l=20,
        r=20,
        t=30,
        b=20,
    ),
    hovermode="x unified",
    xaxis_title=None,
    yaxis_title="Temperature (°C)",
)

st.plotly_chart(
    fig_temp,
    width="stretch",
)


# =========================================================
# TEMPERATURE ANOMALY
# =========================================================

st.markdown(
    '<div class="section-title">🔥 Temperature Anomaly</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Difference between each annual mean temperature "
    "and the 1991–2020 reference climate."
)

fig_anomaly = px.bar(
    anomalies,
    x="year",
    y="anomaly_c",
    labels={
        "year": "Year",
        "anomaly_c": "Temperature anomaly (°C)",
    },
)

fig_anomaly.add_hline(
    y=0,
    line_width=1,
)

fig_anomaly.update_layout(
    template="plotly_dark",
    height=420,
    margin=dict(
        l=20,
        r=20,
        t=20,
        b=20,
    ),
    hovermode="x unified",
)

st.plotly_chart(
    fig_anomaly,
    width="stretch",
)


# =========================================================
# EXTREME HEAT + PRECIPITATION
# =========================================================

left, right = st.columns(
    2
)

with left:
    st.markdown(
        '<div class="section-title">☀️ Extreme Heat</div>',
        unsafe_allow_html=True,
    )

    fig_heat = go.Figure()

    fig_heat.add_trace(
        go.Bar(
            x=summary["year"],
            y=summary[
                "hot_days_30c"
            ],
            name="≥ 30°C",
        )
    )

    fig_heat.add_trace(
        go.Bar(
            x=summary["year"],
            y=summary[
                "extreme_hot_days_35c"
            ],
            name="≥ 35°C",
        )
    )

    fig_heat.update_layout(
        template="plotly_dark",
        barmode="group",
        height=400,
        margin=dict(
            l=15,
            r=15,
            t=20,
            b=20,
        ),
        yaxis_title="Number of days",
        xaxis_title=None,
    )

    st.plotly_chart(
        fig_heat,
        width="stretch",
    )


with right:
    st.markdown(
        '<div class="section-title">🌧 Precipitation</div>',
        unsafe_allow_html=True,
    )

    fig_rain = go.Figure()

    fig_rain.add_trace(
        go.Scatter(
            x=summary["year"],
            y=summary[
                "annual_precipitation_mm"
            ],
            mode="lines+markers",
            fill="tozeroy",
            name="Annual precipitation",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "%{y:.0f} mm"
                "<extra></extra>"
            ),
        )
    )

    fig_rain.update_layout(
        template="plotly_dark",
        height=400,
        margin=dict(
            l=15,
            r=15,
            t=20,
            b=20,
        ),
        yaxis_title="Precipitation (mm)",
        xaxis_title=None,
    )

    st.plotly_chart(
        fig_rain,
        width="stretch",
    )


# =========================================================
# CLIMATE SNAPSHOT
# =========================================================

st.markdown(
    '<div class="section-title">📊 Climate Snapshot</div>',
    unsafe_allow_html=True,
)

hottest_year_row = summary.loc[
    summary[
        "avg_temperature_c"
    ].idxmax()
]

coldest_year_row = summary.loc[
    summary[
        "avg_temperature_c"
    ].idxmin()
]

most_extreme_heat_row = summary.loc[
    summary[
        "extreme_hot_days_35c"
    ].idxmax()
]

s1, s2, s3 = st.columns(
    3
)

with s1:
    st.metric(
        "Hottest Year",
        int(
            hottest_year_row[
                "year"
            ]
        ),
        f"{hottest_year_row['avg_temperature_c']:.2f} °C mean",
    )

with s2:
    st.metric(
        "Coolest Year",
        int(
            coldest_year_row[
                "year"
            ]
        ),
        f"{coldest_year_row['avg_temperature_c']:.2f} °C mean",
    )

with s3:
    st.metric(
        "Most ≥35°C Days",
        int(
            most_extreme_heat_row[
                "extreme_hot_days_35c"
            ]
        ),
        f"Year {int(most_extreme_heat_row['year'])}",
    )


# =========================================================
# SQL DATA EXPLORER
# =========================================================

st.markdown(
    '<div class="section-title">🗄 SQL Climate Data Explorer</div>',
    unsafe_allow_html=True,
)

with st.expander(
    "View annual PostgreSQL results"
):
    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
    )


with st.expander(
    "View temperature anomalies"
):
    st.dataframe(
        anomalies,
        width="stretch",
        hide_index=True,
    )


# =========================================================
# METHODOLOGY
# =========================================================

with st.expander(
    "Methodology & Data Source"
):
    st.markdown(
        """
**Climate source:** ERA5 reanalysis accessed
programmatically through Open-Meteo.

**Historical period:** 1990–2025.

**Climate reference period:** 1991–2020.

**Temperature anomaly:** annual mean temperature
minus the city's 1991–2020 ERA5 mean.

**Warming trend:** least-squares regression slope
calculated in PostgreSQL using annual mean
temperatures and expressed in °C per decade.

**Extreme heat indicators:** number of days where
daily maximum temperature is at least 30°C and 35°C.

ERA5 represents gridded reanalysis conditions around
the selected coordinates rather than a single
physical weather station.
        """
    )


st.divider()

st.caption(
    "ClimatePulse • Python + PostgreSQL + SQL + "
    "MapTiler + Open-Meteo + ERA5 + Streamlit + "
    "Plotly + PyDeck"
)