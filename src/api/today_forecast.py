import streamlit as st
from src.observability import observe_operation
from src.api.home_environment import get_home_environment


@st.cache_data(ttl=900, max_entries=512, show_spinner=False)
@observe_operation("open_meteo_forecast", quality_source="Open-Meteo Forecast")
def get_today_forecast(
    latitude,
    longitude,
    timezone="auto",
):
    """Return today's local daily forecast from the canonical live bundle."""
    bundle = get_home_environment(latitude, longitude, timezone)
    weather = bundle.get("weather", {}) if isinstance(bundle, dict) else {}
    daily = weather.get("daily", {}) if isinstance(weather, dict) else {}
    times = daily.get("time", []) if isinstance(daily, dict) else []
    if not times:
        return {}

    def first_value(key):
        values = daily.get(key, [])
        return values[0] if values else None

    return {
        "date": times[0],
        "temperature_max_c": first_value("temperature_2m_max"),
        "temperature_min_c": first_value("temperature_2m_min"),
        "precipitation_mm": first_value("precipitation_sum"),
        "timezone": weather.get("timezone"),
    }
