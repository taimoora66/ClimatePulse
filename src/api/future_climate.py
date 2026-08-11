import statistics
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

import pandas as pd
import requests


CLIMATE_URL = (
    "https://climate-api.open-meteo.com/v1/climate"
)

CLIMATE_MODELS = (
    "CMCC_CM2_VHR4",
    "FGOALS_f3_H",
    "HiRAM_SIT_HR",
    "MRI_AGCM3_2_S",
    "EC_Earth3P_HR",
    "MPI_ESM1_2_XR",
    "NICAM16_8S",
)


def _request_one_model(
    latitude,
    longitude,
    model,
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": "2041-01-01",
        "end_date": "2049-12-31",
        "models": model,
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "precipitation_sum",
        ],
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
        "cell_selection": "land",
    }

    last_error = None

    for attempt in range(3):
        try:
            response = requests.get(
                CLIMATE_URL,
                params=params,
                timeout=50,
            )

            if response.status_code == 429:
                last_error = RuntimeError(
                    "Climate API rate limit reached."
                )
                if attempt < 2:
                    time.sleep(
                        3 * (
                            attempt + 1
                        )
                    )
                    continue

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            last_error = error
            if attempt < 2:
                time.sleep(
                    2 ** attempt
                )

    raise RuntimeError(
        f"Unable to retrieve climate model {model}."
    ) from last_error


def _summarize_model(
    model,
    payload,
):
    daily = payload.get(
        "daily",
        {}
    )

    dates = daily.get("time", [])
    temp_mean = daily.get(
        "temperature_2m_mean",
        [],
    )
    temp_max = daily.get(
        "temperature_2m_max",
        [],
    )
    precip = daily.get(
        "precipitation_sum",
        [],
    )

    lengths = [
        len(dates),
        len(temp_mean),
        len(temp_max),
        len(precip),
    ]

    if min(lengths) == 0:
        return None

    n = min(lengths)

    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                dates[:n],
                errors="coerce",
            ),
            "temperature_mean_c": pd.to_numeric(
                temp_mean[:n],
                errors="coerce",
            ),
            "temperature_max_c": pd.to_numeric(
                temp_max[:n],
                errors="coerce",
            ),
            "precipitation_mm": pd.to_numeric(
                precip[:n],
                errors="coerce",
            ),
        }
    ).dropna(
        subset=["date"]
    )

    if frame.empty:
        return None

    frame["year"] = (
        frame["date"].dt.year
    )
    frame["hot30"] = (
        frame["temperature_max_c"]
        >= 30.0
    ).astype(int)

    annual = (
        frame
        .groupby(
            "year",
            as_index=False,
        )
        .agg(
            annual_mean_temperature_c=(
                "temperature_mean_c",
                "mean",
            ),
            annual_precipitation_mm=(
                "precipitation_mm",
                "sum",
            ),
            hot_days_30c=(
                "hot30",
                "sum",
            ),
        )
    )

    if annual.empty:
        return None

    return {
        "model": model,
        "period": "2041-2049",
        "future_mean_temperature_c": float(
            annual[
                "annual_mean_temperature_c"
            ].mean()
        ),
        "future_annual_precipitation_mm": float(
            annual[
                "annual_precipitation_mm"
            ].mean()
        ),
        "future_hot_days_30c_per_year": float(
            annual[
                "hot_days_30c"
            ].mean()
        ),
        "years": int(
            len(annual)
        ),
    }


def _clean_values(
    values,
):
    return [
        float(value)
        for value in values
        if value is not None
    ]


def _median(values):
    clean = _clean_values(values)
    return (
        float(statistics.median(clean))
        if clean
        else None
    )


def _minimum(values):
    clean = _clean_values(values)
    return (
        min(clean)
        if clean
        else None
    )


def _maximum(values):
    clean = _clean_values(values)
    return (
        max(clean)
        if clean
        else None
    )


def _agreement_label(
    values,
    relative=False,
):
    clean = _clean_values(values)

    if len(clean) < 2:
        return "Insufficient"

    mean_value = statistics.mean(
        clean
    )
    spread = max(clean) - min(clean)

    if relative:
        denominator = max(
            abs(mean_value),
            1e-6,
        )
        ratio = spread / denominator

        if ratio <= 0.15:
            return "High"
        if ratio <= 0.35:
            return "Moderate"
        return "Low"

    if spread <= 1.0:
        return "High"
    if spread <= 2.0:
        return "Moderate"
    return "Low"


def get_midcentury_ensemble(
    latitude,
    longitude,
    model_names=None,
):
    """
    Summarize a 2041–2049 CMIP6 HighResMIP multi-model
    ensemble.

    The returned min/median/max values describe MODEL SPREAD,
    not emissions scenarios.
    """
    requested_models = tuple(
        model_names
        or CLIMATE_MODELS
    )

    requested_models = tuple(
        model
        for model in requested_models
        if model in CLIMATE_MODELS
    )

    if not requested_models:
        return {}

    model_results = []

    # Keep concurrency intentionally low because climate
    # requests are heavier than live-weather calls.
    with ThreadPoolExecutor(
        max_workers=min(
            2,
            len(requested_models),
        )
    ) as executor:

        futures = {
            executor.submit(
                _request_one_model,
                latitude,
                longitude,
                model,
            ): model
            for model in requested_models
        }

        for future in as_completed(
            futures
        ):
            model = futures[future]

            try:
                payload = future.result()
                result = _summarize_model(
                    model,
                    payload,
                )
                if result:
                    model_results.append(
                        result
                    )
            except Exception:
                # Partial ensembles remain visible, with the
                # returned model count shown in the interface.
                continue

    model_results.sort(
        key=lambda row: row["model"]
    )

    if not model_results:
        return {}

    temperatures = [
        row["future_mean_temperature_c"]
        for row in model_results
    ]
    hot_days = [
        row["future_hot_days_30c_per_year"]
        for row in model_results
    ]
    precipitation = [
        row["future_annual_precipitation_mm"]
        for row in model_results
    ]

    return {
        "period": "2041-2049",
        "model_count": len(model_results),
        "requested_model_count": len(
            requested_models
        ),
        "models": model_results,

        "temperature_median_c": _median(
            temperatures
        ),
        "temperature_min_c": _minimum(
            temperatures
        ),
        "temperature_max_c": _maximum(
            temperatures
        ),

        "hot_days_30c_median": _median(
            hot_days
        ),
        "hot_days_30c_min": _minimum(
            hot_days
        ),
        "hot_days_30c_max": _maximum(
            hot_days
        ),

        "precipitation_median_mm": _median(
            precipitation
        ),
        "precipitation_min_mm": _minimum(
            precipitation
        ),
        "precipitation_max_mm": _maximum(
            precipitation
        ),

        "temperature_agreement": _agreement_label(
            temperatures,
            relative=False,
        ),
        "hot_days_agreement": _agreement_label(
            hot_days,
            relative=True,
        ),
        "precipitation_agreement": _agreement_label(
            precipitation,
            relative=True,
        ),

        "source": (
            "Open-Meteo Climate API / CMIP6 HighResMIP"
        ),
        "ensemble_type": "multi-model spread",
    }