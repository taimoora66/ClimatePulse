from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.climatewatchdata.org/api/v1"
OUT = Path("data/climate_intelligence/climatewatch_targets.parquet")
RAW = Path("data/climate_intelligence/raw/climatewatch")


def fetch_quantifications(iso3: str):
    response = requests.get(
        f"{BASE}/quantifications",
        params={"location": iso3},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def normalize_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def flatten_payload(payload, iso3: str):
    if isinstance(payload, dict):
        payload = payload.get("data", payload)

    if isinstance(payload, dict):
        if "quantifications" in payload:
            payload = payload["quantifications"]
        elif iso3 in payload:
            payload = payload[iso3]

    if not isinstance(payload, list):
        payload = [payload]

    rows = []

    for idx, item in enumerate(payload):
        row = {
            "iso3": iso3,
            "record_index": idx,
            "source": "Climate Watch /api/v1/quantifications",
        }

        if isinstance(item, dict):
            for key, value in item.items():
                row[str(key)] = normalize_value(value)
        else:
            row["raw_record"] = normalize_value(item)

        rows.append(row)

    return rows


def force_parquet_safe_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Climate Watch fields are schema-loose. A field such as `value` can be
    numeric in one row and a range/list in another. To prevent Arrow from
    inferring conflicting types, every non-control column is stored as text.
    """
    out = df.copy()

    # Keep only these structurally numeric columns numeric.
    numeric_columns = {"record_index"}

    for col in out.columns:
        if col in numeric_columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
        else:
            out[col] = out[col].map(
                lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
            ).astype("string")

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--iso",
        nargs="+",
        required=True,
        help="ISO3 codes, e.g. ITA DEU FRA ESP USA CHN",
    )
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    all_rows = []

    for iso3 in [x.upper().strip() for x in args.iso]:
        try:
            payload = fetch_quantifications(iso3)

            raw_path = RAW / f"{iso3}_quantifications.json"
            raw_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            rows = flatten_payload(payload, iso3)
            all_rows.extend(rows)

            print(f"[ok] {iso3} records={len(rows)}")

        except Exception as exc:
            print(f"[warn] {iso3}: {exc}")

    if not all_rows:
        print("[done] no quantification records returned")
        return

    df = pd.DataFrame(all_rows)
    df = force_parquet_safe_schema(df)

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Remove any partial/broken old outputs first.
    if OUT.exists():
        OUT.unlink()
    csv_path = OUT.with_suffix(".csv")
    if csv_path.exists():
        csv_path.unlink()

    # Write CSV first so we always preserve the data even if Parquet fails.
    df.to_csv(csv_path, index=False)
    print(f"[done] csv={csv_path}")

    # Then Parquet using the forced all-string schema.
    df.to_parquet(OUT, index=False)
    print(f"[done] parquet={OUT}")

    print(f"[done] rows={len(df)}")
    print(f"[done] countries={df['iso3'].nunique()}")

    print("\n[dtypes]")
    print(df.dtypes.to_string())


if __name__ == "__main__":
    main()