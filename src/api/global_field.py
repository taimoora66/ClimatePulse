from __future__ import annotations

import streamlit as st
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests
from src.observability import observe_operation


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class GridSpec:
    lat_step: int = 15
    lon_step: int = 15
    min_lat: int = -75
    max_lat: int = 75


DEFAULT_GRID = GridSpec()


def _grid_coordinates(
    spec: GridSpec = DEFAULT_GRID,
):
    latitudes = list(
        range(
            spec.min_lat,
            spec.max_lat + 1,
            spec.lat_step,
        )
    )
    longitudes = list(
        range(
            -180,
            180,
            spec.lon_step,
        )
    )
    points = [
        (float(lat), float(lon))
        for lat in latitudes
        for lon in longitudes
    ]
    return latitudes, longitudes, points


def _chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _request_chunk(points):
    latitudes = ",".join(
        f"{lat:.2f}"
        for lat, _ in points
    )
    longitudes = ",".join(
        f"{lon:.2f}"
        for _, lon in points
    )

    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "timezone": "GMT",
        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "precipitation,"
            "cloud_cover,"
            "wind_speed_10m,"
            "is_day"
        ),
        "hourly": "temperature_2m",
        "past_hours": 24,
        "forecast_hours": 1,
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=60,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )
    response.raise_for_status()
    payload = response.json()

    if isinstance(payload, dict):
        payload = [payload]

    rows = []

    for point, item in zip(points, payload):
        latitude, longitude = point
        current = item.get("current", {})
        hourly = item.get("hourly", {})

        hourly_temperature = [
            value
            for value in hourly.get(
                "temperature_2m",
                [],
            )
            if value is not None
        ]

        change_24h = None
        if len(hourly_temperature) >= 2:
            try:
                change_24h = (
                    float(hourly_temperature[-1])
                    - float(hourly_temperature[0])
                )
            except (TypeError, ValueError):
                change_24h = None

        rows.append(
            {
                "latitude": latitude,
                "longitude": longitude,
                "temperature_c":
                    current.get("temperature_2m"),
                "apparent_temperature_c":
                    current.get("apparent_temperature"),
                "precipitation_mm":
                    current.get("precipitation"),
                "cloud_cover_pct":
                    current.get("cloud_cover"),
                "wind_kmh":
                    current.get("wind_speed_10m"),
                "is_day":
                    current.get("is_day"),
                "temperature_change_24h_c":
                    change_24h,
            }
        )

    return rows


@st.cache_data(ttl=600, max_entries=8, show_spinner=False)
@observe_operation("global_live_field", quality_source="Open-Meteo Global Field")
def get_global_current_field(
    spec: GridSpec = DEFAULT_GRID,
):
    """
    Fetch a low-resolution current global weather grid.

    Open-Meteo supports multiple comma-separated coordinates, so the app
    requests the grid in a few batches instead of one request per point.
    """
    latitudes, longitudes, points = _grid_coordinates(spec)

    rows = []
    for chunk in _chunks(points, 72):
        rows.extend(_request_chunk(chunk))

    frame = pd.DataFrame(rows)

    numeric_columns = [
        "latitude",
        "longitude",
        "temperature_c",
        "apparent_temperature_c",
        "precipitation_mm",
        "cloud_cover_pct",
        "wind_kmh",
        "temperature_change_24h_c",
    ]

    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

    return {
        "frame": frame,
        "latitudes": latitudes,
        "longitudes": longitudes,
        "source": "Open-Meteo Forecast API",
        "grid_resolution_degrees":
            spec.lat_step,
    }


def to_grid(
    frame: pd.DataFrame,
    value_column: str,
    latitudes,
    longitudes,
):
    pivot = frame.pivot_table(
        index="latitude",
        columns="longitude",
        values=value_column,
        aggfunc="mean",
    )

    pivot = pivot.reindex(
        index=[float(value) for value in latitudes],
        columns=[float(value) for value in longitudes],
    )

    values = pivot.to_numpy(dtype=float)

    values = np.concatenate(
        [
            values,
            values[:, 0:1],
        ],
        axis=1,
    )

    display_longitudes = (
        list(longitudes)
        + [180]
    )

    return values, display_longitudes
