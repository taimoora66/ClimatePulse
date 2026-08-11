from datetime import date

from src.db import get_connection


def get_today_climate_context(
    city_id,
    target_date,
    forecast_high_c,
    forecast_low_c,
    window_days=7,
):
    """
    Compare today's forecast with ERA5 climatology.

    Baseline:
        1991-2020.

    Seasonal comparison window:
        +/- 7 calendar days around today's month/day.

    Percentile:
        Percentage of comparable baseline days whose
        maximum temperature was <= today's forecast maximum.

    Recent shift:
        Difference between the 2016-2025 average maximum
        and the 1991-2000 average maximum for the same
        seasonal window.
    """

    if isinstance(
        target_date,
        str,
    ):
        target_date = date.fromisoformat(
            target_date
        )

    anchor_date = date(
        2000,
        target_date.month,
        target_date.day,
    )

    query = """
        WITH seasonal AS (
            SELECT
                observation_date,
                temp_max_c,
                temp_min_c,

                EXTRACT(
                    YEAR FROM observation_date
                )::INTEGER AS year,

                LEAST(
                    ABS(
                        make_date(
                            2000,
                            EXTRACT(
                                MONTH FROM observation_date
                            )::INTEGER,
                            EXTRACT(
                                DAY FROM observation_date
                            )::INTEGER
                        )
                        - %s::DATE
                    ),

                    366
                    - ABS(
                        make_date(
                            2000,
                            EXTRACT(
                                MONTH FROM observation_date
                            )::INTEGER,
                            EXTRACT(
                                DAY FROM observation_date
                            )::INTEGER
                        )
                        - %s::DATE
                    )
                ) AS seasonal_distance

            FROM weather_daily

            WHERE city_id = %s
        ),

        comparable AS (
            SELECT *
            FROM seasonal
            WHERE seasonal_distance <= %s
        )

        SELECT
            COUNT(*) FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS baseline_sample_count,

            AVG(temp_max_c) FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS typical_high_c,

            AVG(temp_min_c) FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS typical_low_c,

            PERCENTILE_CONT(0.10)
            WITHIN GROUP (
                ORDER BY temp_max_c
            )
            FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS high_p10_c,

            PERCENTILE_CONT(0.90)
            WITHIN GROUP (
                ORDER BY temp_max_c
            )
            FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS high_p90_c,

            PERCENTILE_CONT(0.10)
            WITHIN GROUP (
                ORDER BY temp_min_c
            )
            FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS low_p10_c,

            PERCENTILE_CONT(0.90)
            WITHIN GROUP (
                ORDER BY temp_min_c
            )
            FILTER (
                WHERE year BETWEEN 1991 AND 2020
            ) AS low_p90_c,

            100.0
            * AVG(
                CASE
                    WHEN temp_max_c <= %s
                    THEN 1.0
                    ELSE 0.0
                END
            )
            FILTER (
                WHERE
                    year BETWEEN 1991 AND 2020
                    AND temp_max_c IS NOT NULL
            ) AS high_percentile,

            100.0
            * AVG(
                CASE
                    WHEN temp_min_c <= %s
                    THEN 1.0
                    ELSE 0.0
                END
            )
            FILTER (
                WHERE
                    year BETWEEN 1991 AND 2020
                    AND temp_min_c IS NOT NULL
            ) AS low_percentile,

            AVG(temp_max_c) FILTER (
                WHERE year BETWEEN 1991 AND 2000
            ) AS early_decade_high_c,

            AVG(temp_max_c) FILTER (
                WHERE year BETWEEN 2016 AND 2025
            ) AS recent_decade_high_c,

            (
                SELECT temp_max_c
                FROM comparable
                WHERE temp_max_c IS NOT NULL
                ORDER BY temp_max_c DESC
                LIMIT 1
            ) AS seasonal_record_high_c,

            (
                SELECT observation_date
                FROM comparable
                WHERE temp_max_c IS NOT NULL
                ORDER BY temp_max_c DESC
                LIMIT 1
            ) AS seasonal_record_high_date

        FROM comparable;
    """

    values = (
        anchor_date,
        anchor_date,
        city_id,
        int(window_days),
        forecast_high_c,
        forecast_low_c,
    )

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                query,
                values,
            )

            result = cur.fetchone()

    if not result:
        return None

    result = dict(
        result
    )

    early = result.get(
        "early_decade_high_c"
    )

    recent = result.get(
        "recent_decade_high_c"
    )

    if (
        early is not None
        and recent is not None
    ):
        result[
            "seasonal_shift_c"
        ] = (
            float(recent)
            - float(early)
        )

    else:
        result[
            "seasonal_shift_c"
        ] = None

    result[
        "window_days"
    ] = int(
        window_days
    )

    return result