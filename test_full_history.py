from src.api.geocoding import search_locations
from src.services.climate_service import ensure_city_history


results = search_locations("Milan")

milan = results[0]


print()
print("Selected city:")
print(
    milan["name"],
    milan["country"]
)

print()
print("Preparing 1990-2025 climate history...")


result = ensure_city_history(milan)


print()
print("Import finished.")
print("City ID:", result["city_id"])
print("Downloaded:", result["downloaded"])
print(
    "Records saved:",
    result["records_saved"]
)