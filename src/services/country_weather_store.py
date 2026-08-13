from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from psycopg.types.json import Jsonb

from src.db import get_connection


CACHE_TABLE = "climatepulse_global_weather_cache"
CONTROL_TABLE = "climatepulse_global_weather_refresh_control"

_SCHEMA_READY = False


def ensure_global_weather_tables():
    """
    Create the tiny persistent cache/control tables if they do not exist.

    This is intentionally lazy and idempotent, so no manual Neon SQL migration
    is required for the ClimatePulse global-weather cache.
    """
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CACHE_TABLE} (
                    cache_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    fetched_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    provider TEXT NOT NULL DEFAULT 'open-meteo'
                );
                """
            )

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CONTROL_TABLE} (
                    cache_key TEXT PRIMARY KEY,
                    lease_until TIMESTAMPTZ,
                    last_attempt_at TIMESTAMPTZ,
                    last_success_at TIMESTAMPTZ,
                    last_error TEXT
                );
                """
            )

    _SCHEMA_READY = True


def dataframe_to_records(frame):
    if frame is None or frame.empty:
        return []

    clean = frame.copy()

    # JSONB cannot safely store pandas NaN/NaT. Convert them to Python None.
    clean = clean.astype(object).where(
        pd.notnull(clean),
        None,
    )

    return clean.to_dict(
        orient="records"
    )


def records_to_dataframe(records):
    if not records:
        return pd.DataFrame()

    return pd.DataFrame(
        records
    )


def save_global_weather_snapshot(
    cache_key,
    frame,
    fetched_at=None,
):
    """
    Persist the latest successful provider snapshot in Neon.

    Only successful, non-empty provider data are written. A provider failure
    therefore can never overwrite the last-known-good snapshot with blanks.
    """
    ensure_global_weather_tables()

    if frame is None or frame.empty:
        raise ValueError(
            "Refusing to persist an empty global-weather snapshot."
        )

    fetched_at = (
        fetched_at
        or datetime.now(
            timezone.utc
        )
    )

    records = dataframe_to_records(
        frame
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {CACHE_TABLE} (
                    cache_key,
                    payload,
                    fetched_at,
                    updated_at,
                    provider
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW(),
                    'open-meteo'
                )

                ON CONFLICT (cache_key)

                DO UPDATE SET
                    payload = EXCLUDED.payload,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = NOW(),
                    provider = EXCLUDED.provider;
                """,
                (
                    str(cache_key),
                    Jsonb(records),
                    fetched_at,
                ),
            )


def load_global_weather_snapshot(
    cache_key,
):
    """
    Return:
        {
            "frame": DataFrame,
            "fetched_at": aware datetime | None,
            "provider": str | None,
        }
    """
    ensure_global_weather_tables()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    payload,
                    fetched_at,
                    provider
                FROM {CACHE_TABLE}
                WHERE cache_key = %s;
                """,
                (
                    str(cache_key),
                ),
            )

            row = cur.fetchone()

    if not row:
        return {
            "frame": pd.DataFrame(),
            "fetched_at": None,
            "provider": None,
        }

    return {
        "frame": records_to_dataframe(
            row.get(
                "payload"
            )
        ),
        "fetched_at": row.get(
            "fetched_at"
        ),
        "provider": row.get(
            "provider"
        ),
    }


def snapshot_age_seconds(
    fetched_at,
):
    if fetched_at is None:
        return None

    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(
            tzinfo=timezone.utc
        )

    return max(
        0.0,
        (
            datetime.now(
                timezone.utc
            )
            - fetched_at
        ).total_seconds(),
    )


def try_claim_global_weather_refresh(
    cache_key,
    lease_seconds=180,
):
    """
    Cross-session/process refresh lock backed by PostgreSQL.

    Exactly one caller can claim a stale key while the lease is active.
    Other Streamlit sessions continue serving the persisted snapshot instead of
    sending duplicate global requests to Open-Meteo.
    """
    ensure_global_weather_tables()

    lease_seconds = max(
        30,
        int(
            lease_seconds
        ),
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {CONTROL_TABLE} (
                    cache_key,
                    lease_until,
                    last_attempt_at
                )
                VALUES (
                    %s,
                    NOW() + (%s * INTERVAL '1 second'),
                    NOW()
                )

                ON CONFLICT (cache_key)

                DO UPDATE SET
                    lease_until =
                        NOW() + (%s * INTERVAL '1 second'),
                    last_attempt_at =
                        NOW()

                WHERE
                    {CONTROL_TABLE}.lease_until IS NULL
                    OR
                    {CONTROL_TABLE}.lease_until < NOW()

                RETURNING cache_key;
                """,
                (
                    str(cache_key),
                    lease_seconds,
                    lease_seconds,
                ),
            )

            row = cur.fetchone()

    return bool(
        row
    )


def finish_global_weather_refresh(
    cache_key,
    success,
    error=None,
):
    """
    Release the distributed refresh lease and record provider status.
    """
    ensure_global_weather_tables()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {CONTROL_TABLE} (
                    cache_key,
                    lease_until,
                    last_attempt_at,
                    last_success_at,
                    last_error
                )
                VALUES (
                    %s,
                    NULL,
                    NOW(),
                    CASE
                        WHEN %s THEN NOW()
                        ELSE NULL
                    END,
                    %s
                )

                ON CONFLICT (cache_key)

                DO UPDATE SET
                    lease_until = NULL,
                    last_attempt_at = NOW(),
                    last_success_at =
                        CASE
                            WHEN %s
                            THEN NOW()
                            ELSE {CONTROL_TABLE}.last_success_at
                        END,
                    last_error = %s;
                """,
                (
                    str(cache_key),
                    bool(success),
                    None if success else str(error or ""),
                    bool(success),
                    None if success else str(error or ""),
                ),
            )


def get_global_weather_refresh_status(
    cache_key,
):
    ensure_global_weather_tables()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    lease_until,
                    last_attempt_at,
                    last_success_at,
                    last_error
                FROM {CONTROL_TABLE}
                WHERE cache_key = %s;
                """,
                (
                    str(cache_key),
                ),
            )

            row = cur.fetchone()

    return dict(
        row
    ) if row else {}