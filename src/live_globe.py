from __future__ import annotations

import math
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.api.country_live_field import (
    get_live_country_context,
    get_live_country_current,
    merge_live_country_field,
)
from src.services.country_weather_store import (
    finish_global_weather_refresh,
    load_global_weather_snapshot,
    save_global_weather_snapshot,
    snapshot_age_seconds,
    try_claim_global_weather_refresh,
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
# GLOBAL WEATHER POLICY
# =========================================================
#
# IMPORTANT:
# Open-Meteo's rate accounting can scale with number of locations/data volume.
# The global field is therefore intentionally much more conservative than a
# one-city request.
#
# Current country field:
#     refresh every 2 hours
#
# 24h/daily context:
#     refresh every 6 hours
#
# Visitors normally read Neon + Streamlit cache. Only one cross-session caller
# can own a provider refresh lease for a cache key at a time.

CURRENT_KEY = "country_current_v1"
CONTEXT_KEY = "country_context_v1"

CURRENT_MAX_AGE_SECONDS = 2 * 60 * 60
CONTEXT_MAX_AGE_SECONDS = 6 * 60 * 60

REFRESH_LEASE_SECONDS = 4 * 60

# A short Streamlit DB-read cache prevents every widget rerun from querying
# Neon. st.cache_data is shared across Streamlit users/sessions for the process.
NEON_READ_CACHE_SECONDS = 5 * 60


@st.cache_data(
    ttl=NEON_READ_CACHE_SECONDS,
    max_entries=8,
    show_spinner=False,
)
def _cached_neon_snapshot(
    cache_key,
):
    return load_global_weather_snapshot(
        cache_key
    )


def _force_reload_neon(
    cache_key,
):
    _cached_neon_snapshot.clear()
    return _cached_neon_snapshot(
        cache_key
    )


def _snapshot_is_fresh(
    snapshot,
    max_age_seconds,
):
    if not snapshot:
        return False

    frame = snapshot.get(
        "frame"
    )

    if (
        frame is None
        or frame.empty
    ):
        return False

    age = snapshot_age_seconds(
        snapshot.get(
            "fetched_at"
        )
    )

    return (
        age is not None
        and age <= max_age_seconds
    )


def _refresh_snapshot(
    cache_key,
    provider_loader,
):
    """
    Refresh one global dataset only if this process/session wins the Neon lease.

    Returns:
        (snapshot, attempted, error_message)
    """
    claimed = (
        try_claim_global_weather_refresh(
            cache_key,
            lease_seconds=REFRESH_LEASE_SECONDS,
        )
    )

    if not claimed:
        return (
            _cached_neon_snapshot(
                cache_key
            ),
            False,
            None,
        )

    try:
        fresh_frame = provider_loader()

        if (
            fresh_frame is None
            or fresh_frame.empty
        ):
            raise RuntimeError(
                "Provider returned an empty global-weather dataset."
            )

        fetched_at = datetime.now(
            timezone.utc
        )

        save_global_weather_snapshot(
            cache_key,
            fresh_frame,
            fetched_at=fetched_at,
        )

        finish_global_weather_refresh(
            cache_key,
            success=True,
        )

        snapshot = _force_reload_neon(
            cache_key
        )

        return (
            snapshot,
            True,
            None,
        )

    except Exception as error:
        try:
            finish_global_weather_refresh(
                cache_key,
                success=False,
                error=str(
                    error
                ),
            )
        except Exception:
            pass

        # Preserve and serve the previous successful Neon snapshot.
        snapshot = _force_reload_neon(
            cache_key
        )

        return (
            snapshot,
            True,
            str(
                error
            ),
        )


def _get_or_refresh_snapshot(
    cache_key,
    provider_loader,
    max_age_seconds,
    force=False,
):
    """
    Read Neon first.

    Fresh:
        serve immediately; no provider call.

    Stale:
        one caller refreshes through a DB lease; other callers keep serving the
        previous snapshot.

    Missing:
        one caller attempts initial bootstrap.
    """
    snapshot = _cached_neon_snapshot(
        cache_key
    )

    if (
        not force
        and _snapshot_is_fresh(
            snapshot,
            max_age_seconds,
        )
    ):
        return (
            snapshot,
            False,
            None,
        )

    refreshed, attempted, error = (
        _refresh_snapshot(
            cache_key,
            provider_loader,
        )
    )

    # If another session owns the lease, reload Neon once. The old snapshot is
    # still perfectly valid as a last-known-good dataset.
    if not attempted:
        latest = _force_reload_neon(
            cache_key
        )

        if (
            latest
            and latest.get(
                "frame"
            ) is not None
            and not latest[
                "frame"
            ].empty
        ):
            refreshed = latest

    return (
        refreshed,
        attempted,
        error,
    )


def cached_country_field(
    force_current=False,
):
    """
    Public compatibility function used by home_page.py.

    The browser/session does NOT directly own the global provider cache.
    Neon is the persistent source of truth for the latest successful snapshots.
    """
    current_snapshot, _, current_error = (
        _get_or_refresh_snapshot(
            CURRENT_KEY,
            get_live_country_current,
            CURRENT_MAX_AGE_SECONDS,
            force=force_current,
        )
    )

    context_snapshot, _, context_error = (
        _get_or_refresh_snapshot(
            CONTEXT_KEY,
            get_live_country_context,
            CONTEXT_MAX_AGE_SECONDS,
            force=False,
        )
    )

    current_frame = (
        current_snapshot.get(
            "frame"
        )
        if current_snapshot
        else pd.DataFrame()
    )

    context_frame = (
        context_snapshot.get(
            "frame"
        )
        if context_snapshot
        else pd.DataFrame()
    )

    if (
        current_frame is None
        or current_frame.empty
    ):
        message = (
            current_error
            or (
                "No persisted global current-weather snapshot exists yet. "
                "The first successful provider fetch will bootstrap Neon."
            )
        )

        raise RuntimeError(
            message
        )

    frame = merge_live_country_field(
        current_frame,
        context_frame,
    )

    frame.attrs[
        "current_fetched_at"
    ] = (
        current_snapshot.get(
            "fetched_at"
        )
        if current_snapshot
        else None
    )

    frame.attrs[
        "context_fetched_at"
    ] = (
        context_snapshot.get(
            "fetched_at"
        )
        if context_snapshot
        else None
    )

    frame.attrs[
        "current_error"
    ] = current_error

    frame.attrs[
        "context_error"
    ] = context_error

    return frame


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


def _age_text(
    timestamp,
):
    age = snapshot_age_seconds(
        timestamp
    )

    if age is None:
        return "unknown age"

    if age < 90:
        return "under 2 min old"

    if age < 3600:
        return (
            f"{int(age // 60)} min old"
        )

    return (
        f"{age / 3600:.1f} h old"
    )


def _globe_focus(
    selected_location,
):
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

    try:
        latitude = float(
            selected_location.get(
                "latitude"
            )
        )
        longitude = float(
            selected_location.get(
                "longitude"
            )
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

    return {
        "lon": longitude,
        "lat": latitude,
        "scale": (
            1.22
            if kind == "country"
            else 1.38
        ),
    }


def _map_figure(
    frame,
    layer_name,
    selected_location=None,
):
    config = LAYER_CONFIG[
        layer_name
    ]

    local_frame = frame.copy()

    for column in [
        "temperature_change_24h_c",
        "today_high_c",
        "today_low_c",
        "precip_probability_pct",
        "capital",
        "region",
        "condition",
        "is_day",
    ]:
        if column not in local_frame.columns:
            local_frame[
                column
            ] = None

    custom = local_frame[
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
            locations=local_frame[
                "country"
            ],
            locationmode="country names",
            z=local_frame[
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
        str(
            value
        )
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
        if (
            value is not None
            and str(
                value
            ).strip()
            and str(
                value
            ).lower()
            != "nan"
        )
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
    Persistent Neon-backed global country weather globe.

    Normal visitor path:
        Streamlit cache -> Neon snapshot -> render.

    Provider path:
        only when the stored snapshot is stale, and only after winning a
        PostgreSQL refresh lease.
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

    force_refresh = False

    with control_2:
        if st.button(
            "↻ Refresh live countries",
            width="stretch",
            key=(
                "refresh_country_live_field"
            ),
            help=(
                "Refreshes the global current-weather snapshot only when "
                "ClimatePulse can safely claim the shared Neon refresh lease."
            ),
        ):
            # Clearing only the local DB-read cache is safe. The distributed
            # lease prevents multiple public sessions from hammering Open-Meteo.
            _cached_neon_snapshot.clear()
            force_refresh = True

    try:
        with st.spinner(
            "Loading global weather snapshot…"
        ):
            frame = cached_country_field(
                force_current=force_refresh,
            )

        if frame.empty:
            raise RuntimeError(
                "No global country weather rows are available."
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

        current_time = frame.attrs.get(
            "current_fetched_at"
        )

        context_time = frame.attrs.get(
            "context_fetched_at"
        )

        current_error = frame.attrs.get(
            "current_error"
        )

        context_error = frame.attrs.get(
            "context_error"
        )

        if (
            current_error
            or context_error
        ):
            st.caption(
                (
                    "Showing the latest successful Neon-backed Open-Meteo "
                    f"snapshot ({_age_text(current_time)}). "
                    "A provider refresh is temporarily unavailable; no "
                    "estimated replacement values were inserted."
                )
            )
        else:
            st.caption(
                (
                    "Drag to rotate · scroll/pinch to zoom · hover/tap a country. "
                    f"Current global snapshot: {_age_text(current_time)}. "
                    f"24h/daily context: {_age_text(context_time)}. "
                    "Country colors use representative-point weather, not a "
                    "national-area average."
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
            current_error
            or context_error
        ):
            with st.expander(
                "Provider status",
                expanded=False,
            ):
                if current_error:
                    st.code(
                        (
                            "Current field refresh: "
                            + str(
                                current_error
                            )
                        )
                    )

                if context_error:
                    st.code(
                        (
                            "24h/daily context refresh: "
                            + str(
                                context_error
                            )
                        )
                    )

    except Exception as error:
        st.error(
            (
                "The global weather snapshot is not available yet. "
                "ClimatePulse's selected-location, historical and climate "
                "tools remain available."
            )
        )

        st.info(
            (
                "Once Open-Meteo accepts one successful global refresh, "
                "ClimatePulse will persist it in Neon. Future Streamlit "
                "restarts and temporary provider 429 errors can then serve "
                "that last successful snapshot."
            )
        )

        with st.expander(
            "Technical detail"
        ):
            st.code(
                str(
                    error
                )
            )