from __future__ import annotations

import argparse
import math
import re
import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box
from shapely.ops import unary_union

DATA_ROOT = Path("data/climate_intelligence")
POP_CACHE = DATA_ROOT / "population_raw"
HAZARD_CACHE = DATA_ROOT / "hazard_raw"
OUT = DATA_ROOT / "population_exposure.parquet"

POP_PREFIX = "s3://wbg-cckp/data/pop-x0.25/popcount"

SCENARIOS = ("ssp126", "ssp245", "ssp370", "ssp585")
PERIODS = ("2020-2039", "2040-2059", "2060-2079", "2080-2099")
STATS = ("p10", "median", "p90")

THRESHOLDS = {
    "hd30": (15, 30, 60, 90, 120),
    "hd35": (1, 5, 10, 20, 30, 60),
}

BOUNDARY_CANDIDATES = (
    DATA_ROOT / "cckp_build/boundaries/WB_GAD_ADM0.shp",
    DATA_ROOT / "boundaries/WB_GAD_ADM0.shp",
)


def _run(args: list[str]) -> str:
    return subprocess.check_output(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _aws_exe() -> str:
    try:
        _run(["aws", "--version"])
        return "aws"
    except Exception:
        candidate = Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe")
        if candidate.exists():
            return str(candidate)
        raise RuntimeError(
            "AWS CLI was not found. Add AWS CLI v2 to PATH or install it first."
        )


AWS = _aws_exe()


def _period_midpoint(period: str) -> int:
    start, end = map(int, period.split("-"))
    return int(round((start + end) / 2))


def _first_data_var(ds: xr.Dataset) -> str:
    vars_ = list(ds.data_vars)
    if not vars_:
        raise RuntimeError("NetCDF contains no data variables.")
    for name in vars_:
        low = name.lower()
        if "pop" in low or "count" in low:
            return name
    return vars_[0]


def _lat_lon_names(da: xr.DataArray) -> tuple[str, str]:
    lat = "lat" if "lat" in da.coords else "latitude"
    lon = "lon" if "lon" in da.coords else "longitude"
    if lat not in da.coords or lon not in da.coords:
        raise RuntimeError(f"Could not identify lat/lon coordinates: {list(da.coords)}")
    return lat, lon


def _select_population_year(da: xr.DataArray, year: int) -> xr.DataArray:
    for coord_name in da.coords:
        coord = da[coord_name]
        low = coord_name.lower()

        if low == "time":
            try:
                years = pd.to_datetime(coord.values).year
                idx = int(np.argmin(np.abs(years - year)))
                return da.isel({coord.dims[0]: idx}).squeeze(drop=True)
            except Exception:
                pass

        if "year" in low:
            try:
                vals = np.asarray(coord.values, dtype=float)
                idx = int(np.argmin(np.abs(vals - year)))
                return da.isel({coord.dims[0]: idx}).squeeze(drop=True)
            except Exception:
                pass

    # A few products use integer-like time values.
    if "time" in da.dims:
        coord = da["time"]
        try:
            vals = np.asarray(coord.values, dtype=float)
            idx = int(np.argmin(np.abs(vals - year)))
            return da.isel(time=idx).squeeze(drop=True)
        except Exception:
            pass

    return da.squeeze(drop=True)


def _population_keys() -> list[str]:
    print("[population] indexing public CCKP population archive")
    listing = _run(
        [
            AWS,
            "s3",
            "ls",
            f"{POP_PREFIX}/",
            "--recursive",
            "--no-sign-request",
        ]
    )

    keys = []
    for line in listing.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) == 4 and parts[3].endswith(".nc"):
            keys.append(parts[3])

    if not keys:
        raise RuntimeError("No population NetCDF files were found in CCKP pop-x0.25.")

    return keys


def _choose_population_key(keys: list[str], scenario: str) -> str:
    candidates = [
        key for key in keys
        if scenario in key.lower()
        and "popcount" in key.lower()
        and "timeseries" in key.lower()
    ]
    if not candidates:
        candidates = [
            key for key in keys
            if scenario in key.lower()
            and "popcount" in key.lower()
        ]
    if not candidates:
        raise RuntimeError(f"No CCKP population product found for {scenario}.")

    # Prefer the GPW-v4-rev11 SSP family and widest time series.
    candidates.sort(
        key=lambda x: (
            "gpw-v4-rev11" not in x.lower(),
            "2010-2100" not in x.lower(),
            len(x),
        )
    )
    return candidates[0]


def _download_s3_key(key: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and destination.stat().st_size > 0:
        print(f"[cached] {destination.name}")
        return destination

    print(f"[download] s3://wbg-cckp/{key}")
    subprocess.check_call(
        [
            AWS,
            "s3",
            "cp",
            f"s3://wbg-cckp/{key}",
            str(destination),
            "--no-sign-request",
        ]
    )
    return destination


def _population_file(keys: list[str], scenario: str) -> tuple[Path, str]:
    key = _choose_population_key(keys, scenario)
    path = POP_CACHE / Path(key).name
    return _download_s3_key(key, path), key


def _hazard_filename(hazard: str, scenario: str, period: str, stat: str) -> str:
    return (
        f"climatology-{hazard}-annual-mean_cmip6-x0.25_ensemble-all-{scenario}"
        f"_climatology_{stat}_{period}.nc"
    )


def _hazard_s3_key(hazard: str, scenario: str, period: str, stat: str) -> str:
    filename = _hazard_filename(hazard, scenario, period, stat)
    return (
        f"data/cmip6-x0.25/{hazard}/ensemble-all-{scenario}/{filename}"
    )


def _hazard_file(hazard: str, scenario: str, period: str, stat: str) -> Path:
    filename = _hazard_filename(hazard, scenario, period, stat)

    # Reuse any copy already downloaded anywhere under climate_intelligence.
    found = list(DATA_ROOT.rglob(filename))
    if found:
        print(f"[cached hazard] {found[0]}")
        return found[0]

    destination = HAZARD_CACHE / filename
    key = _hazard_s3_key(hazard, scenario, period, stat)
    return _download_s3_key(key, destination)


def _boundary_file() -> Path:
    for path in BOUNDARY_CANDIDATES:
        if path.exists():
            return path

    found = list(DATA_ROOT.rglob("WB_GAD_ADM0.shp"))
    if found:
        return found[0]

    raise FileNotFoundError(
        "WB_GAD_ADM0.shp not found under data/climate_intelligence."
    )


def _read_boundaries() -> gpd.GeoDataFrame:
    path = _boundary_file()
    print(f"[boundaries] {path}")

    g = gpd.read_file(path)

    required = {"ISO_A3", "NAM_0", "geometry"}
    missing = required - set(g.columns)
    if missing:
        raise RuntimeError(f"Boundary file is missing columns: {sorted(missing)}")

    g = g[["ISO_A3", "NAM_0", "geometry"]].copy()
    g["ISO_A3"] = g["ISO_A3"].astype(str).str.upper().str.strip()
    g["NAM_0"] = g["NAM_0"].astype(str).str.strip()

    g = g[
        g["ISO_A3"].str.fullmatch(r"[A-Z]{3}", na=False)
        & g.geometry.notna()
        & ~g.geometry.is_empty
    ].copy()

    # Repair individual geometries without forcing a global union.
    try:
        g["geometry"] = g.geometry.make_valid()
    except Exception:
        g["geometry"] = g.geometry.buffer(0)

    g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()

    print(
        f"[boundaries] rows={len(g)} "
        f"iso3={g['ISO_A3'].nunique()}"
    )
    return g


def _canonical_country_names(g: gpd.GeoDataFrame) -> dict[str, str]:
    names = {}
    for iso3, group in g.groupby("ISO_A3"):
        # Prefer the largest boundary label as canonical sovereign display name.
        areas = group.to_crs("EPSG:6933").geometry.area
        idx = areas.idxmax()
        names[iso3] = str(group.loc[idx, "NAM_0"])
    return names


def _iso_geometry_map(g: gpd.GeoDataFrame) -> dict[str, object]:
    out = {}

    for iso3, group in g.groupby("ISO_A3"):
        geoms = [
            geom for geom in group.geometry
            if geom is not None and not geom.is_empty
        ]

        if not geoms:
            continue

        try:
            merged = unary_union(geoms)
        except Exception:
            repaired = []
            for geom in geoms:
                try:
                    repaired.append(geom.buffer(0))
                except Exception:
                    pass
            merged = unary_union(repaired)

        out[iso3] = merged

    return out


def _align_grids(
    pop: xr.DataArray,
    hazard: xr.DataArray,
) -> tuple[xr.DataArray, xr.DataArray]:
    plat, plon = _lat_lon_names(pop)
    hlat, hlon = _lat_lon_names(hazard)

    pop = pop.rename({plat: "lat", plon: "lon"})
    hazard = hazard.rename({hlat: "lat", hlon: "lon"})

    pop, hazard = xr.align(pop, hazard, join="inner")

    if pop.sizes.get("lat") != hazard.sizes.get("lat"):
        raise RuntimeError("Population and hazard latitude grids do not align.")
    if pop.sizes.get("lon") != hazard.sizes.get("lon"):
        raise RuntimeError("Population and hazard longitude grids do not align.")

    return pop, hazard


def _build_center_assignment(
    lat: np.ndarray,
    lon: np.ndarray,
    boundaries: gpd.GeoDataFrame,
) -> pd.DataFrame:
    lon2, lat2 = np.meshgrid(lon, lat)

    flat = pd.DataFrame(
        {
            "cell": np.arange(lon2.size, dtype=np.int64),
            "lon": lon2.ravel(),
            "lat": lat2.ravel(),
        }
    )

    pts = gpd.GeoDataFrame(
        flat,
        geometry=gpd.points_from_xy(flat["lon"], flat["lat"]),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(
        pts,
        boundaries[["ISO_A3", "geometry"]],
        how="left",
        predicate="within",
    )

    # Multiple WB polygons may share the same sovereign ISO3. Collapse to one
    # cell/ISO pair, but do not collapse different ISO3 values.
    joined = (
        joined.dropna(subset=["ISO_A3"])
        [["cell", "ISO_A3"]]
        .drop_duplicates(["cell", "ISO_A3"])
    )

    # A cell should belong to only one sovereign ISO in the centre-based pass.
    duplicates = joined.duplicated("cell", keep=False)
    if duplicates.any():
        joined = (
            joined.sort_values(["cell", "ISO_A3"])
            .drop_duplicates("cell", keep="first")
        )

    print(
        f"[mask] centre-based countries={joined['ISO_A3'].nunique()} "
        f"cells={len(joined)}"
    )
    return joined


def _grid_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)

    if len(values) < 2:
        raise RuntimeError("Grid must contain at least two coordinates.")

    step = float(np.median(np.diff(values)))
    edges = np.concatenate(
        (
            [values[0] - step / 2],
            (values[:-1] + values[1:]) / 2,
            [values[-1] + step / 2],
        )
    )
    return edges


def _fractional_weights_for_missing_iso(
    iso3: str,
    geom,
    lat: np.ndarray,
    lon: np.ndarray,
) -> pd.DataFrame:
    """
    Build fractional cell-overlap weights for a microstate/small entity whose
    polygon contains no 0.25-degree grid-cell centre.
    """
    if geom is None or geom.is_empty:
        return pd.DataFrame(columns=["cell", "weight"])

    lat_edges = _grid_edges(lat)
    lon_edges = _grid_edges(lon)

    minx, miny, maxx, maxy = geom.bounds

    lon_idx = np.where(
        (lon_edges[:-1] < maxx)
        & (lon_edges[1:] > minx)
    )[0]

    lat_idx = np.where(
        (lat_edges[:-1] < maxy)
        & (lat_edges[1:] > miny)
    )[0]

    rows = []

    nlon = len(lon)

    for i in lat_idx:
        y0 = lat_edges[i]
        y1 = lat_edges[i + 1]

        for j in lon_idx:
            x0 = lon_edges[j]
            x1 = lon_edges[j + 1]

            cell_poly = box(x0, y0, x1, y1)

            try:
                inter = geom.intersection(cell_poly)
            except Exception:
                try:
                    inter = geom.buffer(0).intersection(cell_poly)
                except Exception:
                    continue

            if inter.is_empty:
                continue

            # For these tiny cells, area ratio in geographic coordinates is a
            # practical fractional allocation. Clamp defensively to [0, 1].
            denom = cell_poly.area
            if denom <= 0:
                continue

            weight = float(inter.area / denom)
            weight = min(1.0, max(0.0, weight))

            if weight <= 0:
                continue

            cell = int(i * nlon + j)
            rows.append((cell, weight))

    if not rows:
        # Last-resort representative-point fallback. This avoids silently
        # dropping a sovereign entity while keeping the row explicitly flagged.
        point = geom.representative_point()
        j = int(np.argmin(np.abs(lon - point.x)))
        i = int(np.argmin(np.abs(lat - point.y)))
        cell = int(i * nlon + j)
        return pd.DataFrame(
            {"cell": [cell], "weight": [1.0]}
        )

    return pd.DataFrame(rows, columns=["cell", "weight"])


def _prepare_fallbacks(
    boundaries: gpd.GeoDataFrame,
    center_mask: pd.DataFrame,
    lat: np.ndarray,
    lon: np.ndarray,
) -> dict[str, pd.DataFrame]:
    all_iso = set(boundaries["ISO_A3"].unique())
    center_iso = set(center_mask["ISO_A3"].unique())
    missing = sorted(all_iso - center_iso)

    print(f"[fallback] entities without centre cell={len(missing)}")

    geom_map = _iso_geometry_map(boundaries)

    fallbacks = {}

    for idx, iso3 in enumerate(missing, start=1):
        weights = _fractional_weights_for_missing_iso(
            iso3,
            geom_map.get(iso3),
            lat,
            lon,
        )

        if weights.empty:
            print(f"[fallback warn] {iso3}: no usable cells")
            continue

        fallbacks[iso3] = weights

        if idx <= 5 or idx == len(missing):
            print(
                f"[fallback] {idx}/{len(missing)} {iso3} "
                f"cells={len(weights)}"
            )

    return fallbacks


def _center_country_base(
    center_mask: pd.DataFrame,
    pop_flat: np.ndarray,
    haz_flat: np.ndarray,
) -> pd.DataFrame:
    tmp = center_mask.copy()

    cells = tmp["cell"].to_numpy(dtype=np.int64)

    tmp["population"] = pop_flat[cells]
    tmp["hazard_days"] = haz_flat[cells]

    tmp = tmp.replace([np.inf, -np.inf], np.nan)
    tmp = tmp.dropna(subset=["population", "hazard_days"])
    tmp = tmp[tmp["population"] >= 0]

    return tmp


def _aggregate_center(
    base: pd.DataFrame,
    thresholds: tuple[int, ...],
) -> list[pd.DataFrame]:
    totals = (
        base.groupby("ISO_A3", as_index=False)["population"]
        .sum()
        .rename(columns={"population": "population_total"})
    )

    outputs = []

    for threshold in thresholds:
        exposed = (
            base[base["hazard_days"] >= threshold]
            .groupby("ISO_A3", as_index=False)["population"]
            .sum()
            .rename(columns={"population": "population_exposed"})
        )

        out = totals.merge(exposed, on="ISO_A3", how="left")
        out["population_exposed"] = out["population_exposed"].fillna(0.0)
        out["threshold_days"] = threshold
        out["aggregation_method"] = "grid_cell_centre"
        outputs.append(out)

    return outputs


def _aggregate_fallback(
    iso3: str,
    weights: pd.DataFrame,
    pop_flat: np.ndarray,
    haz_flat: np.ndarray,
    thresholds: tuple[int, ...],
) -> list[dict]:
    cells = weights["cell"].to_numpy(dtype=np.int64)
    w = weights["weight"].to_numpy(dtype=float)

    pop = pop_flat[cells]
    haz = haz_flat[cells]

    valid = np.isfinite(pop) & np.isfinite(haz) & (pop >= 0)

    if not valid.any():
        pop_total = 0.0
    else:
        pop_total = float(np.sum(pop[valid] * w[valid]))

    rows = []

    for threshold in thresholds:
        if valid.any():
            exposed_mask = valid & (haz >= threshold)
            exposed = float(np.sum(pop[exposed_mask] * w[exposed_mask]))
        else:
            exposed = 0.0

        rows.append(
            {
                "ISO_A3": iso3,
                "population_total": pop_total,
                "population_exposed": exposed,
                "threshold_days": threshold,
                "aggregation_method": "fractional_overlap_fallback",
            }
        )

    return rows


def _finalize_rows(
    frame: pd.DataFrame,
    names: dict[str, str],
    *,
    scenario: str,
    period: str,
    stat: str,
    hazard: str,
    population_year: int,
    population_source_key: str,
    hazard_source_file: str,
) -> pd.DataFrame:
    out = frame.copy()

    out["iso3"] = out["ISO_A3"].astype(str)
    out["country"] = out["iso3"].map(names).fillna(out["iso3"])

    out["population_total"] = pd.to_numeric(
        out["population_total"], errors="coerce"
    ).fillna(0.0)

    out["population_exposed"] = pd.to_numeric(
        out["population_exposed"], errors="coerce"
    ).fillna(0.0)

    # Defensively clip floating-point fractional allocations.
    out["population_exposed"] = np.minimum(
        out["population_exposed"],
        out["population_total"],
    )

    out["zero_population_flag"] = out["population_total"] <= 0

    out["exposed_share_pct"] = np.where(
        out["population_total"] > 0,
        out["population_exposed"] / out["population_total"] * 100.0,
        0.0,
    )

    out["scenario"] = scenario
    out["period"] = period
    out["statistic"] = stat
    out["hazard"] = hazard
    out["population_year"] = population_year
    out["population_source_key"] = population_source_key
    out["hazard_source_file"] = hazard_source_file

    keep = [
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
    ]

    return out[keep]


def _validate_layer(layer: pd.DataFrame) -> None:
    if layer.empty:
        raise RuntimeError("Exposure layer is empty.")

    if layer["iso3"].duplicated().any():
        dup = layer[layer["iso3"].duplicated(keep=False)]
        raise RuntimeError(
            "Duplicate ISO3 rows remain within one threshold layer:\n"
            + dup.head(20).to_string(index=False)
        )

    if (layer["population_total"] < 0).any():
        raise RuntimeError("Negative population totals detected.")

    if (layer["population_exposed"] < 0).any():
        raise RuntimeError("Negative exposed populations detected.")

    if (
        layer["population_exposed"]
        > layer["population_total"] + 1e-6
    ).any():
        raise RuntimeError("Exposed population exceeds total population.")

    if not layer["exposed_share_pct"].between(0, 100).all():
        raise RuntimeError("Exposure shares outside 0–100% detected.")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--all",
        action="store_true",
        help="Build all scenarios, periods, statistics and hazards.",
    )

    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=list(SCENARIOS),
    )

    parser.add_argument(
        "--periods",
        nargs="+",
        default=list(PERIODS),
    )

    parser.add_argument(
        "--stats",
        nargs="+",
        default=list(STATS),
    )

    parser.add_argument(
        "--hazards",
        nargs="+",
        default=["hd30", "hd35"],
    )

    args = parser.parse_args()

    boundaries = _read_boundaries()
    canonical_names = _canonical_country_names(boundaries)

    pop_keys = _population_keys()

    result_blocks = []

    center_mask = None
    fallbacks = None
    grid_signature = None

    total_jobs = (
        len(args.scenarios)
        * len(args.periods)
        * len(args.hazards)
        * len(args.stats)
    )
    job = 0

    for scenario in args.scenarios:
        pop_file, pop_key = _population_file(pop_keys, scenario)
        pop_ds = xr.open_dataset(pop_file)
        pop_var = _first_data_var(pop_ds)

        for period in args.periods:
            population_year = _period_midpoint(period)

            pop = _select_population_year(
                pop_ds[pop_var],
                population_year,
            ).astype("float64")

            pop = pop.where(pop >= 0)

            for hazard in args.hazards:
                if hazard not in THRESHOLDS:
                    raise ValueError(
                        f"Unsupported hazard {hazard}. "
                        f"Choose from {sorted(THRESHOLDS)}."
                    )

                for stat in args.stats:
                    job += 1
                    print(
                        f"[{job}/{total_jobs}] "
                        f"{scenario} {period} {hazard} {stat}"
                    )

                    hazard_file = _hazard_file(
                        hazard,
                        scenario,
                        period,
                        stat,
                    )

                    haz_ds = xr.open_dataset(hazard_file)
                    haz_var = list(haz_ds.data_vars)[0]
                    haz = (
                        haz_ds[haz_var]
                        .squeeze(drop=True)
                        .astype("float64")
                    )

                    pop_aligned, haz_aligned = _align_grids(
                        pop,
                        haz,
                    )

                    lat = np.asarray(
                        pop_aligned["lat"].values,
                        dtype=float,
                    )
                    lon = np.asarray(
                        pop_aligned["lon"].values,
                        dtype=float,
                    )

                    signature = (
                        len(lat),
                        len(lon),
                        float(lat[0]),
                        float(lat[-1]),
                        float(lon[0]),
                        float(lon[-1]),
                    )

                    if center_mask is None:
                        center_mask = _build_center_assignment(
                            lat,
                            lon,
                            boundaries,
                        )

                        fallbacks = _prepare_fallbacks(
                            boundaries,
                            center_mask,
                            lat,
                            lon,
                        )

                        grid_signature = signature

                    elif signature != grid_signature:
                        raise RuntimeError(
                            "Grid geometry changed between CCKP layers."
                        )

                    pop_flat = np.asarray(
                        pop_aligned.values,
                        dtype=float,
                    ).ravel()

                    haz_flat = np.asarray(
                        haz_aligned.values,
                        dtype=float,
                    ).ravel()

                    base = _center_country_base(
                        center_mask,
                        pop_flat,
                        haz_flat,
                    )

                    center_layers = _aggregate_center(
                        base,
                        THRESHOLDS[hazard],
                    )

                    fallback_rows_by_threshold = {
                        threshold: []
                        for threshold in THRESHOLDS[hazard]
                    }

                    for iso3, weights in fallbacks.items():
                        rows = _aggregate_fallback(
                            iso3,
                            weights,
                            pop_flat,
                            haz_flat,
                            THRESHOLDS[hazard],
                        )

                        for row in rows:
                            fallback_rows_by_threshold[
                                row["threshold_days"]
                            ].append(row)

                    for center_layer in center_layers:
                        threshold = int(
                            center_layer["threshold_days"].iloc[0]
                        )

                        fallback_frame = pd.DataFrame(
                            fallback_rows_by_threshold[threshold]
                        )

                        combined = pd.concat(
                            [center_layer, fallback_frame],
                            ignore_index=True,
                        )

                        final = _finalize_rows(
                            combined,
                            canonical_names,
                            scenario=scenario,
                            period=period,
                            stat=stat,
                            hazard=hazard,
                            population_year=population_year,
                            population_source_key=pop_key,
                            hazard_source_file=hazard_file.name,
                        )

                        _validate_layer(final)

                        result_blocks.append(final)

                    print(
                        f"[ok] countries="
                        f"{result_blocks[-1]['iso3'].nunique()}"
                    )

    result = pd.concat(
        result_blocks,
        ignore_index=True,
    )

    key = [
        "iso3",
        "scenario",
        "period",
        "statistic",
        "hazard",
        "threshold_days",
    ]

    duplicates = int(result.duplicated(key).sum())
    if duplicates:
        raise RuntimeError(
            f"Final exposure dataset contains {duplicates} duplicate keys."
        )

    result = result.sort_values(key).reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)

    result.to_parquet(OUT, index=False)
    result.to_csv(OUT.with_suffix(".csv"), index=False)

    print("=" * 72)
    print("[done] POPULATION EXPOSURE PRODUCTION DATASET")
    print("[done] rows:", len(result))
    print("[done] countries:", result["iso3"].nunique())
    print("[done] zero-population rows:", int(result["zero_population_flag"].sum()))
    print("[done] duplicates:", duplicates)
    print("[done] parquet:", OUT)
    print("[done] csv:", OUT.with_suffix(".csv"))
    print("=" * 72)


if __name__ == "__main__":
    main()
