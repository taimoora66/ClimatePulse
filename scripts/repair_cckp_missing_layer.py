import pandas as pd
from pathlib import Path

main_path = Path(r".\data\climate_intelligence\cckp_country_projections.parquet")
repair_path = Path(r".\data\climate_intelligence\cckp_pr_repair.parquet")

print("=" * 70)
print("ORBIDENSE CCKP MISSING-LAYER REPAIR")
print("=" * 70)

# Load datasets
main = pd.read_parquet(main_path)
repair = pd.read_parquet(repair_path)

print("Main rows before:", len(main))
print("Repair file rows:", len(repair))

# Select ONLY the missing layer
missing = repair[
    (repair["indicator"] == "pr")
    & (repair["scenario"] == "ssp245")
    & (repair["period"] == "2040-2059")
    & (repair["statistic"] == "median")
    & (repair["value_type"] == "anomaly")
].copy()

print("Repair rows selected:", len(missing))

if len(missing) != 245:
    raise RuntimeError(
        f"Expected exactly 245 repair rows, found {len(missing)}"
    )

# Analytical uniqueness key
key = [
    "iso3",
    "indicator",
    "scenario",
    "period",
    "statistic",
    "value_type",
]

# Ensure layer does not already exist
existing_keys = set(map(tuple, main[key].astype(str).to_numpy()))
repair_keys = set(map(tuple, missing[key].astype(str).to_numpy()))

overlap = existing_keys.intersection(repair_keys)

print("Existing-key overlap:", len(overlap))

if overlap:
    raise RuntimeError(
        "Repair rows already exist in production dataset. "
        "Nothing has been changed."
    )

# Append missing layer
fixed = pd.concat([main, missing], ignore_index=True)

# Sort consistently
fixed = fixed.sort_values(
    [
        "iso3",
        "indicator",
        "scenario",
        "period",
        "statistic",
        "value_type",
    ]
).reset_index(drop=True)

# Final structural checks
if len(fixed) != 70560:
    raise RuntimeError(
        f"Expected 70,560 final rows, found {len(fixed)}"
    )

duplicates = fixed.duplicated(key).sum()

if duplicates:
    raise RuntimeError(
        f"Found {duplicates} duplicate analytical keys."
    )

if fixed["value"].isna().any():
    raise RuntimeError("Null climate values detected.")

# Save repaired production dataset
fixed.to_parquet(main_path, index=False)
fixed.to_csv(main_path.with_suffix(".csv"), index=False)

print()
print("FINAL ROWS:", len(fixed))
print("COUNTRIES:", fixed["iso3"].nunique())
print("NULL VALUES:", fixed["value"].isna().sum())
print("KEY DUPLICATES:", fixed.duplicated(key).sum())
print()
print("REPAIR COMPLETE")
print("=" * 70)
