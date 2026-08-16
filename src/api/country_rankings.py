import streamlit as st
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
import pycountry
import requests
from src.observability import observe_operation


CCKP_API_BASES = (
    "https://cckpapi.worldbank.org/api/v1",
    "https://cckpapi.worldbank.org/cckp/v1",
)

GLOBAL_AGGREGATE_GEOCODES = (
    "global_countries_subnationals",
    "all_countries",
)

CCKP_SCENARIOS = {
    "SSP1-2.6 · Low emissions": "ssp126",
    "SSP2-4.5 · Intermediate": "ssp245",
    "SSP3-7.0 · High": "ssp370",
    "SSP5-8.5 · Very high": "ssp585",
}

CCKP_PERIODS = {
    "Near term · 2020–2039": "2020-2039",
    "Mid-century · 2040–2059": "2040-2059",
    "Late century · 2060–2079": "2060-2079",
    "End century · 2080–2099": "2080-2099",
}

_TRAJECTORY_PERIODS = tuple(
    CCKP_PERIODS.values()
)


def _finite(
    value: Any,
) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number


def _country_name(
    iso3: str,
) -> str | None:
    try:
        country = pycountry.countries.get(
            alpha_3=iso3.upper()
        )

        if country:
            return country.name
    except Exception:
        pass

    return None


def _iso3(
    value: Any,
) -> str | None:
    text = str(value).strip().upper()

    if (
        len(text) == 3
        and text.isalpha()
        and _country_name(text)
    ):
        return text

    return None


def _candidate_dataset_names(
    period: str,
    scenario: str,
    percentile: str,
) -> tuple[str, ...]:
    """
    CCKP download examples show both single-variable and grouped-variable
    climate aggregate dataset names in circulation. Try both.
    """
    return (
        (
            "cmip6-x0.25_"
            "climatology_"
            "tas_"
            "anomaly_"
            "annual_"
            f"{period}_"
            f"{percentile}_"
            f"{scenario}_"
            "ensemble_all_"
            "mean"
        ),
        (
            "cmip6-x0.25_"
            "climatology_"
            "tas,tasmin,tasmax_"
            "anomaly_"
            "annual_"
            f"{period}_"
            f"{percentile}_"
            f"{scenario}_"
            "ensemble_all_"
            "mean"
        ),
    )


def _request_global_projection(
    scenario: str,
    period: str,
    percentile: str,
) -> tuple[Any, str]:
    errors = []

    for dataset in _candidate_dataset_names(
        period=period,
        scenario=scenario,
        percentile=percentile,
    ):
        for geocode in GLOBAL_AGGREGATE_GEOCODES:
            for base in CCKP_API_BASES:
                url = (
                    f"{base}/"
                    f"{dataset}/"
                    f"{geocode}"
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

                    if payload not in (
                        None,
                        {},
                        [],
                    ):
                        return payload, response.url

                    errors.append(
                        f"{response.url}: empty response"
                    )

                except Exception as exc:
                    errors.append(
                        f"{url}: {type(exc).__name__}: {exc}"
                    )

    raise RuntimeError(
        "No usable CCKP country projection response. "
        + " | ".join(errors[-6:])
    )


def _walk(
    obj: Any,
    path: tuple[Any, ...] = (),
):
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


def _lookup(
    record: dict[str, Any],
    names: tuple[str, ...],
):
    lowered = {
        str(key).lower(): value
        for key, value in record.items()
    }

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


def _record_iso3(
    record: dict[str, Any],
    path: tuple[Any, ...],
) -> str | None:
    direct = _lookup(
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

    code = _iso3(direct)

    if code:
        return code

    for token in reversed(path):
        code = _iso3(token)

        if code:
            return code

    return None


def _projection_value(
    record: dict[str, Any],
) -> float | None:
    direct = _lookup(
        record,
        (
            "tas",
            "value",
            "anomaly",
            "median",
            "mean",
            "data",
        ),
    )

    value = _finite(direct)

    if (
        value is not None
        and -20 <= value <= 20
    ):
        return value

    candidates = []

    for key, raw in record.items():
        key_lower = str(key).lower()

        if any(
            bad in key_lower
            for bad in (
                "lat",
                "lon",
                "year",
                "id",
                "area",
                "population",
            )
        ):
            continue

        value = _finite(raw)

        if (
            value is not None
            and -20 <= value <= 20
        ):
            candidates.append(value)

    if len(candidates) == 1:
        return candidates[0]

    return None


def _extract_projection_table(
    payload: Any,
) -> pd.DataFrame:
    rows = []

    # Record-oriented extraction.
    for kind, path, item in _walk(payload):
        if kind != "dict":
            continue

        code = _record_iso3(
            item,
            path,
        )

        if not code:
            continue

        value = _projection_value(item)

        if value is None:
            continue

        name = _lookup(
            item,
            (
                "country_name",
                "country",
                "name",
                "location",
                "spatial_unit_name",
                "area_name",
            ),
        )

        if not name:
            name = _country_name(code)

        if not name:
            continue

        rows.append(
            {
                "iso3": code,
                "country_name": str(name),
                "value": value,
            }
        )

    # Scalar-oriented extraction for ISO3-keyed payloads.
    if not rows:
        for kind, path, raw in _walk(payload):
            if kind != "scalar":
                continue

            code = None

            for token in path:
                code = _iso3(token)

                if code:
                    break

            if not code:
                continue

            value = _finite(raw)

            if (
                value is None
                or not (-20 <= value <= 20)
            ):
                continue

            name = _country_name(code)

            if name:
                rows.append(
                    {
                        "iso3": code,
                        "country_name": name,
                        "value": value,
                    }
                )

    if not rows:
        return pd.DataFrame(
            columns=[
                "iso3",
                "country_name",
                "value",
            ]
        )

    frame = pd.DataFrame(rows)

    frame = (
        frame
        .groupby(
            [
                "iso3",
                "country_name",
            ],
            as_index=False,
        )["value"]
        .median()
    )

    return frame


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def _fetch_percentile_table(
    scenario: str,
    period: str,
    percentile: str,
) -> pd.DataFrame:
    payload, source_url = (
        _request_global_projection(
            scenario=scenario,
            period=period,
            percentile=percentile,
        )
    )

    frame = _extract_projection_table(
        payload
    )

    frame.attrs[
        "source_url"
    ] = source_url

    return frame


@st.cache_data(ttl=86400, max_entries=64, show_spinner=False)
@observe_operation("world_bank_rankings", quality_source="World Bank CCKP")
def get_country_projection_rankings(
    scenario: str = "ssp245",
    period: str = "2040-2059",
) -> pd.DataFrame:
    """
    Rank country spatial-average CMIP6 mean-temperature anomalies.
    """
    median = _fetch_percentile_table(
        scenario=scenario,
        period=period,
        percentile="median",
    ).rename(
        columns={
            "value": "projected_warming_c",
        }
    )

    if median.empty:
        raise RuntimeError(
            "CCKP returned a projection payload, but no country-level "
            "temperature anomalies could be parsed."
        )

    # P10/P90 are independent and optional. Resolve both concurrently while
    # preserving the existing graceful-degradation behavior.
    percentile_results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                _fetch_percentile_table,
                scenario,
                period,
                percentile,
            ): percentile
            for percentile in ("p10", "p90")
        }
        for future in as_completed(futures):
            percentile = futures[future]
            try:
                percentile_results[percentile] = future.result()
            except Exception:
                percentile_results[percentile] = None

    raw_p10 = percentile_results.get("p10")
    p10 = (
        raw_p10.rename(columns={"value": "p10_c"})
        if raw_p10 is not None
        else pd.DataFrame(columns=["iso3", "p10_c"])
    )
    raw_p90 = percentile_results.get("p90")
    p90 = (
        raw_p90.rename(columns={"value": "p90_c"})
        if raw_p90 is not None
        else pd.DataFrame(columns=["iso3", "p90_c"])
    )

    result = median.copy()

    if not p10.empty:
        result = result.merge(
            p10[["iso3", "p10_c"]],
            on="iso3",
            how="left",
        )
    else:
        result["p10_c"] = pd.NA

    if not p90.empty:
        result = result.merge(
            p90[["iso3", "p90_c"]],
            on="iso3",
            how="left",
        )
    else:
        result["p90_c"] = pd.NA

    result = (
        result
        .drop_duplicates(
            subset=["iso3"]
        )
        .sort_values(
            "projected_warming_c",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    result["rank"] = (
        result.index + 1
    )

    result.attrs[
        "source_url"
    ] = median.attrs.get(
        "source_url"
    )

    return result[
        [
            "rank",
            "country_name",
            "iso3",
            "projected_warming_c",
            "p10_c",
            "p90_c",
        ]
    ]


def _extract_single_country_projection_value(payload: Any) -> float | None:
    """Extract a single annual TAS anomaly from a country-specific CCKP payload.

    CCKP's documented country API uses the ISO3 geocode directly. Payload
    serialization can vary, so extraction first looks for explicit TAS/value
    records and then falls back to numeric scalars whose path refers to ``tas``.
    """
    candidates: list[float] = []

    for kind, path, item in _walk(payload):
        if kind == "dict":
            value = _projection_value(item)
            if value is not None:
                # Prefer records that are explicitly TAS-related, but accept a
                # single unambiguous value record as a fallback.
                text = " ".join(str(x).lower() for x in path)
                keys = " ".join(str(k).lower() for k in item.keys())
                if "tas" in text or "tas" in keys or any(
                    key in item for key in ("value", "anomaly", "median", "mean")
                ):
                    candidates.append(value)

        elif kind == "scalar":
            path_text = " ".join(str(x).lower() for x in path)
            if "tasmin" in path_text or "tasmax" in path_text:
                continue
            if "tas" not in path_text and "value" not in path_text and "anomaly" not in path_text:
                continue
            value = _finite(item)
            if value is not None and -20 <= value <= 20:
                candidates.append(value)

    if not candidates:
        return None
    return float(pd.Series(candidates, dtype="float64").median())


@st.cache_data(ttl=86400, max_entries=1024, show_spinner=False)
def _fetch_country_projection_value(
    iso3_code: str,
    scenario: str,
    period: str,
    percentile: str,
) -> float | None:
    """Fetch one documented CCKP country aggregate directly by ISO3 geocode."""
    iso3_code = str(iso3_code).strip().upper()
    errors = []
    for dataset in _candidate_dataset_names(period, scenario, percentile):
        url = f"https://cckpapi.worldbank.org/cckp/v1/{dataset}/{iso3_code}"
        try:
            response = requests.get(
                url,
                params={"_format": "json"},
                timeout=30,
                headers={"User-Agent": "ORBIDENSE-AI/1.0 (climate intelligence dashboard)"},
            )
            response.raise_for_status()
            payload = response.json()
            value = _extract_single_country_projection_value(payload)
            if value is not None:
                return value
            errors.append(f"{response.url}: no TAS value parsed")
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    return None


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
@observe_operation("world_bank_trajectory", quality_source="World Bank CCKP")
def get_country_scenario_trajectory(
    iso3_code: str,
    scenario: str = "ssp245",
) -> pd.DataFrame:
    """Return country CMIP6 TAS-anomaly climatologies across standard periods.

    Country pages now use CCKP's documented country endpoint directly with the
    ISO3 geocode. The global aggregate parser remains the ranking path, but a
    country view no longer depends on extracting the requested country from a
    very large all-countries payload.
    """
    iso3_code = str(iso3_code).strip().upper()
    requests_to_make = [
        (period, percentile)
        for period in _TRAJECTORY_PERIODS
        for percentile in ("median", "p10", "p90")
    ]
    values: dict[tuple[str, str], float | None] = {}

    # Twelve independent country aggregates; bounded concurrency keeps latency
    # low without creating an uncontrolled provider burst.
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                _fetch_country_projection_value,
                iso3_code,
                scenario,
                period,
                percentile,
            ): (period, percentile)
            for period, percentile in requests_to_make
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                values[key] = future.result()
            except Exception:
                values[key] = None

    rows = []
    for period in _TRAJECTORY_PERIODS:
        median_value = _finite(values.get((period, "median")))
        if median_value is None:
            continue
        rows.append({
            "period": period,
            "median_c": median_value,
            "p10_c": _finite(values.get((period, "p10"))),
            "p90_c": _finite(values.get((period, "p90"))),
        })

    # Defensive fallback to the existing global aggregate tables if a provider
    # serialization prevents direct-country parsing for a given release.
    if not rows:
        tables = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(_fetch_percentile_table, scenario, period, percentile): (period, percentile)
                for period, percentile in requests_to_make
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    tables[key] = future.result()
                except Exception:
                    tables[key] = None
        for period in _TRAJECTORY_PERIODS:
            median_table = tables.get((period, "median"))
            if median_table is None or median_table.empty:
                continue
            median_row = median_table[median_table["iso3"] == iso3_code]
            if median_row.empty:
                continue
            median_value = _finite(median_row.iloc[0]["value"])
            if median_value is None:
                continue
            percentile_values = {}
            for percentile in ("p10", "p90"):
                table = tables.get((period, percentile))
                value = None
                if table is not None and not table.empty:
                    row = table[table["iso3"] == iso3_code]
                    if not row.empty:
                        value = _finite(row.iloc[0]["value"])
                percentile_values[percentile] = value
            rows.append({
                "period": period,
                "median_c": median_value,
                "p10_c": percentile_values["p10"],
                "p90_c": percentile_values["p90"],
            })

    return pd.DataFrame(rows)
