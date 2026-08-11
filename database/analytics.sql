CREATE OR REPLACE VIEW annual_climate_summary AS

SELECT
    w.city_id,
    c.city_name,
    c.country_name,

    EXTRACT(YEAR FROM w.observation_date)::INTEGER AS year,

    ROUND(
        AVG(w.temp_mean_c)::NUMERIC,
        2
    ) AS avg_temperature_c,

    ROUND(
        AVG(w.temp_max_c)::NUMERIC,
        2
    ) AS avg_max_temperature_c,

    ROUND(
        AVG(w.temp_min_c)::NUMERIC,
        2
    ) AS avg_min_temperature_c,

    ROUND(
        MAX(w.temp_max_c)::NUMERIC,
        2
    ) AS hottest_day_c,

    ROUND(
        MIN(w.temp_min_c)::NUMERIC,
        2
    ) AS coldest_day_c,

    ROUND(
        SUM(w.precipitation_mm)::NUMERIC,
        2
    ) AS annual_precipitation_mm,

    COUNT(*) FILTER (
        WHERE w.temp_max_c >= 30
    ) AS hot_days_30c,

    COUNT(*) FILTER (
        WHERE w.temp_max_c >= 35
    ) AS extreme_hot_days_35c

FROM weather_daily AS w

JOIN cities AS c
    ON w.city_id = c.city_id

GROUP BY
    w.city_id,
    c.city_name,
    c.country_name,
    EXTRACT(YEAR FROM w.observation_date);

    CREATE OR REPLACE VIEW annual_temperature_anomaly AS

WITH baseline AS (

    SELECT
        city_id,
        AVG(temp_mean_c) AS baseline_temperature_c

    FROM weather_daily

    WHERE observation_date BETWEEN DATE '1991-01-01'
                               AND DATE '2020-12-31'

    GROUP BY city_id
),

annual AS (

    SELECT
        city_id,

        EXTRACT(
            YEAR FROM observation_date
        )::INTEGER AS year,

        AVG(temp_mean_c) AS annual_temperature_c

    FROM weather_daily

    GROUP BY
        city_id,
        EXTRACT(YEAR FROM observation_date)
)

SELECT
    a.city_id,
    c.city_name,
    c.country_name,
    a.year,

    ROUND(
        a.annual_temperature_c::NUMERIC,
        2
    ) AS annual_temperature_c,

    ROUND(
        b.baseline_temperature_c::NUMERIC,
        2
    ) AS baseline_temperature_c,

    ROUND(
        (
            a.annual_temperature_c
            -
            b.baseline_temperature_c
        )::NUMERIC,
        2
    ) AS anomaly_c

FROM annual AS a

JOIN baseline AS b
    ON a.city_id = b.city_id

JOIN cities AS c
    ON a.city_id = c.city_id;
    CREATE OR REPLACE VIEW climate_trend_summary AS

WITH yearly AS (
    SELECT
        city_id,
        EXTRACT(YEAR FROM observation_date)::INTEGER AS year,
        AVG(temp_mean_c) AS annual_temp
    FROM weather_daily
    GROUP BY
        city_id,
        EXTRACT(YEAR FROM observation_date)
),

trend AS (
    SELECT
        city_id,

        REGR_SLOPE(
            annual_temp,
            year
        ) AS slope_per_year,

        MIN(year) AS first_year,
        MAX(year) AS last_year,

        MIN(annual_temp) AS lowest_annual_mean,
        MAX(annual_temp) AS highest_annual_mean

    FROM yearly

    GROUP BY city_id
)

SELECT
    t.city_id,
    c.city_name,
    c.country_name,

    ROUND(
        (t.slope_per_year * 10)::NUMERIC,
        3
    ) AS warming_rate_c_per_decade,

    t.first_year,
    t.last_year,

    ROUND(
        t.lowest_annual_mean::NUMERIC,
        2
    ) AS lowest_annual_mean_c,

    ROUND(
        t.highest_annual_mean::NUMERIC,
        2
    ) AS highest_annual_mean_c

FROM trend AS t

JOIN cities AS c
    ON t.city_id = c.city_id;