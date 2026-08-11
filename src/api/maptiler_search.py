import os
import urllib.parse

import requests
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

def get_maptiler_key():

    try:
        if "MAPTILER_KEY" in st.secrets:
            return st.secrets["MAPTILER_KEY"]
    except Exception:
        pass

    return os.getenv(
        "MAPTILER_KEY"
    )


MAPTILER_KEY = get_maptiler_key()

GEOCODING_URL = (
    "https://api.maptiler.com/geocoding"
)


# =========================================================
# MAPTILER SEARCH
# =========================================================

def search_maptiler_places(
    query,
    limit=10,
):
    """
    Search MapTiler for countries, regions,
    cities, towns, villages and addresses.

    MapTiler already enables fuzzy matching
    and autocomplete by default.
    """

    query = query.strip()

    if len(query) < 2:
        return []

    if not MAPTILER_KEY:
        raise RuntimeError(
            "MAPTILER_KEY is missing from .env"
        )

    # MapTiler allows a maximum of 10 results.
    limit = max(
        1,
        min(
            int(limit),
            10,
        ),
    )

    encoded_query = urllib.parse.quote(
        query,
        safe="",
    )

    url = (
        f"{GEOCODING_URL}/"
        f"{encoded_query}.json"
    )

    # IMPORTANT:
    # Do NOT send autocomplete or fuzzyMatch.
    # Both are already enabled by default.
    params = {
        "key": MAPTILER_KEY,
        "limit": limit,
    }

    response = requests.get(
        url,
        params=params,
        timeout=15,
    )

    if not response.ok:

        raise RuntimeError(
            "MapTiler search failed: "
            f"{response.status_code} "
            f"{response.text[:300]}"
        )

    data = response.json()

    return data.get(
        "features",
        []
    )