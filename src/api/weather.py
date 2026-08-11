import requests


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_historical_weather(
    latitude,
    longitude,
    start_date,
    end_date,
    timezone="auto",
):

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "start_date": start_date,
        "end_date": end_date,

        "daily": [
            "temperature_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],

        "timezone": timezone,

        # Use one consistent reanalysis model
        "models": "era5",
    }

    response = requests.get(
        ARCHIVE_URL,
        params=params,
        timeout=90,
    )

    response.raise_for_status()

    return response.json()