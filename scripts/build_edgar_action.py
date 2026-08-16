from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

URL = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/EDGAR_2025_GHG/EDGAR_AR5_GHG_1970_2024.zip"

RAW_DIR = Path("data/climate_intelligence/raw/edgar_2025")
OUT_COUNTRY = Path("data/climate_intelligence/edgar_country_emissions.parquet")
OUT_SECTOR = Path("data/climate_intelligence/edgar_sector_emissions.parquet")

TOTAL_SHEET = "TOTALS BY COUNTRY"
SECTOR_SHEET = "IPCC 2006"


def year_columns(columns):
    years = []

    for col in columns:
        s = str(col).strip()

        if re.fullmatch(r"Y_(19|20)\d{2}", s):
            year = int(s[2:])

            if 1970 <= year <= 2024:
                years.append(col)

    return years


def detect_header_row(book: Path, sheet: str, scan_rows: int = 30) -> int:
    preview = pd.read_excel(
        book,
        sheet_name=sheet,
        header=None,
        nrows=scan_rows,
    )

    best_row = None
    best_count = 0

    for idx, row in preview.iterrows():
        count = 0

        for value in row.tolist():
            s = str(value).strip()

            if re.fullmatch(r"Y_(19|20)\d{2}", s):
                year = int(s[2:])

                if 1970 <= year <= 2024:
                    count += 1

        if count > best_count:
            best_count = count
            best_row = idx

    if best_row is None or best_count < 10:
        raise RuntimeError(
            f"Could not detect annual header row in {sheet}. "
            f"Best candidate contained only {best_count} year columns."
        )

    print(
        f"[header] {sheet}: "
        f"row={best_row} "
        f"years_detected={best_count}"
    )

    return int(best_row)


def read_annual_sheet(book: Path, sheet: str) -> pd.DataFrame:
    header_row = detect_header_row(book, sheet)

    df = pd.read_excel(
        book,
        sheet_name=sheet,
        header=header_row,
    )

    df.columns = [str(c).strip() for c in df.columns]

    years = year_columns(df.columns)

    if len(years) != 55:
        raise RuntimeError(
            f"Expected 55 annual columns from 1970 to 2024 in {sheet}, "
            f"found {len(years)}."
        )

    return df


def download_archive() -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    archive = RAW_DIR / "EDGAR_AR5_GHG_1970_2024.zip"

    if archive.exists() and archive.stat().st_size > 1_000_000:
        print(f"[cached] {archive}")
        return archive

    print(f"[download] {URL}")

    with requests.get(URL, timeout=180, stream=True) as response:
        response.raise_for_status()

        with archive.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(
        f"[downloaded] {archive} "
        f"bytes={archive.stat().st_size:,}"
    )

    return archive


def extract_workbook(archive: Path) -> Path:
    extract_dir = RAW_DIR / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as z:
        z.extractall(extract_dir)

    books = list(extract_dir.rglob("*.xlsx"))

    if not books:
        raise RuntimeError("No Excel workbook found inside EDGAR archive.")

    preferred = [
        p
        for p in books
        if "AR5" in p.name.upper()
        and "GHG" in p.name.upper()
    ]

    book = preferred[0] if preferred else books[0]

    print(f"[workbook] {book}")

    xls = pd.ExcelFile(book)

    print(f"[sheets] {xls.sheet_names}")

    return book


def clean_year_column(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("Y_", "", regex=False),
        errors="coerce",
    )


def build_country_totals(book: Path) -> pd.DataFrame:
    df = read_annual_sheet(
        book,
        TOTAL_SHEET,
    )

    required = {
        "Country_code_A3",
        "Name",
        "Substance",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            f"Missing required columns in {TOTAL_SHEET}: {missing}"
        )

    years = year_columns(df.columns)

    df = df[
        df["Country_code_A3"]
        .astype(str)
        .str.upper()
        .str.fullmatch(r"[A-Z]{3}", na=False)
    ].copy()

    long = df[
        [
            "Country_code_A3",
            "Name",
            "Substance",
        ]
        + years
    ].melt(
        id_vars=[
            "Country_code_A3",
            "Name",
            "Substance",
        ],
        value_vars=years,
        var_name="year",
        value_name="value_ggco2e",
    )

    long = long.rename(
        columns={
            "Country_code_A3": "iso3",
            "Name": "country",
            "Substance": "substance",
        }
    )

    long["iso3"] = (
        long["iso3"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    long["country"] = (
        long["country"]
        .astype(str)
        .str.strip()
    )

    long["year"] = clean_year_column(
        long["year"]
    )

    long["value_ggco2e"] = pd.to_numeric(
        long["value_ggco2e"],
        errors="coerce",
    )

    long = long.dropna(
        subset=[
            "year",
            "value_ggco2e",
        ]
    )

    long = long[
        long["substance"]
        .astype(str)
        .eq("GWP_100_AR5_GHG")
    ]

    out = (
        long.groupby(
            [
                "iso3",
                "country",
                "year",
            ],
            as_index=False,
        )["value_ggco2e"]
        .sum()
    )

    out["value_mtco2e"] = (
        out["value_ggco2e"] / 1000.0
    )

    out["source"] = "EDGAR_2025_GHG"
    out["source_sheet"] = TOTAL_SHEET
    out["unit_original"] = "Gg CO2eq / yr"
    out["unit"] = "Mt CO2eq / yr"
    out["gwp"] = "IPCC AR5 GWP100"
    out["lulucf"] = "excluded"

    return out


def build_sector_series(book: Path) -> pd.DataFrame:
    df = read_annual_sheet(
        book,
        SECTOR_SHEET,
    )

    required = {
        "Country_code_A3",
        "Name",
        "ipcc_code_2006_for_standard_report",
        "ipcc_code_2006_for_standard_report_name",
        "Substance",
        "fossil_bio",
    }

    missing = required - set(df.columns)

    if missing:
        raise RuntimeError(
            f"Missing required columns in {SECTOR_SHEET}: {missing}"
        )

    years = year_columns(df.columns)

    df = df[
        df["Country_code_A3"]
        .astype(str)
        .str.upper()
        .str.fullmatch(r"[A-Z]{3}", na=False)
    ].copy()

    long = df[
        [
            "Country_code_A3",
            "Name",
            "ipcc_code_2006_for_standard_report",
            "ipcc_code_2006_for_standard_report_name",
            "Substance",
            "fossil_bio",
        ]
        + years
    ].melt(
        id_vars=[
            "Country_code_A3",
            "Name",
            "ipcc_code_2006_for_standard_report",
            "ipcc_code_2006_for_standard_report_name",
            "Substance",
            "fossil_bio",
        ],
        value_vars=years,
        var_name="year",
        value_name="value_ggco2e",
    )

    long = long.rename(
        columns={
            "Country_code_A3": "iso3",
            "Name": "country",
            "ipcc_code_2006_for_standard_report": "sector_code",
            "ipcc_code_2006_for_standard_report_name": "sector",
            "Substance": "substance",
        }
    )

    long["iso3"] = (
        long["iso3"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    long["country"] = (
        long["country"]
        .astype(str)
        .str.strip()
    )

    long["sector"] = (
        long["sector"]
        .astype(str)
        .str.strip()
    )

    long["sector_code"] = (
        long["sector_code"]
        .astype(str)
        .str.strip()
    )

    long["fossil_bio"] = (
        long["fossil_bio"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    long["year"] = clean_year_column(
        long["year"]
    )

    long["value_ggco2e"] = pd.to_numeric(
        long["value_ggco2e"],
        errors="coerce",
    )

    long = long.dropna(
        subset=[
            "year",
            "value_ggco2e",
        ]
    )

    long = long[
        long["substance"]
        .astype(str)
        .eq("GWP_100_AR5_GHG")
    ]

    out = (
        long.groupby(
            [
                "iso3",
                "country",
                "year",
                "sector_code",
                "sector",
                "fossil_bio",
            ],
            as_index=False,
        )["value_ggco2e"]
        .sum()
    )

    out["value_mtco2e"] = (
        out["value_ggco2e"] / 1000.0
    )

    out["source"] = "EDGAR_2025_GHG"
    out["source_sheet"] = SECTOR_SHEET
    out["unit_original"] = "Gg CO2eq / yr"
    out["unit"] = "Mt CO2eq / yr"
    out["gwp"] = "IPCC AR5 GWP100"
    out["lulucf"] = "excluded"

    return out


def validate(
    country: pd.DataFrame,
    sector: pd.DataFrame,
) -> None:

    if country.empty:
        raise RuntimeError(
            "Country emissions output is empty."
        )

    if sector.empty:
        raise RuntimeError(
            "Sector emissions output is empty."
        )

    country_duplicates = country.duplicated(
        [
            "iso3",
            "year",
        ]
    ).sum()

    if country_duplicates:
        raise RuntimeError(
            f"Country output contains "
            f"{country_duplicates} duplicate ISO3-year keys."
        )

    if not country["year"].between(
        1970,
        2024,
    ).all():
        raise RuntimeError(
            "Country output contains years outside 1970–2024."
        )

    if country["value_mtco2e"].isna().any():
        raise RuntimeError(
            "Country output contains null emissions."
        )

    if (
        country["value_mtco2e"] < 0
    ).any():
        raise RuntimeError(
            "Negative national emissions detected."
        )

    print(
        "[validate country]",
        f"rows={len(country)}",
        f"entities={country.iso3.nunique()}",
        f"years={int(country.year.min())}-{int(country.year.max())}",
    )

    print(
        "[validate sector]",
        f"rows={len(sector)}",
        f"entities={sector.iso3.nunique()}",
        f"sectors={sector.sector.nunique()}",
    )


def main():

    archive = download_archive()

    book = extract_workbook(
        archive
    )

    xls = pd.ExcelFile(
        book
    )

    if TOTAL_SHEET not in xls.sheet_names:
        raise RuntimeError(
            f"Missing sheet: {TOTAL_SHEET}"
        )

    if SECTOR_SHEET not in xls.sheet_names:
        raise RuntimeError(
            f"Missing sheet: {SECTOR_SHEET}"
        )

    country = build_country_totals(
        book
    )

    sector = build_sector_series(
        book
    )

    validate(
        country,
        sector,
    )

    OUT_COUNTRY.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    country.to_parquet(
        OUT_COUNTRY,
        index=False,
    )

    sector.to_parquet(
        OUT_SECTOR,
        index=False,
    )

    country.to_csv(
        OUT_COUNTRY.with_suffix(".csv"),
        index=False,
    )

    sector.to_csv(
        OUT_SECTOR.with_suffix(".csv"),
        index=False,
    )

    print(
        f"[done] {OUT_COUNTRY}"
    )

    print(
        f"[done] {OUT_SECTOR}"
    )

    print()

    for iso in [
        "ITA",
        "DEU",
        "FRA",
        "ESP",
        "USA",
        "CHN",
    ]:

        q = country[
            country["iso3"].eq(
                iso
            )
        ].sort_values(
            "year"
        )

        if not q.empty:

            row = q.iloc[-1]

            print(
                f"[sample] {iso} "
                f"{int(row['year'])} "
                f"{float(row['value_mtco2e']):,.2f} MtCO2eq"
            )


if __name__ == "__main__":
    main()