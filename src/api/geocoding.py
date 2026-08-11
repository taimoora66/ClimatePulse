import unicodedata
from functools import lru_cache

import requests

from rapidfuzz import fuzz


GEOCODING_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)


def normalize_text(text):
    """
    Normalize text for better fuzzy matching.

    Examples:
    Milán -> Milan
    München -> Munchen
    """

    if not text:
        return ""

    text = text.strip()

    normalized = unicodedata.normalize(
        "NFKD",
        text
    )

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )

    return normalized


@lru_cache(maxsize=500)
def _search_api(
    query,
    language="en",
    count=15,
):
    """
    Cached Open-Meteo geocoding request.
    """

    params = {
        "name": query,
        "count": count,
        "language": language,
        "format": "json",
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    return data.get(
        "results",
        []
    )


def fuzzy_score(
    query,
    result,
):
    """
    Score a location result against
    the user's search text.
    """

    normalized_query = (
        normalize_text(query)
        .lower()
    )

    name = normalize_text(
        result.get(
            "name",
            ""
        )
    ).lower()

    admin1 = normalize_text(
        result.get(
            "admin1",
            ""
        )
    ).lower()

    country = normalize_text(
        result.get(
            "country",
            ""
        )
    ).lower()

    full_location = " ".join(
        value
        for value in [
            name,
            admin1,
            country,
        ]
        if value
    )

    name_score = fuzz.WRatio(
        normalized_query,
        name,
    )

    full_score = fuzz.WRatio(
        normalized_query,
        full_location,
    )

    prefix_bonus = 0

    if name.startswith(
        normalized_query
    ):
        prefix_bonus = 10

    population = (
        result.get(
            "population"
        )
        or 0
    )

    population_bonus = min(
        population
        / 1_000_000,
        8,
    )

    return (
        max(
            name_score,
            full_score,
        )
        + prefix_bonus
        + population_bonus
    )


def search_locations(
    city_name,
    count=12,
):
    """
    Flexible multilingual and fuzzy
    city/place search.
    """

    original = city_name.strip()

    if len(original) < 2:
        return []

    normalized = normalize_text(
        original
    )

    queries = []

    for query in [
        original,
        normalized,
    ]:

        if (
            query
            and query not in queries
        ):
            queries.append(
                query
            )

    languages = [
        "en",
        "it",
        "de",
        "fr",
        "es",
        "pt",
    ]

    unique_results = {}

    for query in queries:

        for language in languages:

            try:

                api_results = (
                    _search_api(
                        query=query,
                        language=language,
                        count=15,
                    )
                )

            except requests.RequestException:
                continue

            for result in api_results:

                location_id = (
                    result.get(
                        "id"
                    )
                )

                if location_id is None:
                    continue

                if (
                    location_id
                    not in unique_results
                ):

                    unique_results[
                        location_id
                    ] = result

    results = list(
        unique_results.values()
    )

    results.sort(
        key=lambda item: fuzzy_score(
            original,
            item,
        ),
        reverse=True,
    )

    return results[:count]