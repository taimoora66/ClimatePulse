from src.api.current_weather import (
    get_current_weather,
)

from src.api.air_quality import (
    get_current_air_quality,
)


latitude = 45.46427
longitude = 9.18951


weather = get_current_weather(
    latitude,
    longitude,
    timezone="Europe/Rome",
)


air = get_current_air_quality(
    latitude,
    longitude,
    timezone="Europe/Rome",
)


print()
print("CURRENT WEATHER")
print(weather.get("current"))

print()
print("AIR QUALITY")
print(air.get("current"))