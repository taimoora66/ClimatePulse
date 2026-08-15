from src.api.geocoding import search_locations
from src.db import upsert_city


results = search_locations("Milan")

milan_italy = results[0]

city_id = upsert_city(milan_italy)


print()
print("City stored successfully!")
print("City ID:", city_id)
print("Name:", milan_italy["name"])
print("Country:", milan_italy["country"])
print("Latitude:", milan_italy["latitude"])
print("Longitude:", milan_italy["longitude"])