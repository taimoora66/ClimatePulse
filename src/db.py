import os
from datetime import date

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


# =========================================================
# ENVIRONMENT / DATABASE CONNECTION
# =========================================================

load_dotenv()


def get_database_url():
    """
    Use Streamlit Cloud secrets when deployed.
    Fall back to local .env during development.
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

def get_connection():
    """
    Open a PostgreSQL connection.

    Rows are returned as dictionaries, for example:
    row["city_name"]
    """
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


# =========================================================
# CITY STORAGE
# =========================================================

def upsert_city(location):
    """
    Insert a geocoded location into the cities table.

    If the same external location already exists,
    update its metadata and return its city_id.
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
# FAST DAILY WEATHER STORAGE
# =========================================================

def insert_weather_daily(city_id, weather_data):
    """
    Bulk-load daily ERA5 weather into PostgreSQL.

    The function first COPY-loads rows into a temporary
    staging table, then performs one upsert into the real
    weather_daily table.

    This is much faster than executemany() for ~13k rows.
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
                daily["wind_speed_10m_max"][i],
                "ERA5",
            )
        )

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Temporary table exists only for this transaction.
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

            # Very fast bulk insert into staging table.
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

            # Upsert staged rows into the permanent table.
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

HISTORY_START = date(1990, 1, 1)
HISTORY_END = date(2025, 12, 31)


def city_has_complete_history(city_id):
    """
    Return True when the city already has a complete
    1990-01-01 through 2025-12-31 daily climate record.
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