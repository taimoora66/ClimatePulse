"""Preprocess CDP public city data for ORBIDENSE Phase 2.

The current CDP public release is distributed as a multi-sheet workbook. To
avoid fragile runtime scraping and long public-page loads, download the 2025
Full Cities Public Data workbook from CDP Open Data, then run:

  python scripts/sync_cdp_cities.py --input path/to/cdp_2025.xlsx

The parser is intentionally conservative. It extracts only fields it can
identify explicitly and preserves coverage gaps.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import pandas as pd

OUT = Path("data/climate_intelligence/cdp_city_profiles.parquet")


def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def find_col(columns, words):
    for c in columns:
        text = norm(c).casefold()
        if all(w.casefold() in text for w in words):
            return c
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    sheets = pd.read_excel(args.input, sheet_name=None)
    rows = []
    for sheet_name, frame in sheets.items():
        if frame is None or frame.empty:
            continue
        frame.columns = [norm(c) for c in frame.columns]
        city_col = find_col(frame.columns, ["city"]) or find_col(frame.columns, ["organization"])
        if city_col is None:
            continue
        target_year_col = find_col(frame.columns, ["target", "year"])
        progress_col = find_col(frame.columns, ["percentage", "target", "achieved"])
        risk_col = find_col(frame.columns, ["climate", "hazard"]) or find_col(frame.columns, ["risk"])
        country_col = find_col(frame.columns, ["country"])
        if target_year_col is None and progress_col is None and risk_col is None:
            continue
        for _, record in frame.iterrows():
            city = norm(record.get(city_col))
            if not city or city.lower() == "nan":
                continue
            rows.append({
                "city": city,
                "country": norm(record.get(country_col)) if country_col else None,
                "target_year": pd.to_numeric(record.get(target_year_col), errors="coerce") if target_year_col else None,
                "target_progress_pct": pd.to_numeric(record.get(progress_col), errors="coerce") if progress_col else None,
                "primary_risk": norm(record.get(risk_col)) if risk_col else None,
                "source_sheet": sheet_name,
            })
    if not rows:
        raise SystemExit("No conservative city target/risk fields were identified. Review workbook headers before changing parser rules.")
    out = pd.DataFrame(rows)
    # Prefer rows carrying the most evidence, then one compact profile per city.
    out["coverage"] = out[["target_year", "target_progress_pct", "primary_risk"]].notna().sum(axis=1)
    out = out.sort_values(["city", "coverage"], ascending=[True, False]).drop_duplicates("city")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"Wrote {len(out):,} city profiles to {OUT}")


if __name__ == "__main__":
    main()
