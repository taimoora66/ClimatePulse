import os
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests


ARCHIVE_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)

REQUEST_TIMEOUT_SECONDS = float(
    os.getenv(
        "OPEN_METEO_ARCHIVE_TIMEOUT_SECONDS",
        "75",
    )
)

# A one-year archive request is still a weighted Open-Meteo call.
# Keeping requests several seconds apart prevents a new city from
# generating a burst of expensive historical requests.
MIN_SECONDS_BETWEEN_ARCHIVE_REQUESTS = float(
    os.getenv(
        "OPEN_METEO_ARCHIVE_MIN_INTERVAL_SECONDS",
        "3.2",
    )
)

DEFAULT_RETRY_AFTER_SECONDS = float(
    os.getenv(
        "OPEN_METEO_ARCHIVE_DEFAULT_RETRY_AFTER_SECONDS",
        "45",
    )
)

MAX_RETRY_AFTER_SECONDS = float(
    os.getenv(
        "OPEN_METEO_ARCHIVE_MAX_RETRY_AFTER_SECONDS",
        "180",
    )
)


class HistoricalWeatherError(
    RuntimeError
):
    pass


class HistoricalWeatherRateLimitError(
    HistoricalWeatherError
):
    def __init__(
        self,
        message=(
            "Historical climate service is temporarily busy."
        ),
        retry_after_seconds=None,
    ):
        super().__init__(message)

        self.retry_after_seconds = (
            retry_after_seconds
        )


class HistoricalWeatherUnavailableError(
    HistoricalWeatherError
):
    pass


_request_lock = threading.Lock()
_last_request_started_at = 0.0


def _parse_retry_after(
    response,
):
    value = response.headers.get(
        "Retry-After"
    )

    if not value:
        return None

    try:
        return max(
            0.0,
            float(value),
        )
    except (TypeError, ValueError):
        pass

    try:
        retry_time = parsedate_to_datetime(
            value
        )

        if retry_time.tzinfo is None:
            retry_time = retry_time.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        return max(
            0.0,
            (
                retry_time.astimezone(
                    timezone.utc
                )
                - now
            ).total_seconds(),
        )

    except Exception:
        return None


def _wait_for_request_slot():
    global _last_request_started_at

    elapsed = (
        time.monotonic()
        - _last_request_started_at
    )

    wait_seconds = max(
        0.0,
        (
            MIN_SECONDS_BETWEEN_ARCHIVE_REQUESTS
            - elapsed
        ),
    )

    if wait_seconds:
        time.sleep(
            wait_seconds
        )

    _last_request_started_at = (
        time.monotonic()
    )


def get_historical_weather(
    latitude,
    longitude,
    start_date,
    end_date,
    timezone="auto",
):
    """
    Fetch a bounded ERA5 daily interval.

    The production service calls this one calendar year at
    a time. This avoids one enormous 1990-2025 request and
    lets interrupted imports resume from PostgreSQL.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ],
        "timezone": timezone,
        "models": "era5",
    }

    with _request_lock:
        _wait_for_request_slot()

        try:
            response = requests.get(
                ARCHIVE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

        except requests.RequestException as error:
            raise HistoricalWeatherUnavailableError(
                "Historical climate service could not be reached."
            ) from error

    if response.status_code == 429:
        retry_after = _parse_retry_after(
            response
        )

        if retry_after is None:
            retry_after = (
                DEFAULT_RETRY_AFTER_SECONDS
            )

        retry_after = min(
            max(
                retry_after,
                5.0,
            ),
            MAX_RETRY_AFTER_SECONDS,
        )

        raise HistoricalWeatherRateLimitError(
            retry_after_seconds=retry_after
        )

    if response.status_code >= 500:
        raise HistoricalWeatherUnavailableError(
            "Historical climate service is temporarily unavailable."
        )

    if not response.ok:
        raise HistoricalWeatherUnavailableError(
            "Historical climate data could not be retrieved."
        )

    try:
        data = response.json()

    except ValueError as error:
        raise HistoricalWeatherUnavailableError(
            "Historical climate service returned an invalid response."
        ) from error

    if not data.get("daily"):
        raise HistoricalWeatherUnavailableError(
            "Historical climate data are unavailable for this interval."
        )

    return data