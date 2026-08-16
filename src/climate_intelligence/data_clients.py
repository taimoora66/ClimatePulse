from __future__ import annotations

import io
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pycountry
import requests
import streamlit as st

from src.observability import observe_operation

CLIMATE_WATCH_BASE = "https://www.climatewatchdata.org/api/v1"
EDGAR_BOOKLET_URL = "https://edgar.jrc.ec.europa.eu/booklet/EDGAR_2025_GHG_booklet_2025.xlsx"
CAT_RATINGS_PATH = Path("data/climate_intelligence/cat_ratings_2026_07.csv")
CDP_CITY_PROFILES_PATH = Path("data/climate_intelligence/cdp_city_profiles.parquet")
CAT_SECTOR_BENCHMARKS_PATH = Path("data/climate_intelligence/cat_sector_benchmarks.parquet")


def _safe_json(response: requests.Response) -> Any:
    response.raise_for_status()
    return response.json()


def _country_name(iso3: str) -> str:
    try:
        obj = pycountry.countries.get(alpha_3=str(iso3).upper())
        return obj.name if obj else str(iso3).upper()
    except Exception:
        return str(iso3).upper()


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace(",", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0))
    except Exception:
        return None
    return number if math.isfinite(number) else None


def _walk_records(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_records(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_records(item)


@st.cache_data(ttl=21600, max_entries=256, show_spinner=False)
@observe_operation("climate_watch_quantifications", quality_source="Climate Watch / WRI")
def get_ndc_quantifications(iso3: str) -> list[dict[str, Any]]:
    """Structured NDC quantification records from Climate Watch.

    The API is used as a structured convenience layer; the UI labels UNFCCC's
    NDC Registry as the authoritative document source.
    """
    iso3 = str(iso3).upper().strip()
    response = requests.get(
        f"{CLIMATE_WATCH_BASE}/quantifications",
        params={"location": iso3},
        timeout=8,
        headers={"User-Agent": "ORBIDENSE-AI/1.0"},
    )
    payload = _safe_json(response)
    records = []
    for record in _walk_records(payload):
        if not isinstance(record, dict):
            continue
        text = " ".join(str(v) for v in record.values() if v is not None)
        if iso3.lower() in text.lower() or record.get("iso_code3") == iso3:
            records.append(record)
    # Some API serializations already return only the requested location and
    # do not repeat the ISO code in each nested record.
    if not records:
        if isinstance(payload, list):
            records = [r for r in payload if isinstance(r, dict)]
        elif isinstance(payload, dict):
            for key in ("data", "quantifications", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    records = [r for r in value if isinstance(r, dict)]
                    break
    return records


@st.cache_data(ttl=21600, max_entries=256, show_spinner=False)
@observe_operation("climate_watch_timeline", quality_source="Climate Watch / WRI")
def get_climate_policy_timeline(iso3: str) -> list[dict[str, Any]]:
    iso3 = str(iso3).upper().strip()
    response = requests.get(
        f"{CLIMATE_WATCH_BASE}/timeline/{iso3}",
        timeout=8,
        headers={"User-Agent": "ORBIDENSE-AI/1.0"},
    )
    payload = _safe_json(response)
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("data", "timeline", "events", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


@st.cache_data(ttl=21600, max_entries=256, show_spinner=False)
@observe_operation("climate_watch_emissions", quality_source="Climate Watch / CAIT")
def get_climate_watch_emissions(iso3: str) -> pd.DataFrame:
    """Retrieve country historical emissions from Climate Watch Data Explorer.

    Climate Watch documents ``/api/v1/data/historical_emissions`` as the
    structured JSON endpoint. It accepts ISO3 values through ``regions[]`` and
    returns record-oriented rows with an ``emissions`` year/value array.

    We intentionally prefer this documented endpoint over the older
    ``/emissions`` serializer because its response schema is explicit and much
    more stable for application parsing.
    """
    iso3 = str(iso3).upper().strip()
    endpoint = f"{CLIMATE_WATCH_BASE}/data/historical_emissions"
    headers = {"User-Agent": "ORBIDENSE-AI/1.0"}
    rows: list[dict[str, Any]] = []

    # A single country can span several pages because Climate Watch can expose
    # multiple data sources, gases and sectors. Follow pagination conservatively
    # and stop when the endpoint returns no more records.
    for page in range(1, 21):
        response = requests.get(
            endpoint,
            params=[
                ("regions[]", iso3),
                ("start_year", "1990"),
                ("end_year", "2024"),
                ("sort_dir", "ASC"),
                ("page", str(page)),
            ],
            timeout=10,
            headers=headers,
        )
        payload = _safe_json(response)
        records = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(records, list) or not records:
            break

        for record in records:
            if not isinstance(record, dict):
                continue
            record_iso = str(record.get("iso_code3") or "").upper().strip()
            if record_iso and record_iso != iso3:
                continue
            sector = record.get("sector") or "Total"
            gas = record.get("gas") or "All GHG"
            unit = record.get("unit") or "MtCO2e"
            data_source = record.get("data_source") or record.get("source") or "Climate Watch"
            emissions = record.get("emissions") or []
            if not isinstance(emissions, list):
                continue
            for point in emissions:
                if not isinstance(point, dict):
                    continue
                year = _as_number(point.get("year"))
                value = _as_number(point.get("value"))
                if year is None or value is None:
                    continue
                rows.append({
                    "year": int(year),
                    "value": value,
                    "sector": str(sector),
                    "gas": str(gas),
                    "unit": str(unit),
                    "data_source": str(data_source),
                })

        # Climate Watch documents 50 records per page. A short page is the
        # terminal page and avoids an unnecessary extra request.
        if len(records) < 50:
            break

    if not rows:
        return pd.DataFrame(
            columns=["year", "value", "sector", "gas", "unit", "data_source"]
        )

    frame = pd.DataFrame(rows).drop_duplicates()

    # Prefer CAIT/Climate Watch rows when several sources describe the same
    # country. Keep the fallback sources only when no preferred rows exist.
    preferred = frame[frame["data_source"].astype(str).str.contains(
        "CAIT|Climate Watch", case=False, regex=True, na=False
    )]
    if not preferred.empty:
        frame = preferred

    return frame.sort_values(["sector", "gas", "year"]).reset_index(drop=True)


@st.cache_data(ttl=86400, max_entries=2, show_spinner=False)
@observe_operation("edgar_2025_booklet", quality_source="EDGAR / JRC")
def get_edgar_booklet_sheets() -> dict[str, pd.DataFrame]:
    """Download and parse the official EDGAR 2025 GHG workbook.

    The workbook is cached for 24 hours. Failure returns an empty dict so the
    product can fall back to Climate Watch/CAIT without blocking the page.
    """
    try:
        response = requests.get(
            EDGAR_BOOKLET_URL,
            timeout=20,
            headers={"User-Agent": "ORBIDENSE-AI/1.0"},
        )
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), sheet_name=None)
    except Exception:
        return {}


def _find_column(columns, tokens):
    for column in columns:
        normalized = str(column).strip().lower().replace("_", " ")
        if all(token in normalized for token in tokens):
            return column
    return None


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def get_edgar_country_sector_snapshot(iso3: str, country_name: str | None = None) -> pd.DataFrame:
    """Best-effort extraction of latest country-sector GHG values from EDGAR.

    EDGAR workbook structure can change between releases, so parsing is
    deliberately defensive and source provenance is displayed in the UI.
    """
    sheets = get_edgar_booklet_sheets()
    if not sheets:
        return pd.DataFrame(columns=["sector", "value", "unit", "year"])
    candidate_names = [country_name or "", _country_name(iso3), iso3]
    candidate_names = [str(x).lower() for x in candidate_names if x]
    frames = []
    for sheet_name, raw in sheets.items():
        if raw is None or raw.empty:
            continue
        frame = raw.copy()
        frame.columns = [str(c).strip() for c in frame.columns]
        country_col = _find_column(frame.columns, ("country",))
        sector_col = _find_column(frame.columns, ("sector",))
        if country_col is None or sector_col is None:
            continue
        mask = frame[country_col].astype(str).str.lower().apply(
            lambda text: any(name in text or text in name for name in candidate_names)
        )
        subset = frame[mask].copy()
        if subset.empty:
            continue
        year_columns = []
        for column in subset.columns:
            match = re.fullmatch(r"20\d{2}", str(column).strip())
            if match:
                year_columns.append((int(match.group(0)), column))
        if not year_columns:
            continue
        year, value_col = max(year_columns)
        subset["value"] = pd.to_numeric(subset[value_col], errors="coerce")
        subset = subset.dropna(subset=["value"])
        if subset.empty:
            continue
        subset["sector"] = subset[sector_col].astype(str)
        subset["year"] = year
        subset["unit"] = "EDGAR workbook unit"
        frames.append(subset[["sector", "value", "unit", "year"]])
    if not frames:
        return pd.DataFrame(columns=["sector", "value", "unit", "year"])
    result = pd.concat(frames, ignore_index=True)
    result = result.groupby(["sector", "year", "unit"], as_index=False)["value"].sum()
    return result.sort_values("value", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def get_cat_rating(iso3: str) -> dict[str, Any] | None:
    if not CAT_RATINGS_PATH.exists():
        return None
    frame = pd.read_csv(CAT_RATINGS_PATH)
    match = frame[frame["iso3"].astype(str).str.upper() == str(iso3).upper()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


@st.cache_data(ttl=3600, max_entries=512, show_spinner=False)
def get_cdp_city_profile(city_name: str, country_iso3: str | None = None) -> dict[str, Any] | None:
    """Read a preprocessed CDP city profile when the Phase-2 sync has run."""
    if not CDP_CITY_PROFILES_PATH.exists():
        return None
    frame = pd.read_parquet(CDP_CITY_PROFILES_PATH)
    city_key = str(city_name).strip().casefold()
    matches = frame[frame["city"].astype(str).str.strip().str.casefold() == city_key]
    if country_iso3 and "iso3" in matches.columns:
        narrowed = matches[matches["iso3"].astype(str).str.upper() == str(country_iso3).upper()]
        if not narrowed.empty:
            matches = narrowed
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()


@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def get_cat_sector_benchmarks(iso3: str) -> pd.DataFrame:
    """Read Phase-3 CAT sector benchmark data after an explicit data sync."""
    if not CAT_SECTOR_BENCHMARKS_PATH.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(CAT_SECTOR_BENCHMARKS_PATH)
    if "iso3" not in frame.columns:
        return pd.DataFrame()
    return frame[frame["iso3"].astype(str).str.upper() == str(iso3).upper()].copy()
