CREATE TABLE IF NOT EXISTS cities (
    city_id BIGSERIAL PRIMARY KEY,

    external_id BIGINT UNIQUE NOT NULL,

    city_name TEXT NOT NULL,
    country_name TEXT NOT NULL,
    country_code VARCHAR(2),
    admin1 TEXT,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    timezone TEXT NOT NULL,
    population BIGINT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS weather_daily (
    city_id BIGINT NOT NULL,

    observation_date DATE NOT NULL,

    temp_mean_c DOUBLE PRECISION,
    temp_max_c DOUBLE PRECISION,
    temp_min_c DOUBLE PRECISION,

    precipitation_mm DOUBLE PRECISION,
    wind_max_kmh DOUBLE PRECISION,

    source_model TEXT NOT NULL DEFAULT 'ERA5',

    PRIMARY KEY (
        city_id,
        observation_date
    ),

    CONSTRAINT fk_weather_city
        FOREIGN KEY (city_id)
        REFERENCES cities(city_id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_weather_date
ON weather_daily(observation_date);


CREATE INDEX IF NOT EXISTS idx_weather_city
ON weather_daily(city_id);