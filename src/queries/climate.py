import pandas as pd

from src.db import get_connection


def get_available_cities():

    query = """
        SELECT
            city_id,
            city_name,
            country_name
        FROM cities
        ORDER BY country_name, city_name;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return pd.DataFrame(rows)


def get_annual_climate_summary(city_id):

    query = """
        SELECT
            year,
            avg_temperature_c,
            avg_max_temperature_c,
            avg_min_temperature_c,
            hottest_day_c,
            coldest_day_c,
            annual_precipitation_mm,
            hot_days_30c,
            extreme_hot_days_35c
        FROM annual_climate_summary
        WHERE city_id = %s
        ORDER BY year;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (city_id,))
            rows = cur.fetchall()

    return pd.DataFrame(rows)


def get_temperature_anomalies(city_id):

    query = """
        SELECT
            year,
            annual_temperature_c,
            baseline_temperature_c,
            anomaly_c
        FROM annual_temperature_anomaly
        WHERE city_id = %s
        ORDER BY year;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (city_id,))
            rows = cur.fetchall()

    return pd.DataFrame(rows)


def get_city_details(city_id):

    query = """
        SELECT
            city_id,
            city_name,
            country_name,
            country_code,
            admin1,
            latitude,
            longitude,
            timezone,
            population
        FROM cities
        WHERE city_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (city_id,))
            row = cur.fetchone()

    return row
def get_climate_trend(city_id):

    query = """
        SELECT
            warming_rate_c_per_decade,
            first_year,
            last_year,
            lowest_annual_mean_c,
            highest_annual_mean_c
        FROM climate_trend_summary
        WHERE city_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (city_id,))
            row = cur.fetchone()

    return row