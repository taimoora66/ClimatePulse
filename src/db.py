import os
from datetime import date
from functools import lru_cache

import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


# =========================================================
# ENVIRONMENT / DATABASE
# =========================================================

load_dotenv()


def get_database_url():
    """
    Streamlit Cloud:
        read DATABASE_URL from st.secrets.

    Local development:
        fall back to DATABASE_URL from .env.
    """
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass

    return os.getenv("DATABASE_URL")


DATABASE_URL = get_database_url()

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. "
        "Configure it in Streamlit Secrets "
        "or in the local .env file."
    )


# =========================================================
# CONNECTION POOL
# =========================================================

@lru_cache(maxsize=1)
def get_pool():
    """
    Keep a small reusable PostgreSQL connection pool.

    This avoids creating a brand-new TLS/PostgreSQL
    connection to Neon for every SQL query.
    """
    return ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=0,
        max_size=5,
        timeout=10,
        max_idle=300,
        max_lifetime=1800,
        kwargs={
            "row_factory": dict_row,
        },
        check=ConnectionPool.check_connection,
        open=True,
    )


def get_connection():
    """
    Return a pooled connection context manager.

    Existing code can continue using:

        with get_connection() as conn:
            ...
    """
    return get_pool().connection()


# =========================================================
# CITY STORAGE
# =========================================================

def upsert_city(location):
    """
    Insert/update a city and return its internal city_id.
    """
    query = """
        INSERT INTO cities (
            external_id,
            city_name,
            country_name,
            country_code,
            admin1,
            latitude,
            longitude,
            timezone,
            population
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )

        ON CONFLICT (external_id)

        DO UPDATE SET
            city_name =
                EXCLUDED.city_name,

            country_name =
                EXCLUDED.country_name,

            country_code =
                EXCLUDED.country_code,

            admin1 =
                EXCLUDED.admin1,

            latitude =
                EXCLUDED.latitude,

            longitude =
                EXCLUDED.longitude,

            timezone =
                EXCLUDED.timezone,

            population =
                EXCLUDED.population

        RETURNING city_id;
    """

    values = (
        location.get("id"),
        location.get("name"),
        location.get("country"),
        location.get("country_code"),
        location.get("admin1"),
        location.get("latitude"),
        location.get("longitude"),
        location.get("timezone"),
        location.get("population"),
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                values,
            )

            result = cur.fetchone()

    return result["city_id"]


# =========================================================
# FAST DAILY ERA5 STORAGE
# =========================================================

def insert_weather_daily(
    city_id,
    weather_data,
):
    """
    Bulk-load daily ERA5 data using PostgreSQL COPY.

    For ~13,000 daily records this is substantially
    faster than issuing thousands of INSERT statements.
    """
    daily = weather_data.get("daily")

    if not daily:
        return 0

    dates = daily.get("time", [])

    if not dates:
        return 0

    records = []

    for i in range(len(dates)):
        records.append(
            (
                city_id,
                dates[i],
                daily["temperature_2m_mean"][i],
                daily["temperature_2m_max"][i],
                daily["temperature_2m_min"][i],
                daily["precipitation_sum"][i],
                (daily.get("wind_speed_10m_max") or [None] * len(dates))[i],
                "ERA5",
            )
        )

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                CREATE TEMP TABLE weather_daily_stage (
                    city_id BIGINT,
                    observation_date DATE,
                    temp_mean_c DOUBLE PRECISION,
                    temp_max_c DOUBLE PRECISION,
                    temp_min_c DOUBLE PRECISION,
                    precipitation_mm DOUBLE PRECISION,
                    wind_max_kmh DOUBLE PRECISION,
                    source_model TEXT
                )
                ON COMMIT DROP;
                """
            )

            with cur.copy(
                """
                COPY weather_daily_stage (
                    city_id,
                    observation_date,
                    temp_mean_c,
                    temp_max_c,
                    temp_min_c,
                    precipitation_mm,
                    wind_max_kmh,
                    source_model
                )
                FROM STDIN
                """
            ) as copy:

                for record in records:
                    copy.write_row(record)

            cur.execute(
                """
                INSERT INTO weather_daily (
                    city_id,
                    observation_date,
                    temp_mean_c,
                    temp_max_c,
                    temp_min_c,
                    precipitation_mm,
                    wind_max_kmh,
                    source_model
                )

                SELECT
                    city_id,
                    observation_date,
                    temp_mean_c,
                    temp_max_c,
                    temp_min_c,
                    precipitation_mm,
                    wind_max_kmh,
                    source_model

                FROM weather_daily_stage

                ON CONFLICT (
                    city_id,
                    observation_date
                )

                DO UPDATE SET
                    temp_mean_c =
                        EXCLUDED.temp_mean_c,

                    temp_max_c =
                        EXCLUDED.temp_max_c,

                    temp_min_c =
                        EXCLUDED.temp_min_c,

                    precipitation_mm =
                        EXCLUDED.precipitation_mm,

                    wind_max_kmh =
                        EXCLUDED.wind_max_kmh,

                    source_model =
                        EXCLUDED.source_model;
                """
            )

    return len(records)


# =========================================================
# HISTORICAL COVERAGE CHECK
# =========================================================

HISTORY_START = date(
    1990,
    1,
    1,
)

HISTORY_END = date(
    2025,
    12,
    31,
)


def city_has_complete_history(
    city_id,
):
    """
    Return True when the city already contains the
    complete 1990–2025 daily history.
    """
    query = """
        SELECT
            MIN(observation_date) AS first_date,
            MAX(observation_date) AS last_date
        FROM weather_daily
        WHERE city_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (city_id,),
            )

            result = cur.fetchone()

    if not result:
        return False

    if result["first_date"] is None:
        return False

    if result["last_date"] is None:
        return False

    return (
        result["first_date"] <= HISTORY_START
        and
        result["last_date"] >= HISTORY_END
    )


# =========================================================
# HISTORY YEAR COVERAGE
# =========================================================

def get_existing_history_years(
    city_id,
):
    """
    Return years that already have daily rows stored.

    A successful yearly Open-Meteo chunk is inserted
    transactionally, so a present year can be safely skipped
    when resuming a background history job.
    """
    query = """
        SELECT DISTINCT
            EXTRACT(
                YEAR FROM observation_date
            )::INTEGER AS year
        FROM weather_daily
        WHERE city_id = %s
        ORDER BY year;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (city_id,),
            )

            rows = cur.fetchall()

    return {
        int(row["year"])
        for row in rows
        if row["year"] is not None
    }


def get_history_record_count(
    city_id,
):
    query = """
        SELECT COUNT(*) AS record_count
        FROM weather_daily
        WHERE city_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (city_id,),
            )

            row = cur.fetchone()

    return int(
        row["record_count"]
        if row
        else 0
    )