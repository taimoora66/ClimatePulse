from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import math


try:
    import numpy as np
    import thermofeel as tf
except Exception:
    np = None
    tf = None


@dataclass
class ContextItem:
    label: str
    level: str
    value: str
    note: str = ""


def _number(
    value: Any,
):
    try:
        result = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(
        result
    ):
        return None

    return result


def weather_code_text(
    code,
):
    try:
        code = int(
            code
        )
    except Exception:
        return "Weather"

    mapping = {
        0: "Clear",
        1: "Mostly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy showers",
        95: "Thunderstorm",
        96: "Thunderstorm / hail",
        99: "Thunderstorm / hail",
    }

    return mapping.get(
        code,
        "Weather",
    )


def aqi_level(
    european_aqi,
):
    value = _number(
        european_aqi
    )

    if value is None:
        return (
            "Unavailable",
            "unknown",
        )

    if value <= 20:
        return (
            "Good",
            "good",
        )

    if value <= 40:
        return (
            "Fair",
            "fair",
        )

    if value <= 60:
        return (
            "Moderate",
            "moderate",
        )

    if value <= 80:
        return (
            "Poor",
            "poor",
        )

    if value <= 100:
        return (
            "Very poor",
            "very-poor",
        )

    return (
        "Extremely poor",
        "extreme",
    )


def _to_celsius_if_kelvin(
    value,
):
    value = _number(
        value
    )

    if value is None:
        return None

    if value > 100:
        return (
            value
            - 273.15
        )

    return value


def simple_wbgt_c(
    temperature_c,
    relative_humidity,
):
    """
    Use ECMWF thermofeel's WBGT-simple implementation when available.

    This is a screening heat-stress index using air temperature and
    relative humidity. It is NOT the same as full outdoor UTCI because
    mean radiant temperature is not reconstructed from the current
    ClimatePulse forecast feed.
    """
    t = _number(
        temperature_c
    )
    rh = _number(
        relative_humidity
    )

    if (
        t is None
        or rh is None
        or tf is None
        or np is None
    ):
        return None

    try:
        result = tf.calculate_wbgt_simple(
            np.asarray(
                [
                    t
                    + 273.15
                ],
                dtype=float,
            ),
            np.asarray(
                [
                    rh
                ],
                dtype=float,
            ),
        )

        return _to_celsius_if_kelvin(
            float(
                result[0]
            )
        )

    except Exception:
        return None


def heat_stress_context(
    temperature_c,
    apparent_temperature_c,
    relative_humidity,
):
    wbgt = simple_wbgt_c(
        temperature_c,
        relative_humidity,
    )

    if wbgt is not None:
        if wbgt >= 31:
            return {
                "metric": "WBGT screening",
                "value_c": wbgt,
                "label": "High heat stress",
                "level": "high",
            }

        if wbgt >= 25:
            return {
                "metric": "WBGT screening",
                "value_c": wbgt,
                "label": "Moderate heat stress",
                "level": "moderate",
            }

        if wbgt >= 20:
            return {
                "metric": "WBGT screening",
                "value_c": wbgt,
                "label": "Low heat stress",
                "level": "low",
            }

        return {
            "metric": "WBGT screening",
            "value_c": wbgt,
            "label": "Low thermal load",
            "level": "good",
        }

    apparent = _number(
        apparent_temperature_c
    )

    if apparent is None:
        apparent = _number(
            temperature_c
        )

    if apparent is None:
        return {
            "metric": "Thermal context",
            "value_c": None,
            "label": "Unavailable",
            "level": "unknown",
        }

    if apparent >= 38:
        label = "Very high apparent heat"
        level = "high"
    elif apparent >= 32:
        label = "High apparent heat"
        level = "moderate"
    elif apparent >= 26:
        label = "Warm"
        level = "low"
    else:
        label = "Comfortable / mild"
        level = "good"

    return {
        "metric": "Apparent temperature",
        "value_c": apparent,
        "label": label,
        "level": level,
    }


def pollen_context(
    current_air,
):
    values = {
        "Alder": _number(
            current_air.get(
                "alder_pollen"
            )
        ),
        "Birch": _number(
            current_air.get(
                "birch_pollen"
            )
        ),
        "Grass": _number(
            current_air.get(
                "grass_pollen"
            )
        ),
        "Mugwort": _number(
            current_air.get(
                "mugwort_pollen"
            )
        ),
        "Ragweed": _number(
            current_air.get(
                "ragweed_pollen"
            )
        ),
    }

    available = {
        key: value
        for key, value in values.items()
        if value is not None
    }

    if not available:
        return {
            "label": "Not available",
            "level": "unknown",
            "dominant": None,
            "value": None,
        }

    dominant = max(
        available,
        key=available.get,
    )

    value = available[
        dominant
    ]

    # Pollen units differ by forecast product/species and there is no
    # single universal health threshold. We therefore report the dominant
    # forecast species/value without inventing a medical category.
    return {
        "label": "Forecast available",
        "level": "info",
        "dominant": dominant,
        "value": value,
    }


def build_health_context(
    weather_current,
    air_current,
    daily,
):
    heat = heat_stress_context(
        weather_current.get(
            "temperature_2m"
        ),
        weather_current.get(
            "apparent_temperature"
        ),
        weather_current.get(
            "relative_humidity_2m"
        ),
    )

    aqi_text, aqi_code = aqi_level(
        air_current.get(
            "european_aqi"
        )
    )

    min_temp = None

    try:
        values = daily.get(
            "temperature_2m_min",
            [],
        )

        if values:
            min_temp = _number(
                values[0]
            )
    except Exception:
        pass

    tropical_night = (
        min_temp is not None
        and min_temp > 20.0
    )

    uv_max = None

    try:
        values = daily.get(
            "uv_index_max",
            [],
        )

        if values:
            uv_max = _number(
                values[0]
            )
    except Exception:
        pass

    pollen = pollen_context(
        air_current
    )

    return {
        "heat": heat,
        "air_quality": {
            "value": _number(
                air_current.get(
                    "european_aqi"
                )
            ),
            "label": aqi_text,
            "level": aqi_code,
        },
        "night": {
            "minimum_c": min_temp,
            "tropical_night": tropical_night,
            "label": (
                "Limited overnight cooling"
                if tropical_night
                else "Normal overnight cooling"
            ),
            "level": (
                "moderate"
                if tropical_night
                else "good"
            ),
        },
        "uv": {
            "value": uv_max,
            "label": (
                "Very high"
                if (
                    uv_max is not None
                    and uv_max >= 8
                )
                else "High"
                if (
                    uv_max is not None
                    and uv_max >= 6
                )
                else "Moderate"
                if (
                    uv_max is not None
                    and uv_max >= 3
                )
                else "Low"
                if uv_max is not None
                else "Unavailable"
            ),
            "level": (
                "high"
                if (
                    uv_max is not None
                    and uv_max >= 8
                )
                else "moderate"
                if (
                    uv_max is not None
                    and uv_max >= 6
                )
                else "low"
            ),
        },
        "pollen": pollen,
    }


def build_compound_context(
    health,
    weather_current,
    air_current,
    daily,
):
    contexts = []

    heat_level = (
        health.get(
            "heat",
            {}
        ).get(
            "level"
        )
    )

    aqi_value = _number(
        air_current.get(
            "european_aqi"
        )
    )

    if (
        heat_level in {
            "moderate",
            "high",
        }
        and health.get(
            "night",
            {}
        ).get(
            "tropical_night"
        )
    ):
        contexts.append(
            {
                "name": "Day + night heat",
                "level": "high",
                "message": (
                    "Elevated daytime thermal stress "
                    "with limited overnight cooling."
                ),
            }
        )

    if (
        heat_level in {
            "moderate",
            "high",
        }
        and aqi_value is not None
        and aqi_value > 60
    ):
        contexts.append(
            {
                "name": "Heat + air pollution",
                "level": "high",
                "message": (
                    "Heat stress and poor air quality "
                    "are elevated at the same time."
                ),
            }
        )

    precipitation_max = None
    precip_prob = None

    try:
        precip_values = daily.get(
            "precipitation_sum",
            [],
        )

        prob_values = daily.get(
            "precipitation_probability_max",
            [],
        )

        if precip_values:
            precipitation_max = _number(
                precip_values[0]
            )

        if prob_values:
            precip_prob = _number(
                prob_values[0]
            )
    except Exception:
        pass

    if (
        precipitation_max is not None
        and precipitation_max >= 30
        and (
            precip_prob is None
            or precip_prob >= 60
        )
    ):
        contexts.append(
            {
                "name": "Heavy-rain context",
                "level": "moderate",
                "message": (
                    "Substantial forecast rainfall is present. "
                    "This is not a flood forecast."
                ),
            }
        )

    if not contexts:
        contexts.append(
            {
                "name": "No major compound signal",
                "level": "good",
                "message": (
                    "No compound condition currently exceeds "
                    "ClimatePulse screening rules."
                ),
            }
        )

    return contexts


def build_context_alerts(
    health,
    compound,
    weather_current,
    air_current,
    daily,
):
    alerts = []

    heat_level = (
        health.get(
            "heat",
            {}
        ).get(
            "level"
        )
    )

    if heat_level == "high":
        alerts.append(
            {
                "title": "Heat stress",
                "level": "high",
                "message": health[
                    "heat"
                ][
                    "label"
                ],
            }
        )

    if (
        health.get(
            "uv",
            {}
        ).get(
            "value"
        )
        is not None
        and health[
            "uv"
        ][
            "value"
        ]
        >= 6
    ):
        alerts.append(
            {
                "title": "High UV",
                "level": "moderate",
                "message": (
                    f"Daily maximum UV index "
                    f"{health['uv']['value']:.1f}."
                ),
            }
        )

    aqi = (
        health.get(
            "air_quality",
            {}
        ).get(
            "value"
        )
    )

    if (
        aqi is not None
        and aqi > 60
    ):
        alerts.append(
            {
                "title": "Air quality",
                "level": "moderate",
                "message": (
                    f"European AQI {aqi:.0f} "
                    f"({health['air_quality']['label']})."
                ),
            }
        )

    for item in compound:
        if item.get(
            "level"
        ) == "high":
            alerts.append(
                {
                    "title": item[
                        "name"
                    ],
                    "level": "high",
                    "message": item[
                        "message"
                    ],
                }
            )

    return alerts


def build_guidance(
    health,
):
    guidance = []

    if health[
        "heat"
    ][
        "level"
    ] in {
        "moderate",
        "high",
    }:
        guidance.append(
            {
                "title": "Heat",
                "text": (
                    "Prefer cooler hours for strenuous outdoor activity "
                    "and use shade and hydration."
                ),
                "source": "WHO heat-health guidance",
            }
        )

    uv_value = health[
        "uv"
    ][
        "value"
    ]

    if (
        uv_value is not None
        and uv_value >= 3
    ):
        guidance.append(
            {
                "title": "UV",
                "text": (
                    "Use sun protection and seek shade during "
                    "high-UV periods."
                ),
                "source": "WHO UV guidance",
            }
        )

    aqi = health[
        "air_quality"
    ][
        "value"
    ]

    if (
        aqi is not None
        and aqi > 60
    ):
        guidance.append(
            {
                "title": "Air quality",
                "text": (
                    "People who are sensitive to air pollution may "
                    "consider reducing intense outdoor activity."
                ),
                "source": "EEA European AQI health messaging",
            }
        )

    if health[
        "night"
    ][
        "tropical_night"
    ]:
        guidance.append(
            {
                "title": "Night heat",
                "text": (
                    "Overnight cooling may be limited; keep sleeping "
                    "spaces as cool as practical."
                ),
                "source": "ClimatePulse climate-health context",
            }
        )

    if not guidance:
        guidance.append(
            {
                "title": "Conditions",
                "text": (
                    "No major environmental-stress signal is elevated "
                    "in the current ClimatePulse context."
                ),
                "source": "ClimatePulse screening rules",
            }
        )

    return guidance


def _hourly_rows(
    hourly,
    air_hourly,
):
    times = hourly.get(
        "time",
        [],
    )

    air_times = air_hourly.get(
        "time",
        [],
    )

    air_lookup = {}

    for index, time_value in enumerate(
        air_times
    ):
        air_lookup[
            time_value
        ] = {
            key: (
                values[index]
                if (
                    isinstance(
                        values,
                        list,
                    )
                    and index < len(
                        values
                    )
                )
                else None
            )
            for key, values in (
                air_hourly.items()
            )
            if key != "time"
        }

    rows = []

    for index, time_value in enumerate(
        times
    ):
        row = {
            "time": time_value,
        }

        for key, values in (
            hourly.items()
        ):
            if key == "time":
                continue

            row[
                key
            ] = (
                values[index]
                if (
                    isinstance(
                        values,
                        list,
                    )
                    and index < len(
                        values
                    )
                )
                else None
            )

        row.update(
            {
                f"air_{key}": value
                for key, value in air_lookup.get(
                    time_value,
                    {},
                ).items()
            }
        )

        rows.append(
            row
        )

    return rows


def find_low_stress_window(
    hourly,
    air_hourly,
    hours=30,
):
    """
    Find a practical 2-hour outdoor window.

    This is intentionally transparent: it filters out hours with high
    rain probability, strong heat, high UV, or poor AQI, then selects
    the earliest remaining 2-hour window with the lowest apparent heat.
    It is guidance, not a medical recommendation.
    """
    rows = _hourly_rows(
        hourly,
        air_hourly,
    )

    now = datetime.now()

    candidates = []

    for row in rows[:hours]:
        try:
            timestamp = datetime.fromisoformat(
                row[
                    "time"
                ]
            )
        except Exception:
            continue

        if timestamp < now:
            continue

        apparent = _number(
            row.get(
                "apparent_temperature"
            )
        )

        uv = _number(
            row.get(
                "uv_index"
            )
        )

        rain_prob = _number(
            row.get(
                "precipitation_probability"
            )
        )

        aqi = _number(
            row.get(
                "air_european_aqi"
            )
        )

        flags = []

        if (
            apparent is not None
            and apparent >= 32
        ):
            flags.append(
                "heat"
            )

        if (
            uv is not None
            and uv >= 6
        ):
            flags.append(
                "uv"
            )

        if (
            rain_prob is not None
            and rain_prob >= 50
        ):
            flags.append(
                "rain"
            )

        if (
            aqi is not None
            and aqi > 60
        ):
            flags.append(
                "air"
            )

        if not flags:
            candidates.append(
                {
                    "time": timestamp,
                    "apparent_temperature": apparent,
                    "uv_index": uv,
                    "rain_probability": rain_prob,
                    "aqi": aqi,
                }
            )

    for first, second in zip(
        candidates,
        candidates[
            1:
        ],
    ):
        if (
            second[
                "time"
            ]
            - first[
                "time"
            ]
        ).total_seconds() == 3600:
            return {
                "start": first[
                    "time"
                ],
                "end": (
                    second[
                        "time"
                    ]
                    .replace(
                        minute=0,
                        second=0,
                    )
                ),
                "apparent_temperature": (
                    first[
                        "apparent_temperature"
                    ]
                ),
                "uv_index": first[
                    "uv_index"
                ],
                "rain_probability": first[
                    "rain_probability"
                ],
                "aqi": first[
                    "aqi"
                ],
            }

    return None


def build_intelligence_brief(
    place_name,
    weather_current,
    health,
    compound,
    forecast_high=None,
    forecast_low=None,
):
    """
    Deterministic, data-grounded plain-language summary for the Home page.
    It does not call an LLM and cannot invent values outside the context
    object passed to it.
    """
    temperature = _number(
        weather_current.get(
            "temperature_2m"
        )
    )

    apparent = _number(
        weather_current.get(
            "apparent_temperature"
        )
    )

    pieces = []

    if temperature is not None:
        sentence = (
            f"{place_name} is currently "
            f"{temperature:.1f}°C"
        )

        if (
            apparent is not None
            and abs(
                apparent
                - temperature
            )
            >= 1.0
        ):
            sentence += (
                f", feeling like "
                f"{apparent:.1f}°C"
            )

        pieces.append(
            sentence
            + "."
        )

    if (
        forecast_high is not None
        and forecast_low is not None
    ):
        pieces.append(
            (
                f"Today's forecast spans roughly "
                f"{forecast_low:.1f}–"
                f"{forecast_high:.1f}°C."
            )
        )

    heat = health.get(
        "heat",
        {}
    )

    if heat.get(
        "label"
    ):
        pieces.append(
            (
                f"Thermal context is classified as "
                f"{str(heat['label']).lower()}."
            )
        )

    air = health.get(
        "air_quality",
        {}
    )

    if air.get(
        "label"
    ) not in {
        None,
        "Unavailable",
    }:
        pieces.append(
            (
                f"Air quality is currently "
                f"{str(air['label']).lower()}."
            )
        )

    if health.get(
        "night",
        {}
    ).get(
        "tropical_night"
    ):
        pieces.append(
            "Limited overnight cooling is expected."
        )

    elevated_compound = [
        item
        for item in compound
        if item.get(
            "level"
        ) in {
            "moderate",
            "high",
        }
    ]

    if elevated_compound:
        names = ", ".join(
            item.get(
                "name",
                "compound context",
            )
            for item in elevated_compound[
                :2
            ]
        )

        pieces.append(
            (
                "ClimatePulse also detects "
                f"{names.lower()}."
            )
        )

    if not pieces:
        return (
            "ClimatePulse has live environmental data for this location, "
            "but there is not enough information to generate a full brief."
        )

    return " ".join(
        pieces
    )