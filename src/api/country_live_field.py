from __future__ import annotations

from io import StringIO

import pandas as pd
import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

GOOGLE_CENTROIDS_URL = (
    "https://raw.githubusercontent.com/google/dspl/master/"
    "samples/google/canonical/countries.csv"
)

REST_COUNTRIES_URL = (
    "https://restcountries.com/v3.1/all"
)


WMO_TEXT = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Heavy rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}


def weather_text(code):
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "Unknown"

    return WMO_TEXT.get(
        code,
        f"WMO {code}",
    )


def _country_catalog_google():
    response = requests.get(
        GOOGLE_CENTROIDS_URL,
        timeout=20,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )
    response.raise_for_status()

    frame = pd.read_csv(
        StringIO(response.text)
    )

    frame = frame.rename(
        columns={
            "country": "cca2",
            "name": "country",
            "latitude": "latitude",
            "longitude": "longitude",
        }
    )

    frame["capital"] = ""
    frame["region"] = ""
    frame["subregion"] = ""

    return frame[
        [
            "cca2",
            "country",
            "latitude",
            "longitude",
            "capital",
            "region",
            "subregion",
        ]
    ].copy()


def _country_catalog_rest():
    response = requests.get(
        REST_COUNTRIES_URL,
        params={
            "fields": (
                "name,cca2,latlng,capital,region,subregion"
            )
        },
        timeout=25,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )
    response.raise_for_status()

    payload = response.json()

    rows = []

    for item in payload:
        latlng = item.get(
            "latlng"
        ) or []

        if len(latlng) < 2:
            continue

        name = (
            item.get(
                "name",
                {},
            ).get(
                "common"
            )
            or ""
        )

        rows.append(
            {
                "cca2": item.get(
                    "cca2"
                ),
                "country": name,
                "latitude": latlng[0],
                "longitude": latlng[1],
                "capital": ", ".join(
                    item.get(
                        "capital"
                    )
                    or []
                ),
                "region": item.get(
                    "region"
                )
                or "",
                "subregion": item.get(
                    "subregion"
                )
                or "",
            }
        )

    return pd.DataFrame(
        rows
    )


def get_country_catalog():
    """
    Country representative coordinates.

    Primary:
        Google canonical country-coordinate dataset.

    Fallback:
        REST Countries.

    These coordinates are representative country points used for current
    weather lookup. They are not national spatial-average weather values.
    """
    errors = []

    for loader in (
        _country_catalog_google,
        _country_catalog_rest,
    ):
        try:
            frame = loader()

            if (
                frame is not None
                and not frame.empty
            ):
                frame["latitude"] = pd.to_numeric(
                    frame["latitude"],
                    errors="coerce",
                )
                frame["longitude"] = pd.to_numeric(
                    frame["longitude"],
                    errors="coerce",
                )

                frame = frame.dropna(
                    subset=[
                        "country",
                        "latitude",
                        "longitude",
                    ]
                )

                frame = frame.drop_duplicates(
                    subset=[
                        "country"
                    ],
                    keep="first",
                )

                return frame.reset_index(
                    drop=True
                )

        except Exception as error:
            errors.append(
                str(error)
            )

    raise RuntimeError(
        "Country metadata could not be loaded. "
        + " | ".join(errors)
    )


def _chunks(values, size):
    for start in range(
        0,
        len(values),
        size,
    ):
        yield values[
            start:
            start + size
        ]


def _request_weather_chunk(
    frame,
):
    latitudes = ",".join(
        f"{value:.4f}"
        for value in frame[
            "latitude"
        ]
    )

    longitudes = ",".join(
        f"{value:.4f}"
        for value in frame[
            "longitude"
        ]
    )

    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "timezone": "GMT",
        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "relative_humidity_2m,"
            "precipitation,"
            "cloud_cover,"
            "wind_speed_10m,"
            "weather_code,"
            "is_day"
        ),
        "hourly": "temperature_2m",
        "past_hours": 24,
        "forecast_hours": 1,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "forecast_days": 1,
    }

    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=75,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )
    response.raise_for_status()

    payload = response.json()

    if isinstance(
        payload,
        dict,
    ):
        payload = [
            payload
        ]

    rows = []

    for (
        _,
        country_row,
    ), item in zip(
        frame.iterrows(),
        payload,
    ):
        current = item.get(
            "current",
            {},
        )

        hourly = item.get(
            "hourly",
            {},
        )

        daily = item.get(
            "daily",
            {},
        )

        hourly_temperature = [
            value
            for value in hourly.get(
                "temperature_2m",
                [],
            )
            if value is not None
        ]

        change_24h = None

        if len(
            hourly_temperature
        ) >= 2:
            try:
                change_24h = (
                    float(
                        hourly_temperature[-1]
                    )
                    - float(
                        hourly_temperature[0]
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                change_24h = None

        code = current.get(
            "weather_code"
        )

        rows.append(
            {
                **country_row.to_dict(),
                "temperature_c":
                    current.get(
                        "temperature_2m"
                    ),
                "feels_like_c":
                    current.get(
                        "apparent_temperature"
                    ),
                "humidity_pct":
                    current.get(
                        "relative_humidity_2m"
                    ),
                "precipitation_mm":
                    current.get(
                        "precipitation"
                    ),
                "cloud_pct":
                    current.get(
                        "cloud_cover"
                    ),
                "wind_kmh":
                    current.get(
                        "wind_speed_10m"
                    ),
                "weather_code":
                    code,
                "condition":
                    weather_text(
                        code
                    ),
                "is_day":
                    current.get(
                        "is_day"
                    ),
                "temperature_change_24h_c":
                    change_24h,
                "today_high_c":
                    (
                        daily.get(
                            "temperature_2m_max"
                        )
                        or [None]
                    )[0],
                "today_low_c":
                    (
                        daily.get(
                            "temperature_2m_min"
                        )
                        or [None]
                    )[0],
                "precip_probability_pct":
                    (
                        daily.get(
                            "precipitation_probability_max"
                        )
                        or [None]
                    )[0],
            }
        )

    return rows


def get_live_country_field():
    """
    Build current country-level map values.

    Important interpretation:
    each value is current weather at a representative point for that country.
    It is not a national-area average.
    """
    catalog = get_country_catalog()

    rows = []

    chunk_size = 55

    for start in range(
        0,
        len(catalog),
        chunk_size,
    ):
        chunk = catalog.iloc[
            start:
            start + chunk_size
        ].copy()

        rows.extend(
            _request_weather_chunk(
                chunk
            )
        )

    frame = pd.DataFrame(
        rows
    )

    numeric = [
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
    ]

    for column in numeric:
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

    return frame