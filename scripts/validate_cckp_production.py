import pandas as pd
import numpy as np

p = r".\data\climate_intelligence\cckp_country_projections.parquet"
d = pd.read_parquet(p)

print("=" * 80)
print("ORBIDENSE CCKP — SCIENTIFIC VALIDATION")
print("=" * 80)

# 1. STRUCTURE
print("\n[1] STRUCTURE")
print("Rows:", len(d))
print("Countries/entities:", d["iso3"].nunique())
print("Null values:", int(d["value"].isna().sum()))
print("Exact duplicates:", int(d.duplicated().sum()))

# 2. AGGREGATION METHODS
print("\n[2] AGGREGATION METHODS")
print(d["aggregation_method"].value_counts().to_string())

# 3. EXTREME VALUES
print("\n[3] TEMPERATURE ANOMALY — LOWEST")
x = d[(d.indicator=="tas") & (d.value_type=="anomaly")]
print(x.nsmallest(15,"value")[
    ["iso3","country","scenario","period","statistic","value","aggregation_method"]
].to_string(index=False))

print("\n[4] TEMPERATURE ANOMALY — HIGHEST")
print(x.nlargest(15,"value")[
    ["iso3","country","scenario","period","statistic","value","aggregation_method"]
].to_string(index=False))

print("\n[5] PRECIPITATION ANOMALY — LOWEST")
x = d[(d.indicator=="pr") & (d.value_type=="anomaly")]
print(x.nsmallest(15,"value")[
    ["iso3","country","scenario","period","statistic","value","unit","aggregation_method"]
].to_string(index=False))

print("\n[6] PRECIPITATION ANOMALY — HIGHEST")
print(x.nlargest(15,"value")[
    ["iso3","country","scenario","period","statistic","value","unit","aggregation_method"]
].to_string(index=False))

# 4. PERCENTILE ORDERING
print("\n[7] P10 <= MEDIAN <= P90 TEST")

keys = ["iso3","indicator","scenario","period","value_type"]

w = d.pivot_table(
    index=keys,
    columns="statistic",
    values="value",
    aggfunc="first"
).reset_index()

complete = w.dropna(subset=["p10","median","p90"]).copy()

bad = complete[
    (complete["p10"] > complete["median"]) |
    (complete["median"] > complete["p90"])
]

print("Complete percentile triplets:", len(complete))
print("Ordering violations:", len(bad))

if len(bad):
    print(bad.head(30).to_string(index=False))

# 5. HEAT-DAY PHYSICAL BOUNDS
print("\n[8] HEAT-DAY PHYSICAL BOUNDS")

heat = d[d.indicator.isin(["hd30","hd35"])]
bad_heat = heat[(heat.value < 0) | (heat.value > 366)]

print("Heat-day rows:", len(heat))
print("Outside 0–366 days:", len(bad_heat))

# 6. HD35 SHOULD NOT EXCEED HD30
print("\n[9] HD35 <= HD30 TEST")

h = d[d.indicator.isin(["hd30","hd35"])].pivot_table(
    index=["iso3","scenario","period","statistic"],
    columns="indicator",
    values="value",
    aggfunc="first"
).dropna()

bad_threshold = h[h["hd35"] > h["hd30"]]

print("Comparable heat rows:", len(h))
print("HD35 > HD30 violations:", len(bad_threshold))

if len(bad_threshold):
    print(bad_threshold.head(20).to_string())

# 7. COVERAGE MATRIX
print("\n[10] COVERAGE")

coverage = d.groupby(
    ["indicator","scenario","period","statistic","value_type"]
).agg(
    countries=("iso3","nunique"),
    rows=("value","size")
).reset_index()

print(coverage.to_string(index=False))

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)

