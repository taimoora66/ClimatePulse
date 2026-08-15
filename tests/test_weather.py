from src.api.weather import get_historical_weather


data = get_historical_weather(
    latitude=45.46427,
    longitude=9.18951,
    start_date="2025-01-01",
    end_date="2025-01-31",
)


daily = data["daily"]


print("Number of days:", len(daily["time"]))
print()

for i in range(5):

    print(
        daily["time"][i],
        "| Mean:", daily["temperature_2m_mean"][i],
        "| Max:", daily["temperature_2m_max"][i],
        "| Min:", daily["temperature_2m_min"][i],
        "| Rain:", daily["precipitation_sum"][i],
        "| Wind:", daily["wind_speed_10m_max"][i],
    )