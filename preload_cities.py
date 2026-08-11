import argparse
import csv
import hashlib
import sys
import time
from pathlib import Path

from src.api.maptiler_search import search_maptiler_places
from src.api.weather import (
    HistoricalWeatherRateLimitError,
    HistoricalWeatherUnavailableError,
    get_historical_weather,
)
from src.db import (
    city_has_complete_history,
    get_existing_history_years,
    insert_weather_daily,
    upsert_city,
)


HISTORY_START_YEAR = 1990
HISTORY_END_YEAR = 2025


def stable_external_id(value):
    """
    Convert a MapTiler feature id into the same stable BIGINT-style
    identifier used by ClimatePulse.
    """
    digest = hashlib.blake2b(
        str(value).encode("utf-8"),
        digest_size=8,
    ).digest()

    number = int.from_bytes(
        digest,
        byteorder="big",
        signed=False,
    )

    return number & 0x7FFFFFFFFFFFFFFF


def first_nonempty(*values):
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def feature_coordinates(feature):
    center = feature.get("center")

    if (
        isinstance(center, (list, tuple))
        and len(center) >= 2
    ):
        return float(center[0]), float(center[1])

    geometry = feature.get("geometry", {})

    if geometry.get("type") == "Point":
        coordinates = geometry.get("coordinates")

        if (
            isinstance(coordinates, (list, tuple))
            and len(coordinates) >= 2
        ):
            return (
                float(coordinates[0]),
                float(coordinates[1]),
            )

    return None


def context_value(feature, wanted_types):
    wanted_types = {
        str(value).lower()
        for value in wanted_types
    }

    for item in feature.get("context", []):
        item_types = item.get("place_type", [])

        if isinstance(item_types, str):
            item_types = [item_types]

        item_types = {
            str(value).lower()
            for value in item_types
        }

        item_id = str(
            item.get("id", "")
        ).lower()

        matches = bool(
            item_types.intersection(
                wanted_types
            )
        )

        if not matches:
            matches = any(
                item_id.startswith(
                    value
                )
                for value in wanted_types
            )

        if matches:
            properties = item.get(
                "properties",
                {},
            )

            name = first_nonempty(
                item.get("text_en"),
                item.get("text"),
                properties.get("name_en"),
                properties.get("name"),
            )

            short_code = first_nonempty(
                item.get("short_code"),
                properties.get("short_code"),
                properties.get("country_code"),
            )

            return name, short_code

    return None, None


def feature_name(feature):
    properties = feature.get(
        "properties",
        {},
    )

    return first_nonempty(
        feature.get("text_en"),
        feature.get("text"),
        properties.get("name_en"),
        properties.get("name"),
        feature.get("name"),
    ) or "Unknown location"


def feature_place_types(feature):
    values = feature.get(
        "place_type",
        [],
    )

    if isinstance(values, str):
        values = [values]

    return {
        str(value).lower()
        for value in values
        if value
    }


def choose_best_feature(features):
    """
    Prefer real populated/municipal place results over country-level
    or POI results.
    """
    priority = {
        "place": 100,
        "municipality": 95,
        "locality": 90,
        "neighbourhood": 80,
        "region": 60,
        "subregion": 55,
        "county": 50,
        "address": 20,
        "poi": 10,
        "country": 0,
    }

    ranked = []

    for feature in features:
        if feature_coordinates(feature) is None:
            continue

        types = feature_place_types(
            feature
        )

        score = max(
            (
                priority.get(
                    feature_type,
                    1,
                )
                for feature_type in types
            ),
            default=1,
        )

        relevance = feature.get(
            "relevance"
        )

        try:
            score += (
                float(relevance)
                * 10
            )
        except (TypeError, ValueError):
            pass

        ranked.append(
            (
                score,
                feature,
            )
        )

    if not ranked:
        return None

    ranked.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return ranked[0][1]


def resolve_location(query):
    """
    Resolve a preload query through MapTiler using international
    English display names.
    """
    features = search_maptiler_places(
        query,
        limit=10,
        language="en",
    )

    feature = choose_best_feature(
        features
    )

    if feature is None:
        raise RuntimeError(
            f"No usable MapTiler result for: {query}"
        )

    coordinates = feature_coordinates(
        feature
    )

    longitude, latitude = coordinates

    country_name, country_code = context_value(
        feature,
        {
            "country",
        },
    )

    admin1, _ = context_value(
        feature,
        {
            "region",
            "subregion",
            "state",
            "province",
        },
    )

    properties = feature.get(
        "properties",
        {},
    )

    if not country_name:
        country_name = first_nonempty(
            properties.get("country_name_en"),
            properties.get("country_name"),
            properties.get("country"),
        )

    if country_code:
        country_code = (
            str(country_code)
            .split("-")[-1]
            .upper()
        )

    external_source_id = (
        feature.get("id")
        or (
            f"{feature_name(feature)}|"
            f"{latitude:.6f}|"
            f"{longitude:.6f}"
        )
    )

    return {
        "id": stable_external_id(
            external_source_id
        ),
        "name": feature_name(
            feature
        ),
        "country": country_name,
        "country_code": country_code,
        "admin1": admin1,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "population": (
            properties.get("population")
            or feature.get("population")
        ),
    }


def load_queries(csv_path):
    rows = []

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row in reader:
            query = (
                row.get("query")
                or ""
            ).strip()

            if not query:
                continue

            rows.append(
                {
                    "priority": int(
                        row.get(
                            "priority",
                            len(rows) + 1,
                        )
                    ),
                    "query": query,
                }
            )

    rows.sort(
        key=lambda row: row[
            "priority"
        ]
    )

    return rows


def preload_city(
    query,
    stop_on_rate_limit=True,
):
    print()
    print("=" * 72)
    print(f"Resolving: {query}")

    location = resolve_location(
        query
    )

    display_name = (
        f"{location.get('name')}, "
        f"{location.get('country')}"
    )

    print(
        f"Resolved to: {display_name}"
    )

    city_id = upsert_city(
        location
    )

    if city_has_complete_history(
        city_id
    ):
        print(
            "History already complete in Neon — skipped."
        )

        return {
            "status": "already_ready",
            "city_id": city_id,
            "location": location,
        }

    existing_years = (
        get_existing_history_years(
            city_id
        )
    )

    missing_years = [
        year
        for year in range(
            HISTORY_START_YEAR,
            HISTORY_END_YEAR + 1,
        )
        if year not in existing_years
    ]

    total_years = (
        HISTORY_END_YEAR
        - HISTORY_START_YEAR
        + 1
    )

    print(
        f"Already stored: "
        f"{total_years - len(missing_years)}/{total_years} years"
    )

    for index, year in enumerate(
        missing_years,
        start=1,
    ):
        print(
            f"  [{index}/{len(missing_years)}] "
            f"Importing {year}...",
            end=" ",
            flush=True,
        )

        try:
            weather = get_historical_weather(
                latitude=location[
                    "latitude"
                ],
                longitude=location[
                    "longitude"
                ],
                start_date=f"{year}-01-01",
                end_date=f"{year}-12-31",
                timezone=location.get(
                    "timezone",
                    "auto",
                ),
            )

            records_saved = (
                insert_weather_daily(
                    city_id,
                    weather,
                )
            )

            print(
                f"OK ({records_saved} daily rows)"
            )

        except HistoricalWeatherRateLimitError as error:
            wait_seconds = (
                error.retry_after_seconds
                or 60
            )

            print(
                "RATE LIMITED"
            )

            print(
                f"Open-Meteo asked us to wait about "
                f"{int(wait_seconds)} seconds."
            )

            if stop_on_rate_limit:
                print(
                    "Stopping safely. Run the same command later; "
                    "completed years will be skipped automatically."
                )

                return {
                    "status": "rate_limited",
                    "city_id": city_id,
                    "location": location,
                }

            time.sleep(
                wait_seconds
            )

        except HistoricalWeatherUnavailableError as error:
            print(
                "TEMPORARILY UNAVAILABLE"
            )

            print(
                str(error)
            )

            print(
                "Stopping safely so we do not hammer the provider."
            )

            return {
                "status": "unavailable",
                "city_id": city_id,
                "location": location,
            }

    complete = city_has_complete_history(
        city_id
    )

    print()

    if complete:
        print(
            f"COMPLETE: {display_name} now has "
            "1990–2025 history in Neon."
        )

        return {
            "status": "ready",
            "city_id": city_id,
            "location": location,
        }

    print(
        "Import ended but coverage is still incomplete. "
        "Run the preloader again to resume."
    )

    return {
        "status": "partial",
        "city_id": city_id,
        "location": location,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Preload popular ClimatePulse locations into Neon "
            "using resumable yearly ERA5 imports."
        )
    )

    parser.add_argument(
        "--csv",
        default="preload_cities.csv",
        help=(
            "CSV file containing priority and query columns."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help=(
            "Maximum number of city queries to process in this run. "
            "Default: 3."
        ),
    )

    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help=(
            "1-based row position in the priority-sorted CSV."
        ),
    )

    parser.add_argument(
        "--city",
        default=None,
        help=(
            "Preload one city directly, e.g. "
            '--city "Rome, Italy".'
        ),
    )

    args = parser.parse_args()

    if args.city:
        preload_city(
            args.city
        )

        return

    csv_path = Path(
        args.csv
    )

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Preload list not found: {csv_path}"
        )

    rows = load_queries(
        csv_path
    )

    start_index = max(
        args.start - 1,
        0,
    )

    selected_rows = rows[
        start_index:
        start_index + max(args.limit, 0)
    ]

    if not selected_rows:
        print(
            "No rows selected."
        )

        return

    print(
        "ClimatePulse preload run"
    )

    print(
        f"Selected {len(selected_rows)} location(s)."
    )

    for row in selected_rows:
        result = preload_city(
            row["query"]
        )

        if result["status"] in {
            "rate_limited",
            "unavailable",
        }:
            # Protect the free endpoint.
            break


if __name__ == "__main__":
    main()
