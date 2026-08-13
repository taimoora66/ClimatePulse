"""
One-time/manual bootstrap for ClimatePulse's Neon global-weather cache.

Run only when you want to seed/refresh the persistent snapshots from the local
project environment:

    python bootstrap_global_weather.py

It uses the same DATABASE_URL from .env / Streamlit Secrets logic as src.db.
"""

from datetime import datetime, timezone

from src.api.country_live_field import (
    get_live_country_context,
    get_live_country_current,
)
from src.services.country_weather_store import (
    finish_global_weather_refresh,
    save_global_weather_snapshot,
    try_claim_global_weather_refresh,
)


CURRENT_KEY = "country_current_v1"
CONTEXT_KEY = "country_context_v1"


def refresh_one(
    key,
    loader,
):
    print(
        f"Refreshing {key}..."
    )

    if not try_claim_global_weather_refresh(
        key,
        lease_seconds=300,
    ):
        print(
            f"Skipped {key}: another refresh lease is active."
        )
        return False

    try:
        frame = loader()

        save_global_weather_snapshot(
            key,
            frame,
            fetched_at=datetime.now(
                timezone.utc
            ),
        )

        finish_global_weather_refresh(
            key,
            success=True,
        )

        print(
            f"Saved {len(frame)} rows for {key}."
        )

        return True

    except Exception as error:
        finish_global_weather_refresh(
            key,
            success=False,
            error=str(
                error
            ),
        )

        print(
            f"{key} failed: {error}"
        )

        return False


if __name__ == "__main__":
    current_ok = refresh_one(
        CURRENT_KEY,
        get_live_country_current,
    )

    context_ok = refresh_one(
        CONTEXT_KEY,
        get_live_country_context,
    )

    if (
        current_ok
        and context_ok
    ):
        print(
            "ClimatePulse global weather cache is fully bootstrapped."
        )
    else:
        print(
            "Bootstrap was incomplete. Existing Neon snapshots, if any, "
            "were preserved."
        )