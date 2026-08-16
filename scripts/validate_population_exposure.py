from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path("data/climate_intelligence/population_exposure.parquet")

REQUIRED = {
    "iso3",
    "country",
    "scenario",
    "period",
    "statistic",
    "hazard",
    "threshold_days",
    "population_year",
    "population_total",
    "population_exposed",
    "exposed_share_pct",
    "zero_population_flag",
    "aggregation_method",
    "population_source_key",
    "hazard_source_file",
}


def main():
    if not PATH.exists():
        raise SystemExit(
            "population_exposure.parquet not found"
        )

    d = pd.read_parquet(PATH)

    missing = REQUIRED - set(d.columns)
    assert not missing, f"missing columns: {sorted(missing)}"

    key = [
        "iso3",
        "scenario",
        "period",
        "statistic",
        "hazard",
        "threshold_days",
    ]

    duplicates = int(d.duplicated(key).sum())

    assert duplicates == 0, (
        f"duplicate exposure keys: {duplicates}"
    )

    assert d["population_total"].notna().all()
    assert d["population_exposed"].notna().all()
    assert d["exposed_share_pct"].notna().all()

    assert d["population_total"].ge(0).all()
    assert d["population_exposed"].ge(0).all()

    assert (
        d["population_exposed"]
        <= d["population_total"] + 1e-6
    ).all()

    assert d["exposed_share_pct"].between(
        0,
        100,
    ).all()

    zero = d["population_total"] <= 0

    assert (
        d.loc[zero, "exposed_share_pct"]
        .eq(0)
        .all()
    ), "zero-population entities must have 0% exposure"

    # Monotonicity:
    # stricter hazard-day thresholds cannot increase exposure.
    bad = []

    group_cols = [
        "iso3",
        "scenario",
        "period",
        "statistic",
        "hazard",
    ]

    for key_values, g in d.groupby(group_cols):
        g = g.sort_values("threshold_days")

        exposed = g["population_exposed"].to_numpy(
            dtype=float
        )

        share = g["exposed_share_pct"].to_numpy(
            dtype=float
        )

        if len(exposed) > 1:
            if np.any(
                exposed[1:]
                > exposed[:-1] + 1e-6
            ):
                bad.append(
                    (key_values, "population_exposed")
                )

            if np.any(
                share[1:]
                > share[:-1] + 1e-8
            ):
                bad.append(
                    (key_values, "exposed_share_pct")
                )

    assert not bad, (
        f"non-monotonic exposure groups: {bad[:20]}"
    )

    coverage = (
        d.groupby(
            [
                "scenario",
                "period",
                "statistic",
                "hazard",
                "threshold_days",
            ]
        )["iso3"]
        .nunique()
    )

    print("=" * 72)
    print("ORBIDENSE POPULATION EXPOSURE VALIDATION")
    print("=" * 72)
    print("rows:", len(d))
    print("unique countries/entities:", d["iso3"].nunique())
    print("duplicate keys:", duplicates)
    print("null totals:", int(d["population_total"].isna().sum()))
    print("null exposed:", int(d["population_exposed"].isna().sum()))
    print("null shares:", int(d["exposed_share_pct"].isna().sum()))
    print("zero-population rows:", int(zero.sum()))
    print(
        "fallback rows:",
        int(
            d["aggregation_method"]
            .eq("fractional_overlap_fallback")
            .sum()
        ),
    )
    print(
        "coverage min/max per layer:",
        int(coverage.min()),
        "/",
        int(coverage.max()),
    )

    print()
    print("Exposure monotonicity: PASS")
    print("Physical bounds: PASS")
    print("Schema: PASS")
    print("Key uniqueness: PASS")
    print("=" * 72)
    print("VALIDATION COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
