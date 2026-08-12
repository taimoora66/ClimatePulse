from __future__ import annotations

from typing import Any

import requests


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"


GLOBAL_PULSE_LOCATIONS = (
    {"name": "Milan", "country": "Italy", "lat": 45.4642, "lon": 9.1900},
    {"name": "London", "country": "United Kingdom", "lat": 51.5072, "lon": -0.1276},
    {"name": "Cairo", "country": "Egypt", "lat": 30.0444, "lon": 31.2357},
    {"name": "Lagos", "country": "Nigeria", "lat": 6.5244, "lon": 3.3792},
    {"name": "Islamabad", "country": "Pakistan", "lat": 33.6844, "lon": 73.0479},
    {"name": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090},
    {"name": "Bangkok", "country": "Thailand", "lat": 13.7563, "lon": 100.5018},
    {"name": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503},
    {"name": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093},
    {"name": "New York", "country": "United States", "lat": 40.7128, "lon": -74.0060},
    {"name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lon": -99.1332},
    {"name": "São Paulo", "country": "Brazil", "lat": -23.5505, "lon": -46.6333},
    {"name": "Vancouver", "country": "Canada", "lat": 49.2827, "lon": -123.1207},
    {"name": "Buenos Aires", "country": "Argentina", "lat": -34.6037, "lon": -58.3816},
    {"name": "Cape Town", "country": "South Africa", "lat": -33.9249, "lon": 18.4241},
    {"name": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198},
)


def _request_json(
    url: str,
    params: dict[str, Any],
    timeout: int = 35,
    headers: dict[str, str] | None = None,
):
    request_headers = {
        "User-Agent": (
            "ClimatePulse/1.0 "
            "(environmental data dashboard)"
        )
    }

    if headers:
        request_headers.update(headers)

    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers=request_headers,
    )
    response.raise_for_status()
    return response.json()


def get_home_environment(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
):
    """
    Load one compact weather request plus one air-quality request.

    The Home page then derives its health/context indicators locally.
    """
    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone or "auto",
        "forecast_days": 7,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m,"
            "wind_gusts_10m,"
            "cloud_cover,"
            "is_day"
        ),
        "hourly": (
            "temperature_2m,"
            "apparent_temperature,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "precipitation_probability,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m,"
            "wind_gusts_10m,"
            "uv_index,"
            "shortwave_radiation,"
            "cloud_cover"
        ),
        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "apparent_temperature_max,"
            "apparent_temperature_min,"
            "precipitation_sum,"
            "precipitation_probability_max,"
            "uv_index_max,"
            "sunrise,"
            "sunset"
        ),
    }

    air_params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone or "auto",
        "forecast_days": 5,
        "current": (
            "european_aqi,"
            "pm2_5,"
            "pm10,"
            "ozone,"
            "nitrogen_dioxide,"
            "alder_pollen,"
            "birch_pollen,"
            "grass_pollen,"
            "mugwort_pollen,"
            "ragweed_pollen"
        ),
        "hourly": (
            "european_aqi,"
            "pm2_5,"
            "pm10,"
            "ozone,"
            "nitrogen_dioxide,"
            "alder_pollen,"
            "birch_pollen,"
            "grass_pollen,"
            "mugwort_pollen,"
            "ragweed_pollen"
        ),
    }

    weather = _request_json(
        FORECAST_URL,
        weather_params,
    )

    try:
        air = _request_json(
            AIR_URL,
            air_params,
        )
    except Exception:
        air = {}

    return {
        "weather": weather,
        "air": air,
    }


def get_global_weather_pulse():
    """
    Two batched requests for a small set of global reference cities:
    weather + air quality.

    This powers the interactive globe without one request per city.
    """
    latitudes = ",".join(
        str(item["lat"])
        for item in GLOBAL_PULSE_LOCATIONS
    )

    longitudes = ",".join(
        str(item["lon"])
        for item in GLOBAL_PULSE_LOCATIONS
    )

    weather_payload = _request_json(
        FORECAST_URL,
        {
            "latitude": latitudes,
            "longitude": longitudes,
            "current": (
                "temperature_2m,"
                "apparent_temperature,"
                "weather_code,"
                "wind_speed_10m,"
                "cloud_cover,"
                "precipitation,"
                "is_day"
            ),
            "timezone": "GMT",
        },
        timeout=40,
    )

    try:
        air_payload = _request_json(
            AIR_URL,
            {
                "latitude": latitudes,
                "longitude": longitudes,
                "current": (
                    "european_aqi,"
                    "pm2_5,"
                    "ozone"
                ),
                "timezone": "GMT",
            },
            timeout=40,
        )
    except Exception:
        air_payload = []

    if isinstance(weather_payload, dict):
        weather_payload = [weather_payload]

    if isinstance(air_payload, dict):
        air_payload = [air_payload]

    rows = []

    for index, metadata in enumerate(
        GLOBAL_PULSE_LOCATIONS
    ):
        weather_response = (
            weather_payload[index]
            if index < len(weather_payload)
            else {}
        )

        air_response = (
            air_payload[index]
            if index < len(air_payload)
            else {}
        )

        current = (
            weather_response.get("current", {})
            if isinstance(weather_response, dict)
            else {}
        )

        air_current = (
            air_response.get("current", {})
            if isinstance(air_response, dict)
            else {}
        )

        rows.append(
            {
                **metadata,
                "temperature_c": current.get("temperature_2m"),
                "apparent_temperature_c": current.get("apparent_temperature"),
                "weather_code": current.get("weather_code"),
                "wind_kmh": current.get("wind_speed_10m"),
                "cloud_cover": current.get("cloud_cover"),
                "precipitation_mm": current.get("precipitation"),
                "is_day": current.get("is_day"),
                "european_aqi": air_current.get("european_aqi"),
                "pm2_5": air_current.get("pm2_5"),
                "ozone": air_current.get("ozone"),
            }
        )

    return rows


def is_probably_us_point(
    latitude: float,
    longitude: float,
) -> bool:
    """
    Conservative bounding-box screen used only to decide whether the
    official US NWS alerts endpoint is relevant.

    Alaska and Hawaii are included with broad bounding ranges.
    """
    continental = (
        24 <= latitude <= 50
        and -125 <= longitude <= -66
    )

    alaska = (
        51 <= latitude <= 72
        and -170 <= longitude <= -129
    )

    hawaii = (
        18 <= latitude <= 23
        and -161 <= longitude <= -154
    )

    return (
        continental
        or alaska
        or hawaii
    )


def get_official_alerts(
    latitude: float,
    longitude: float,
):
    """
    Retrieve authoritative NWS active alerts for US points.

    Elsewhere this function returns an empty list rather than pretending
    ClimatePulse has a universal official-warning API.
    """
    if not is_probably_us_point(
        latitude,
        longitude,
    ):
        return []

    payload = _request_json(
        NWS_ALERTS_URL,
        {
            "point": (
                f"{latitude:.4f},"
                f"{longitude:.4f}"
            )
        },
        timeout=25,
        headers={
            "Accept": "application/geo+json",
        },
    )

    alerts = []

    for feature in payload.get(
        "features",
        [],
    ):
        properties = feature.get(
            "properties",
            {},
        )

        alerts.append(
            {
                "event": properties.get(
                    "event"
                ),
                "headline": properties.get(
                    "headline"
                ),
                "severity": properties.get(
                    "severity"
                ),
                "urgency": properties.get(
                    "urgency"
                ),
                "certainty": properties.get(
                    "certainty"
                ),
                "effective": properties.get(
                    "effective"
                ),
                "expires": properties.get(
                    "expires"
                ),
                "description": properties.get(
                    "description"
                ),
                "instruction": properties.get(
                    "instruction"
                ),
                "source": "US National Weather Service",
            }
        )

    return alerts