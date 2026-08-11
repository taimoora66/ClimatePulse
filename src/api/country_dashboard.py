import math
from typing import Any

import numpy as np
import pandas as pd
import pycountry
import requests


# World Bank CCKP currently exposes spatial aggregates through API routes.
# The current /api/v1 route is attempted first; /cckp/v1 remains as a
# compatibility fallback because both forms appear in World Bank material.
CCKP_API_BASES = (
    "https://cckpapi.worldbank.org/api/v1",
    "https://cckpapi.worldbank.org/cckp/v1",
)

GLOBAL_AGGREGATE_GEOCODE = "global_countries_subnationals"

# Confirmed current CRU naming used by World Bank material.
TAS_DATASETS = (
    "cru-x0.5_timeseries_tas_timeseries_annual_1901-2024_mean_historical_cru_ts4.09_mean",
    "cru-x0.5_timeseries_tas_timeseries_annual_1901-2023_mean_historical_cru_ts4.08_mean",
)

PR_DATASETS = (
    "cru-x0.5_timeseries_pr_timeseries_annual_1901-2024_mean_historical_cru_ts4.09_mean",
    "cru-x0.5_timeseries_pr_timeseries_annual_1901-2023_mean_historical_cru_ts4.08_mean",
)


def _finite(
    value: Any,
) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def _country_name(
    iso3: str,
) -> str:
    try:
        country = pycountry.countries.get(
            alpha_3=iso3.upper()
        )
        if country:
            return country.name
    except Exception:
        pass

    return iso3.upper()


def _request_global_dataset(
    dataset_candidates: tuple[str, ...],
) -> tuple[Any, str]:
    """
    Request CCKP's global country/subnational aggregate once.

    This is more reliable than constructing undocumented country-specific
    aggregate URLs. The returned object is filtered to the requested ISO3
    after parsing.
    """
    errors: list[str] = []

    for dataset in dataset_candidates:
        for base in CCKP_API_BASES:
            url = (
                f"{base}/"
                f"{dataset}/"
                f"{GLOBAL_AGGREGATE_GEOCODE}"
            )

            try:
                response = requests.get(
                    url,
                    params={"_format": "json"},
                    timeout=60,
                    headers={
                        "User-Agent": (
                            "ClimatePulse/1.0 "
                            "(climate intelligence dashboard)"
                        )
                    },
                )

                response.raise_for_status()
                payload = response.json()

                if payload not in (None, {}, []):
                    return payload, response.url

                errors.append(
                    f"{response.url}: empty response"
                )

            except Exception as exc:
                errors.append(
                    f"{url}: {type(exc).__name__}: {exc}"
                )

    raise RuntimeError(
        "World Bank CCKP did not return a usable national aggregate. "
        + " | ".join(errors[-4:])
    )


def _walk(
    obj: Any,
    path: tuple[Any, ...] = (),
):
    """
    Yield every scalar and every dictionary from arbitrary JSON.

    CCKP API envelopes have changed over time, so the parser avoids
    depending on one exact top-level structure.
    """
    if isinstance(obj, dict):
        yield ("dict", path, obj)

        for key, value in obj.items():
            yield from _walk(
                value,
                path + (key,),
            )

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk(
                value,
                path + (index,),
            )

    else:
        yield ("scalar", path, obj)


def _year_from_any(
    value: Any,
) -> int | None:
    text = str(value)

    # Covers "1991", "1991-01-01", etc.
    if len(text) >= 4:
        try:
            year = int(text[:4])
            if 1901 <= year <= 2024:
                return year
        except ValueError:
            pass

    return None


def _iso3_from_any(
    value: Any,
) -> str | None:
    text = str(value).strip().upper()

    if (
        len(text) == 3
        and text.isalpha()
        and pycountry.countries.get(alpha_3=text)
    ):
        return text

    return None


def _dict_lookup(
    record: dict[str, Any],
    candidates: tuple[str, ...],
):
    lookup = {
        str(key).lower(): value
        for key, value in record.items()
    }

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def _record_iso3(
    record: dict[str, Any],
    path: tuple[Any, ...],
) -> str | None:
    direct = _dict_lookup(
        record,
        (
            "iso3",
            "iso_3",
            "country_code",
            "countrycode",
            "adm0_a3",
            "geocode",
            "code",
        ),
    )

    iso3 = _iso3_from_any(direct)

    if iso3:
        return iso3

    # Many aggregate payloads are keyed by country code.
    for token in reversed(path):
        iso3 = _iso3_from_any(token)
        if iso3:
            return iso3

    return None


def _record_year(
    record: dict[str, Any],
    path: tuple[Any, ...],
) -> int | None:
    direct = _dict_lookup(
        record,
        (
            "year",
            "time",
            "date",
            "period",
        ),
    )

    year = _year_from_any(direct)

    if year:
        return year

    for token in reversed(path):
        year = _year_from_any(token)
        if year:
            return year

    return None


def _record_value(
    record: dict[str, Any],
    variable_code: str,
) -> float | None:
    candidates = (
        variable_code,
        "value",
        "mean",
        "data",
        "annual",
        "timeseries",
    )

    direct = _dict_lookup(
        record,
        candidates,
    )

    number = _finite(direct)

    if number is not None:
        return number

    # A dictionary can contain a single unexpected numeric field.
    numeric = []

    for key, raw in record.items():
        key_lower = str(key).lower()

        if any(
            token in key_lower
            for token in (
                "lat",
                "lon",
                "id",
                "year",
                "time",
                "area",
                "population",
            )
        ):
            continue

        value = _finite(raw)

        if value is not None:
            numeric.append(value)

    if len(numeric) == 1:
        return numeric[0]

    return None


def _extract_country_timeseries(
    payload: Any,
    iso3: str,
    variable_code: str,
    output_column: str,
) -> pd.DataFrame:
    """
    Extract annual national series for one ISO3 from a global CCKP
    aggregate response.
    """
    iso3 = iso3.upper()
    rows: list[tuple[int, float]] = []

    # Record-oriented extraction.
    for kind, path, item in _walk(payload):
        if kind != "dict":
            continue

        record = item

        record_iso3 = _record_iso3(
            record,
            path,
        )

        if record_iso3 != iso3:
            continue

        year = _record_year(
            record,
            path,
        )

        value = _record_value(
            record,
            variable_code,
        )

        if (
            year is not None
            and value is not None
        ):
            rows.append(
                (year, value)
            )

    # Scalar-oriented extraction for payloads shaped like:
    # {"FRA": {"1901": 12.3, ...}}
    if not rows:
        for kind, path, raw in _walk(payload):
            if kind != "scalar":
                continue

            path_iso3 = None
            path_year = None

            for token in path:
                if path_iso3 is None:
                    path_iso3 = _iso3_from_any(token)

                if path_year is None:
                    path_year = _year_from_any(token)

            if (
                path_iso3 != iso3
                or path_year is None
            ):
                continue

            value = _finite(raw)

            if value is not None:
                rows.append(
                    (path_year, value)
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "year",
                output_column,
            ]
        )

    frame = pd.DataFrame(
        rows,
        columns=[
            "year",
            output_column,
        ],
    )

    # Repeated nested representations are collapsed robustly.
    frame = (
        frame
        .groupby(
            "year",
            as_index=False,
        )[output_column]
        .median()
        .sort_values("year")
        .reset_index(drop=True)
    )

    return frame


def _trend_per_decade(
    frame: pd.DataFrame,
) -> float | None:
    subset = frame[
        (
            frame["year"] >= 1971
        )
        &
        (
            frame["year"] <= 2024
        )
    ].dropna(
        subset=["mean_temperature_c"]
    )

    if len(subset) < 20:
        return None

    slope = np.polyfit(
        subset["year"].astype(float),
        subset["mean_temperature_c"].astype(float),
        1,
    )[0]

    return float(slope * 10.0)


def get_country_historical_climate(
    iso3_code: str,
) -> pd.DataFrame:
    """
    National spatial-average historical climate.

    Source:
        World Bank Climate Change Knowledge Portal
        CRU country/subnational spatial aggregates.

    Strategy:
        Fetch the documented global aggregate and filter by ISO3.

    Returns:
        year
        mean_temperature_c
        annual_precipitation_mm
    """
    iso3 = str(iso3_code).strip().upper()

    tas_payload, tas_url = _request_global_dataset(
        TAS_DATASETS
    )

    pr_payload, pr_url = _request_global_dataset(
        PR_DATASETS
    )

    temperature = _extract_country_timeseries(
        tas_payload,
        iso3=iso3,
        variable_code="tas",
        output_column="mean_temperature_c",
    )

    precipitation = _extract_country_timeseries(
        pr_payload,
        iso3=iso3,
        variable_code="pr",
        output_column="annual_precipitation_mm",
    )

    frame = temperature.merge(
        precipitation,
        on="year",
        how="outer",
    )

    frame = (
        frame
        .sort_values("year")
        .reset_index(drop=True)
    )

    if frame.empty:
        raise RuntimeError(
            f"CCKP returned global aggregates but no national "
            f"time series could be extracted for {iso3} "
            f"({_country_name(iso3)})."
        )

    # Conservative physical sanity checks.
    if "mean_temperature_c" in frame.columns:
        frame.loc[
            (
                frame["mean_temperature_c"] < -70
            )
            |
            (
                frame["mean_temperature_c"] > 60
            ),
            "mean_temperature_c",
        ] = np.nan

    if "annual_precipitation_mm" in frame.columns:
        frame.loc[
            (
                frame["annual_precipitation_mm"] < 0
            )
            |
            (
                frame["annual_precipitation_mm"] > 15000
            ),
            "annual_precipitation_mm",
        ] = np.nan

    # If the API supplied no usable data after sanity filtering, fail
    # explicitly rather than rendering fake country statistics.
    if (
        frame["mean_temperature_c"].notna().sum() < 20
    ):
        raise RuntimeError(
            f"Insufficient national temperature observations "
            f"were parsed for {iso3}."
        )

    frame.attrs["iso3"] = iso3
    frame.attrs["country_name"] = _country_name(iso3)
    frame.attrs["temperature_source_url"] = tas_url
    frame.attrs["precipitation_source_url"] = pr_url
    frame.attrs[
        "warming_rate_c_per_decade"
    ] = _trend_per_decade(frame)

    valid_temp = frame.dropna(
        subset=["mean_temperature_c"]
    )

    valid_pr = frame.dropna(
        subset=["annual_precipitation_mm"]
    )

    if not valid_temp.empty:
        warmest = valid_temp.loc[
            valid_temp[
                "mean_temperature_c"
            ].idxmax()
        ]

        coolest = valid_temp.loc[
            valid_temp[
                "mean_temperature_c"
            ].idxmin()
        ]

        frame.attrs["warmest_year"] = int(
            warmest["year"]
        )
        frame.attrs[
            "warmest_temperature_c"
        ] = float(
            warmest["mean_temperature_c"]
        )

        frame.attrs["coolest_year"] = int(
            coolest["year"]
        )
        frame.attrs[
            "coolest_temperature_c"
        ] = float(
            coolest["mean_temperature_c"]
        )

    if not valid_pr.empty:
        wettest = valid_pr.loc[
            valid_pr[
                "annual_precipitation_mm"
            ].idxmax()
        ]

        driest = valid_pr.loc[
            valid_pr[
                "annual_precipitation_mm"
            ].idxmin()
        ]

        frame.attrs["wettest_year"] = int(
            wettest["year"]
        )
        frame.attrs[
            "wettest_precipitation_mm"
        ] = float(
            wettest["annual_precipitation_mm"]
        )

        frame.attrs["driest_year"] = int(
            driest["year"]
        )
        frame.attrs[
            "driest_precipitation_mm"
        ] = float(
            driest["annual_precipitation_mm"]
        )

    return frame