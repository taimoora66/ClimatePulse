from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..services.fire import active_fires_near, firms_configured
from ..services.spatial_field import local_air_field, local_weather_field
from ..state import get_location, merge_ai_context
from ..ui import PLOTLY_CONFIG, callout, chips, footer, page_header, section, style_figure

LAYER_META = {
    "Temperature": ("temperature_c", "°C", "Turbo", 18, -20, 45),
    "Feels like": ("apparent_temperature_c", "°C", "Turbo", 18, -20, 50),
    "Precipitation": ("precipitation_mm", "mm", "Blues", 20, 0, 10),
    "Wind": ("wind_kmh", "km/h", "Viridis", 18, 0, 80),
    "Cloud": ("cloud_pct", "%", "Greys", 18, 0, 100),
    "Air quality": ("european_aqi", "European AQI", "RdYlGn_r", 18, 0, 120),
}


def _field_range(series: pd.Series) -> tuple[float | None, float | None]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None, None
    if len(clean) >= 8:
        low = float(clean.quantile(0.02))
        high = float(clean.quantile(0.98))
    else:
        low = float(clean.min())
        high = float(clean.max())
    if math.isclose(low, high, rel_tol=1e-9, abs_tol=1e-9):
        pad = max(abs(low) * .05, .5)
        return low - pad, high + pad
    return low, high


def _density_figure(frame: pd.DataFrame, selected, layer: str, expanded: bool) -> go.Figure:
    field, unit, colorscale, radius, _, _ = LAYER_META[layer]
    clean = frame.dropna(subset=[field]).copy()
    zmin, zmax = _field_range(clean[field] if field in clean else pd.Series(dtype=float))
    fig = go.Figure()
    if not clean.empty:
        fig.add_trace(
            go.Densitymap(
                lat=clean["latitude"],
                lon=clean["longitude"],
                z=clean[field],
                radius=radius,
                colorscale=colorscale,
                zmin=zmin,
                zmax=zmax,
                opacity=.72,
                hovertemplate=(
                    f"<b>{layer}</b><br>%{{z:.1f}} {unit}<br>"
                    "Lat %{lat:.3f}<br>Lon %{lon:.3f}<extra></extra>"
                ),
                colorbar={"title": unit, "thickness": 12},
                name=layer,
            )
        )
    fig.add_trace(
        go.Scattermap(
            lat=[selected.latitude],
            lon=[selected.longitude],
            mode="markers+text",
            text=[selected.name],
            textposition="top center",
            marker={"size": 16, "color": "white"},
            hovertemplate=f"<b>{selected.label}</b><extra></extra>",
            name="Selected place",
        )
    )
    fig.update_layout(
        map={
            "style": "open-street-map",
            "center": {"lat": selected.latitude, "lon": selected.longitude},
            "zoom": 8.2 if expanded else 7.2,
        },
        showlegend=False,
        dragmode="zoom",
        uirevision=f"map-{selected.latitude:.3f}-{selected.longitude:.3f}-{layer}",
    )
    return style_figure(fig, height=760 if expanded else 610)


def _add_fire_layer(fig: go.Figure, selected, radius_km: int) -> tuple[go.Figure, int | None]:
    if not firms_configured():
        return fig, None
    try:
        fires = active_fires_near(selected.latitude, selected.longitude, max(radius_km * 2, 80))
    except Exception:
        return fig, None
    if fires.empty:
        return fig, 0
    size = pd.to_numeric(fires.get("frp"), errors="coerce").fillna(0).clip(lower=0)
    size = 8 + 12 * (size / max(float(size.max()), 1.0))
    fig.add_trace(
        go.Scattermap(
            lat=fires["latitude"],
            lon=fires["longitude"],
            mode="markers",
            marker={"size": size, "color": "#ff5a3d", "opacity": .85},
            text=[
                f"Active fire / thermal anomaly<br>FRP: {row.get('frp','—')}<br>Confidence: {row.get('confidence','—')}"
                for _, row in fires.iterrows()
            ],
            hoverinfo="text",
            name="NASA FIRMS active fire",
        )
    )
    return fig, int(len(fires))


def render() -> None:
    page_header(
        "Interactive Environmental Map",
        "Explore neighbourhood-to-regional environmental fields around any selected place. Zoom, pan, hover and switch layers without treating interpolated fields as station observations.",
        eyebrow="OBSERVE",
    )
    selected = get_location()

    controls = st.container(border=True)
    with controls:
        c1, c2, c3, c4 = st.columns([2.2, 1.2, 1.0, 1.1], vertical_alignment="bottom")
        layer = c1.selectbox("Layer", list(LAYER_META), key="od_map_layer")
        radius_km = c2.select_slider(
            "Map radius",
            options=[15, 25, 45, 75, 120],
            value=45,
            format_func=lambda x: f"{x} km",
            key="od_map_radius",
        )
        fire_overlay = c3.toggle(
            "NASA fire overlay",
            value=False,
            disabled=not firms_configured(),
            key="od_map_fire_overlay",
        )
        expanded = bool(st.session_state.get("od_map_panel_expanded", False))
        if c4.button(
            "↙ Minimize map" if expanded else "⛶ Expand map",
            use_container_width=True,
            key="od_map_expand",
        ):
            st.session_state["od_map_panel_expanded"] = not expanded
            st.rerun()

    with st.spinner("Building local environmental field…"):
        try:
            if layer == "Air quality":
                frame = local_air_field(selected.latitude, selected.longitude, radius_km, 7)
            else:
                frame = local_weather_field(selected.latitude, selected.longitude, radius_km, 7)
        except Exception as exc:
            st.error(f"Local map field could not be loaded: {type(exc).__name__}")
            return

    expanded = bool(st.session_state.get("od_map_panel_expanded", False))
    fig = _density_figure(frame, selected, layer, expanded)
    fire_count = None
    if fire_overlay:
        fig, fire_count = _add_fire_layer(fig, selected, radius_km)

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={**PLOTLY_CONFIG, "scrollZoom": True},
        key=f"map_explorer_{layer}_{radius_km}_{expanded}_{fire_overlay}",
    )

    field, unit, _, _, _, _ = LAYER_META[layer]
    clean = frame[field].dropna() if field in frame else pd.Series(dtype=float)
    m1, m2, m3, m4 = st.columns(4)
    if not clean.empty:
        m1.metric("Local minimum", f"{clean.min():.1f} {unit}")
        m2.metric("Local median", f"{clean.median():.1f} {unit}")
        m3.metric("Local maximum", f"{clean.max():.1f} {unit}")
    else:
        m1.metric("Local minimum", "—")
        m2.metric("Local median", "—")
        m3.metric("Local maximum", "—")
    m4.metric("Active fire detections", "—" if fire_count is None else str(fire_count))

    chips([
        ("Open-Meteo gridded/model field", "blue"),
        ("City/regional exploration", "green"),
        ("NASA FIRMS optional", "orange"),
        ("Zoom + pan + hover", "blue"),
    ])
    callout(
        "How to interpret this map",
        "The coloured surface is created from a compact grid of model/API values around the selected place for exploration. It is not a station map, cadastral product or official warning layer. NASA FIRMS points, when enabled, are satellite fire/thermal detections and require a free FIRMS MAP_KEY.",
        kind="warning",
    )
    merge_ai_context({
        "page": "Interactive Environmental Map",
        "selected_place": selected.to_dict(),
        "layer": layer,
        "radius_km": radius_km,
        "local_min": None if clean.empty else float(clean.min()),
        "local_median": None if clean.empty else float(clean.median()),
        "local_max": None if clean.empty else float(clean.max()),
        "active_fire_count": fire_count,
    })
    footer()
