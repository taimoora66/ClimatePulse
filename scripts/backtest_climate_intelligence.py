"""ORBIDENSE climate-intelligence validation / backtest harness.

Run locally before deployment:
    python scripts/backtest_climate_intelligence.py

The script separates deterministic calculation tests from optional online
provider checks. Provider outages never turn into silent data substitution.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.climate_intelligence.logic import (
    classify_gap,
    linear_trend_per_decade,
    percent_change,
    sector_shares,
    target_gap,
)

OUTPUT = ROOT / "data" / "climate_intelligence" / "backtest_report.json"


def check(name, condition, detail=""):
    return {"check": name, "pass": bool(condition), "detail": str(detail)}


def deterministic_checks():
    results = []
    trend_frame = pd.DataFrame({"year": [2000, 2001, 2002, 2003], "value": [10, 11, 12, 13]})
    results.append(check("trend_per_decade", abs(linear_trend_per_decade(trend_frame) - 10.0) < 1e-9))
    results.append(check("percent_change", abs(percent_change(100, 80) + 20.0) < 1e-9))
    results.append(check("target_gap_positive_shortfall", target_gap(620, 500) == 120))
    results.append(check("gap_classification", classify_gap(120, 500) == "Large gap"))
    sectors = pd.DataFrame({"sector": ["Power", "Transport", "Industry"], "value": [50, 30, 20]})
    shares = sector_shares(sectors)
    results.append(check("sector_shares_sum", abs(shares["share_pct"].sum() - 100.0) < 1e-9))
    results.append(check("sector_rank", shares.iloc[0]["sector"] == "Power"))
    return results


def online_checks():
    results = []
    try:
        from src.climate_intelligence.data_clients import (
            get_cat_rating,
            get_climate_policy_timeline,
            get_climate_watch_emissions,
            get_ndc_quantifications,
        )
        from src.api.country_rankings import get_country_scenario_trajectory
    except Exception as exc:
        return [check("online_environment", False, f"provider dependencies unavailable: {type(exc).__name__}")]
    countries = ["ITA", "DEU", "FRA", "USA", "CHN"]
    for iso3 in countries:
        try:
            trajectory = get_country_scenario_trajectory(iso3, "ssp245")
            ok = not trajectory.empty and set(trajectory.columns) >= {"period", "median_c"}
            if ok and {"p10_c", "p90_c"}.issubset(trajectory.columns):
                bounded = trajectory.dropna(subset=["p10_c", "median_c", "p90_c"])
                ok = ok and bool(((bounded["p10_c"] <= bounded["median_c"]) & (bounded["median_c"] <= bounded["p90_c"])).all())
            results.append(check(f"cckp_trajectory_{iso3}", ok, f"rows={len(trajectory)}"))
        except Exception as exc:
            results.append(check(f"cckp_trajectory_{iso3}", False, type(exc).__name__))

        rating = get_cat_rating(iso3)
        results.append(check(f"cat_snapshot_{iso3}", rating is not None, rating.get("rating") if rating else "not covered"))

        try:
            ndc = get_ndc_quantifications(iso3)
            results.append(check(f"climatewatch_ndc_{iso3}", isinstance(ndc, list) and len(ndc) > 0, f"records={len(ndc)}"))
        except Exception as exc:
            results.append(check(f"climatewatch_ndc_{iso3}", False, type(exc).__name__))

        try:
            emissions = get_climate_watch_emissions(iso3)
            results.append(check(f"emissions_{iso3}", isinstance(emissions, pd.DataFrame) and len(emissions) > 0, f"rows={len(emissions)}"))
        except Exception as exc:
            results.append(check(f"emissions_{iso3}", False, type(exc).__name__))

        try:
            timeline = get_climate_policy_timeline(iso3)
            results.append(check(f"timeline_{iso3}", isinstance(timeline, list) and len(timeline) > 0, f"records={len(timeline)}"))
        except Exception as exc:
            results.append(check(f"timeline_{iso3}", False, type(exc).__name__))
    return results


def main():
    deterministic = deterministic_checks()
    online = online_checks()
    report = {
        "deterministic": deterministic,
        "online": online,
        "deterministic_pass_pct": round(sum(x["pass"] for x in deterministic) / len(deterministic) * 100, 1),
        "online_pass_pct": round(sum(x["pass"] for x in online) / len(online) * 100, 1) if online else None,
        "interpretation": "Online checks measure data availability/integration, not scientific model skill.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["deterministic_pass_pct"] < 100:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
