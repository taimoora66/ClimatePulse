import requests
from src.observability import observe_operation


AIR_QUALITY_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)


@observe_operation("open_meteo_air_quality", quality_source="Open-Meteo Air Quality")
def get_current_air_quality(
    latitude,
    longitude,
    timezone="auto",
):

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": [
            "pm10",
            "pm2_5",
            "nitrogen_dioxide",
            "ozone",
            "european_aqi",
        ],

        "timezone": timezone,
    }

    response = requests.get(
        AIR_QUALITY_URL,
        params=params,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()
