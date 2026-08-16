import pandas as pd
from src.climate_intelligence.logic import (
    classify_gap,
    linear_trend_per_decade,
    percent_change,
    sector_shares,
    target_gap,
)


def test_linear_trend_per_decade():
    frame = pd.DataFrame({"year": [2000, 2001, 2002, 2003], "value": [1.0, 1.1, 1.2, 1.3]})
    assert abs(linear_trend_per_decade(frame) - 1.0) < 1e-9


def test_gap_semantics():
    assert target_gap(620, 500) == 120
    assert classify_gap(120, 500) == "Large gap"
    assert classify_gap(-10, 500) == "On or beyond target"


def test_percent_change():
    assert percent_change(100, 80) == -20


def test_sector_shares():
    frame = pd.DataFrame({"sector": ["Power", "Transport", "Industry"], "value": [50, 30, 20]})
    out = sector_shares(frame)
    assert abs(out["share_pct"].sum() - 100) < 1e-9
    assert out.iloc[0]["sector"] == "Power"
