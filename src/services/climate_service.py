import threading
import time
from concurrent.futures import ThreadPoolExecutor

from src.api.weather import (
    HistoricalWeatherRateLimitError,
    HistoricalWeatherUnavailableError,
    get_historical_weather,
)
from src.db import (
    city_has_complete_history,
    get_existing_history_years,
    insert_weather_daily,
    upsert_city,
)
from src.observability import observe_operation


HISTORY_START_YEAR = 1990
HISTORY_END_YEAR = 2025

# One worker deliberately serializes new-city history jobs.
# Existing-city reads remain fast from PostgreSQL.
_executor = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="climate-history",
)

_jobs_lock = threading.Lock()
_jobs = {}


def _new_job_state(
    city_id,
    location,
):
    return {
        "city_id": city_id,
        "location_name": location.get(
            "name",
            "Selected location",
        ),
        "status": "queued",
        "completed_years": 0,
        "total_years": (
            HISTORY_END_YEAR
            - HISTORY_START_YEAR
            + 1
        ),
        "current_year": None,
        "message": (
            "Historical climate is queued."
        ),
        "error": None,
    }


def _update_job(
    city_id,
    **changes,
):
    with _jobs_lock:
        if city_id not in _jobs:
            return

        _jobs[city_id].update(
            changes
        )


def get_history_job_status(
    city_id,
):
    if city_has_complete_history(
        city_id
    ):
        return {
            "city_id": city_id,
            "status": "ready",
            "completed_years": (
                HISTORY_END_YEAR
                - HISTORY_START_YEAR
                + 1
            ),
            "total_years": (
                HISTORY_END_YEAR
                - HISTORY_START_YEAR
                + 1
            ),
            "current_year": None,
            "message": (
                "Historical climate is ready."
            ),
            "error": None,
        }

    with _jobs_lock:
        job = _jobs.get(
            city_id
        )

        if job:
            return dict(
                job
            )

    existing_years = (
        get_existing_history_years(
            city_id
        )
    )

    completed = len(
        [
            year
            for year in existing_years
            if (
                HISTORY_START_YEAR
                <= year
                <= HISTORY_END_YEAR
            )
        ]
    )

    return {
        "city_id": city_id,
        "status": (
            "partial"
            if completed
            else "not_started"
        ),
        "completed_years": completed,
        "total_years": (
            HISTORY_END_YEAR
            - HISTORY_START_YEAR
            + 1
        ),
        "current_year": None,
        "message": (
            "Historical climate has not finished importing."
        ),
        "error": None,
    }


def _download_history_job(
    city_id,
    location,
):
    try:
        existing_years = (
            get_existing_history_years(
                city_id
            )
        )

        missing_years = [
            year
            for year in range(
                HISTORY_START_YEAR,
                HISTORY_END_YEAR + 1,
            )
            if year not in existing_years
        ]

        completed = (
            (
                HISTORY_END_YEAR
                - HISTORY_START_YEAR
                + 1
            )
            - len(missing_years)
        )

        _update_job(
            city_id,
            status="running",
            completed_years=completed,
            message=(
                "Preparing historical climate in the background."
            ),
        )

        for year in missing_years:

            _update_job(
                city_id,
                status="running",
                current_year=year,
                message=(
                    f"Importing ERA5 history: {year}"
                ),
            )

            attempts = 0

            while True:
                attempts += 1

                try:
                    weather = (
                        get_historical_weather(
                            latitude=location[
                                "latitude"
                            ],
                            longitude=location[
                                "longitude"
                            ],
                            start_date=(
                                f"{year}-01-01"
                            ),
                            end_date=(
                                f"{year}-12-31"
                            ),
                            timezone=location.get(
                                "timezone",
                                "auto",
                            ),
                        )
                    )

                    insert_weather_daily(
                        city_id,
                        weather,
                    )

                    completed += 1

                    _update_job(
                        city_id,
                        status="running",
                        completed_years=completed,
                        current_year=year,
                        message=(
                            f"Historical climate: "
                            f"{completed}/"
                            f"{HISTORY_END_YEAR - HISTORY_START_YEAR + 1} "
                            f"years stored"
                        ),
                    )

                    break

                except HistoricalWeatherRateLimitError as error:
                    if attempts >= 5:
                        _update_job(
                            city_id,
                            status="waiting",
                            current_year=year,
                            message=(
                                "Historical provider is busy. "
                                "The background import will resume "
                                "when this location is requested again."
                            ),
                        )
                        return

                    wait_seconds = (
                        error.retry_after_seconds
                        or 45
                    )

                    _update_job(
                        city_id,
                        status="waiting",
                        current_year=year,
                        message=(
                            "Historical provider is busy; "
                            f"retrying in about "
                            f"{int(wait_seconds)} seconds."
                        ),
                    )

                    time.sleep(
                        wait_seconds
                    )

                    _update_job(
                        city_id,
                        status="running",
                    )

                except HistoricalWeatherUnavailableError:
                    if attempts >= 3:
                        _update_job(
                            city_id,
                            status="paused",
                            current_year=year,
                            message=(
                                "Historical import paused temporarily. "
                                "Live conditions remain available."
                            ),
                        )
                        return

                    time.sleep(
                        min(
                            10 * attempts,
                            30,
                        )
                    )

        if city_has_complete_history(
            city_id
        ):
            _update_job(
                city_id,
                status="ready",
                completed_years=(
                    HISTORY_END_YEAR
                    - HISTORY_START_YEAR
                    + 1
                ),
                current_year=None,
                message=(
                    "Historical climate is ready."
                ),
            )

        else:
            _update_job(
                city_id,
                status="partial",
                current_year=None,
                message=(
                    "Historical climate is partially stored."
                ),
            )

    except Exception as error:
        _update_job(
            city_id,
            status="error",
            current_year=None,
            error=str(error),
            message=(
                "Historical import stopped unexpectedly."
            ),
        )


@observe_operation("era5_history_pipeline", quality_source="ERA5 History")
def ensure_city_history(
    location,
):
    """
    Upsert the selected location and return immediately.

    Complete history:
        returns ready.

    Missing history:
        starts/resumes one background import and returns
        loading instead of blocking the Streamlit request.
    """
    city_id = upsert_city(
        location
    )

    if city_has_complete_history(
        city_id
    ):
        return {
            "city_id": city_id,
            "downloaded": False,
            "records_saved": 0,
            "history_status": "ready",
        }

    with _jobs_lock:
        existing_job = _jobs.get(
            city_id
        )

        running = (
            existing_job
            and existing_job.get(
                "status"
            )
            in {
                "queued",
                "running",
                "waiting",
            }
        )

        if not running:
            _jobs[city_id] = (
                _new_job_state(
                    city_id,
                    location,
                )
            )

            _executor.submit(
                _download_history_job,
                city_id,
                dict(location),
            )

    return {
        "city_id": city_id,
        "downloaded": False,
        "records_saved": 0,
        "history_status": "loading",
    }
