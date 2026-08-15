from __future__ import annotations

import html

from datetime import datetime, timezone
from typing import Any

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from src.analytics import record_error
except Exception:
    record_error = None

from src.api.home_environment import (
    get_global_weather_pulse,
    get_home_environment,
    get_home_environment_detail,
    get_official_alerts,
)
from src.api.future_climate import (
    get_midcentury_ensemble,
)
from src.api.country_rankings import (
    CCKP_SCENARIOS,
    get_country_scenario_trajectory,
)
from src.ai_assistant import (
    ask_huggingface,
    get_ai_status,
)
from src.location_widget import render_location_control
from src.live_globe import (
    cached_country_field,
    render_live_weather_globe,
)
from src.services.context_engine import (
    aqi_level,
    build_compound_context,
    build_context_alerts,
    build_guidance,
    build_health_context,
    build_intelligence_brief,
    find_low_stress_window,
    weather_code_text,
)


FUTURE_CORE_MODELS = (
    "CMCC_CM2_VHR4",
    "MRI_AGCM3_2_S",
    "EC_Earth3P_HR",
    "MPI_ESM1_2_XR",
)


@st.cache_data(
    ttl=600,
    max_entries=128,
    show_spinner=False,
)
def cached_home_environment(
    latitude,
    longitude,
    timezone,
):
    return get_home_environment(
        latitude,
        longitude,
        timezone,
    )


@st.cache_data(
    ttl=900,
    max_entries=128,
    show_spinner=False,
)
def cached_home_environment_detail(
    latitude,
    longitude,
    timezone,
):
    return get_home_environment_detail(
        latitude,
        longitude,
        timezone,
    )


@st.cache_data(
    ttl=600,
    max_entries=8,
    show_spinner=False,
)
def cached_global_pulse():
    return get_global_weather_pulse()


@st.cache_data(
    ttl=180,
    max_entries=64,
    show_spinner=False,
)
def cached_official_alerts(
    latitude,
    longitude,
):
    try:
        return get_official_alerts(
            latitude,
            longitude,
        )
    except Exception:
        return []


@st.cache_data(
    ttl=86400,
    max_entries=64,
    show_spinner=False,
)
def cached_home_future(
    latitude,
    longitude,
):
    return get_midcentury_ensemble(
        latitude=latitude,
        longitude=longitude,
        model_names=FUTURE_CORE_MODELS,
    )


@st.cache_data(
    ttl=86400,
    max_entries=128,
    show_spinner=False,
)
def cached_country_trajectory(
    iso3,
    scenario,
):
    return get_country_scenario_trajectory(
        iso3_code=iso3,
        scenario=scenario,
    )


def _num(
    value,
):
    try:
        return float(
            value
        )
    except Exception:
        return None


def _fmt(
    value,
    spec=".1f",
    suffix="",
):
    value = _num(
        value
    )

    if value is None:
        return "—"

    return (
        f"{value:{spec}}"
        f"{suffix}"
    )


def _go_to(
    target,
):
    st.session_state[
        "main_navigation"
    ] = target


def _location_context(
    city,
    point_location,
    country_feature,
    country_location,
):
    """
    Resolve the active location without depending on historical DB import.

    This is important for small places/regions: live weather can load
    immediately even while ERA5 history is still being prepared.
    """
    if city is not None:
        name = (
            city.get(
                "city_name"
            )
            or city.get(
                "name"
            )
            or "Selected location"
        )

        country = (
            city.get(
                "country_name"
            )
            or city.get(
                "country"
            )
            or ""
        )

        label = (
            f"{name}, {country}"
            if country
            else name
        )

        return {
            "name": label,
            "latitude": city.get(
                "latitude"
            ),
            "longitude": city.get(
                "longitude"
            ),
            "timezone": city.get(
                "timezone",
                "auto",
            ),
            "country_code": (
                city.get(
                    "country_code"
                )
            ),
            "kind": "city",
            "scope_note": None,
        }

    if point_location is not None:
        name = (
            point_location.get(
                "name"
            )
            or "Selected place"
        )

        admin = (
            point_location.get(
                "admin1"
            )
        )

        country = (
            point_location.get(
                "country"
            )
        )

        parts = []

        for value in [
            name,
            admin,
            country,
        ]:
            if (
                value
                and value not in parts
            ):
                parts.append(
                    str(
                        value
                    )
                )

        return {
            "name": ", ".join(
                parts
            ),
            "latitude": point_location.get(
                "latitude"
            ),
            "longitude": point_location.get(
                "longitude"
            ),
            "timezone": point_location.get(
                "timezone",
                "auto",
            ),
            "country_code": point_location.get(
                "country_code"
            ),
            "kind": (
                point_location.get(
                    "result_type"
                )
                or "place"
            ),
            "scope_note": point_location.get(
                "scope_note"
            ),
        }

    if (
        country_feature
        and country_location
    ):
        name = (
            country_feature.get(
                "text_en"
            )
            or country_feature.get(
                "text"
            )
            or country_feature.get(
                "place_name_en"
            )
            or country_feature.get(
                "place_name"
            )
            or country_location.get(
                "country"
            )
            or country_location.get(
                "name"
            )
            or "Selected country"
        )

        return {
            "name": name,
            "latitude": country_location.get(
                "latitude"
            ),
            "longitude": country_location.get(
                "longitude"
            ),
            "timezone": country_location.get(
                "timezone",
                "auto",
            ),
            "country_code": (
                country_location.get(
                    "country_code"
                )
            ),
            "kind": "country",
            "scope_note": (
                "Live conditions are shown at the country search centroid; "
                "historical country climate uses national spatial averages."
            ),
        }

    return None


def _condition_palette(
    current,
    air_current,
    trend=None,
):
    """
    ORBIDENSE AI Home hero presentation palette.

    V30 design rule:
    environmental conditions may change the accent/glow, but the whole
    ORBIDENSE AI hero should remain a stable dark-blue/teal brand surface.
    This prevents a hot current location from turning the entire header red.
    """

    temp = _num(
        current.get(
            "temperature_2m"
        )
    )

    feels = _num(
        current.get(
            "apparent_temperature"
        )
    )

    wind = _num(
        current.get(
            "wind_speed_10m"
        )
    )

    aqi = _num(
        air_current.get(
            "european_aqi"
        )
    )

    warming = None

    if isinstance(
        trend,
        dict,
    ):
        warming = _num(
            trend.get(
                "warming_rate_c_per_decade"
            )
            or trend.get(
                "trend_c_per_decade"
            )
            or trend.get(
                "slope_c_per_decade"
            )
        )

    thermal = (
        feels
        if feels is not None
        else temp
    )

    # Brand background stays stable.
    start_color = "#0a2a35"
    end_color = "#06131d"

    # Only the accent communicates current environmental context.
    accent = "#45dcff"

    if thermal is not None:
        if thermal >= 40:
            accent = "#ff695f"

        elif thermal >= 34:
            accent = "#ff8a52"

        elif thermal >= 28:
            accent = "#ffc15a"

        elif thermal >= 20:
            accent = "#4de0c4"

        elif thermal >= 10:
            accent = "#59bfff"

        else:
            accent = "#8ba2ff"

    if (
        wind is not None
        and wind >= 50
    ):
        accent = "#bb92ff"

    if (
        aqi is not None
        and aqi > 100
    ):
        accent = "#ff7180"

    if (
        warming is not None
        and warming >= 0.35
        and thermal is not None
        and thermal >= 25
    ):
        # Still use only a restrained accent.
        accent = "#ff825b"

    return {
        "start":
            start_color,
        "end":
            end_color,
        "accent":
            accent,
    }

def _subsolar_point(
    when=None,
):
    """
    Approximate the current subsolar point for the legacy Plotly fallback.
    The primary V21 globe uses src/live_globe.py.
    """
    if when is None:
        when = datetime.now(
            timezone.utc
        )

    day = when.timetuple().tm_yday

    hour = (
        when.hour
        + when.minute / 60.0
        + when.second / 3600.0
    )

    gamma = (
        2.0
        * math.pi
        / 365.0
        * (
            day
            - 1
            + (
                hour
                - 12.0
            )
            / 24.0
        )
    )

    declination = (
        0.006918
        - 0.399912
        * math.cos(
            gamma
        )
        + 0.070257
        * math.sin(
            gamma
        )
        - 0.006758
        * math.cos(
            2
            * gamma
        )
        + 0.000907
        * math.sin(
            2
            * gamma
        )
        - 0.002697
        * math.cos(
            3
            * gamma
        )
        + 0.00148
        * math.sin(
            3
            * gamma
        )
    )

    equation_of_time = 229.18 * (
        0.000075
        + 0.001868
        * math.cos(
            gamma
        )
        - 0.032077
        * math.sin(
            gamma
        )
        - 0.014615
        * math.cos(
            2
            * gamma
        )
        - 0.040849
        * math.sin(
            2
            * gamma
        )
    )

    solar_noon_minutes = (
        720
        - equation_of_time
    )

    current_minutes = (
        when.hour
        * 60
        + when.minute
        + when.second
        / 60.0
    )

    longitude = (
        solar_noon_minutes
        - current_minutes
    ) / 4.0

    while longitude > 180:
        longitude -= 360

    while longitude < -180:
        longitude += 360

    return (
        math.degrees(
            declination
        ),
        longitude,
    )


def _solar_cosine(
    latitude,
    longitude,
    subsolar_lat,
    subsolar_lon,
):
    lat = math.radians(
        latitude
    )

    lon = math.radians(
        longitude
    )

    solar_lat = math.radians(
        subsolar_lat
    )

    solar_lon = math.radians(
        subsolar_lon
    )

    return (
        math.sin(
            lat
        )
        * math.sin(
            solar_lat
        )
        + math.cos(
            lat
        )
        * math.cos(
            solar_lat
        )
        * math.cos(
            lon
            - solar_lon
        )
    )


def _night_grid():
    """
    Legacy Plotly-globe night mask fallback.
    """
    subsolar_lat, subsolar_lon = (
        _subsolar_point()
    )

    latitudes = []
    longitudes = []
    opacities = []

    for latitude in range(
        -80,
        81,
        8,
    ):
        for longitude in range(
            -180,
            181,
            8,
        ):
            cosine = _solar_cosine(
                latitude,
                longitude,
                subsolar_lat,
                subsolar_lon,
            )

            if cosine < 0:
                latitudes.append(
                    latitude
                )

                longitudes.append(
                    longitude
                )

                opacities.append(
                    min(
                        0.44,
                        0.16
                        + abs(
                            cosine
                        )
                        * 0.30,
                    )
                )

    return (
        latitudes,
        longitudes,
        opacities,
        subsolar_lat,
        subsolar_lon,
    )


def _weather_overlay_points(
    global_pulse,
):
    """
    Prepare legacy city-level rain/cloud markers for the Plotly fallback.
    """
    result = {
        "rain_lat": [],
        "rain_lon": [],
        "rain_text": [],
        "cloud_lat": [],
        "cloud_lon": [],
        "cloud_text": [],
    }

    for row in global_pulse:
        rain = _num(
            row.get(
                "precipitation_mm"
            )
        )

        cloud = _num(
            row.get(
                "cloud_cover"
            )
        )

        if (
            rain is not None
            and rain > 0
        ):
            result[
                "rain_lat"
            ].append(
                row[
                    "lat"
                ]
            )

            result[
                "rain_lon"
            ].append(
                row[
                    "lon"
                ]
            )

            result[
                "rain_text"
            ].append(
                (
                    f"<b>{row['name']}</b><br>"
                    f"Rain: {rain:.1f} mm"
                )
            )

        if (
            cloud is not None
            and cloud >= 75
        ):
            result[
                "cloud_lat"
            ].append(
                row[
                    "lat"
                ]
                + 1.5
            )

            result[
                "cloud_lon"
            ].append(
                row[
                    "lon"
                ]
                + 1.5
            )

            result[
                "cloud_text"
            ].append(
                (
                    f"<b>{row['name']}</b><br>"
                    f"Cloud cover: {cloud:.0f}%"
                )
            )

    return result


def _ai_context(
    selected,
    current,
    air_current,
    health,
    compound,
    official_alerts,
    trend,
):
    """
    Compact context object used by the optional Home AI panel.
    The global sidebar assistant also has its own context built in app.py.
    """
    return {
        "selected_location": (
            selected.get(
                "name"
            )
            if selected
            else None
        ),
        "current_weather": current,
        "current_air_quality": air_current,
        "health_context": health,
        "compound_context": compound,
        "official_alerts": official_alerts,
        "historical_trend": trend,
    }



def _globe_metric(
    row,
    layer,
):
    mapping = {
        "Temperature": row.get(
            "temperature_c"
        ),
        "Feels like": row.get(
            "apparent_temperature_c"
        ),
        "Air quality": row.get(
            "european_aqi"
        ),
        "Wind": row.get(
            "wind_kmh"
        ),
    }

    return _num(
        mapping.get(
            layer
        )
    )


def _globe_scale(
    layer,
):
    if layer in {
        "Temperature",
        "Feels like",
    }:
        return {
            "colorscale": "Turbo",
            "cmin": -10,
            "cmax": 40,
            "title": "°C",
        }

    if layer == "Air quality":
        return {
            "colorscale": [
                [0.0, "#44d19d"],
                [0.20, "#7bdc65"],
                [0.40, "#f0d85b"],
                [0.60, "#ff9d4d"],
                [0.80, "#ff5a68"],
                [1.0, "#a75ee8"],
            ],
            "cmin": 0,
            "cmax": 120,
            "title": "AQI",
        }

    return {
        "colorscale": "Blues",
        "cmin": 0,
        "cmax": 50,
        "title": "km/h",
    }


def _build_globe(
    global_pulse,
    selected,
    layer,
):
    scale = _globe_scale(
        layer
    )

    lats = []
    lons = []
    texts = []
    values = []
    sizes = []

    for row in global_pulse:
        value = _globe_metric(
            row,
            layer,
        )

        if value is None:
            continue

        lats.append(
            row[
                "lat"
            ]
        )
        lons.append(
            row[
                "lon"
            ]
        )
        values.append(
            value
        )
        sizes.append(
            9
            + min(
                9,
                abs(
                    value
                )
                / 7,
            )
        )

        texts.append(
            (
                f"<b>{row['name']}, "
                f"{row['country']}</b><br>"
                f"Temperature: {_fmt(row.get('temperature_c'), '.1f', '°C')}<br>"
                f"Feels like: {_fmt(row.get('apparent_temperature_c'), '.1f', '°C')}<br>"
                f"AQI: {_fmt(row.get('european_aqi'), '.0f')}<br>"
                f"Wind: {_fmt(row.get('wind_kmh'), '.0f', ' km/h')}<br>"
                f"Cloud: {_fmt(row.get('cloud_cover'), '.0f', '%')}<br>"
                f"Rain: {_fmt(row.get('precipitation_mm'), '.1f', ' mm')}<br>"
                f"{weather_code_text(row.get('weather_code'))}"
            )
        )

    fig = go.Figure()

    (
        night_lat,
        night_lon,
        night_opacity,
        subsolar_lat,
        subsolar_lon,
    ) = _night_grid()

    fig.add_trace(
        go.Scattergeo(
            lat=night_lat,
            lon=night_lon,
            mode="markers",
            marker=dict(
                size=12,
                color=[
                    f"rgba(0,3,12,{value:.3f})"
                    for value in night_opacity
                ],
                line=dict(
                    width=0
                ),
            ),
            hoverinfo="skip",
            showlegend=False,
            name="Night side",
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lat=[
                subsolar_lat
            ],
            lon=[
                subsolar_lon
            ],
            text=[
                "<b>Sun overhead</b><br>Current subsolar point"
            ],
            hoverinfo="text",
            mode="markers",
            marker=dict(
                size=20,
                color="#ffd75a",
                opacity=0.95,
                line=dict(
                    width=1,
                    color="#fff4b5",
                ),
                symbol="circle",
            ),
            showlegend=False,
            name="Sun",
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lat=lats,
            lon=lons,
            text=texts,
            hoverinfo="text",
            mode="markers",
            marker=dict(
                size=sizes,
                color=values,
                colorscale=scale[
                    "colorscale"
                ],
                cmin=scale[
                    "cmin"
                ],
                cmax=scale[
                    "cmax"
                ],
                opacity=0.96,
                line=dict(
                    width=1.0,
                    color="rgba(190,239,255,.76)",
                ),
                colorbar=dict(
                    title=scale[
                        "title"
                    ],
                    thickness=10,
                    len=0.42,
                    x=0.98,
                    y=0.46,
                    bgcolor="rgba(4,14,23,.50)",
                    outlinewidth=0,
                ),
            ),
            name=layer,
        )
    )

    overlay = _weather_overlay_points(
        global_pulse
    )

    if overlay[
        "rain_lat"
    ]:
        fig.add_trace(
            go.Scattergeo(
                lat=overlay[
                    "rain_lat"
                ],
                lon=overlay[
                    "rain_lon"
                ],
                text=overlay[
                    "rain_text"
                ],
                hoverinfo="text",
                mode="markers",
                marker=dict(
                    size=9,
                    color="#50b9ff",
                    symbol="diamond",
                    opacity=0.90,
                ),
                showlegend=False,
                name="Rain",
            )
        )

    if overlay[
        "cloud_lat"
    ]:
        fig.add_trace(
            go.Scattergeo(
                lat=overlay[
                    "cloud_lat"
                ],
                lon=overlay[
                    "cloud_lon"
                ],
                text=overlay[
                    "cloud_text"
                ],
                hoverinfo="text",
                mode="markers",
                marker=dict(
                    size=11,
                    color="#d5e2ea",
                    symbol="circle",
                    opacity=0.55,
                ),
                showlegend=False,
                name="Cloud",
            )
        )

    if selected:
        fig.add_trace(
            go.Scattergeo(
                lat=[
                    selected[
                        "latitude"
                    ]
                ],
                lon=[
                    selected[
                        "longitude"
                    ]
                ],
                text=[
                    (
                        f"<b>{selected['name']}</b><br>"
                        "Selected location"
                    )
                ],
                hoverinfo="text",
                mode="markers",
                marker=dict(
                    size=18,
                    symbol="star",
                    color="#ffffff",
                    line=dict(
                        width=2,
                        color="#46e3ff",
                    ),
                ),
                name="Selected",
            )
        )

    fig.update_geos(
        projection_type="orthographic",
        showland=True,
        landcolor="#102c38",
        showocean=True,
        oceancolor="#020812",
        showlakes=True,
        lakecolor="#03111f",
        showcountries=True,
        countrycolor="rgba(112,215,239,.18)",
        showcoastlines=True,
        coastlinecolor="rgba(84,229,255,.52)",
        bgcolor="rgba(0,0,0,0)",
        lataxis_showgrid=False,
        lonaxis_showgrid=False,
    )

    fig.update_layout(
        height=555,
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        dragmode="pan",
        font=dict(
            color="#dceaf3",
        ),
    )

    return fig


def _forecast_frame(
    hourly,
    hours=30,
):
    frame = pd.DataFrame(
        hourly
    )

    if frame.empty:
        return frame

    frame[
        "time"
    ] = pd.to_datetime(
        frame[
            "time"
        ],
        errors="coerce",
    )

    now = pd.Timestamp.now()

    return (
        frame
        .dropna(
            subset=[
                "time"
            ]
        )
        .loc[
            lambda data: (
                data[
                    "time"
                ]
                >= now.floor(
                    "h"
                )
            )
        ]
        .head(
            hours
        )
    )


def _forecast_chart(
    frame,
):
    fig = go.Figure()

    if frame.empty:
        return fig

    if "temperature_2m" in frame:
        fig.add_trace(
            go.Scatter(
                x=frame[
                    "time"
                ],
                y=frame[
                    "temperature_2m"
                ],
                mode="lines",
                name="Air temperature",
                line=dict(
                    width=2.6,
                ),
                fill="tozeroy",
                fillcolor="rgba(50,183,255,.05)",
            )
        )

    if "apparent_temperature" in frame:
        fig.add_trace(
            go.Scatter(
                x=frame[
                    "time"
                ],
                y=frame[
                    "apparent_temperature"
                ],
                mode="lines",
                name="Feels like",
                line=dict(
                    width=1.7,
                    dash="dot",
                ),
            )
        )

    fig.update_layout(
        height=245,
        margin=dict(
            l=8,
            r=8,
            t=15,
            b=5,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            y=1.12,
            x=0,
        ),
        font=dict(
            color="#8da6b7",
            size=10,
        ),
        xaxis=dict(
            gridcolor="rgba(139,179,208,.06)",
            showline=False,
        ),
        yaxis=dict(
            title="°C",
            gridcolor="rgba(139,179,208,.06)",
            showline=False,
        ),
        hovermode="x unified",
    )

    return fig


def _timeline_city_data(
    summary,
    anomalies,
):
    if (
        summary is None
        or summary.empty
    ):
        return pd.DataFrame()

    frame = summary.copy()

    if "year" not in frame:
        return pd.DataFrame()

    frame[
        "year"
    ] = pd.to_numeric(
        frame[
            "year"
        ],
        errors="coerce",
    )

    frame[
        "temperature_c"
    ] = pd.to_numeric(
        frame.get(
            "avg_temperature_c"
        ),
        errors="coerce",
    )

    if (
        anomalies is not None
        and not anomalies.empty
        and {
            "year",
            "anomaly_c",
        }.issubset(
            anomalies.columns
        )
    ):
        anom = anomalies[
            [
                "year",
                "anomaly_c",
            ]
        ].copy()

        anom[
            "year"
        ] = pd.to_numeric(
            anom[
                "year"
            ],
            errors="coerce",
        )

        anom[
            "anomaly_c"
        ] = pd.to_numeric(
            anom[
                "anomaly_c"
            ],
            errors="coerce",
        )

        frame = frame.drop(
            columns=[
                "anomaly_c"
            ],
            errors="ignore",
        ).merge(
            anom,
            on="year",
            how="left",
        )

    if "anomaly_c" not in frame:
        baseline = frame[
            (
                frame[
                    "year"
                ]
                >= 1991
            )
            &
            (
                frame[
                    "year"
                ]
                <= 2020
            )
        ][
            "temperature_c"
        ].mean()

        frame[
            "anomaly_c"
        ] = (
            frame[
                "temperature_c"
            ]
            - baseline
        )

    return frame.dropna(
        subset=[
            "year"
        ]
    )


def _timeline_country_data(
    country_national,
):
    if (
        country_national is None
        or country_national.empty
    ):
        return pd.DataFrame()

    frame = country_national.copy()

    frame[
        "year"
    ] = pd.to_numeric(
        frame[
            "year"
        ],
        errors="coerce",
    )

    frame[
        "temperature_c"
    ] = pd.to_numeric(
        frame[
            "mean_temperature_c"
        ],
        errors="coerce",
    )

    baseline = frame[
        (
            frame[
                "year"
            ]
            >= 1991
        )
        &
        (
            frame[
                "year"
            ]
            <= 2020
        )
    ][
        "temperature_c"
    ].mean()

    frame[
        "anomaly_c"
    ] = (
        frame[
            "temperature_c"
        ]
        - baseline
    )

    return frame


def _timeline_figure(
    historical,
    future_points=None,
):
    fig = go.Figure()

    if (
        historical is not None
        and not historical.empty
        and "anomaly_c" in historical
    ):
        fig.add_trace(
            go.Scatter(
                x=historical[
                    "year"
                ],
                y=historical[
                    "anomaly_c"
                ],
                mode="lines",
                name="Historical / reanalysis",
                line=dict(
                    width=2.0,
                ),
                hovertemplate=(
                    "<b>%{x:.0f}</b><br>"
                    "Anomaly: %{y:.2f}°C"
                    "<extra>Historical</extra>"
                ),
            )
        )

    if (
        future_points is not None
        and not future_points.empty
    ):
        if {
            "low_c",
            "high_c",
        }.issubset(
            future_points.columns
        ):
            x_values = list(
                future_points[
                    "year"
                ]
            ) + list(
                reversed(
                    future_points[
                        "year"
                    ].tolist()
                )
            )

            y_values = list(
                future_points[
                    "high_c"
                ]
            ) + list(
                reversed(
                    future_points[
                        "low_c"
                    ].tolist()
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    fill="toself",
                    fillcolor="rgba(89,194,255,.08)",
                    line=dict(
                        color="rgba(0,0,0,0)"
                    ),
                    hoverinfo="skip",
                    showlegend=True,
                    name="Projection envelope",
                )
            )

        fig.add_trace(
            go.Scatter(
                x=future_points[
                    "year"
                ],
                y=future_points[
                    "median_c"
                ],
                mode="lines+markers",
                name="Future projection",
                line=dict(
                    width=2.4,
                    dash="dot",
                ),
                customdata=future_points[
                    [
                        "low_c",
                        "high_c",
                    ]
                ].values,
                hovertemplate=(
                    "<b>%{x:.0f}</b><br>"
                    "Median: %{y:.2f}°C<br>"
                    "Range: %{customdata[0]:.2f}–"
                    "%{customdata[1]:.2f}°C"
                    "<extra>Projection</extra>"
                ),
            )
        )

    if (
        historical is not None
        and not historical.empty
    ):
        last_year = int(
            historical[
                "year"
            ].max()
        )

        fig.add_vline(
            x=last_year,
            line_dash="dash",
            line_width=1,
            line_color="rgba(100,212,255,.35)",
            annotation_text="Observed → projected",
            annotation_position="top",
        )

    fig.update_layout(
        height=280,
        margin=dict(
            l=8,
            r=8,
            t=20,
            b=5,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="#8da6b7",
            size=10,
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.12,
        ),
        xaxis=dict(
            gridcolor="rgba(139,179,208,.06)",
        ),
        yaxis=dict(
            title="Anomaly (°C)",
            gridcolor="rgba(139,179,208,.06)",
        ),
    )

    return fig


def _trend_snapshot(
    summary,
    anomalies,
    trend,
    environment,
):
    snapshot = {
        "current_temp": None,
        "current_aqi": None,
        "recent_anomaly": None,
        "warming_trend": None,
        "annual_precip": None,
        "annual_mean": None,
    }

    if environment:
        current = environment[
            "weather"
        ].get(
            "current",
            {},
        )

        air = environment[
            "air"
        ].get(
            "current",
            {},
        )

        snapshot[
            "current_temp"
        ] = _num(
            current.get(
                "temperature_2m"
            )
        )

        snapshot[
            "current_aqi"
        ] = _num(
            air.get(
                "european_aqi"
            )
        )

    if (
        anomalies is not None
        and not anomalies.empty
        and "anomaly_c" in anomalies
    ):
        values = pd.to_numeric(
            anomalies[
                "anomaly_c"
            ],
            errors="coerce",
        ).dropna()

        if not values.empty:
            snapshot[
                "recent_anomaly"
            ] = float(
                values.iloc[
                    -1
                ]
            )

    if isinstance(
        trend,
        dict,
    ):
        snapshot[
            "warming_trend"
        ] = _num(
            trend.get(
                "trend_c_per_decade"
            )
            or trend.get(
                "warming_per_decade_c"
            )
            or trend.get(
                "slope_c_per_decade"
            )
        )

    if (
        summary is not None
        and not summary.empty
    ):
        ordered = summary.sort_values(
            "year"
        )

        last = ordered.iloc[
            -1
        ]

        snapshot[
            "annual_mean"
        ] = _num(
            last.get(
                "avg_temperature_c"
            )
        )

        snapshot[
            "annual_precip"
        ] = _num(
            last.get(
                "total_precipitation_mm"
            )
            or last.get(
                "precipitation_mm"
            )
        )

    return snapshot


def _build_live_feed(
    global_pulse,
    local_alerts,
    official_alerts,
):
    items = []

    for alert in official_alerts[
        :2
    ]:
        items.append(
            {
                "tag": "OFFICIAL",
                "title": (
                    alert.get(
                        "event"
                    )
                    or "Weather warning"
                ),
                "detail": (
                    alert.get(
                        "headline"
                    )
                    or alert.get(
                        "source"
                    )
                ),
            }
        )

    for alert in local_alerts[
        :2
    ]:
        items.append(
            {
                "tag": "CONTEXT",
                "title": alert[
                    "title"
                ],
                "detail": alert[
                    "message"
                ],
            }
        )

    if global_pulse:
        hottest = max(
            (
                row
                for row in global_pulse
                if _num(
                    row.get(
                        "temperature_c"
                    )
                )
                is not None
            ),
            key=lambda row: _num(
                row.get(
                    "temperature_c"
                )
            ),
            default=None,
        )

        worst_aqi = max(
            (
                row
                for row in global_pulse
                if _num(
                    row.get(
                        "european_aqi"
                    )
                )
                is not None
            ),
            key=lambda row: _num(
                row.get(
                    "european_aqi"
                )
            ),
            default=None,
        )

        if hottest:
            items.append(
                {
                    "tag": "GLOBAL",
                    "title": (
                        f"{hottest['name']} "
                        f"{_fmt(hottest['temperature_c'], '.1f', '°C')}"
                    ),
                    "detail": (
                        "Warmest current reference-city observation "
                        "in the ORBIDENSE AI live globe sample."
                    ),
                }
            )

        if worst_aqi:
            items.append(
                {
                    "tag": "AIR",
                    "title": (
                        f"{worst_aqi['name']} AQI "
                        f"{_fmt(worst_aqi['european_aqi'], '.0f')}"
                    ),
                    "detail": (
                        "Highest European-AQI value in the current "
                        "ORBIDENSE AI reference-city sample."
                    ),
                }
            )

    return items[
        :5
    ]


def _compare_global_pulse(
    global_pulse,
    left_name,
    right_name,
):
    by_name = {
        row[
            "name"
        ]: row
        for row in global_pulse
    }

    left = by_name.get(
        left_name
    )

    right = by_name.get(
        right_name
    )

    if not left or not right:
        return None

    return pd.DataFrame(
        {
            "Metric": [
                "Temperature °C",
                "Feels like °C",
                "European AQI",
                "Wind km/h",
            ],
            left_name: [
                _num(
                    left.get(
                        "temperature_c"
                    )
                ),
                _num(
                    left.get(
                        "apparent_temperature_c"
                    )
                ),
                _num(
                    left.get(
                        "european_aqi"
                    )
                ),
                _num(
                    left.get(
                        "wind_kmh"
                    )
                ),
            ],
            right_name: [
                _num(
                    right.get(
                        "temperature_c"
                    )
                ),
                _num(
                    right.get(
                        "apparent_temperature_c"
                    )
                ),
                _num(
                    right.get(
                        "european_aqi"
                    )
                ),
                _num(
                    right.get(
                        "wind_kmh"
                    )
                ),
            ],
        }
    )


def _home_css():
    return """
<style>
:root {
    --cp-cyan: #44dfff;
    --cp-cyan2: #7ef8ff;
    --cp-bg: #06111b;
    --cp-card: rgba(8, 26, 39, .94);
    --cp-border: rgba(72, 221, 255, .20);
    --cp-text: #e9f7ff;
    --cp-muted: #8ca9b8;
}

.cp-v19-wrap {
    position: relative;
}

.cp-v19-hero {
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(74, 225, 255, .22);
    background:
        radial-gradient(circle at 78% 48%, rgba(57,230,255,.12), transparent 18%),
        radial-gradient(circle at 86% 42%, rgba(70,255,184,.07), transparent 20%),
        linear-gradient(135deg, rgba(5,18,30,.98), rgba(5,16,27,.95));
    border-radius: 17px;
    padding: 22px 25px;
    margin: 4px 0 14px;
    box-shadow:
        0 0 28px rgba(27,189,244,.07),
        inset 0 0 44px rgba(41,203,255,.025);
}

.cp-v19-hero::after {
    content: "";
    position: absolute;
    right: -60px;
    top: -85px;
    width: 350px;
    height: 350px;
    border-radius: 50%;
    border: 1px solid rgba(80,234,255,.10);
    box-shadow:
        0 0 70px rgba(58,229,255,.09),
        inset 0 0 60px rgba(46,205,255,.05);
}

.cp-v19-brandline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    position: relative;
    z-index: 2;
}

.cp-v19-brand {
    color: #fff;
    font-size: 1.55rem;
    font-weight: 860;
    letter-spacing: -.02em;
}

.cp-v19-brand span {
    color: var(--cp-cyan);
}

.cp-v19-wave {
    color: var(--cp-cyan);
    font-family: monospace;
    letter-spacing: .03em;
    opacity: .82;
    font-size: .9rem;
}

.cp-v19-status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #72efb6;
    border: 1px solid rgba(67,232,171,.22);
    background: rgba(24,151,104,.08);
    border-radius: 999px;
    padding: 6px 10px;
    font-size: .65rem;
    font-weight: 750;
    white-space: nowrap;
}

.cp-v19-status-dot {
    width: 7px;
    height: 7px;
    background: #4beca4;
    border-radius: 50%;
    box-shadow: 0 0 12px #4beca4;
}

.cp-v19-sub {
    color: #73dfff;
    font-size: .78rem;
    font-weight: 700;
    margin-top: 8px;
}

.cp-v19-copy {
    color: #8ea8b8;
    font-size: .72rem;
    line-height: 1.55;
    max-width: 760px;
    margin-top: 5px;
}

.cp-v19-card {
    border: 1px solid var(--cp-border);
    background:
        linear-gradient(150deg, rgba(9,30,44,.97), rgba(5,17,28,.98));
    border-radius: 13px;
    box-shadow:
        0 0 23px rgba(40,217,255,.035),
        inset 0 0 26px rgba(58,214,255,.018);
    height: 100%;
}

.cp-v19-card-inner {
    padding: 15px;
}

.cp-v19-eyebrow {
    color: #4fdcfb;
    font-size: .57rem;
    font-weight: 820;
    letter-spacing: .12em;
    text-transform: uppercase;
}

.cp-v19-h2 {
    color: #f7fbff;
    font-size: 1.02rem;
    font-weight: 820;
    margin-top: 5px;
}

.cp-v19-big {
    color: #fff;
    font-size: 1.45rem;
    font-weight: 850;
    margin-top: 5px;
}

.cp-v19-note {
    color: #7896a7;
    font-size: .64rem;
    line-height: 1.45;
    margin-top: 4px;
}

.cp-v19-mini-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.cp-v19-mini {
    border: 1px solid rgba(73,215,255,.17);
    background: rgba(13,48,66,.46);
    border-radius: 10px;
    padding: 11px;
    min-height: 92px;
}

.cp-v19-mini-label {
    color: #6e93a6;
    font-size: .57rem;
}

.cp-v19-mini-value {
    color: #f8fcff;
    font-size: .86rem;
    font-weight: 790;
    margin-top: 5px;
}

.cp-v19-mini-note {
    color: #708c9d;
    font-size: .57rem;
    line-height: 1.35;
    margin-top: 4px;
}

.cp-v19-section {
    color: #dff7ff;
    font-size: .82rem;
    font-weight: 800;
    letter-spacing: .02em;
    margin: 17px 0 8px;
}

.cp-v19-feed {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 7px;
}

.cp-v19-feed-item {
    border: 1px solid rgba(78,203,236,.12);
    background: #091a27;
    border-radius: 9px;
    padding: 10px;
    min-height: 83px;
}

.cp-v19-feed-tag {
    color: #5de1ff;
    font-size: .49rem;
    font-weight: 850;
    letter-spacing: .1em;
}

.cp-v19-feed-title {
    color: #eef9ff;
    font-size: .67rem;
    font-weight: 770;
    margin-top: 5px;
}

.cp-v19-feed-copy {
    color: #718a9a;
    font-size: .55rem;
    line-height: 1.35;
    margin-top: 4px;
}

.cp-v19-brief {
    border-left: 3px solid #45e0ff;
    background: linear-gradient(
        90deg,
        rgba(37,183,226,.08),
        rgba(6,18,29,.3)
    );
    border-radius: 9px;
    padding: 13px 14px;
}

.cp-v19-brief-title {
    color: #c9f3ff;
    font-size: .68rem;
    font-weight: 820;
}

.cp-v19-brief-copy {
    color: #9bb1be;
    font-size: .65rem;
    line-height: 1.52;
    margin-top: 5px;
}

.cp-v19-action {
    border: 1px solid rgba(70,215,255,.13);
    background: rgba(14,48,65,.35);
    border-radius: 9px;
    padding: 10px 11px;
    margin-bottom: 7px;
}

.cp-v19-action b {
    color: #b9ecff;
    font-size: .64rem;
}

.cp-v19-action p {
    color: #7f9baa;
    font-size: .59rem;
    line-height: 1.42;
    margin: 4px 0 0;
}

.cp-v19-source {
    color: #4d6a7c;
    font-size: .50rem;
    margin-top: 4px;
}

.cp-v19-badge {
    display: inline-flex;
    border: 1px solid rgba(88,224,255,.18);
    background: rgba(58,184,220,.07);
    color: #8be7ff;
    border-radius: 999px;
    padding: 4px 8px;
    font-size: .55rem;
    font-weight: 720;
    margin: 4px 4px 0 0;
}

@media (max-width: 930px) {
    .cp-v19-feed {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .cp-v19-brandline {
        align-items: flex-start;
    }
    .cp-v19-wave {
        display: none;
    }
}

@media (max-width: 520px) {
    .cp-v19-hero {
        padding: 17px;
    }
    .cp-v19-brand {
        font-size: 1.02rem;
    }
    .cp-v19-feed {
        grid-template-columns: 1fr;
    }
    .cp-v19-status {
        font-size: .55rem;
        padding: 5px 8px;
    }
}

.cp-v26-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 9px;
    margin: 11px 0 8px;
}

.cp-v26-metric {
    min-width: 0;
    padding: 12px 12px 11px;
    border-radius: 12px;
    border: 1px solid rgba(73, 214, 246, .14);
    background:
        linear-gradient(
            145deg,
            rgba(9, 31, 45, .96),
            rgba(6, 22, 33, .94)
        );
}

.cp-v26-metric-label {
    color: #7292a3;
    font-size: .69rem;
    line-height: 1.2;
}

.cp-v26-metric-value {
    margin-top: 5px;
    color: #f2fbff;
    font-size: 1.16rem;
    line-height: 1.1;
    font-weight: 800;
    letter-spacing: -.015em;
}

.cp-v26-metric-note {
    margin-top: 5px;
    color: #49cfea;
    font-size: .67rem;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.cp-v26-table-wrap {
    width: 100%;
    overflow-x: auto;
    border-radius: 12px;
    border: 1px solid rgba(73, 214, 246, .13);
    background: rgba(5, 20, 30, .96);
}

.cp-v26-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: auto;
    color: #dcecf3;
    font-size: .72rem;
}

.cp-v26-table th {
    padding: 9px 10px;
    color: #8fb0bf;
    background: #0a2433;
    font-size: .66rem;
    font-weight: 720;
    text-align: left;
    white-space: nowrap;
    border-bottom: 1px solid rgba(73, 214, 246, .12);
}

.cp-v26-table td {
    padding: 9px 10px;
    color: #e6f2f7;
    background: rgba(6, 24, 35, .94);
    border-bottom: 1px solid rgba(73, 214, 246, .07);
    white-space: nowrap;
}

.cp-v26-table tbody tr:last-child td {
    border-bottom: 0;
}

.cp-v26-table tbody tr:hover td {
    background: rgba(12, 42, 57, .96);
}

.cp-v26-empty {
    padding: 13px;
    border-radius: 10px;
    color: #7595a5;
    background: rgba(7, 25, 36, .9);
}

@media (max-width: 850px) {
    .cp-v26-metric-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def _status_text(
    environment,
    official_alerts,
    context_alerts,
):
    if official_alerts:
        return "Official warning active"

    if context_alerts:
        return "Environmental signal active"

    if environment:
        return "All systems normal"

    return "Live Earth online"


def _selected_daily_values(
    daily,
):
    high = None
    low = None

    try:
        values = daily.get(
            "temperature_2m_max",
            [],
        )

        if values:
            high = _num(
                values[0]
            )

        values = daily.get(
            "temperature_2m_min",
            [],
        )

        if values:
            low = _num(
                values[0]
            )
    except Exception:
        pass

    return (
        high,
        low,
    )


def _home_top_cards(
    selected,
    environment,
    history_years,
):
    if environment:
        current = environment[
            "weather"
        ].get(
            "current",
            {},
        )

        air = environment[
            "air"
        ].get(
            "current",
            {},
        )

        weather_text = weather_code_text(
            current.get(
                "weather_code"
            )
        )

        aqi_text, _ = aqi_level(
            air.get(
                "european_aqi"
            )
        )
    else:
        current = {}
        air = {}
        weather_text = "Search a location"
        aqi_text = "—"

    history_text = (
        history_years
        if history_years
        else "Historical record"
    )

    return f"""
<div class="cp-v19-mini-grid">
    <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Climate history</div>
        <div class="cp-v19-mini-value">{history_text}</div>
        <div class="cp-v19-mini-note">Observed / reanalysis trend context</div>
    </div>
    <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Database</div>
        <div class="cp-v19-mini-value">PostgreSQL / Neon</div>
        <div class="cp-v19-mini-note">Cloud analytical storage</div>
    </div>
    <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Weather</div>
        <div class="cp-v19-mini-value">{weather_text}</div>
        <div class="cp-v19-mini-note">
            {_fmt(current.get('temperature_2m'), '.1f', '°C')} ·
            AQI {aqi_text}
        </div>
    </div>
    <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Climate models</div>
        <div class="cp-v19-mini-value">ERA5 / CRU / CMIP6</div>
        <div class="cp-v19-mini-note">Past → present → future</div>
    </div>
</div>
"""



def _safe_country_extreme(
    frame,
    column,
    largest=True,
):
    if (
        frame is None
        or frame.empty
        or column not in frame.columns
    ):
        return None

    values = frame.copy()

    values[column] = pd.to_numeric(
        values[column],
        errors="coerce",
    )

    values = values.dropna(
        subset=[column]
    )

    if values.empty:
        return None

    row = (
        values.nlargest(
            1,
            column,
        )
        if largest
        else values.nsmallest(
            1,
            column,
        )
    ).iloc[0]

    return row.to_dict()


def _pulse_metric_value(
    row,
    value_column,
    suffix="",
    decimals=1,
):
    if not row:
        return "—"

    value = _num(
        row.get(
            value_column
        )
    )

    if value is None:
        return "—"

    return (
        f"{value:.{decimals}f}"
        f"{suffix}"
    )



def _escape_html(
    value,
):
    return html.escape(
        str(
            value
            if value is not None
            else ""
        )
    )


def _dark_metric_card(
    label,
    value,
    note="",
):
    return f"""
<div class="cp-v26-metric">
  <div class="cp-v26-metric-label">{_escape_html(label)}</div>
  <div class="cp-v26-metric-value">{_escape_html(value)}</div>
  <div class="cp-v26-metric-note">{_escape_html(note)}</div>
</div>
    """


def _dark_table_html(
    frame,
):
    if (
        frame is None
        or frame.empty
    ):
        return (
            '<div class="cp-v26-empty">'
            'No live rows available.'
            '</div>'
        )

    headers = "".join(
        f"<th>{_escape_html(column)}</th>"
        for column in frame.columns
    )

    rows = []

    for _, row in frame.iterrows():
        cells = "".join(
            f"<td>{_escape_html(value)}</td>"
            for value in row.tolist()
        )

        rows.append(
            f"<tr>{cells}</tr>"
        )

    return f"""
<div class="cp-v26-table-wrap">
<table class="cp-v26-table">
  <thead>
    <tr>{headers}</tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
</div>
    """


def _country_live_feed(
    local_alerts,
    official_alerts,
):
    items = []

    for alert in official_alerts[:2]:
        items.append(
            {
                "tag": "OFFICIAL",
                "title": (
                    alert.get(
                        "event"
                    )
                    or "Weather warning"
                ),
                "detail": (
                    alert.get(
                        "headline"
                    )
                    or alert.get(
                        "source"
                    )
                    or ""
                ),
            }
        )

    for alert in local_alerts[:2]:
        items.append(
            {
                "tag": "LOCAL",
                "title":
                    alert.get(
                        "title"
                    )
                    or "Local context",
                "detail":
                    alert.get(
                        "message"
                    )
                    or "",
            }
        )

    try:
        frame = cached_country_field()

        if (
            frame is not None
            and not frame.empty
        ):
            hottest = _safe_country_extreme(
                frame,
                "temperature_c",
                largest=True,
            )

            windiest = _safe_country_extreme(
                frame,
                "wind_kmh",
                largest=True,
            )

            wettest = _safe_country_extreme(
                frame,
                "precipitation_mm",
                largest=True,
            )

            largest_change = _safe_country_extreme(
                frame,
                "temperature_change_24h_c",
                largest=True,
            )

            if hottest:
                items.append(
                    {
                        "tag": "GLOBAL HEAT",
                        "title": (
                            f"{hottest.get('country', '—')} · "
                            f"{_pulse_metric_value(hottest, 'temperature_c', '°C')}"
                        ),
                        "detail": (
                            "Highest current representative-country-point "
                            "temperature in the live globe dataset."
                        ),
                    }
                )

            if windiest:
                items.append(
                    {
                        "tag": "GLOBAL WIND",
                        "title": (
                            f"{windiest.get('country', '—')} · "
                            f"{_pulse_metric_value(windiest, 'wind_kmh', ' km/h', 0)}"
                        ),
                        "detail": (
                            "Strongest current representative-country-point "
                            "wind in the live globe dataset."
                        ),
                    }
                )

            if wettest:
                items.append(
                    {
                        "tag": "GLOBAL RAIN",
                        "title": (
                            f"{wettest.get('country', '—')} · "
                            f"{_pulse_metric_value(wettest, 'precipitation_mm', ' mm')}"
                        ),
                        "detail": (
                            "Largest current precipitation value in the "
                            "live globe dataset."
                        ),
                    }
                )

            if largest_change:
                items.append(
                    {
                        "tag": "24H CHANGE",
                        "title": (
                            f"{largest_change.get('country', '—')} · "
                            f"{_pulse_metric_value(largest_change, 'temperature_change_24h_c', '°C')}"
                        ),
                        "detail": (
                            "Largest 24-hour representative-point temperature "
                            "rise; this is weather change, not climate warming."
                        ),
                    }
                )

    except Exception:
        pass

    return items[:6]



def _global_pulse_panel():
    """
    Live world snapshot beside the globe using the same representative-country
    current-weather dataset as the globe.
    """
    st.html(
        """
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">Global pulse · now</div>
    <div class="cp-v19-h2">What stands out right now?</div>
    <div class="cp-v19-note">
      Live country signals from the same dataset and timestamp family as the globe.
    </div>
  </div>
</div>
        """
    )

    try:
        frame = cached_country_field()

        if (
            frame is None
            or frame.empty
        ):
            raise RuntimeError(
                "No live country rows returned."
            )

        hottest = _safe_country_extreme(
            frame,
            "temperature_c",
            largest=True,
        )

        coldest = _safe_country_extreme(
            frame,
            "temperature_c",
            largest=False,
        )

        windiest = _safe_country_extreme(
            frame,
            "wind_kmh",
            largest=True,
        )

        wettest = _safe_country_extreme(
            frame,
            "precipitation_mm",
            largest=True,
        )

        largest_rise = _safe_country_extreme(
            frame,
            "temperature_change_24h_c",
            largest=True,
        )

        median_temp = pd.to_numeric(
            frame[
                "temperature_c"
            ],
            errors="coerce",
        ).median()

        cards = [
            _dark_metric_card(
                "Hottest now",
                _pulse_metric_value(
                    hottest,
                    "temperature_c",
                    "°C",
                ),
                (
                    hottest.get(
                        "country"
                    )
                    if hottest
                    else "—"
                ),
            ),
            _dark_metric_card(
                "Coldest now",
                _pulse_metric_value(
                    coldest,
                    "temperature_c",
                    "°C",
                ),
                (
                    coldest.get(
                        "country"
                    )
                    if coldest
                    else "—"
                ),
            ),
            _dark_metric_card(
                "Strongest wind",
                _pulse_metric_value(
                    windiest,
                    "wind_kmh",
                    " km/h",
                    0,
                ),
                (
                    windiest.get(
                        "country"
                    )
                    if windiest
                    else "—"
                ),
            ),
            _dark_metric_card(
                "Most rain now",
                _pulse_metric_value(
                    wettest,
                    "precipitation_mm",
                    " mm",
                ),
                (
                    wettest.get(
                        "country"
                    )
                    if wettest
                    else "—"
                ),
            ),
            _dark_metric_card(
                "Country median",
                (
                    f"{median_temp:.1f}°C"
                    if pd.notna(
                        median_temp
                    )
                    else "—"
                ),
                "Current representative-point sample",
            ),
            _dark_metric_card(
                "Largest 24h rise",
                _pulse_metric_value(
                    largest_rise,
                    "temperature_change_24h_c",
                    "°C",
                ),
                (
                    largest_rise.get(
                        "country"
                    )
                    if largest_rise
                    else "—"
                ),
            ),
        ]

        st.html(
            f"""
<div class="cp-v26-metric-grid">
  {''.join(cards)}
</div>
            """
        )

        st.caption(
            (
                "24-hour change is short-term weather change, not a "
                "long-term climate warming rate."
            )
        )

        ranking = frame[
            [
                "country",
                "temperature_c",
                "feels_like_c",
                "wind_kmh",
                "condition",
            ]
        ].copy()

        for column in [
            "temperature_c",
            "feels_like_c",
            "wind_kmh",
        ]:
            ranking[column] = pd.to_numeric(
                ranking[column],
                errors="coerce",
            )

        ranking = (
            ranking.dropna(
                subset=[
                    "temperature_c"
                ]
            )
            .sort_values(
                "temperature_c",
                ascending=False,
            )
            .head(6)
        )

        ranking[
            "temperature_c"
        ] = ranking[
            "temperature_c"
        ].map(
            lambda value:
                f"{value:.1f}"
        )

        ranking[
            "feels_like_c"
        ] = ranking[
            "feels_like_c"
        ].map(
            lambda value:
                (
                    f"{value:.1f}"
                    if pd.notna(
                        value
                    )
                    else "—"
                )
        )

        ranking[
            "wind_kmh"
        ] = ranking[
            "wind_kmh"
        ].map(
            lambda value:
                (
                    f"{value:.0f}"
                    if pd.notna(
                        value
                    )
                    else "—"
                )
        )

        ranking = ranking.rename(
            columns={
                "country":
                    "Country",
                "temperature_c":
                    "Temp °C",
                "feels_like_c":
                    "Feels °C",
                "wind_kmh":
                    "Wind km/h",
                "condition":
                    "Condition",
            }
        )

        st.markdown(
            "#### Hottest current country points"
        )

        st.html(
            _dark_table_html(
                ranking
            )
        )

        st.caption(
            (
                "Country values are current weather at representative country "
                "points, not national spatial averages."
            )
        )

    except Exception:
        st.info(
            (
                "Global Pulse is preparing. The live globe and local "
                "weather tools remain available."
            )
        )




def _wind_compass(degrees):
    value = _num(degrees)
    if value is None:
        return "—"
    directions = (
        "N", "NE", "E", "SE",
        "S", "SW", "W", "NW",
    )
    return directions[int((value + 22.5) // 45) % 8]


def _first_daily_value(daily, key):
    values = daily.get(key, []) if isinstance(daily, dict) else []
    if isinstance(values, (list, tuple)) and values:
        return values[0]
    return None


def _local_advisory(official_alerts, context_alerts, guidance):
    """Return one concise, honest local advisory for the Home weather strip."""
    if official_alerts:
        alert = official_alerts[0] or {}
        title = alert.get("event") or "Official weather alert"
        text = alert.get("headline") or alert.get("instruction") or alert.get("description") or "An official weather alert is active for this area."
        return {
            "kind": "official",
            "label": "OFFICIAL ALERT",
            "title": title,
            "text": text,
            "source": alert.get("source") or "Official warning service",
        }

    if context_alerts:
        alert = context_alerts[0] or {}
        return {
            "kind": "context",
            "label": "LOCAL WEATHER SIGNAL",
            "title": alert.get("title") or "Weather context",
            "text": alert.get("message") or "Conditions may warrant extra attention today.",
            "source": "ORBIDENSE AI contextual screening",
        }

    if guidance:
        item = guidance[0] or {}
        return {
            "kind": "guidance",
            "label": "LOCAL GUIDANCE",
            "title": item.get("title") or "Weather guidance",
            "text": item.get("text") or "Conditions are generally suitable for normal activities.",
            "source": item.get("source") or "Environmental guidance",
        }

    return {
        "kind": "normal",
        "label": "LOCAL CONDITIONS",
        "title": "No significant weather-health signal",
        "text": "Current conditions do not trigger a notable heat, air-quality or weather advisory in the available data.",
        "source": "Current ORBIDENSE AI environmental context",
    }


def _render_local_weather_strip(
    selected,
    environment,
    current,
    air_current,
    daily,
    official_alerts,
    context_alerts,
    guidance,
):
    """Compact weather-app style conditions displayed beside Current location."""
    if not selected:
        return

    if not environment:
        st.html(
            """
<div class="orb-local-weather orb-local-weather-loading">
  <div class="orb-local-loading-dot"></div>
  <div>
    <strong>Loading local conditions</strong>
    <span>Weather, forecast and air quality are being prepared.</span>
  </div>
</div>
            """
        )
        return

    temp = _num(current.get("temperature_2m"))
    feels = _num(current.get("apparent_temperature"))
    humidity = _num(current.get("relative_humidity_2m"))
    rain_now = _num(current.get("precipitation"))
    wind = _num(current.get("wind_speed_10m"))
    wind_dir = _wind_compass(current.get("wind_direction_10m"))
    pressure = _num(current.get("surface_pressure"))

    high = _num(_first_daily_value(daily, "temperature_2m_max"))
    low = _num(_first_daily_value(daily, "temperature_2m_min"))
    rain_prob = _num(_first_daily_value(daily, "precipitation_probability_max"))
    weather_code = _first_daily_value(daily, "weather_code")
    condition = weather_code_text(weather_code)

    aqi = _num(air_current.get("european_aqi"))
    aqi_label, aqi_class = aqi_level(aqi)

    advisory = _local_advisory(
        official_alerts,
        context_alerts,
        guidance,
    )

    def esc(value):
        return html.escape(str(value), quote=True)

    def metric(icon, label, value, note, tone="cyan"):
        return f"""
<div class="orb-weather-metric orb-tone-{tone}">
  <div class="orb-weather-icon">{icon}</div>
  <div class="orb-weather-copy">
    <div class="orb-weather-label">{esc(label)}</div>
    <div class="orb-weather-value">{esc(value)}</div>
    <div class="orb-weather-note">{esc(note)}</div>
  </div>
</div>
        """

    temp_value = f"{temp:.1f}°C" if temp is not None else "—"
    feels_note = f"Feels like {feels:.1f}°C" if feels is not None else "Current air temperature"
    forecast_value = (
        f"{high:.0f}° / {low:.0f}°"
        if high is not None and low is not None
        else "—"
    )
    forecast_note = condition
    if rain_prob is not None:
        forecast_note += f" · Rain {rain_prob:.0f}%"

    aqi_value = f"{aqi:.0f} AQI" if aqi is not None else "—"
    precip_value = f"{rain_now:.1f} mm" if rain_now is not None else "—"
    humidity_value = f"{humidity:.0f}%" if humidity is not None else "—"
    wind_value = f"{wind:.0f} km/h" if wind is not None else "—"
    pressure_value = f"{pressure:.0f} hPa" if pressure is not None else "—"

    aqi_tone = {
        "good": "green",
        "fair": "green",
        "moderate": "amber",
        "poor": "red",
        "very-poor": "red",
        "extreme": "red",
    }.get(aqi_class, "cyan")

    advisory_kind = advisory["kind"]
    advisory_icon = {
        "official": "⚠",
        "context": "△",
        "guidance": "◇",
        "normal": "✓",
    }.get(advisory_kind, "◇")

    cards = "".join([
        metric("♨", "Temperature", temp_value, feels_note, "cyan"),
        metric("☀", "Today", forecast_value, forecast_note, "amber"),
        metric("◉", "Air quality", aqi_value, aqi_label, aqi_tone),
        metric("◌", "Precipitation", precip_value, "Current precipitation", "cyan"),
        metric("◍", "Humidity", humidity_value, "Relative humidity", "blue"),
        metric("≋", "Wind", wind_value, wind_dir, "cyan"),
        metric("◴", "Pressure", pressure_value, "Surface pressure", "amber"),
    ])

    st.html(
        f"""
<style>
.orb-local-weather-shell {{
    width: 100%;
    min-width: 0;
}}
.orb-local-weather-grid {{
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    align-items: stretch;
    border: 1px solid rgba(57, 204, 222, .20);
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(6, 28, 40, .92), rgba(4, 20, 31, .96));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.025), 0 12px 32px rgba(0,0,0,.16);
    overflow: hidden;
}}
.orb-weather-metric {{
    position: relative;
    display: flex;
    align-items: center;
    gap: .42rem;
    min-width: 0;
    padding: .66rem .52rem;
    border-right: 1px solid rgba(113, 157, 177, .13);
}}
.orb-weather-metric:last-child {{ border-right: 0; }}
.orb-weather-icon {{
    display: grid;
    place-items: center;
    flex: 0 0 1.88rem;
    width: 1.88rem;
    height: 1.88rem;
    border-radius: 12px;
    font-size: 1.18rem;
    color: #5ce6f2;
    background: rgba(13, 85, 108, .18);
    border: 1px solid rgba(71, 218, 232, .10);
}}
.orb-tone-green .orb-weather-icon {{ color: #55e68c; background: rgba(29, 145, 85, .12); }}
.orb-tone-amber .orb-weather-icon {{ color: #ffbd49; background: rgba(177, 119, 22, .12); }}
.orb-tone-red .orb-weather-icon {{ color: #ff6b66; background: rgba(177, 54, 54, .12); }}
.orb-tone-blue .orb-weather-icon {{ color: #63aaff; background: rgba(46, 97, 168, .13); }}
.orb-weather-copy {{ min-width: 0; }}
.orb-weather-label {{
    color: #7896a8;
    font-size: clamp(.49rem, .50vw, .57rem);
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.orb-weather-value {{
    margin-top: .10rem;
    color: #f3fbff;
    font-size: clamp(.72rem, .78vw, .94rem);
    line-height: 1.12;
    font-weight: 850;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.orb-weather-note {{
    margin-top: .22rem;
    color: #8ba5b3;
    font-size: clamp(.49rem, .50vw, .59rem);
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.orb-local-advisory {{
    margin-top: .42rem;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: .60rem;
    padding: .48rem .70rem;
    border-radius: 12px;
    border: 1px solid rgba(65, 202, 222, .12);
    background: rgba(6, 27, 38, .72);
}}
.orb-local-advisory.official {{ border-color: rgba(255, 105, 88, .30); background: rgba(91, 32, 29, .22); }}
.orb-local-advisory.context {{ border-color: rgba(255, 187, 71, .25); background: rgba(93, 68, 21, .17); }}
.orb-local-advisory.normal {{ border-color: rgba(64, 222, 132, .20); background: rgba(22, 86, 60, .13); }}
.orb-advisory-icon {{
    flex: 0 0 1.85rem;
    width: 1.85rem;
    height: 1.85rem;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: rgba(43, 206, 224, .10);
    color: #55dfe9;
    font-weight: 900;
}}
.orb-local-advisory.official .orb-advisory-icon {{ color:#ff776d; background:rgba(214,74,63,.12); }}
.orb-local-advisory.context .orb-advisory-icon {{ color:#ffc25f; background:rgba(214,151,48,.12); }}
.orb-local-advisory.normal .orb-advisory-icon {{ color:#55e68c; background:rgba(48,181,105,.10); }}
.orb-advisory-body {{ min-width:0; flex:1; }}
.orb-advisory-top {{
    color:#7e9bab;
    font-size:.55rem;
    font-weight:850;
    letter-spacing:.10em;
    text-transform:uppercase;
}}
.orb-advisory-line {{
    margin-top:.05rem;
    color:#dcebf2;
    font-size:.69rem;
    line-height:1.30;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}}
.orb-advisory-line strong {{ color:#f4fbff; }}
.orb-advisory-source {{
    flex:0 0 auto;
    color:#668696;
    font-size:.55rem;
    white-space:nowrap;
}}
.orb-local-weather-loading {{
    min-height: 72px;
    display:flex;
    align-items:center;
    gap:.7rem;
    padding:.75rem 1rem;
    border:1px solid rgba(57,204,222,.18);
    border-radius:16px;
    background:rgba(6,28,40,.78);
}}
.orb-local-weather-loading strong {{ display:block;color:#f3fbff;font-size:.78rem; }}
.orb-local-weather-loading span {{ display:block;color:#7e9bab;font-size:.64rem;margin-top:.12rem; }}
.orb-local-loading-dot {{ width:.7rem;height:.7rem;border-radius:50%;background:#4fe1ed;box-shadow:0 0 16px rgba(79,225,237,.65); }}
@media (max-width: 1250px) {{
    .orb-local-weather-grid {{ grid-template-columns: repeat(4, minmax(110px, 1fr)); }}
    .orb-weather-metric:nth-child(4) {{ border-right:0; }}
}}
@media (max-width: 860px) {{
    .orb-local-weather-grid {{ grid-template-columns: repeat(2, minmax(130px, 1fr)); }}
    .orb-weather-metric {{ border-bottom:1px solid rgba(113,157,177,.10); }}
    .orb-advisory-source {{ display:none; }}
}}
</style>
<div class="orb-local-weather-shell">
  <div class="orb-local-weather-grid">{cards}</div>
  <div class="orb-local-advisory {esc(advisory_kind)}">
    <div class="orb-advisory-icon">{esc(advisory_icon)}</div>
    <div class="orb-advisory-body">
      <div class="orb-advisory-top">{esc(advisory['label'])}</div>
      <div class="orb-advisory-line"><strong>{esc(advisory['title'])}</strong> · {esc(advisory['text'])}</div>
    </div>
    <div class="orb-advisory-source">{esc(advisory['source'])}</div>
  </div>
</div>
        """
    )



def _locations_match(first, second, tolerance=0.0025):
    """Return True when two location dictionaries represent the same point."""
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False
    try:
        return (
            abs(float(first.get("latitude")) - float(second.get("latitude"))) <= tolerance
            and abs(float(first.get("longitude")) - float(second.get("longitude"))) <= tolerance
        )
    except (TypeError, ValueError):
        return False


def _render_selected_location_card(selected):
    """Compact display for a manually searched/selected location."""
    if not selected:
        return

    label = html.escape(str(selected.get("name") or "Selected location"), quote=True)
    kind = str(selected.get("kind") or "place").replace("_", " ").title()

    st.html(
        f"""
<style>
.orb-selected-location {{
    width:100%;
    min-height:52px;
    display:grid;
    grid-template-columns:34px minmax(0,1fr) 18px;
    align-items:center;
    gap:8px;
    padding:7px 12px;
    border-radius:13px;
    border:1px solid rgba(72,218,248,.26);
    background:linear-gradient(135deg,rgba(10,39,54,.96),rgba(6,24,34,.98));
    box-shadow:0 8px 26px rgba(0,0,0,.20), inset 0 1px 0 rgba(255,255,255,.025);
    overflow:hidden;
}}
.orb-selected-location-icon {{
    width:34px;height:34px;border-radius:50%;display:grid;place-items:center;
    color:#55e7f2;background:rgba(13,102,126,.18);
    border:1px solid rgba(82,224,241,.20);font-size:1rem;
}}
.orb-selected-location-copy {{min-width:0;}}
.orb-selected-location-title {{
    color:#f4fbff;font-size:.78rem;font-weight:820;line-height:1.15;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}
.orb-selected-location-sub {{
    margin-top:.14rem;color:#7898a8;font-size:.58rem;font-weight:650;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}
.orb-selected-location-arrow {{color:#55dfea;font-size:1rem;text-align:right;}}
</style>
<div class="orb-selected-location" title="{label}">
  <div class="orb-selected-location-icon">◎</div>
  <div class="orb-selected-location-copy">
    <div class="orb-selected-location-title">{label}</div>
    <div class="orb-selected-location-sub">Selected {html.escape(kind.lower(), quote=True)} · live conditions</div>
  </div>
  <div class="orb-selected-location-arrow">→</div>
</div>
        """
    )

def render_home_page(
    city=None,
    point_location=None,
    summary=None,
    anomalies=None,
    trend=None,
    country_feature=None,
    country_location=None,
    country_national=None,
    country_iso3=None,
):
    st.html(
        _home_css()
    )

    selected = _location_context(
        city,
        point_location,
        country_feature,
        country_location,
    )

    # =========================================================
    # CURRENT LOCATION — AUTOMATIC FIRST-VISIT BOOTSTRAP
    # =========================================================
    #
    # On a visitor's first Home render, the browser component attempts
    # geolocation immediately. The browser still controls permission: the
    # application cannot bypass a denied permission. Once coordinates arrive:
    # browser coordinates -> reverse geocode -> session state -> app-level
    # location sync -> current weather/history/globe rerender.
    #
    # If permission is denied/unavailable, the compact control remains as a
    # manual retry and the global search remains the fallback.
    # =========================================================

    existing_browser_location = st.session_state.get(
        "v21_browser_location"
    )

    # A manual search must take precedence over the previously detected
    # browser location. Browser geolocation is only the automatic default.
    manual_selection_active = bool(selected) and not _locations_match(
        selected,
        existing_browser_location,
    )

    # Reserve one responsive row: active location on the left and weather
    # intelligence on the right. The weather strip always follows `selected`.
    location_col, local_weather_col = st.columns(
        [1.42, 6.58],
        gap="small",
        vertical_alignment="top",
    )

    with location_col:
        if manual_selection_active:
            detected_location = None
            _render_selected_location_card(selected)
        else:
            detected_location = render_location_control(
                active_location=existing_browser_location
            )

    if (
        not detected_location
        and not existing_browser_location
        and not selected
    ):
        st.html(
            """
<div style="
    margin: .20rem 0 .75rem 0;
    padding: .72rem .90rem;
    border: 1px solid rgba(68, 218, 232, .16);
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(8,31,43,.78), rgba(5,20,30,.88));
    color: #a9c4cf;
    font-size: .82rem;
">
    <strong style="color:#edfaff;">Preparing your local Earth view</strong><br>
    Allow browser location when prompted. ORBIDENSE AI will automatically
    load current weather, environmental context and center the live map on
    your detected position. You can always use global search instead.
</div>
            """
        )

    if detected_location:
        st.session_state[
            "v21_browser_location"
        ] = detected_location

        # app.py watches this flag and promotes the browser point
        # to ORBIDENSE AI's active location before downstream data load.
        st.session_state[
            "v27_location_sync_pending"
        ] = True

        st.toast(
            (
                "Current location · "
                + detected_location.get(
                    "label",
                    "detected",
                )
            ),
            icon="📍",
        )

        # Immediately rerun so current weather, trend context,
        # history preparation and all routed pages receive the point.
        st.rerun()

    saved_browser = st.session_state.get(
        "v21_browser_location"
    )

    # IMPORTANT: do not overwrite a location explicitly chosen through
    # global search. Browser geolocation is a fallback/default only.
    if saved_browser and not selected:
        selected = {
            "name": (
                saved_browser.get(
                    "label"
                )
                or saved_browser.get(
                    "name"
                )
                or (
                    "Current location "
                    f"({saved_browser['latitude']:.3f}°, "
                    f"{saved_browser['longitude']:.3f}°)"
                )
            ),
            "latitude": saved_browser[
                "latitude"
            ],
            "longitude": saved_browser[
                "longitude"
            ],
            "timezone": saved_browser.get(
                "timezone",
                "auto",
            ),
            "country_code": saved_browser.get(
                "country_code"
            ),
            "kind": "browser",
            "scope_note": saved_browser.get(
                "scope_note",
                "Browser coordinates are used only for this session.",
            ),
        }

    environment = None

    if selected:
        try:
            environment = cached_home_environment(
                selected[
                    "latitude"
                ],
                selected[
                    "longitude"
                ],
                selected.get(
                    "timezone",
                    "auto",
                ),
            )
        except Exception:
            environment = None

    # Global pulse is intentionally lazy. It is not needed for the weather
    # strip or globe, so do not put a ~3 s provider request on Home's critical
    # first-paint path. It is loaded only when the comparison widget is reached.
    global_pulse = []

    official_alerts = []

    if selected:
        official_alerts = cached_official_alerts(
            selected[
                "latitude"
            ],
            selected[
                "longitude"
            ],
        )

    current = (
        environment[
            "weather"
        ].get(
            "current",
            {},
        )
        if environment
        else {}
    )

    air_current = (
        environment[
            "air"
        ].get(
            "current",
            {},
        )
        if environment
        else {}
    )

    daily = (
        environment[
            "weather"
        ].get(
            "daily",
            {},
        )
        if environment
        else {}
    )

    hourly = (
        environment[
            "weather"
        ].get(
            "hourly",
            {},
        )
        if environment
        else {}
    )

    air_hourly = (
        environment[
            "air"
        ].get(
            "hourly",
            {},
        )
        if environment
        else {}
    )

    health = (
        build_health_context(
            current,
            air_current,
            daily,
        )
        if environment
        else {
            "heat": {
                "label": "Choose a location",
                "metric": "Climate-health context",
                "value_c": None,
                "level": "unknown",
            },
            "air_quality": {
                "value": None,
                "label": "Unavailable",
                "level": "unknown",
            },
            "night": {
                "minimum_c": None,
                "tropical_night": False,
                "label": "Unavailable",
                "level": "unknown",
            },
            "uv": {
                "value": None,
                "label": "Unavailable",
                "level": "unknown",
            },
            "pollen": {
                "label": "Not available",
                "level": "unknown",
                "dominant": None,
                "value": None,
            },
        }
    )

    compound = (
        build_compound_context(
            health,
            current,
            air_current,
            daily,
        )
        if environment
        else []
    )

    context_alerts = (
        build_context_alerts(
            health,
            compound,
            current,
            air_current,
            daily,
        )
        if environment
        else []
    )

    guidance = (
        build_guidance(
            health
        )
        if environment
        else []
    )

    # Weather-app style local conditions: intentionally uses the same detected
    # coordinates as the Home globe so the location, weather and map remain
    # synchronized. Official alerts are shown only where the configured
    # authoritative warning service supports them; elsewhere the advisory is
    # clearly labelled as contextual guidance rather than an official warning.
    with local_weather_col:
        _render_local_weather_strip(
            selected=selected,
            environment=environment,
            current=current,
            air_current=air_current,
            daily=daily,
            official_alerts=official_alerts,
            context_alerts=context_alerts,
            guidance=guidance,
        )

    status_text = _status_text(
        environment,
        official_alerts,
        context_alerts,
    )

    palette = _condition_palette(
        current,
        air_current,
        trend,
    )

    st.html(
        f"""
<div class="cp-v19-wrap">
  <div class="cp-v19-hero" style="
      background:
          radial-gradient(circle at 78% 48%, {palette['accent']}22, transparent 18%),
          linear-gradient(135deg, {palette['start']} 0%, {palette['end']} 100%);
      border-color: {palette['accent']}55;
      box-shadow: 0 0 30px {palette['accent']}14;
  ">
    <div class="cp-v19-brandline">
      <div>
        <div class="cp-v19-brand">
            GLOBAL CLIMATE <span>INTELLIGENCE</span>
        </div>
        <div class="cp-v19-sub">
            Live Earth · climate context · health · future change
        </div>
      </div>
      <div class="cp-v19-wave">
          ╲╱╲╱╲▂▃▅▇▅▃▂╲╱╲▂▆▂╲╱
      </div>
      <div class="cp-v19-status">
          <span class="cp-v19-status-dot"></span>
          {status_text}
      </div>
    </div>
    <div class="cp-v19-copy">
        Explore the planet in real time, then move seamlessly from
        today's conditions to historical climate, human-health context,
        compound environmental signals and future projections.
    </div>
  </div>
</div>
        """
    )

    # Global Pulse summary now lives in the compact Home header beside the
    # ORBIDENSE AI identity. Give the live globe the full content width.
    st.markdown(
        "### Live Earth weather field"
    )

    render_live_weather_globe(
        selected_location=selected,
        height=620,
    )

    st.caption(
        "Rotate, zoom and hover/tap countries for current conditions. "
        "Switch layers to compare temperature, feels-like, 24-hour change, "
        "rain, cloud and wind."
    )

    # Compact insight snapshot + optional-module controls.
    st.html(
        '<div class="cp-v19-section">Selected-place intelligence</div>'
    )

    snapshot = _trend_snapshot(
        summary,
        anomalies,
        trend,
        environment,
    )

    st.html(
        f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-mini-grid">
      <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Current temperature</div>
        <div class="cp-v19-mini-value">{_fmt(snapshot['current_temp'], '.1f', '°C')}</div>
        <div class="cp-v19-mini-note">Live selected-location context</div>
      </div>
      <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Latest anomaly</div>
        <div class="cp-v19-mini-value">{_fmt(snapshot['recent_anomaly'], '+.2f', '°C')}</div>
        <div class="cp-v19-mini-note">Relative to ORBIDENSE AI baseline</div>
      </div>
      <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">Warming trend</div>
        <div class="cp-v19-mini-value">{_fmt(snapshot['warming_trend'], '+.2f', '°C/dec')}</div>
        <div class="cp-v19-mini-note">Historical trend where available</div>
      </div>
      <div class="cp-v19-mini">
        <div class="cp-v19-mini-label">European AQI</div>
        <div class="cp-v19-mini-value">{_fmt(snapshot['current_aqi'], '.0f')}</div>
        <div class="cp-v19-mini-note">Current air-quality context</div>
      </div>
    </div>
  </div>
</div>
        """
    )

    with st.expander(
        "Customize Home modules",
        expanded=False,
    ):
        option_1, option_2, option_3 = st.columns(
            3
        )

        with option_1:
            show_forecast = st.checkbox(
                "Forecast & outdoor window",
                value=True,
                key="v19_show_forecast",
            )

        with option_2:
            show_health = st.checkbox(
                "Climate-health & compound risk",
                value=True,
                key="v19_show_health",
            )

        with option_3:
            show_timeline = st.checkbox(
                "Climate timeline preview",
                value=True,
                key="v19_show_timeline",
            )

    # Live feed.
    st.html(
        '<div class="cp-v19-section">Live climate feed</div>'
    )

    feed_items = _country_live_feed(
        context_alerts,
        official_alerts,
    )

    if feed_items:
        feed_html = "".join(
            f"""
<div class="cp-v19-feed-item">
    <div class="cp-v19-feed-tag">{item['tag']}</div>
    <div class="cp-v19-feed-title">{item['title']}</div>
    <div class="cp-v19-feed-copy">{item['detail']}</div>
</div>
            """
            for item in feed_items
        )

        st.html(
            f"""
<div class="cp-v19-feed">
    {feed_html}
</div>
            """
        )
    else:
        st.caption(
            "Live feed appears when global or local signals are available."
        )

    # Deterministic intelligence brief + mini compare.
    brief_col, compare_col = st.columns(
        [
            1.0,
            1.0,
        ],
        gap="medium",
    )

    with brief_col:
        st.html(
            '<div class="cp-v19-section">Climate intelligence brief</div>'
        )

        if environment and selected:
            forecast_high, forecast_low = _selected_daily_values(
                daily
            )

            brief = build_intelligence_brief(
                selected[
                    "name"
                ],
                current,
                health,
                compound,
                forecast_high=forecast_high,
                forecast_low=forecast_low,
            )
        else:
            brief = (
                "Search a city, place or country — or enable current "
                "location — to generate a data-grounded ORBIDENSE AI brief."
            )

        st.html(
            f"""
<div class="cp-v19-brief">
    <div class="cp-v19-brief-title">
        Grounded summary
    </div>
    <div class="cp-v19-brief-copy">
        {brief}
    </div>
</div>
            """
        )

        st.caption(
            "Generated deterministically from the displayed data — no free-form AI claims."
        )

    with compare_col:
        st.html(
            '<div class="cp-v19-section">Interactive comparison tool</div>'
        )

        if not global_pulse:
            try:
                global_pulse = cached_global_pulse()
            except Exception:
                global_pulse = []

        if global_pulse:
            names = [
                row[
                    "name"
                ]
                for row in global_pulse
            ]

            c1, c2 = st.columns(
                2
            )

            with c1:
                left_name = st.selectbox(
                    "Place A",
                    names,
                    index=0,
                    key="v19_quick_compare_left",
                )

            with c2:
                right_default = (
                    1
                    if len(
                        names
                    )
                    > 1
                    else 0
                )

                right_name = st.selectbox(
                    "Place B",
                    names,
                    index=right_default,
                    key="v19_quick_compare_right",
                )

            comparison = _compare_global_pulse(
                global_pulse,
                left_name,
                right_name,
            )

            if comparison is not None:
                display_comparison = (
                    comparison.copy()
                )

                for column in display_comparison.columns[
                    1:
                ]:
                    display_comparison[
                        column
                    ] = pd.to_numeric(
                        display_comparison[
                            column
                        ],
                        errors="coerce",
                    ).map(
                        lambda value:
                            (
                                f"{value:.1f}"
                                if pd.notna(
                                    value
                                )
                                else "—"
                            )
                    )

                st.html(
                    _dark_table_html(
                        display_comparison
                    )
                )

            st.button(
                "Open full Compare Places",
                width="stretch",
                on_click=_go_to,
                args=(
                    "Compare Places",
                ),
                key="v19_open_full_compare",
            )

    if (
        show_forecast
        and environment
    ):
        # Hourly data is intentionally lazy. The fast summary bundle above
        # already rendered location/weather/AQI/map; only now pay for the
        # detailed series required by the chart and outdoor-window analysis.
        if selected:
            try:
                detail_environment = cached_home_environment_detail(
                    selected["latitude"],
                    selected["longitude"],
                    selected.get("timezone", "auto"),
                )
                detail_weather = detail_environment.get("weather", {})
                detail_air = detail_environment.get("air", {})
                hourly = detail_weather.get("hourly", {}) or hourly
                air_hourly = detail_air.get("hourly", {}) or air_hourly
            except Exception:
                pass

        st.html(
            '<div class="cp-v19-section">Forecast intelligence</div>'
        )

        forecast_col, outdoor_col = st.columns(
            [
                1.45,
                0.55,
            ],
            gap="medium",
        )

        with forecast_col:
            forecast_frame = _forecast_frame(
                hourly,
                hours=30,
            )

            st.plotly_chart(
                _forecast_chart(
                    forecast_frame
                ),
                width="stretch",
                config={
                    "displayModeBar": False,
                },
                key="v19_forecast_chart",
            )

        with outdoor_col:
            best_window = find_low_stress_window(
                hourly,
                air_hourly,
            )

            if best_window:
                st.html(
                    f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">Best practical window</div>
    <div class="cp-v19-big">
        {best_window['start'].strftime('%H:%M')}–{best_window['end'].strftime('%H:%M')}
    </div>
    <div class="cp-v19-note">
        Heat {_fmt(best_window.get('apparent_temperature'), '.1f', '°C')}
        · UV {_fmt(best_window.get('uv_index'), '.1f')}
        · rain {_fmt(best_window.get('rain_probability'), '.0f', '%')}
        · AQI {_fmt(best_window.get('aqi'), '.0f')}
    </div>
  </div>
</div>
                    """
                )
            else:
                st.info(
                    "No low-stress two-hour outdoor window was found in the next day."
                )

    if (
        show_health
        and environment
    ):
        st.html(
            '<div class="cp-v19-section">Climate-health & compound risk</div>'
        )

        h1, h2 = st.columns(
            2,
            gap="medium",
        )

        with h1:
            st.html(
                f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">Heat-health context</div>
    <div class="cp-v19-big">{health['heat']['label']}</div>
    <span class="cp-v19-badge">
        {health['heat']['metric']}
        {(' · ' + _fmt(health['heat']['value_c'], '.1f', '°C')) if health['heat']['value_c'] is not None else ''}
    </span>
    <span class="cp-v19-badge">
        Tonight · {health['night']['label']}
    </span>
    <span class="cp-v19-badge">
        UV · {health['uv']['label']}
    </span>
    <span class="cp-v19-badge">
        Air · {health['air_quality']['label']}
    </span>
  </div>
</div>
                """
            )

        with h2:
            compound_html = "".join(
                f"""
<div class="cp-v19-action">
    <b>{item['name']}</b>
    <p>{item['message']}</p>
</div>
                """
                for item in compound
            )

            st.html(
                f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">Compound Risk Pulse</div>
    <div style="height:8px"></div>
    {compound_html}
  </div>
</div>
                """
            )

        with st.expander(
            "Personalized practical guidance",
            expanded=False,
        ):
            for item in guidance:
                st.html(
                    f"""
<div class="cp-v19-action">
    <b>{item['title']}</b>
    <p>{item['text']}</p>
    <div class="cp-v19-source">{item['source']}</div>
</div>
                    """
                )

            if official_alerts:
                st.markdown(
                    "#### Official warnings"
                )

                for alert in official_alerts:
                    st.warning(
                        (
                            f"**{alert.get('event') or 'Weather warning'}**  \n"
                            f"{alert.get('headline') or ''}  \n"
                            f"Source: {alert.get('source')}"
                        )
                    )
            else:
                st.caption(
                    "Official-warning coverage is provider-dependent. "
                    "US points use the National Weather Service when applicable; "
                    "ORBIDENSE AI context alerts remain clearly separate."
                )

    if show_timeline:
        st.html(
            '<div class="cp-v19-section">Climate timeline</div>'
        )

        future_points = None

        if selected and selected[
            "kind"
        ] == "country":
            history = _timeline_country_data(
                country_national
            )

            if country_iso3:
                try:
                    trajectory = cached_country_trajectory(
                        country_iso3,
                        "ssp245",
                    )

                    if (
                        trajectory is not None
                        and not trajectory.empty
                    ):
                        years = {
                            "2020-2039": 2030,
                            "2040-2059": 2050,
                            "2060-2079": 2070,
                            "2080-2099": 2090,
                        }

                        future_points = pd.DataFrame(
                            {
                                "year": [
                                    years.get(
                                        value,
                                        2050,
                                    )
                                    for value in trajectory[
                                        "period"
                                    ]
                                ],
                                "median_c": trajectory[
                                    "median_c"
                                ],
                                "low_c": trajectory[
                                    "p10_c"
                                ],
                                "high_c": trajectory[
                                    "p90_c"
                                ],
                            }
                        )
                except Exception:
                    future_points = None

        else:
            history = _timeline_city_data(
                summary,
                anomalies,
            )

            if (
                "v19_home_future"
                in st.session_state
            ):
                future_points = st.session_state[
                    "v19_home_future"
                ]

            if (
                selected
                and selected[
                    "kind"
                ]
                in {
                    "city",
                    "browser",
                }
            ):
                if st.button(
                    "Load mid-century projection preview",
                    key="v19_load_future_preview",
                ):
                    try:
                        ensemble = cached_home_future(
                            selected[
                                "latitude"
                            ],
                            selected[
                                "longitude"
                            ],
                        )

                        baseline = history[
                            (
                                history[
                                    "year"
                                ]
                                >= 1991
                            )
                            &
                            (
                                history[
                                    "year"
                                ]
                                <= 2020
                            )
                        ][
                            "temperature_c"
                        ].mean()

                        future_points = pd.DataFrame(
                            {
                                "year": [
                                    2045
                                ],
                                "median_c": [
                                    ensemble[
                                        "temperature_median_c"
                                    ]
                                    - baseline
                                ],
                                "low_c": [
                                    ensemble[
                                        "temperature_min_c"
                                    ]
                                    - baseline
                                ],
                                "high_c": [
                                    ensemble[
                                        "temperature_max_c"
                                    ]
                                    - baseline
                                ],
                            }
                        )

                        st.session_state[
                            "v19_home_future"
                        ] = future_points

                    except Exception as error:
                        if record_error is not None:
                            record_error(
                                error,
                                component="home_timeline",
                                operation="future_projection_preview",
                                page_name="Home",
                                severity="warning",
                            )

        if (
            history is not None
            and not history.empty
        ):
            st.plotly_chart(
                _timeline_figure(
                    history,
                    future_points,
                ),
                width="stretch",
                config={
                    "displayModeBar": False,
                },
                key="v19_home_timeline",
            )

            st.caption(
                "Historical/reanalysis and model projections are kept visually distinct."
            )
        else:
            st.info(
                "Search a city or country with historical climate data to unlock the timeline."
            )


    if environment:
        st.html(
            '<div class="cp-v19-section">What deserves your attention</div>'
        )

        attention = []

        if official_alerts:
            attention.append(
                {
                    "title": "Official weather warning",
                    "text": (
                        official_alerts[
                            0
                        ].get(
                            "headline"
                        )
                        or official_alerts[
                            0
                        ].get(
                            "event"
                        )
                        or "Active official warning"
                    ),
                    "source": (
                        official_alerts[
                            0
                        ].get(
                            "source"
                        )
                        or "Official warning provider"
                    ),
                }
            )

        for item in guidance:
            attention.append(
                {
                    "title": item[
                        "title"
                    ],
                    "text": item[
                        "text"
                    ],
                    "source": item[
                        "source"
                    ],
                }
            )

        if attention:
            columns = st.columns(
                min(
                    3,
                    len(
                        attention
                    ),
                ),
                gap="small",
            )

            for column, item in zip(
                columns,
                attention[
                    :3
                ],
            ):
                with column:
                    st.html(
                        f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">{item['title']}</div>
    <div class="cp-v19-note" style="font-size:.70rem;color:#b7c7d1;">
        {item['text']}
    </div>
    <div class="cp-v19-source">{item['source']}</div>
  </div>
</div>
                        """
                    )

    st.html(
        '<div class="cp-v19-section">ORBIDENSE AI Assistant</div>'
    )

    ai_status = get_ai_status()

    ai_left, ai_right = st.columns(
        [
            0.72,
            0.28,
        ],
        gap="medium",
    )

    with ai_left:
        st.html(
            """
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">Open-source climate assistant</div>
    <div class="cp-v19-h2">Ask about this place, the globe, climate science or the data.</div>
    <div class="cp-v19-note">
        ORBIDENSE AI passes the current displayed data into the assistant before it answers.
        It is instructed not to invent live values, warnings or diagnoses.
    </div>
  </div>
</div>
            """
        )

        if (
            "v20_ai_messages"
            not in st.session_state
        ):
            st.session_state[
                "v20_ai_messages"
            ] = []

        for message in st.session_state[
            "v20_ai_messages"
        ][
            -6:
        ]:
            with st.chat_message(
                message[
                    "role"
                ]
            ):
                st.markdown(
                    message[
                        "content"
                    ]
                )

        question = st.chat_input(
            "Ask ORBIDENSE AI…",
            key="v20_ai_question",
        )

        if question:
            st.session_state[
                "v20_ai_messages"
            ].append(
                {
                    "role": "user",
                    "content": question,
                }
            )

            answer = ask_huggingface(
                question,
                _ai_context(
                    selected,
                    current,
                    air_current,
                    health,
                    compound,
                    official_alerts,
                    trend,
                ),
            )

            st.session_state[
                "v20_ai_messages"
            ].append(
                {
                    "role": "assistant",
                    "content": answer[
                        "answer"
                    ],
                }
            )

            st.rerun()

    with ai_right:
        st.html(
            f"""
<div class="cp-v19-card">
  <div class="cp-v19-card-inner">
    <div class="cp-v19-eyebrow">AI status</div>
    <div class="cp-v19-big">
        {'Connected' if ai_status['configured'] else 'Needs HF token'}
    </div>
    <div class="cp-v19-note">
        Model: {ai_status['model']}
    </div>
    <div class="cp-v19-note" style="margin-top:10px;">
        Open-source model through Hugging Face Inference Providers.
    </div>
  </div>
</div>
            """
        )

        if not ai_status[
            "configured"
        ]:
            st.caption(
                "Add HF_TOKEN to .env locally and Streamlit secrets online."
            )

    st.html(
        """
<div style="
    text-align:center;
    color:#48677a;
    font-size:.58rem;
    padding:18px 0 4px;
">
    ORBIDENSE AI · EARTH DATA · RISK INTELLIGENCE · BETTER DECISIONS
</div>
        """
    )



def render_dashboard_page(
    city=None,
    point_location=None,
    summary=None,
    anomalies=None,
    trend=None,
    country_feature=None,
    country_location=None,
    country_national=None,
):
    """
    Clean secondary dashboard.

    Home remains the landing experience; Dashboard is the compact,
    analysis-first view users can always return to.
    """
    st.html(
        _home_css()
    )

    selected = _location_context(
        city,
        point_location,
        country_feature,
        country_location,
    )

    st.html(
        """
<div class="cp-home-hero">
    <div class="cp-home-kicker">ORBIDENSE AI · EARTH INTELLIGENCE</div>
    <div class="cp-home-title">
        Conditions, context and climate — without the clutter.
    </div>
    <div class="cp-home-copy">
        A compact analytical view for the selected city, place, region or
        country. Search from the global search bar above at any time.
    </div>
</div>
        """
    )

    if not selected:
        st.info(
            "Search a city, place, region or country to load the dashboard."
        )
        return

    try:
        environment = cached_home_environment(
            selected[
                "latitude"
            ],
            selected[
                "longitude"
            ],
            selected.get(
                "timezone",
                "auto",
            ),
        )

    except Exception as error:
        environment = None
        if record_error is not None:
            record_error(
                error,
                component="home_environment",
                operation="load_live_conditions",
                page_name="Home",
                severity="warning",
            )

    if not environment:
        return

    weather = environment[
        "weather"
    ]
    air = environment[
        "air"
    ]

    current = weather.get(
        "current",
        {},
    )

    current_air = air.get(
        "current",
        {},
    )

    daily = weather.get(
        "daily",
        {},
    )

    health = build_health_context(
        current,
        current_air,
        daily,
    )

    compound = build_compound_context(
        health,
        current,
        current_air,
        daily,
    )

    st.markdown(
        f"## {selected['name']}"
    )

    if selected.get(
        "scope_note"
    ):
        st.caption(
            selected[
                "scope_note"
            ]
        )

    k1, k2, k3, k4 = st.columns(
        4
    )

    k1.metric(
        "Temperature",
        _fmt(
            current.get(
                "temperature_2m"
            ),
            ".1f",
            "°C",
        ),
    )

    k2.metric(
        "Feels like",
        _fmt(
            current.get(
                "apparent_temperature"
            ),
            ".1f",
            "°C",
        ),
    )

    k3.metric(
        "European AQI",
        _fmt(
            current_air.get(
                "european_aqi"
            ),
            ".0f",
        ),
    )

    k4.metric(
        "Wind",
        _fmt(
            current.get(
                "wind_speed_10m"
            ),
            ".0f",
            " km/h",
        ),
    )

    left, right = st.columns(
        [
            1.45,
            0.55,
        ],
        gap="medium",
    )

    with left:
        st.markdown(
            "### Forecast"
        )

        frame = _forecast_frame(
            weather.get(
                "hourly",
                {},
            ),
            hours=30,
        )

        st.plotly_chart(
            _forecast_chart(
                frame
            ),
            width="stretch",
            config={
                "displayModeBar": False,
            },
            key="v21_dashboard_forecast",
        )

    with right:
        st.markdown(
            "### What matters"
        )

        st.html(
            f"""
<div class="cp-home-card">
    <div class="cp-home-label">Heat-health context</div>
    <div class="cp-home-value">{health['heat']['label']}</div>
    <div class="cp-home-note">
        Air: {health['air_quality']['label']} ·
        UV: {health['uv']['label']} ·
        Tonight: {health['night']['label']}
    </div>
</div>
            """
        )

        for item in compound[
            :3
        ]:
            st.html(
                f"""
<div class="cp-home-guidance">
    <b>{item['name']}</b>
    <div>{item['message']}</div>
</div>
                """
            )

    st.markdown(
        "### Historical climate"
    )

    if selected[
        "kind"
    ] == "country":
        historical = _timeline_country_data(
            country_national
        )
    else:
        historical = _timeline_city_data(
            summary,
            anomalies,
        )

    if (
        historical is not None
        and not historical.empty
    ):
        st.plotly_chart(
            _timeline_figure(
                historical,
                None,
            ),
            width="stretch",
            config={
                "displayModeBar": False,
            },
            key="v21_dashboard_history",
        )

    else:
        st.info(
            "Historical climate is still loading or is not available for this "
            "selection. Live conditions above remain valid."
        )


def render_climate_timeline_page(
    city=None,
    point_location=None,
    summary=None,
    anomalies=None,
    country_feature=None,
    country_national=None,
    country_iso3=None,
):
    st.html(
        _home_css()
    )

    st.html(
        """
<div class="cp-v19-hero">
    <div class="cp-v19-eyebrow">Climate Timeline</div>
    <div class="cp-v19-brand">
        One place. <span>Past → present → future.</span>
    </div>
    <div class="cp-v19-copy">
        ORBIDENSE AI explicitly separates historical observations/reanalysis
        from model projections while presenting them in one continuous,
        interactive climate narrative.
    </div>
</div>
        """
    )

    if (
        city is None
        and country_feature is None
    ):
        st.info(
            "Search a city or country first."
        )
        st.stop()

    if country_feature is not None:
        historical = _timeline_country_data(
            country_national
        )

        scenario_name = st.selectbox(
            "Future scenario",
            list(
                CCKP_SCENARIOS.keys()
            ),
            index=1,
            key="v19_timeline_country_scenario",
        )

        future = None

        if country_iso3:
            try:
                trajectory = cached_country_trajectory(
                    country_iso3,
                    CCKP_SCENARIOS[
                        scenario_name
                    ],
                )

                if (
                    trajectory is not None
                    and not trajectory.empty
                ):
                    years = {
                        "2020-2039": 2030,
                        "2040-2059": 2050,
                        "2060-2079": 2070,
                        "2080-2099": 2090,
                    }

                    future = pd.DataFrame(
                        {
                            "year": [
                                years.get(
                                    period,
                                    2050,
                                )
                                for period in trajectory[
                                    "period"
                                ]
                            ],
                            "median_c": trajectory[
                                "median_c"
                            ],
                            "low_c": trajectory[
                                "p10_c"
                            ],
                            "high_c": trajectory[
                                "p90_c"
                            ],
                        }
                    )
            except Exception:
                future = None

        st.plotly_chart(
            _timeline_figure(
                historical,
                future,
            ),
            width="stretch",
            config={
                "displayModeBar": True,
            },
            key="v19_timeline_country",
        )

        st.caption(
            "Country history uses national spatial averages. "
            "Future values use country-aggregated CMIP6 scenario information."
        )

    else:
        historical = _timeline_city_data(
            summary,
            anomalies,
        )

        future = st.session_state.get(
            "v19_timeline_city_future"
        )

        if st.button(
            "Load 2041–2049 multi-model projection",
            key="v19_timeline_city_future_button",
        ):
            try:
                ensemble = cached_home_future(
                    city[
                        "latitude"
                    ],
                    city[
                        "longitude"
                    ],
                )

                baseline = historical[
                    (
                        historical[
                            "year"
                        ]
                        >= 1991
                    )
                    &
                    (
                        historical[
                            "year"
                        ]
                        <= 2020
                    )
                ][
                    "temperature_c"
                ].mean()

                future = pd.DataFrame(
                    {
                        "year": [
                            2045
                        ],
                        "median_c": [
                            ensemble[
                                "temperature_median_c"
                            ]
                            - baseline
                        ],
                        "low_c": [
                            ensemble[
                                "temperature_min_c"
                            ]
                            - baseline
                        ],
                        "high_c": [
                            ensemble[
                                "temperature_max_c"
                            ]
                            - baseline
                        ],
                    }
                )

                st.session_state[
                    "v19_timeline_city_future"
                ] = future

            except Exception as error:
                if record_error is not None:
                    record_error(
                        error,
                        component="climate_timeline",
                        operation="future_projection",
                        page_name="Climate Timeline",
                        severity="warning",
                    )

        st.plotly_chart(
            _timeline_figure(
                historical,
                future,
            ),
            width="stretch",
            config={
                "displayModeBar": True,
            },
            key="v19_timeline_city",
        )

        st.caption(
            "City history uses the existing ORBIDENSE AI ERA5 pipeline. "
            "Full 2100 city-scale NEX-GDDP-CMIP6 should be served from a "
            "preprocessed cache rather than queried live from the full archive."
        )

    if (
        historical is not None
        and not historical.empty
    ):
        with st.expander(
            "Timeline data & provenance",
            expanded=False,
        ):
            st.dataframe(
                historical,
                width="stretch",
                hide_index=True,
            )