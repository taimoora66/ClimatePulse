import requests
from src.observability import observe_operation


FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


@observe_operation("open_meteo_current", quality_source="Open-Meteo Forecast")
def get_current_weather(
    latitude,
    longitude,
    timezone="auto",
):

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ],

        "timezone": timezone,
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()
