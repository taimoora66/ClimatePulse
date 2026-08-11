import requests


FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


def get_today_forecast(
    latitude,
    longitude,
    timezone="auto",
):
    """
    Return today's local daily forecast.

    This compares daily forecast values with
    daily ERA5 climatology later in the app.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
        ],
        "timezone": timezone,
        "forecast_days": 1,
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    daily = data.get(
        "daily",
        {},
    )

    times = daily.get(
        "time",
        [],
    )

    if not times:
        return {}

    def first_value(key):
        values = daily.get(
            key,
            [],
        )

        if not values:
            return None

        return values[0]

    return {
        "date": times[0],

        "temperature_max_c": first_value(
            "temperature_2m_max"
        ),

        "temperature_min_c": first_value(
            "temperature_2m_min"
        ),

        "precipitation_mm": first_value(
            "precipitation_sum"
        ),

        "timezone": data.get(
            "timezone"
        ),
    }