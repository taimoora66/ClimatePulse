from src.queries.climate import (
    get_available_cities,
    get_annual_climate_summary,
    get_temperature_anomalies,
)


cities = get_available_cities()

print()
print("AVAILABLE CITIES")
print(cities)


if not cities.empty:

    city_id = int(cities.iloc[0]["city_id"])

    print()
    print("ANNUAL CLIMATE SUMMARY")

    summary = get_annual_climate_summary(
        city_id
    )

    print(summary.head())


    print()
    print("TEMPERATURE ANOMALIES")

    anomalies = get_temperature_anomalies(
        city_id
    )

    print(anomalies.head())