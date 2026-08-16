"""Normalize a CAT sector-indicator download for ORBIDENSE Phase 3.

Download the current CAT Data Explorer sector dataset, then run:
  python scripts/sync_cat_sector_benchmarks.py --input cat_sector_data.csv

No web scraping is performed in the public app. This keeps provenance stable,
load times low and CAT's published dataset as the source of truth.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import pycountry

OUT = Path("data/climate_intelligence/cat_sector_benchmarks.parquet")


def iso3_from_name(name):
    if not name:
        return None
    aliases = {"United States": "USA", "USA": "USA", "EU": "EUU", "UAE": "ARE", "Türkiye": "TUR", "South Korea": "KOR", "Viet Nam": "VNM"}
    if str(name) in aliases:
        return aliases[str(name)]
    try:
        return pycountry.countries.lookup(str(name)).alpha_3
    except Exception:
        return None


def find(columns, tokens):
    for c in columns:
        text = str(c).casefold()
        if all(t.casefold() in text for t in tokens):
            return c
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    args = p.parse_args()
    frame = pd.read_csv(args.input) if str(args.input).lower().endswith(".csv") else pd.read_excel(args.input)
    country_col = find(frame.columns, ["country"])
    sector_col = find(frame.columns, ["sector"])
    indicator_col = find(frame.columns, ["indicator"])
    current_col = find(frame.columns, ["current"]) or find(frame.columns, ["value"])
    benchmark_col = find(frame.columns, ["2030"]) or find(frame.columns, ["benchmark"])
    unit_col = find(frame.columns, ["unit"])
    if not all([country_col, sector_col, indicator_col]):
        raise SystemExit("Required CAT columns were not identified; inspect the current download before adjusting mapping.")
    out = pd.DataFrame({
        "country": frame[country_col].astype(str),
        "sector": frame[sector_col].astype(str),
        "indicator": frame[indicator_col].astype(str),
        "current_value": pd.to_numeric(frame[current_col], errors="coerce") if current_col else pd.NA,
        "benchmark_2030": pd.to_numeric(frame[benchmark_col], errors="coerce") if benchmark_col else pd.NA,
        "unit": frame[unit_col].astype(str) if unit_col else "",
    })
    out["iso3"] = out["country"].map(iso3_from_name)
    out = out.dropna(subset=["iso3"])
    def status(row):
        a, b = row.get("current_value"), row.get("benchmark_2030")
        if pd.isna(a) or pd.isna(b):
            return "Benchmark available"
        return "At/above benchmark" if float(a) >= float(b) else "Gap to benchmark"
    out["status"] = out.apply(status, axis=1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(f"Wrote {len(out):,} sector benchmark rows to {OUT}")


if __name__ == "__main__":
    main()
