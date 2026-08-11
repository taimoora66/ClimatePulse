from src.api.weather import get_historical_weather

from src.db import (
    upsert_city,
    insert_weather_daily,
    city_has_complete_history,
)


START_DATE = "1990-01-01"
END_DATE = "2025-12-31"


def ensure_city_history(location):

    city_id = upsert_city(location)

    if city_has_complete_history(city_id):

        return {
            "city_id": city_id,
            "downloaded": False,
            "records_saved": 0,
        }

    weather = get_historical_weather(
        latitude=location["latitude"],
        longitude=location["longitude"],
        start_date=START_DATE,
        end_date=END_DATE,
        timezone=location["timezone"],
    )

    records_saved = insert_weather_daily(
        city_id,
        weather,
    )

    return {
        "city_id": city_id,
        "downloaded": True,
        "records_saved": records_saved,
    }