from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.api.country_live_field import (
    get_live_country_field,
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


@st.cache_data(
    ttl=900,
    max_entries=2,
    show_spinner=False,
)
def cached_country_field():
    return get_live_country_field()


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

    Searching a country/city now rotates the live globe to that place instead
    of leaving the camera fixed over Europe/Africa.
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

    # Country searches should show the country in regional context.
    # Local/city/browser selections may zoom slightly closer.
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

    Every rendered country is colored by current weather at a representative
    country point. Hover/tap reveals a full current snapshot.

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
            cached_country_field.clear()
            st.rerun()

    try:
        with st.spinner(
            "Loading live country weather…"
        ):
            frame = cached_country_field()

        if frame.empty:
            raise RuntimeError(
                "No live country rows were returned."
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