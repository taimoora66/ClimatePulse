import math
from typing import Any

import numpy as np
import pandas as pd
import requests


CCKP_API_BASES = (
    "https://cckpapi.worldbank.org/api/v1",
    "https://cckpapi.worldbank.org/cckp/v1",
)

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
        number = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(
        number
    ):
        return None

    return number


def _request_dataset(
    dataset_candidates: tuple[str, ...],
    geocode: str,
) -> tuple[Any, str]:
    errors = []

    for dataset in dataset_candidates:
        for base in CCKP_API_BASES:
            url = (
                f"{base}/"
                f"{dataset}/"
                f"{geocode}"
            )

            try:
                response = requests.get(
                    url,
                    params={
                        "_format": "json",
                    },
                    timeout=45,
                    headers={
                        "User-Agent": (
                            "ClimatePulse/1.0 "
                            "(public climate-data dashboard)"
                        )
                    },
                )

                response.raise_for_status()

                payload = response.json()

                if payload not in (
                    None,
                    {},
                    [],
                ):
                    return payload, url

            except Exception as exc:
                errors.append(
                    f"{url}: {exc}"
                )

    raise RuntimeError(
        "No usable historical country climate response. "
        + " | ".join(
            errors[-4:]
        )
    )


def _year_token(
    value: Any,
) -> int | None:
    try:
        year = int(
            str(
                value
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if 1901 <= year <= 2024:
        return year

    return None


def _flatten_scalars(
    obj: Any,
    path: tuple[Any, ...] = (),
) -> list[
    tuple[
        tuple[Any, ...],
        Any,
    ]
]:
    values = []

    if isinstance(
        obj,
        dict,
    ):
        for key, value in obj.items():
            values.extend(
                _flatten_scalars(
                    value,
                    path
                    + (
                        key,
                    ),
                )
            )
        return values

    if isinstance(
        obj,
        list,
    ):
        for index, value in enumerate(
            obj
        ):
            values.extend(
                _flatten_scalars(
                    value,
                    path
                    + (
                        index,
                    ),
                )
            )
        return values

    values.append(
        (
            path,
            obj,
        )
    )

    return values


def _extract_year_series(
    payload: Any,
    column_name: str,
) -> pd.DataFrame:
    observations = []

    # Form A: year encoded somewhere in the nested path.
    for path, raw in _flatten_scalars(
        payload
    ):
        number = _finite(
            raw
        )

        if number is None:
            continue

        year = None

        for token in reversed(
            path
        ):
            year = _year_token(
                token
            )
            if year is not None:
                break

        if year is not None:
            observations.append(
                (
                    year,
                    number,
                )
            )

    # Form B: record dictionaries with explicit year/value fields.
    def walk_records(
        obj: Any,
    ):
        if isinstance(
            obj,
            dict,
        ):
            lowered = {
                str(k).lower(): v
                for k, v in obj.items()
            }

            year = None

            for key in (
                "year",
                "time",
                "date",
                "period",
            ):
                if key in lowered:
                    raw_year = str(
                        lowered[
                            key
                        ]
                    )[:4]
                    year = _year_token(
                        raw_year
                    )
                    if year is not None:
                        break

            if year is not None:
                for key in (
                    "value",
                    "mean",
                    "tas",
                    "pr",
                    "data",
                ):
                    if key in lowered:
                        number = _finite(
                            lowered[
                                key
                            ]
                        )
                        if number is not None:
                            observations.append(
                                (
                                    year,
                                    number,
                                )
                            )
                            break

            for value in obj.values():
                walk_records(
                    value
                )

        elif isinstance(
            obj,
            list,
        ):
            for value in obj:
                walk_records(
                    value
                )

    walk_records(
        payload
    )

    if not observations:
        return pd.DataFrame(
            columns=[
                "year",
                column_name,
            ]
        )

    frame = pd.DataFrame(
        observations,
        columns=[
            "year",
            column_name,
        ],
    )

    # Exact duplicates/nested repeats are common in API envelopes.
    frame = (
        frame
        .groupby(
            "year",
            as_index=False,
        )[
            column_name
        ]
        .median()
        .sort_values(
            "year"
        )
        .reset_index(
            drop=True
        )
    )

    return frame


def _trend_per_decade(
    frame: pd.DataFrame,
) -> float | None:
    subset = (
        frame[
            (
                frame[
                    "year"
                ] >= 1971
            )
            &
            (
                frame[
                    "year"
                ] <= 2024
            )
        ]
        .dropna(
            subset=[
                "mean_temperature_c",
            ]
        )
    )

    if len(
        subset
    ) < 20:
        return None

    slope = np.polyfit(
        subset[
            "year"
        ].to_numpy(
            dtype=float
        ),
        subset[
            "mean_temperature_c"
        ].to_numpy(
            dtype=float
        ),
        1,
    )[0]

    return float(
        slope
        * 10.0
    )


def get_country_historical_climate(
    iso3_code: str,
) -> pd.DataFrame:
    """
    National spatial-average annual climate from World Bank
    CCKP / CRU.

    Current CRU TS4.09 is attempted first; the previous TS4.08
    endpoint is retained as a compatibility fallback.
    """
    iso3 = str(
        iso3_code
    ).strip().upper()

    tas_payload, tas_url = _request_dataset(
        TAS_DATASETS,
        iso3,
    )

    pr_payload, pr_url = _request_dataset(
        PR_DATASETS,
        iso3,
    )

    temperature = _extract_year_series(
        tas_payload,
        "mean_temperature_c",
    )

    precipitation = _extract_year_series(
        pr_payload,
        "annual_precipitation_mm",
    )

    frame = temperature.merge(
        precipitation,
        on="year",
        how="outer",
    )

    frame = (
        frame
        .sort_values(
            "year"
        )
        .reset_index(
            drop=True
        )
    )

    if frame.empty:
        return frame

    # Physical sanity checks only.
    frame.loc[
        (
            frame[
                "mean_temperature_c"
            ]
            < -70
        )
        |
        (
            frame[
                "mean_temperature_c"
            ]
            > 60
        ),
        "mean_temperature_c",
    ] = np.nan

    frame.loc[
        (
            frame[
                "annual_precipitation_mm"
            ]
            < 0
        )
        |
        (
            frame[
                "annual_precipitation_mm"
            ]
            > 15000
        ),
        "annual_precipitation_mm",
    ] = np.nan

    frame.attrs[
        "iso3"
    ] = iso3

    frame.attrs[
        "temperature_source_url"
    ] = tas_url

    frame.attrs[
        "precipitation_source_url"
    ] = pr_url

    frame.attrs[
        "warming_rate_c_per_decade"
    ] = _trend_per_decade(
        frame
    )

    valid_temp = frame.dropna(
        subset=[
            "mean_temperature_c",
        ]
    )

    valid_pr = frame.dropna(
        subset=[
            "annual_precipitation_mm",
        ]
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

        frame.attrs[
            "warmest_year"
        ] = int(
            warmest[
                "year"
            ]
        )
        frame.attrs[
            "warmest_temperature_c"
        ] = float(
            warmest[
                "mean_temperature_c"
            ]
        )
        frame.attrs[
            "coolest_year"
        ] = int(
            coolest[
                "year"
            ]
        )
        frame.attrs[
            "coolest_temperature_c"
        ] = float(
            coolest[
                "mean_temperature_c"
            ]
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

        frame.attrs[
            "wettest_year"
        ] = int(
            wettest[
                "year"
            ]
        )
        frame.attrs[
            "wettest_precipitation_mm"
        ] = float(
            wettest[
                "annual_precipitation_mm"
            ]
        )
        frame.attrs[
            "driest_year"
        ] = int(
            driest[
                "year"
            ]
        )
        frame.attrs[
            "driest_precipitation_mm"
        ] = float(
            driest[
                "annual_precipitation_mm"
            ]
        )

    return frame