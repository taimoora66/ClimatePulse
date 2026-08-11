from src.api.geocoding import search_locations


results = search_locations("Milan")


for location in results:

    print()
    print("Name:", location.get("name"))
    print("Country:", location.get("country"))
    print("Admin1:", location.get("admin1"))
    print("Latitude:", location.get("latitude"))
    print("Longitude:", location.get("longitude"))
    print("Timezone:", location.get("timezone"))