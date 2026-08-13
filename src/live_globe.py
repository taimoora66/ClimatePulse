from __future__ import annotations

import math
import threading
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.api.country_live_field import (
    get_live_country_context,
    get_live_country_current,
    merge_live_country_field,
)


LAYER_CONFIG = {
    "Temperature": {
        "column": "temperature_c",
        "title": "°C",
        "colorscale": "Turbo",
        "zmin": -35,
        "zmax": 45,
    },
    "Feels like": {
        "column": "feels_like_c",
        "title": "°C",
        "colorscale": "Turbo",
        "zmin": -35,
        "zmax": 50,
    },
    "24h change": {
        "column":
            "temperature_change_24h_c",
        "title": "Δ°C",
        "colorscale": "RdBu_r",
        "zmin": -10,
        "zmax": 10,
    },
    "Rain": {
        "column": "precipitation_mm",
        "title": "mm",
        "colorscale": "Blues",
        "zmin": 0,
        "zmax": 12,
    },
    "Cloud": {
        "column": "cloud_pct",
        "title": "%",
        "colorscale": "Greys",
        "zmin": 0,
        "zmax": 100,
    },
    "Wind": {
        "column": "wind_kmh",
        "title": "km/h",
        "colorscale": "Viridis",
        "zmin": 0,
        "zmax": 80,
    },
}


# =========================================================
# RATE-SAFE SERVER CACHE
# =========================================================
#
# The free Open-Meteo service has request limits. A global country layer
# represents hundreds of coordinate lookups, so treating it like a single
# selected-city request is unnecessarily expensive.
#
# No data field or country is removed. We simply refresh each data family at
# a cadence that matches how quickly that family changes.
#
# Current model weather: 60 minutes
# 24h/daily context:    3 hours
#
# st.cache_data is shared by sessions within the Streamlit process, so normal
# page reruns and layer switches reuse the same server-side snapshot.

CURRENT_CACHE_TTL_SECONDS = 3600
CONTEXT_CACHE_TTL_SECONDS = 10800
MANUAL_REFRESH_COOLDOWN_SECONDS = 3600


@st.cache_data(
    ttl=CURRENT_CACHE_TTL_SECONDS,
    max_entries=2,
    show_spinner=False,
)
def cached_country_current():
    return get_live_country_current()


@st.cache_data(
    ttl=CONTEXT_CACHE_TTL_SECONDS,
    max_entries=2,
    show_spinner=False,
)
def cached_country_context():
    return get_live_country_context()


@st.cache_resource
def _country_live_store():
    """
    Process-wide last-known-good snapshot.

    This is NOT synthetic data. It contains only previous successful
    Open-Meteo responses. It prevents a temporary 429 from blanking the globe.
    """
    return {
        "lock": threading.Lock(),
        "current": None,
        "context": None,
        "current_stale": False,
        "context_stale": False,
        "current_error": None,
        "context_error": None,
        "last_manual_refresh_monotonic": 0.0,
    }


def _copy_frame(
    value,
):
    if (
        isinstance(
            value,
            pd.DataFrame,
        )
        and not value.empty
    ):
        return value.copy()

    return None


def cached_country_field():
    """
    Return the complete globe dataframe with last-known-good protection.

    Existing home_page.py imports this function, so its public interface is
    intentionally preserved.
    """
    store = _country_live_store()

    current = None
    context = None

    current_error = None
    context_error = None

    current_stale = False
    context_stale = False

    # Current conditions
    try:
        current = (
            cached_country_current()
        )

        if (
            current is None
            or current.empty
        ):
            raise RuntimeError(
                "No current country-weather rows were returned."
            )

        with store[
            "lock"
        ]:
            store[
                "current"
            ] = current.copy()
            store[
                "current_stale"
            ] = False
            store[
                "current_error"
            ] = None

    except Exception as error:
        current_error = str(
            error
        )

        with store[
            "lock"
        ]:
            current = _copy_frame(
                store.get(
                    "current"
                )
            )

            store[
                "current_stale"
            ] = current is not None
            store[
                "current_error"
            ] = current_error

        if current is None:
            raise

        current_stale = True

    # 24h + daily context
    try:
        context = (
            cached_country_context()
        )

        if (
            context is None
            or context.empty
        ):
            raise RuntimeError(
                "No country 24h/daily context rows were returned."
            )

        with store[
            "lock"
        ]:
            store[
                "context"
            ] = context.copy()
            store[
                "context_stale"
            ] = False
            store[
                "context_error"
            ] = None

    except Exception as error:
        context_error = str(
            error
        )

        with store[
            "lock"
        ]:
            context = _copy_frame(
                store.get(
                    "context"
                )
            )

            store[
                "context_stale"
            ] = context is not None
            store[
                "context_error"
            ] = context_error

        # Context is useful but current conditions are the essential dataset.
        # If this is the first-ever load and context is unavailable, the globe
        # can still render current conditions rather than failing completely.
        context_stale = (
            context is not None
        )

    with store[
        "lock"
    ]:
        if current_stale:
            store[
                "current_stale"
            ] = True

        if context_stale:
            store[
                "context_stale"
            ] = True

        if current_error:
            store[
                "current_error"
            ] = current_error

        if context_error:
            store[
                "context_error"
            ] = context_error

    return merge_live_country_field(
        current,
        context,
    )


def _country_live_status():
    store = _country_live_store()

    with store[
        "lock"
    ]:
        return {
            "current_stale":
                bool(
                    store.get(
                        "current_stale"
                    )
                ),
            "context_stale":
                bool(
                    store.get(
                        "context_stale"
                    )
                ),
            "current_error":
                store.get(
                    "current_error"
                ),
            "context_error":
                store.get(
                    "context_error"
                ),
        }


def _manual_refresh_current():
    """
    Rate-safe global manual refresh.

    The guard is process-wide rather than browser-session-only, so multiple
    visitors cannot independently clear the shared current-weather cache.
    """
    store = _country_live_store()

    now = time.monotonic()

    with store[
        "lock"
    ]:
        last_refresh = float(
            store.get(
                "last_manual_refresh_monotonic",
                0.0,
            )
            or 0.0
        )

        elapsed = (
            now
            - last_refresh
        )

        if (
            last_refresh > 0
            and elapsed
            < MANUAL_REFRESH_COOLDOWN_SECONDS
        ):
            remaining = int(
                MANUAL_REFRESH_COOLDOWN_SECONDS
                - elapsed
            )

            return (
                False,
                remaining,
            )

        store[
            "last_manual_refresh_monotonic"
        ] = now

    # Refresh only fast-changing current conditions.
    # The 24h/daily context keeps its independent 3-hour cache.
    cached_country_current.clear()

    return (
        True,
        0,
    )


def _fmt(
    value,
    suffix="",
    decimals=1,
):
    if value is None:
        return "—"

    try:
        if math.isnan(
            float(value)
        ):
            return "—"
    except (
        TypeError,
        ValueError,
    ):
        return "—"

    return (
        f"{float(value):.{decimals}f}"
        f"{suffix}"
    )


def _globe_focus(
    selected_location,
):
    """
    Return orthographic projection rotation/scale for the current selection.

    Searching a country/city rotates the live globe to that place instead of
    leaving the camera fixed over Europe/Africa.
    """
    default = {
        "lon": 10.0,
        "lat": 12.0,
        "scale": 1.0,
    }

    if not isinstance(
        selected_location,
        dict,
    ):
        return default

    latitude = selected_location.get(
        "latitude"
    )

    longitude = selected_location.get(
        "longitude"
    )

    try:
        latitude = float(
            latitude
        )
        longitude = float(
            longitude
        )

    except (
        TypeError,
        ValueError,
    ):
        return default

    kind = str(
        selected_location.get(
            "kind",
            ""
        )
    ).lower()

    scale = (
        1.22
        if kind == "country"
        else 1.38
    )

    return {
        "lon":
            longitude,
        "lat":
            latitude,
        "scale":
            scale,
    }


def _map_figure(
    frame,
    layer_name,
    selected_location=None,
):
    config = LAYER_CONFIG[
        layer_name
    ]

    # Guarantee optional context columns exist even during the first temporary
    # context outage, so hover rendering never crashes.
    for column in [
        "temperature_change_24h_c",
        "today_high_c",
        "today_low_c",
        "precip_probability_pct",
    ]:
        if column not in frame.columns:
            frame[
                column
            ] = None

    custom = frame[
        [
            "country",
            "capital",
            "region",
            "condition",
            "temperature_c",
            "feels_like_c",
            "humidity_pct",
            "precipitation_mm",
            "cloud_pct",
            "wind_kmh",
            "temperature_change_24h_c",
            "today_high_c",
            "today_low_c",
            "precip_probability_pct",
            "is_day",
        ]
    ].to_numpy()

    figure = go.Figure()

    figure.add_trace(
        go.Choropleth(
            locations=frame[
                "country"
            ],
            locationmode="country names",
            z=frame[
                config[
                    "column"
                ]
            ],
            customdata=custom,
            colorscale=config[
                "colorscale"
            ],
            zmin=config[
                "zmin"
            ],
            zmax=config[
                "zmax"
            ],
            marker_line_color=(
                "rgba(145,215,235,.52)"
            ),
            marker_line_width=0.55,
            colorbar=dict(
                title=dict(
                    text=config[
                        "title"
                    ],
                    font=dict(
                        color="#dff8ff",
                    ),
                ),
                tickfont=dict(
                    color="#b9d0da",
                ),
                thickness=11,
                len=0.60,
                outlinewidth=0,
                bgcolor=(
                    "rgba(4,17,27,.72)"
                ),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Capital: %{customdata[1]}<br>"
                "Region: %{customdata[2]}<br>"
                "Condition: %{customdata[3]}<br><br>"
                "Temperature: %{customdata[4]:.1f}°C<br>"
                "Feels like: %{customdata[5]:.1f}°C<br>"
                "Humidity: %{customdata[6]:.0f}%<br>"
                "Rain now: %{customdata[7]:.1f} mm<br>"
                "Cloud: %{customdata[8]:.0f}%<br>"
                "Wind: %{customdata[9]:.0f} km/h<br>"
                "24h temperature change: "
                "%{customdata[10]:+.1f}°C<br>"
                "Today high / low: "
                "%{customdata[11]:.1f} / "
                "%{customdata[12]:.1f}°C<br>"
                "Max precip probability: "
                "%{customdata[13]:.0f}%<br>"
                "<extra></extra>"
            ),
            name=layer_name,
        )
    )

    if selected_location:
        latitude = selected_location.get(
            "latitude"
        )
        longitude = selected_location.get(
            "longitude"
        )

        if (
            latitude is not None
            and longitude is not None
        ):
            figure.add_trace(
                go.Scattergeo(
                    lat=[
                        float(
                            latitude
                        )
                    ],
                    lon=[
                        float(
                            longitude
                        )
                    ],
                    mode="markers",
                    marker=dict(
                        size=10,
                        color="#ffffff",
                        line=dict(
                            color="#42dfff",
                            width=3,
                        ),
                        symbol="star",
                    ),
                    text=[
                        selected_location.get(
                            "name",
                            "Selected location",
                        )
                    ],
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Selected ClimatePulse location"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    focus = _globe_focus(
        selected_location
    )

    figure.update_geos(
        projection_type="orthographic",
        projection_rotation=dict(
            lon=focus[
                "lon"
            ],
            lat=focus[
                "lat"
            ],
            roll=0,
        ),
        projection_scale=focus[
            "scale"
        ],
        showcoastlines=True,
        coastlinecolor=(
            "rgba(89,204,230,.58)"
        ),
        showland=True,
        landcolor="#0b2330",
        showocean=True,
        oceancolor="#020b13",
        showlakes=True,
        lakecolor="#03121c",
        showcountries=True,
        countrycolor=(
            "rgba(127,211,232,.42)"
        ),
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )

    figure.update_layout(
        height=620,
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0,
        ),
        paper_bgcolor=(
            "rgba(0,0,0,0)"
        ),
        plot_bgcolor=(
            "rgba(0,0,0,0)"
        ),
        uirevision=(
            "climatepulse-country-globe"
        ),
    )

    return figure


def _country_card(
    row,
):
    daylight = (
        "Day"
        if row.get(
            "is_day"
        ) == 1
        else "Night"
    )

    st.markdown(
        f"### {row['country']}"
    )

    subtitle = " · ".join(
        value
        for value in [
            row.get(
                "capital"
            ),
            row.get(
                "region"
            ),
            row.get(
                "condition"
            ),
            daylight,
        ]
        if value
    )

    if subtitle:
        st.caption(
            subtitle
        )

    m1, m2, m3, m4 = st.columns(
        4
    )

    m1.metric(
        "Temperature",
        _fmt(
            row.get(
                "temperature_c"
            ),
            "°C",
        ),
    )

    m2.metric(
        "Feels like",
        _fmt(
            row.get(
                "feels_like_c"
            ),
            "°C",
        ),
    )

    m3.metric(
        "Humidity",
        _fmt(
            row.get(
                "humidity_pct"
            ),
            "%",
            0,
        ),
    )

    m4.metric(
        "Wind",
        _fmt(
            row.get(
                "wind_kmh"
            ),
            " km/h",
            0,
        ),
    )

    n1, n2, n3, n4 = st.columns(
        4
    )

    n1.metric(
        "Rain now",
        _fmt(
            row.get(
                "precipitation_mm"
            ),
            " mm",
        ),
    )

    n2.metric(
        "Cloud",
        _fmt(
            row.get(
                "cloud_pct"
            ),
            "%",
            0,
        ),
    )

    n3.metric(
        "Today high / low",
        (
            f"{_fmt(row.get('today_high_c'), '°C')} / "
            f"{_fmt(row.get('today_low_c'), '°C')}"
        ),
    )

    n4.metric(
        "24h temp change",
        _fmt(
            row.get(
                "temperature_change_24h_c"
            ),
            "°C",
        ),
    )


def render_live_weather_globe(
    selected_location=None,
    height=620,
):
    """
    Country-first live global weather globe.

    Every rendered country is colored by weather at a representative country
    point. Hover/tap reveals the complete current + 24h/daily snapshot.

    Important:
    these are representative-point weather values, not national spatial
    averages.
    """
    control_1, control_2 = st.columns(
        [
            0.73,
            0.27,
        ],
        vertical_alignment="center",
    )

    with control_1:
        layer = st.segmented_control(
            "Live country layer",
            options=list(
                LAYER_CONFIG.keys()
            ),
            default="Temperature",
            key=(
                "climatepulse_country_layer"
            ),
            label_visibility="collapsed",
        )

        if layer is None:
            layer = "Temperature"

    with control_2:
        if st.button(
            "↻ Refresh live countries",
            width="stretch",
            key=(
                "refresh_country_live_field"
            ),
        ):
            refreshed, remaining = (
                _manual_refresh_current()
            )

            if refreshed:
                st.toast(
                    (
                        "Refreshing current country conditions. "
                        "24h/daily context keeps its independent cache."
                    )
                )
                st.rerun()

            else:
                minutes = max(
                    1,
                    math.ceil(
                        remaining
                        / 60
                    ),
                )

                st.toast(
                    (
                        "The global live field was refreshed recently. "
                        f"Manual refresh is available again in about "
                        f"{minutes} min."
                    )
                )

    try:
        with st.spinner(
            "Loading live country weather…"
        ):
            frame = cached_country_field()

        if frame.empty:
            raise RuntimeError(
                "No live country rows were returned."
            )

        status = (
            _country_live_status()
        )

        figure = _map_figure(
            frame,
            layer,
            selected_location,
        )

        figure.update_layout(
            height=height
        )

        st.plotly_chart(
            figure,
            width="stretch",
            config={
                "displayModeBar": False,
                "scrollZoom": True,
                "responsive": True,
            },
            key=(
                "climatepulse_country_live_globe"
            ),
        )

        if (
            status[
                "current_stale"
            ]
            or status[
                "context_stale"
            ]
        ):
            st.caption(
                (
                    "Open-Meteo is temporarily rate-limiting or unavailable. "
                    "ClimatePulse is showing the last successful provider "
                    "snapshot rather than replacing it with estimated data."
                )
            )
        else:
            st.caption(
                (
                    "Drag to rotate · scroll/pinch to zoom · hover/tap a country "
                    "for current conditions. Country colors use live weather at "
                    "a representative country point, not a national-area average."
                )
            )

        country_names = sorted(
            frame[
                "country"
            ].dropna().unique()
        )

        default_index = 0

        if selected_location:
            selected_code = (
                selected_location.get(
                    "country_code"
                )
            )

            if selected_code:
                match = frame.loc[
                    frame[
                        "cca2"
                    ].astype(
                        str
                    ).str.upper()
                    == str(
                        selected_code
                    ).upper()
                ]

                if not match.empty:
                    default_name = (
                        match.iloc[0][
                            "country"
                        ]
                    )

                    if (
                        default_name
                        in country_names
                    ):
                        default_index = (
                            country_names.index(
                                default_name
                            )
                        )

        with st.expander(
            "Inspect a country",
            expanded=False,
        ):
            chosen = st.selectbox(
                "Country",
                options=country_names,
                index=default_index,
                key=(
                    "climatepulse_country_inspector"
                ),
            )

            row = (
                frame.loc[
                    frame[
                        "country"
                    ]
                    == chosen
                ]
                .iloc[0]
                .to_dict()
            )

            _country_card(
                row
            )

        if (
            status[
                "current_error"
            ]
            or status[
                "context_error"
            ]
        ):
            with st.expander(
                "Provider status",
                expanded=False,
            ):
                if status[
                    "current_error"
                ]:
                    st.code(
                        (
                            "Current field: "
                            + status[
                                "current_error"
                            ]
                        )
                    )

                if status[
                    "context_error"
                ]:
                    st.code(
                        (
                            "24h/daily context: "
                            + status[
                                "context_error"
                            ]
                        )
                    )

    except Exception as error:
        st.error(
            (
                "Live country weather could not be loaded. "
                "Local ClimatePulse pages remain available."
            )
        )

        with st.expander(
            "Technical detail"
        ):
            st.code(
                str(error)
            )