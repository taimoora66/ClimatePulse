from __future__ import annotations

import streamlit as st
from datetime import date

import numpy as np
import pandas as pd
import requests
from src.observability import observe_operation


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
@observe_operation("open_meteo_archive", quality_source="Open-Meteo Archive")
def get_point_history(
    latitude: float,
    longitude: float,
    start_year: int = 1990,
    end_year: int = 2025,
):
    """
    Point-based historical fallback using Open-Meteo's historical API.

    This is deliberately labelled as a point/grid-cell history. It is not a
    national spatial average for country selections and not an area-average
    climate for administrative regions.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": f"{start_year}-01-01",
        "end_date": f"{end_year}-12-31",
        "timezone": "GMT",
        "daily": (
            "temperature_2m_mean,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum"
        ),
    }

    response = requests.get(
        ARCHIVE_URL,
        params=params,
        # Historical data are secondary to the live experience. Bound a
        # provider stall so an unavailable archive never holds a page for
        # more than a reasonable request window.
        timeout=30,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )

    response.raise_for_status()

    payload = response.json()
    daily = payload.get(
        "daily",
        {},
    )

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                daily.get(
                    "time",
                    []
                ),
                errors="coerce",
            ),
            "temperature_mean": pd.to_numeric(
                daily.get(
                    "temperature_2m_mean",
                    []
                ),
                errors="coerce",
            ),
            "temperature_max": pd.to_numeric(
                daily.get(
                    "temperature_2m_max",
                    []
                ),
                errors="coerce",
            ),
            "temperature_min": pd.to_numeric(
                daily.get(
                    "temperature_2m_min",
                    []
                ),
                errors="coerce",
            ),
            "precipitation": pd.to_numeric(
                daily.get(
                    "precipitation_sum",
                    []
                ),
                errors="coerce",
            ),
        }
    )

    frame = frame.dropna(
        subset=["date"]
    )

    if frame.empty:
        return {
            "summary": pd.DataFrame(),
            "anomalies": pd.DataFrame(),
            "trend": None,
            "country_frame": pd.DataFrame(),
        }

    frame["year"] = frame["date"].dt.year

    grouped = frame.groupby(
        "year",
        as_index=False,
    )

    summary = grouped.agg(
        avg_temperature_c=(
            "temperature_mean",
            "mean",
        ),
        avg_max_temperature_c=(
            "temperature_max",
            "mean",
        ),
        avg_min_temperature_c=(
            "temperature_min",
            "mean",
        ),
        hottest_day_c=(
            "temperature_max",
            "max",
        ),
        coldest_day_c=(
            "temperature_min",
            "min",
        ),
        annual_precipitation_mm=(
            "precipitation",
            "sum",
        ),
    )

    hot_days = (
        frame.assign(
            hot=(
                frame["temperature_max"]
                >= 30
            ).astype(int),
            extreme=(
                frame["temperature_max"]
                >= 35
            ).astype(int),
        )
        .groupby(
            "year",
            as_index=False,
        )
        .agg(
            hot_days_30c=(
                "hot",
                "sum",
            ),
            extreme_hot_days_35c=(
                "extreme",
                "sum",
            ),
        )
    )

    summary = summary.merge(
        hot_days,
        on="year",
        how="left",
    )

    baseline = summary.loc[
        summary["year"].between(
            1991,
            2020,
        ),
        "avg_temperature_c",
    ].mean()

    anomalies = summary[
        [
            "year",
            "avg_temperature_c",
        ]
    ].copy()

    anomalies = anomalies.rename(
        columns={
            "avg_temperature_c":
                "annual_temperature_c"
        }
    )

    anomalies[
        "baseline_temperature_c"
    ] = baseline

    anomalies[
        "anomaly_c"
    ] = (
        anomalies[
            "annual_temperature_c"
        ]
        - baseline
    )

    valid = summary.dropna(
        subset=[
            "year",
            "avg_temperature_c",
        ]
    )

    trend = None

    if len(valid) >= 5:
        slope, intercept = np.polyfit(
            valid["year"].astype(float),
            valid["avg_temperature_c"].astype(float),
            1,
        )

        trend = {
            "trend_c_per_decade":
                float(slope * 10),
            "slope_c_per_decade":
                float(slope * 10),
            "warming_rate_c_per_decade":
                float(slope * 10),
            "source":
                "Open-Meteo historical point fallback",
        }

    country_frame = summary[
        [
            "year",
            "avg_temperature_c",
            "annual_precipitation_mm",
        ]
    ].copy()

    country_frame = country_frame.rename(
        columns={
            "avg_temperature_c":
                "mean_temperature_c",
            "annual_precipitation_mm":
                "precipitation_mm",
        }
    )

    return {
        "summary": summary,
        "anomalies": anomalies,
        "trend": trend,
        "country_frame": country_frame,
    }
