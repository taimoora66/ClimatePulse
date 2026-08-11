import os
import urllib.parse

import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


def get_maptiler_key():
    try:
        if "MAPTILER_KEY" in st.secrets:
            return st.secrets[
                "MAPTILER_KEY"
            ]
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

SEARCH_TYPES = ",".join(
    [
        "country",
        "region",
        "subregion",
        "county",
        "joint_municipality",
        "joint_submunicipality",
        "municipality",
        "municipal_district",
        "locality",
        "neighbourhood",
        "place",
        "postal_code",
        "address",
        "road",
        "poi",
    ]
)


def search_maptiler_places(
    query,
    limit=10,
    language="en",
):
    """
    Global forward geocoding.

    Design goals:
    - fuzzy/autocomplete behavior is left at MapTiler's
      documented defaults;
    - English is requested for international display names;
    - matching_text / matching_place_name returned by
      MapTiler can still preserve the user's local-language
      match;
    - small settlements, neighbourhoods, administrative
      areas, addresses and POIs are explicitly searchable;
    - proximity=ip is only a ranking bias for ambiguous
      names; it does not geographically restrict results.
    """
    query = str(query).strip()

    if len(query) < 2:
        return []

    if not MAPTILER_KEY:
        raise RuntimeError(
            "MAPTILER_KEY is missing. "
            "Configure it in Streamlit Secrets "
            "or in the local .env file."
        )

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

    params = {
        "key": MAPTILER_KEY,
        "limit": limit,
        "language": language,
        "types": SEARCH_TYPES,
        "proximity": "ip",
        "worldview": "default",
    }

    response = requests.get(
        url,
        params=params,
        timeout=12,
    )

    if not response.ok:
        raise RuntimeError(
            "MapTiler search failed: "
            f"{response.status_code} "
            f"{response.text[:300]}"
        )

    data = response.json()

    features = data.get(
        "features",
        [],
    )

    if not isinstance(
        features,
        list,
    ):
        return []

    return features