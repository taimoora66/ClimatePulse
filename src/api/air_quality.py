import streamlit as st
from src.observability import observe_operation
from src.api.home_environment import get_home_environment


@st.cache_data(ttl=600, max_entries=512, show_spinner=False)
@observe_operation("open_meteo_air_quality", quality_source="Open-Meteo Air Quality")
def get_current_air_quality(
    latitude,
    longitude,
    timezone="auto",
):
    """Return current AQI from ORBIDENSE's canonical live bundle."""
    bundle = get_home_environment(latitude, longitude, timezone)
    return bundle.get("air", {}) if isinstance(bundle, dict) else {}
