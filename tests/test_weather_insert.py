from src.api.geocoding import search_locations
from src.api.weather import get_historical_weather

from src.db import (
    upsert_city,
    insert_weather_daily,
)


# ---------------------------------------
# 1. Find Milan online
# ---------------------------------------

results = search_locations("Milan")

milan = results[0]


# ---------------------------------------
# 2. Store Milan / get its database ID
# ---------------------------------------

city_id = upsert_city(milan)


# ---------------------------------------
# 3. Retrieve January 2025 ERA5 weather
# ---------------------------------------

weather = get_historical_weather(
    latitude=milan["latitude"],
    longitude=milan["longitude"],
    start_date="2025-01-01",
    end_date="2025-01-31",
    timezone=milan["timezone"],
)


# ---------------------------------------
# 4. Store weather in PostgreSQL
# ---------------------------------------

records_saved = insert_weather_daily(
    city_id,
    weather,
)


print()
print("Weather import successful!")
print("City:", milan["name"])
print("Country:", milan["country"])
print("City ID:", city_id)
print("Weather records saved:", records_saved)