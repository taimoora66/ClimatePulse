import streamlit as st
from src.observability import observe_operation
from src.api.home_environment import get_home_environment


@st.cache_data(ttl=300, max_entries=512, show_spinner=False)
@observe_operation("open_meteo_current", quality_source="Open-Meteo Forecast")
def get_current_weather(
    latitude,
    longitude,
    timezone="auto",
):
    """Return current weather from ORBIDENSE's canonical live bundle.

    This preserves the public return shape while avoiding a separate provider
    request when the same location is also requesting AQI/forecast context.
    """
    bundle = get_home_environment(latitude, longitude, timezone)
    return bundle.get("weather", {}) if isinstance(bundle, dict) else {}
