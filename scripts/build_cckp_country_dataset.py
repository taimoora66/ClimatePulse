from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio.features
import xarray as xr
from affine import Affine
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform as shapely_transform


BUCKET_ROOT = "s3://wbg-cckp/data/cmip6-x0.25"
COLLECTION = "cmip6-x0.25"

DEFAULT_VARIABLES = ("tas", "pr", "hd30", "hd35")
DEFAULT_SCENARIOS = ("ssp126", "ssp245", "ssp370", "ssp585")
DEFAULT_PERIODS = ("2020-2039", "2040-2059", "2060-2079", "2080-2099")
DEFAULT_STATS = ("p10", "median", "p90")

PRODUCTS_BY_VARIABLE = {
    "tas": ("anomaly", "climatology"),
    "pr": ("anomaly", "climatology"),
    "hd30": ("climatology",),
    "hd35": ("climatology",),
}

ISO3_CANDIDATES = (
    "ISO_A3",
    "ISO3",
    "ISO3_CODE",
    "ADM0_A3",
    "WB_A3",
    "SOV_A3",
    "GID_0",
    "ADM0_ISO",
    "CNTR_ID",
    "ISO",
)

# World Bank WB_GAD_ADM0 uses NAM_0 for the readable country/territory name.
NAME_CANDIDATES = (
    "NAM_0",
    "NAME_EN",
    "NAME",
    "ADMIN",
    "SOVEREIGN",
    "SOVEREIGNT",
    "COUNTRY",
    "CNTR_NAME",
    "WB_NAME",
    "NAME_LONG",
)


def find_aws_executable() -> str:
    exe = shutil.which("aws")
    if exe:
        return exe

    windows_path = Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe")
    if windows_path.exists():
        return str(windows_path)

    raise RuntimeError(
        "AWS CLI not found. Confirm that `aws --version` works "
        "or install AWS CLI v2."
    )


def run_aws_cp(s3_uri: str, local_path: Path) -> None:
    aws = find_aws_executable()
    local_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        aws,
        "s3",
        "cp",
        s3_uri,
        str(local_path),
        "--no-sign-request",
        "--only-show-errors",
    ]

    subprocess.run(command, check=True)


def extract_boundary_zip(boundary_zip: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    marker = extract_dir / ".extracted_ok"

    if marker.exists():
        return

    with zipfile.ZipFile(boundary_zip) as archive:
        archive.extractall(extract_dir)

    marker.write_text("ok", encoding="utf-8")


def find_adm0_shapefile(extract_dir: Path) -> Path:
    shapefiles = list(extract_dir.rglob("*.shp"))

    if not shapefiles:
        raise RuntimeError(f"No shapefile found under {extract_dir}")

    def score(path: Path) -> int:
        name = path.name.lower()
        value = 0

        scoring = (
            ("adm0", 100),
            ("admin0", 100),
            ("sovereign", 80),
            ("country", 60),
            ("global", 20),
            ("adm1", -100),
            ("admin1", -100),
            ("adm2", -100),
            ("admin2", -100),
        )

        for token, weight in scoring:
            if token in name:
                value += weight

        try:
            value += int(path.stat().st_size / 1_000_000)
        except OSError:
            pass

        return value

    selected = max(shapefiles, key=score)
    print(f"[boundaries] selected shapefile: {selected}")
    return selected


def detect_column(columns, candidates, kind: str) -> str:
    upper_map = {column.upper(): column for column in columns}

    for candidate in candidates:
        if candidate.upper() in upper_map:
            return upper_map[candidate.upper()]

    raise RuntimeError(
        f"Could not identify {kind} column.\n"
        f"Available columns: {list(columns)}\n"
        f"Expected one of: {list(candidates)}"
    )


def clean_boundaries(shp_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path)

    if gdf.empty:
        raise RuntimeError("Boundary shapefile is empty.")

    if gdf.crs is None:
        raise RuntimeError("Boundary shapefile has no CRS.")

    gdf = gdf.to_crs("EPSG:4326")

    iso_col = detect_column(gdf.columns, ISO3_CANDIDATES, "ISO3")
    name_col = detect_column(gdf.columns, NAME_CANDIDATES, "country name")

    print(f"[boundaries] ISO3 field: {iso_col}")
    print(f"[boundaries] name field: {name_col}")

    out = gdf[[iso_col, name_col, "geometry"]].copy()
    out.columns = ["iso3", "country", "geometry"]

    out["iso3"] = (
        out["iso3"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    out["country"] = (
        out["country"]
        .astype(str)
        .str.strip()
    )

    out = out[
        out["iso3"].str.fullmatch(r"[A-Z]{3}", na=False)
    ].copy()

    out = out[
        out.geometry.notnull()
        & ~out.geometry.is_empty
    ].copy()

    if out.empty:
        raise RuntimeError("No usable country geometries remain after filtering.")

    # Repair source topology before dissolve.
    out["geometry"] = out.geometry.make_valid()

    out = out[
        out.geometry.notnull()
        & ~out.geometry.is_empty
    ].copy()

    invalid_mask = ~out.geometry.is_valid

    if invalid_mask.any():
        print(
            f"[boundaries] repairing "
            f"{int(invalid_mask.sum())} remaining invalid geometries"
        )
        out.loc[invalid_mask, "geometry"] = (
            out.loc[invalid_mask, "geometry"].buffer(0)
        )

    out = out[
        out.geometry.notnull()
        & ~out.geometry.is_empty
        & out.geometry.is_valid
    ].copy()

    if out.empty:
        raise RuntimeError(
            "All geometries became invalid after geometry repair."
        )

    out = out.dissolve(
        by="iso3",
        as_index=False,
        aggfunc={"country": "first"},
    )

    out["geometry"] = out.geometry.make_valid()

    out = out[
        out.geometry.notnull()
        & ~out.geometry.is_empty
        & out.geometry.is_valid
    ].copy()

    return out.reset_index(drop=True)


def grid_from_dataset(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    lat_name = "lat" if "lat" in ds.coords else "latitude"
    lon_name = "lon" if "lon" in ds.coords else "longitude"

    if lat_name not in ds.coords or lon_name not in ds.coords:
        raise RuntimeError(
            f"Latitude/longitude coordinates not found. "
            f"Available coords: {list(ds.coords)}"
        )

    lat = np.asarray(ds[lat_name].values, dtype=float)
    lon = np.asarray(ds[lon_name].values, dtype=float)

    if lat.ndim != 1 or lon.ndim != 1:
        raise RuntimeError(
            "Expected one-dimensional latitude and longitude coordinates."
        )

    return lat, lon


def rasterize_country_ids(
    boundaries: gpd.GeoDataFrame,
    lat: np.ndarray,
    lon: np.ndarray,
) -> tuple[np.ndarray, pd.DataFrame]:
    dlat = float(np.median(np.diff(lat)))
    dlon = float(np.median(np.diff(lon)))

    yres = abs(dlat)
    xres = abs(dlon)

    lat_north = float(np.max(lat))
    lon_west = float(np.min(lon))

    transform = (
        Affine.translation(
            lon_west - xres / 2,
            lat_north + yres / 2,
        )
        * Affine.scale(
            xres,
            -yres,
        )
    )

    lookup = (
        boundaries[["iso3", "country"]]
        .copy()
        .reset_index(drop=True)
    )

    lookup["country_id"] = np.arange(
        1,
        len(lookup) + 1,
        dtype=np.int32,
    )

    shapes = [
        (geometry, int(country_id))
        for geometry, country_id in zip(
            boundaries.geometry,
            lookup["country_id"],
        )
        if geometry is not None and not geometry.is_empty
    ]

    north_up = rasterio.features.rasterize(
        shapes=shapes,
        out_shape=(len(lat), len(lon)),
        fill=0,
        transform=transform,
        all_touched=False,
        dtype="int32",
    )

    # Verified CCKP latitudes increase south -> north.
    country_ids = (
        np.flipud(north_up)
        if lat[0] < lat[-1]
        else north_up
    )

    return country_ids, lookup


def weighted_country_means(
    arr: np.ndarray,
    country_ids: np.ndarray,
    lat: np.ndarray,
    n_countries: int,
) -> np.ndarray:
    if arr.shape != country_ids.shape:
        raise RuntimeError(
            f"Climate/boundary grid mismatch: "
            f"climate={arr.shape}, countries={country_ids.shape}"
        )

    row_weights = np.cos(
        np.deg2rad(lat)
    ).astype(np.float64)

    weights = np.broadcast_to(
        row_weights[:, None],
        arr.shape,
    )

    valid = (
        np.isfinite(arr)
        & (country_ids > 0)
        & np.isfinite(weights)
        & (weights > 0)
    )

    ids = country_ids[valid].astype(np.int64)
    values = arr[valid].astype(np.float64)
    valid_weights = weights[valid].astype(np.float64)

    weighted_sum = np.bincount(
        ids,
        weights=values * valid_weights,
        minlength=n_countries + 1,
    )

    weight_sum = np.bincount(
        ids,
        weights=valid_weights,
        minlength=n_countries + 1,
    )

    means = np.full(
        n_countries + 1,
        np.nan,
        dtype=float,
    )

    good = weight_sum > 0

    means[good] = (
        weighted_sum[good]
        / weight_sum[good]
    )

    return means


def _candidate_indices(
    values: np.ndarray,
    lower: float,
    upper: float,
    half_cell: float,
) -> np.ndarray:
    mask = (
        (values >= lower - half_cell)
        & (values <= upper + half_cell)
    )
    return np.flatnonzero(mask)


def build_fractional_overlap_fallback(
    boundaries: gpd.GeoDataFrame,
    lookup: pd.DataFrame,
    country_ids: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
) -> dict[int, dict]:
    """
    Build exact polygon/cell overlap weights only for entities that received
    zero centre-based grid cells. This keeps the main aggregation fast while
    providing defensible coverage for microstates and small islands.
    """
    primary_ids = set(
        int(x)
        for x in np.unique(country_ids)
        if int(x) > 0
    )

    id_by_iso3 = dict(
        zip(
            lookup["iso3"],
            lookup["country_id"],
        )
    )

    missing_iso3 = [
        iso3
        for iso3, country_id in id_by_iso3.items()
        if int(country_id) not in primary_ids
    ]

    print(
        f"[fallback] {len(missing_iso3)} entities "
        f"have no centre-based grid cell"
    )

    if not missing_iso3:
        return {}

    dlat = abs(float(np.median(np.diff(lat))))
    dlon = abs(float(np.median(np.diff(lon))))

    to_equal_area = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:6933",
        always_xy=True,
    ).transform

    boundary_by_iso = boundaries.set_index("iso3")
    fallback: dict[int, dict] = {}

    for iso3 in missing_iso3:
        country_id = int(id_by_iso3[iso3])
        geometry = boundary_by_iso.loc[iso3, "geometry"]

        if geometry is None or geometry.is_empty:
            continue

        minx, miny, maxx, maxy = geometry.bounds

        row_idx = _candidate_indices(
            lat,
            miny,
            maxy,
            dlat / 2,
        )

        col_idx = _candidate_indices(
            lon,
            minx,
            maxx,
            dlon / 2,
        )

        geometry_equal_area = shapely_transform(
            to_equal_area,
            geometry,
        )

        cells = []

        for i in row_idx:
            lat_center = float(lat[i])

            for j in col_idx:
                lon_center = float(lon[j])

                cell = box(
                    lon_center - dlon / 2,
                    lat_center - dlat / 2,
                    lon_center + dlon / 2,
                    lat_center + dlat / 2,
                )

                intersection = geometry.intersection(cell)

                if intersection.is_empty:
                    continue

                intersection_equal_area = shapely_transform(
                    to_equal_area,
                    intersection,
                )

                area = float(
                    intersection_equal_area.area
                )

                if area > 0:
                    cells.append(
                        (
                            int(i),
                            int(j),
                            area,
                        )
                    )

        method = "fractional_overlap_equal_area"

        # Emergency fallback for pathological/very tiny geometries that still
        # fail to intersect a candidate 0.25° cell because of topology or
        # antimeridian edge cases.
        if not cells:
            point = geometry.representative_point()

            i = int(
                np.argmin(
                    np.abs(
                        lat - float(point.y)
                    )
                )
            )

            j = int(
                np.argmin(
                    np.abs(
                        lon - float(point.x)
                    )
                )
            )

            cells = [
                (
                    i,
                    j,
                    1.0,
                )
            ]

            method = "representative_point_nearest_grid_cell"

        fallback[country_id] = {
            "iso3": iso3,
            "cells": cells,
            "method": method,
        }

    print(
        f"[fallback] prepared "
        f"{len(fallback)} small-entity fallbacks"
    )

    return fallback


def apply_fallback_means(
    means: np.ndarray,
    arr: np.ndarray,
    fallback: dict[int, dict],
) -> tuple[np.ndarray, dict[int, str]]:
    methods: dict[int, str] = {}

    for country_id, spec in fallback.items():
        values = []
        weights = []

        for row, col, weight in spec["cells"]:
            value = float(arr[row, col])

            if not np.isfinite(value):
                continue

            if weight <= 0:
                continue

            values.append(value)
            weights.append(float(weight))

        if values:
            means[country_id] = float(
                np.average(
                    values,
                    weights=weights,
                )
            )

            methods[country_id] = spec["method"]

    return means, methods


def make_key(
    variable: str,
    scenario: str,
    product: str,
    stat: str,
    period: str,
) -> str:
    filename = (
        f"{product}-{variable}-annual-mean_"
        f"{COLLECTION}_ensemble-all-{scenario}_"
        f"climatology_{stat}_{period}.nc"
    )

    return (
        f"{BUCKET_ROOT}/"
        f"{variable}/"
        f"ensemble-all-{scenario}/"
        f"{filename}"
    )


def process_one(
    local_file: Path,
    country_ids: np.ndarray,
    lookup: pd.DataFrame,
    lat: np.ndarray,
    fallback: dict[int, dict],
    variable: str,
    scenario: str,
    product: str,
    stat: str,
    period: str,
) -> pd.DataFrame:
    with xr.open_dataset(local_file) as ds:
        data_variables = list(ds.data_vars)

        if not data_variables:
            raise RuntimeError(
                f"No data variables found in {local_file}"
            )

        variable_name = data_variables[0]
        data_array = ds[variable_name]

        if "time" in data_array.dims:
            data_array = data_array.isel(time=0)

        arr = np.asarray(
            data_array.values,
            dtype=float,
        )

        means = weighted_country_means(
            arr,
            country_ids,
            lat,
            len(lookup),
        )

        means, fallback_methods = apply_fallback_means(
            means,
            arr,
            fallback,
        )

        units = str(
            data_array.attrs.get(
                "units",
                "",
            )
        )

        long_name = str(
            data_array.attrs.get(
                "long_name",
                "",
            )
        )

        percentile = data_array.attrs.get(
            "percentile"
        )

        models = str(
            data_array.attrs.get(
                "models_in_ensemble",
                "",
            )
        )

        doi = str(
            ds.attrs.get(
                "wb_cmip6-x0.25_doi",
                "",
            )
        )

    rows = lookup.copy()

    rows["value"] = rows["country_id"].map(
        lambda country_id: means[int(country_id)]
    )

    def method_for(country_id: int) -> str:
        return fallback_methods.get(
            int(country_id),
            "centre_cell_mask_coslat_area_weighted",
        )

    rows["aggregation_method"] = rows["country_id"].map(
        method_for
    )

    rows["indicator"] = variable
    rows["scenario"] = scenario
    rows["period"] = period
    rows["statistic"] = stat
    rows["value_type"] = product
    rows["unit"] = units
    rows["variable_long_name"] = long_name
    rows["ensemble_percentile"] = percentile
    rows["models_in_ensemble"] = models

    rows["source"] = (
        "World Bank Climate Change Knowledge Portal "
        "(CMIP6-x0.25)"
    )

    rows["source_doi"] = doi

    rows["reference_period"] = (
        "1995-2014"
        if product == "anomaly"
        else ""
    )

    return rows.drop(
        columns=["country_id"]
    )


def build(args: argparse.Namespace) -> None:
    boundary_zip = Path(
        args.boundary_zip
    ).resolve()

    if not boundary_zip.exists():
        raise FileNotFoundError(
            boundary_zip
        )

    workdir = Path(
        args.workdir
    ).resolve()

    cache_dir = (
        workdir
        / "netcdf_cache"
    )

    boundary_dir = (
        workdir
        / "boundaries"
    )

    cache_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    extract_boundary_zip(
        boundary_zip,
        boundary_dir,
    )

    shapefile = find_adm0_shapefile(
        boundary_dir
    )

    boundaries = clean_boundaries(
        shapefile
    )

    print(
        f"[boundaries] "
        f"{len(boundaries)} ISO3 entities"
    )

    sample_key = make_key(
        "tas",
        "ssp245",
        "climatology",
        "median",
        "2040-2059",
    )

    sample_file = (
        cache_dir
        / Path(sample_key).name
    )

    if not sample_file.exists():
        print(
            f"[download] sample "
            f"{sample_key}"
        )

        run_aws_cp(
            sample_key,
            sample_file,
        )

    with xr.open_dataset(
        sample_file
    ) as ds:
        lat, lon = grid_from_dataset(
            ds
        )

    print(
        f"[grid] "
        f"lat={len(lat)} "
        f"lon={len(lon)} "
        f"lat_range=({lat.min()}, {lat.max()}) "
        f"lon_range=({lon.min()}, {lon.max()})"
    )

    country_ids, lookup = rasterize_country_ids(
        boundaries,
        lat,
        lon,
    )

    assigned_cells = int(
        (country_ids > 0).sum()
    )

    represented_ids = set(
        int(x)
        for x in np.unique(country_ids)
        if int(x) > 0
    )

    print(
        f"[mask] "
        f"{assigned_cells:,} grid cells "
        f"assigned to countries"
    )

    print(
        f"[mask] "
        f"{len(represented_ids)} / "
        f"{len(lookup)} entities represented "
        f"by centre-based cells"
    )

    fallback = build_fractional_overlap_fallback(
        boundaries,
        lookup,
        country_ids,
        lat,
        lon,
    )

    frames: list[pd.DataFrame] = []

    total = sum(
        len(
            PRODUCTS_BY_VARIABLE.get(
                variable,
                ("climatology",),
            )
        )
        * len(args.scenarios)
        * len(args.periods)
        * len(args.stats)
        for variable in args.variables
    )

    done = 0

    for variable in args.variables:
        products = PRODUCTS_BY_VARIABLE.get(
            variable,
            ("climatology",),
        )

        for scenario in args.scenarios:
            for product in products:
                for period in args.periods:
                    for stat in args.stats:
                        done += 1

                        key = make_key(
                            variable,
                            scenario,
                            product,
                            stat,
                            period,
                        )

                        local_file = (
                            cache_dir
                            / Path(key).name
                        )

                        try:
                            if not local_file.exists():
                                print(
                                    f"[{done}/{total}] "
                                    f"download "
                                    f"{Path(key).name}"
                                )

                                run_aws_cp(
                                    key,
                                    local_file,
                                )
                            else:
                                print(
                                    f"[{done}/{total}] "
                                    f"cached "
                                    f"{Path(key).name}"
                                )

                            frame = process_one(
                                local_file,
                                country_ids,
                                lookup,
                                lat,
                                fallback,
                                variable,
                                scenario,
                                product,
                                stat,
                                period,
                            )

                            frames.append(
                                frame
                            )

                        except subprocess.CalledProcessError as exc:
                            print(
                                f"[ERROR] "
                                f"AWS download failed "
                                f"for {key}: {exc}",
                                file=sys.stderr,
                            )

                        except Exception as exc:
                            print(
                                f"[ERROR] "
                                f"Processing failed "
                                f"for {key}: "
                                f"{type(exc).__name__}: {exc}",
                                file=sys.stderr,
                            )

                        finally:
                            if (
                                local_file.exists()
                                and not args.keep_downloads
                                and local_file != sample_file
                            ):
                                try:
                                    local_file.unlink()
                                except OSError:
                                    pass

    if not frames:
        raise RuntimeError(
            "No climate files were successfully processed."
        )

    out = pd.concat(
        frames,
        ignore_index=True,
    )

    out["value"] = pd.to_numeric(
        out["value"],
        errors="coerce",
    )

    out = out[
        np.isfinite(
            out["value"]
        )
    ].copy()

    scenario_labels = {
        "ssp126": "SSP1-2.6",
        "ssp245": "SSP2-4.5",
        "ssp370": "SSP3-7.0",
        "ssp585": "SSP5-8.5",
    }

    indicator_labels = {
        "tas": "Mean temperature",
        "pr": "Precipitation",
        "hd30": "Hot days above 30°C",
        "hd35": "Hot days above 35°C",
    }

    out["scenario_label"] = (
        out["scenario"]
        .map(scenario_labels)
        .fillna(out["scenario"])
    )

    out["indicator_label"] = (
        out["indicator"]
        .map(indicator_labels)
        .fillna(out["indicator"])
    )

    output = Path(
        args.output
    ).resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    out = out.sort_values(
        [
            "iso3",
            "indicator",
            "scenario",
            "value_type",
            "period",
            "statistic",
        ]
    ).reset_index(
        drop=True
    )

    out.to_parquet(
        output,
        index=False,
    )

    csv_output = output.with_suffix(
        ".csv"
    )

    out.to_csv(
        csv_output,
        index=False,
    )

    print(
        f"[done] rows={len(out):,}"
    )

    print(
        f"[done] countries="
        f"{out['iso3'].nunique()}"
    )

    fallback_rows = int(
        out["aggregation_method"]
        .ne("centre_cell_mask_coslat_area_weighted")
        .sum()
    )

    print(
        f"[done] fallback rows="
        f"{fallback_rows:,}"
    )

    print(
        f"[done] parquet={output}"
    )

    print(
        f"[done] csv={csv_output}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build ORBIDENSE country-level CMIP6 projections "
            "from the World Bank CCKP public S3 archive."
        )
    )

    parser.add_argument(
        "--boundary-zip",
        required=True,
        help=(
            "Path to the World Bank sovereignty/admin boundary ZIP."
        ),
    )

    parser.add_argument(
        "--workdir",
        default=(
            "data/climate_intelligence/"
            "cckp_build"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/climate_intelligence/"
            "cckp_country_projections.parquet"
        ),
    )

    parser.add_argument(
        "--variables",
        nargs="+",
        default=list(
            DEFAULT_VARIABLES
        ),
    )

    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=list(
            DEFAULT_SCENARIOS
        ),
    )

    parser.add_argument(
        "--periods",
        nargs="+",
        default=list(
            DEFAULT_PERIODS
        ),
    )

    parser.add_argument(
        "--stats",
        nargs="+",
        default=list(
            DEFAULT_STATS
        ),
    )

    parser.add_argument(
        "--keep-downloads",
        action="store_true",
        help=(
            "Keep downloaded NetCDF files instead of "
            "deleting them after aggregation."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    build(
        parse_args()
    )