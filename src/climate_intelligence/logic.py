from __future__ import annotations

import math
from typing import Any

import pandas as pd


def finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def linear_trend_per_decade(frame: pd.DataFrame, year_col="year", value_col="value") -> float | None:
    if frame is None or frame.empty or year_col not in frame or value_col not in frame:
        return None
    data = frame[[year_col, value_col]].copy()
    data[year_col] = pd.to_numeric(data[year_col], errors="coerce")
    data[value_col] = pd.to_numeric(data[value_col], errors="coerce")
    data = data.dropna().sort_values(year_col)
    if len(data) < 3:
        return None
    x = data[year_col].astype(float)
    y = data[value_col].astype(float)
    x_centered = x - x.mean()
    denominator = float((x_centered ** 2).sum())
    if denominator == 0:
        return None
    slope_per_year = float((x_centered * (y - y.mean())).sum() / denominator)
    return slope_per_year * 10.0


def percent_change(start: Any, end: Any) -> float | None:
    a, b = finite(start), finite(end)
    if a is None or b is None or a == 0:
        return None
    return (b - a) / abs(a) * 100.0


def target_gap(policy_projection: Any, target: Any) -> float | None:
    """Positive = policy projection remains above target (shortfall)."""
    policy, goal = finite(policy_projection), finite(target)
    if policy is None or goal is None:
        return None
    return policy - goal


def classify_gap(gap: Any, target: Any) -> str:
    gap_value, target_value = finite(gap), finite(target)
    if gap_value is None or target_value is None:
        return "Not assessed"
    denominator = max(abs(target_value), 1e-9)
    ratio = gap_value / denominator
    if ratio <= 0:
        return "On or beyond target"
    if ratio <= 0.05:
        return "Near target"
    if ratio <= 0.15:
        return "Off track"
    return "Large gap"


def latest_total_emissions(frame: pd.DataFrame) -> tuple[int | None, float | None, str | None]:
    if frame is None or frame.empty:
        return None, None, None
    data = frame.copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(subset=["year", "value"])
    if data.empty:
        return None, None, None
    # Prefer explicit total rows when present.
    total_mask = data["sector"].astype(str).str.lower().str.contains("total|all sectors|including lulucf|excluding lulucf")
    total = data[total_mask] if total_mask.any() else data
    latest_year = int(total["year"].max())
    latest = total[total["year"] == latest_year]
    value = float(latest["value"].sum()) if not latest.empty else None
    unit = str(latest.iloc[0].get("unit", "MtCO2e")) if not latest.empty else None
    return latest_year, value, unit


def sector_shares(frame: pd.DataFrame, top_n: int = 6) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["sector", "value", "share_pct"])
    data = frame.copy()
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(subset=["value"])
    data = data[data["value"] > 0]
    if data.empty:
        return pd.DataFrame(columns=["sector", "value", "share_pct"])
    # Avoid double counting obvious total rows in a sector composition.
    data = data[~data["sector"].astype(str).str.lower().str.contains("total|all sectors")]
    if data.empty:
        return pd.DataFrame(columns=["sector", "value", "share_pct"])
    grouped = data.groupby("sector", as_index=False)["value"].sum().sort_values("value", ascending=False)
    total = grouped["value"].sum()
    grouped["share_pct"] = grouped["value"] / total * 100.0 if total else 0.0
    return grouped.head(top_n).reset_index(drop=True)


def parse_target_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract transparent target-like fields without pretending semantic certainty.

    Climate Watch serializations vary by NDC generation. We retain the original
    record fields and only lift explicit year/value/reduction fields that can be
    recognized by name.
    """
    parsed = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        lowered = {str(k).lower(): v for k, v in record.items()}
        year = None
        for key, value in lowered.items():
            if "year" in key or "target date" in key:
                candidate = finite(value)
                if candidate and 1990 <= candidate <= 2200:
                    year = int(candidate)
                    break
        reduction = None
        for key, value in lowered.items():
            if "reduction" in key and ("percent" in key or "%" in str(value)):
                reduction = finite(value)
                if reduction is not None:
                    break
        target_emissions = None
        for key, value in lowered.items():
            if "emission" in key and ("target" in key or "quant" in key):
                candidate = finite(value)
                if candidate is not None:
                    target_emissions = candidate
                    break
        label = None
        for key in ("name", "title", "target", "scenario", "type", "target_type"):
            if key in lowered and lowered[key]:
                label = str(lowered[key])
                break
        if year or reduction is not None or target_emissions is not None:
            parsed.append({
                "year": year,
                "reduction_pct": reduction,
                "target_emissions": target_emissions,
                "label": label or "NDC target",
                "raw": record,
            })
    # Keep one representative per target year/label combination.
    deduped = []
    seen = set()
    for item in parsed:
        key = (item.get("year"), item.get("label"), item.get("reduction_pct"), item.get("target_emissions"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return sorted(deduped, key=lambda x: (x.get("year") or 9999, str(x.get("label"))))
