from __future__ import annotations

from datetime import datetime, timezone
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

# Keep the URL comfortably below common proxy/server limits.
COUNTRY_CHUNK_SIZE = 55

# This is deliberately NOT an aggressive retry client.
# A 429 means the provider is asking us to slow down; retry storms make it worse.
REQUEST_TIMEOUT_SECONDS = 75


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


class OpenMeteoRateLimitError(RuntimeError):
    """Raised when Open-Meteo responds with HTTP 429."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


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

    These are representative country points for live weather lookup.
    They are NOT national spatial-average weather values.
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


def _coordinate_params(frame):
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

    return latitudes, longitudes


def _open_meteo_json(params):
    """
    Make one Open-Meteo request.

    Important:
    - HTTP 429 is NOT retried automatically.
    - The Streamlit layer keeps a last-known-good snapshot and controls
      the refresh cadence instead.
    """
    response = requests.get(
        OPEN_METEO_URL,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": "ClimatePulse/1.0"
        },
    )

    if response.status_code == 429:
        retry_after = response.headers.get(
            "Retry-After"
        )

        raise OpenMeteoRateLimitError(
            (
                "Open-Meteo rate limit reached (HTTP 429). "
                "ClimatePulse will keep the last successful country snapshot "
                "when one is available and will wait for the normal cache "
                "refresh interval before requesting the provider again."
            ),
            retry_after=retry_after,
        )

    response.raise_for_status()

    return response.json()


def _normalise_multi_location_payload(
    payload,
    expected_count,
):
    """
    Open-Meteo returns a list for multiple coordinates and a dict for one.
    Validate the response length so countries cannot silently receive another
    country's weather after an upstream/response-shape problem.
    """
    if isinstance(
        payload,
        dict,
    ):
        payload = [
            payload
        ]

    if not isinstance(
        payload,
        list,
    ):
        raise RuntimeError(
            "Unexpected Open-Meteo multi-location response format."
        )

    if len(payload) != int(
        expected_count
    ):
        raise RuntimeError(
            (
                "Open-Meteo returned a different number of locations "
                f"than requested ({len(payload)} returned, "
                f"{expected_count} requested)."
            )
        )

    return payload


# =========================================================
# FAST-CHANGING CURRENT CONDITIONS
# =========================================================

def _request_current_chunk(
    frame,
):
    latitudes, longitudes = (
        _coordinate_params(
            frame
        )
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
    }

    payload = _open_meteo_json(
        params
    )

    payload = (
        _normalise_multi_location_payload(
            payload,
            len(frame),
        )
    )

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

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

                "current_source_time":
                    current.get(
                        "time"
                    ),

                "current_fetched_at_utc":
                    fetched_at,
            }
        )

    return rows


def get_live_country_current():
    """
    Fetch current representative-point weather for every country.

    All current variables from the previous ClimatePulse implementation are
    retained. The only change is that they are fetched independently from the
    slower 24-hour/daily context so each group can use an appropriate cache.
    """
    catalog = get_country_catalog()

    rows = []

    for start in range(
        0,
        len(catalog),
        COUNTRY_CHUNK_SIZE,
    ):
        chunk = catalog.iloc[
            start:
            start + COUNTRY_CHUNK_SIZE
        ].copy()

        rows.extend(
            _request_current_chunk(
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
    ]

    for column in numeric:
        if column in frame.columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            )

    return frame


# =========================================================
# SLOWER 24-HOUR + DAILY CONTEXT
# =========================================================

def _request_context_chunk(
    frame,
):
    latitudes, longitudes = (
        _coordinate_params(
            frame
        )
    )

    # Same scientific fields as the previous implementation:
    # - hourly temperature for the previous 24 h + one current/forecast hour
    # - today's max/min temperature
    # - today's maximum precipitation probability
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "timezone": "GMT",
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

    payload = _open_meteo_json(
        params
    )

    payload = (
        _normalise_multi_location_payload(
            payload,
            len(frame),
        )
    )

    fetched_at = datetime.now(
        timezone.utc
    ).isoformat()

    rows = []

    for (
        _,
        country_row,
    ), item in zip(
        frame.iterrows(),
        payload,
    ):
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

        rows.append(
            {
                "cca2":
                    country_row.get(
                        "cca2"
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

                "context_fetched_at_utc":
                    fetched_at,
            }
        )

    return rows


def get_live_country_context():
    """
    Fetch the 24-hour and daily context used by the globe.

    No data field is removed:
    - 24 h temperature change
    - today's high
    - today's low
    - maximum precipitation probability
    """
    catalog = get_country_catalog()

    rows = []

    for start in range(
        0,
        len(catalog),
        COUNTRY_CHUNK_SIZE,
    ):
        chunk = catalog.iloc[
            start:
            start + COUNTRY_CHUNK_SIZE
        ].copy()

        rows.extend(
            _request_context_chunk(
                chunk
            )
        )

    frame = pd.DataFrame(
        rows
    )

    numeric = [
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


# =========================================================
# FULL RICH DATASET
# =========================================================

def merge_live_country_field(
    current_frame,
    context_frame,
):
    """
    Reconstruct the exact rich dataframe expected by ClimatePulse.

    Current data are required. Context can temporarily fall back to NaN only
    when no historical last-known-good context exists yet.
    """
    if (
        current_frame is None
        or current_frame.empty
    ):
        return pd.DataFrame()

    result = current_frame.copy()

    context_columns = [
        "temperature_change_24h_c",
        "today_high_c",
        "today_low_c",
        "precip_probability_pct",
        "context_fetched_at_utc",
    ]

    if (
        context_frame is None
        or context_frame.empty
    ):
        for column in context_columns:
            result[column] = None

        return result

    available_context = [
        "cca2",
        *[
            column
            for column in context_columns
            if column
            in context_frame.columns
        ],
    ]

    return result.merge(
        context_frame[
            available_context
        ],
        on="cca2",
        how="left",
        validate="one_to_one",
    )


def get_live_country_field():
    """
    Backwards-compatible full fetch.

    Existing imports elsewhere in ClimatePulse will keep working. The
    production globe itself uses separate Streamlit caches for current and
    context data so this function normally is not called on every rerun.
    """
    current = (
        get_live_country_current()
    )

    context = (
        get_live_country_context()
    )

    return merge_live_country_field(
        current,
        context,
    )