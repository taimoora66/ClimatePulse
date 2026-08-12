from __future__ import annotations

from typing import Any

import requests
import streamlit as st


NOMINATIM_REVERSE_URL = (
    "https://nominatim.openstreetmap.org/reverse"
)


@st.cache_data(
    ttl=86400,
    max_entries=256,
    show_spinner=False,
)
def reverse_geocode_location(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Best-effort reverse geocoding for browser coordinates.

    Important:
    live weather does not depend on this lookup. If the service is slow or
    temporarily unavailable, ClimatePulse still activates the coordinates
    immediately and falls back to a coordinate label.
    """

    payload = {}

    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params={
                "lat": float(latitude),
                "lon": float(longitude),
                "format": "jsonv2",
                "zoom": 10,
                "addressdetails": 1,
            },
            headers={
                "User-Agent":
                    "ClimatePulse/1.0 environmental-data application"
            },
            timeout=4,
        )

        response.raise_for_status()
        payload = response.json()

    except Exception:
        # Never block location activation because a place-name service failed.
        payload = {}

    address = payload.get(
        "address",
        {},
    )

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or ""
    )

    region = (
        address.get("state")
        or address.get("region")
        or ""
    )

    country = (
        address.get("country")
        or ""
    )

    country_code = (
        address.get("country_code")
        or ""
    ).upper()

    label_parts = []

    for value in [
        city,
        region,
        country,
    ]:
        if (
            value
            and value not in label_parts
        ):
            label_parts.append(
                value
            )

    coordinate_label = (
        f"{float(latitude):.4f}°, "
        f"{float(longitude):.4f}°"
    )

    label = (
        ", ".join(label_parts)
        or payload.get("display_name")
        or coordinate_label
    )

    return {
        "id": (
            "browser:"
            f"{float(latitude):.5f}:"
            f"{float(longitude):.5f}"
        ),
        "name":
            city
            or label,
        "label":
            label,
        "city":
            city,
        "admin1":
            region,
        "country":
            country,
        "country_code":
            country_code
            or None,
        "latitude":
            float(latitude),
        "longitude":
            float(longitude),
        "timezone":
            "auto",
        "kind":
            "browser",
        "result_type":
            "location",
        "source":
            "browser_geolocation",
        "scope_note": (
            "Current browser coordinates. "
            "Live weather is evaluated at the detected point."
        ),
    }


_LOCATION_HTML = """
<div id="cp-location-root">
    <button
        id="cp-location-button"
        type="button"
        aria-label="Use my current location"
    >
        <span id="cp-location-icon">◎</span>

        <div id="cp-location-copy">
            <div id="cp-location-title">
                Use my location
            </div>

            <div id="cp-location-subtitle">
                Detect current conditions
            </div>
        </div>

        <span id="cp-location-arrow">→</span>
    </button>

    <div id="cp-location-progress">
        <span id="cp-location-spinner"></span>
        <span id="cp-location-status">
            Detecting location…
        </span>
    </div>
</div>
"""


_LOCATION_CSS = r"""
#cp-location-root {
    width: 100%;
    max-width: 280px;

    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

#cp-location-button {
    width: 100%;
    min-height: 52px;

    display: grid;
    grid-template-columns:
        34px
        1fr
        20px;

    align-items: center;
    gap: 8px;

    padding:
        7px
        12px;

    border-radius: 13px;

    border:
        1px solid
        rgba(
            72,
            218,
            248,
            .20
        );

    background:
        linear-gradient(
            135deg,
            rgba(
                10,
                39,
                54,
                .96
            ),
            rgba(
                6,
                24,
                34,
                .98
            )
        );

    color: #effbff;

    box-shadow:
        0 8px 26px
        rgba(
            0,
            0,
            0,
            .22
        );

    cursor: pointer;
    text-align: left;

    transition:
        border-color .18s ease,
        transform .18s ease,
        box-shadow .18s ease,
        opacity .18s ease;
}

#cp-location-button:hover {
    transform:
        translateY(-1px);

    border-color:
        rgba(
            78,
            224,
            255,
            .55
        );

    box-shadow:
        0 11px 30px
        rgba(
            0,
            0,
            0,
            .27
        ),
        0 0 20px
        rgba(
            70,
            217,
            250,
            .06
        );
}

#cp-location-button:disabled {
    cursor: wait;
    opacity: .72;
}

#cp-location-icon {
    width: 32px;
    height: 32px;

    display: flex;
    align-items: center;
    justify-content: center;

    border-radius: 50%;

    color: #57e0ff;

    background:
        rgba(
            36,
            162,
            197,
            .12
        );

    border:
        1px solid
        rgba(
            86,
            225,
            255,
            .18
        );

    font-size: 19px;
}

#cp-location-title {
    color: #eefaff;

    font-size: 13px;
    line-height: 1.15;

    font-weight: 770;

    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

#cp-location-subtitle {
    margin-top: 3px;

    color: #728f9e;

    font-size: 9px;
    line-height: 1.2;

    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

#cp-location-arrow {
    color: #4edcff;
    font-size: 16px;
}

#cp-location-progress {
    display: none;

    align-items: center;
    gap: 8px;

    min-height: 28px;

    margin-top: 7px;

    padding:
        5px
        10px;

    border-radius: 9px;

    color: #77a0b0;

    background:
        rgba(
            6,
            26,
            37,
            .78
        );

    font-size: 10px;
}

#cp-location-progress.visible {
    display: flex;
}

#cp-location-spinner {
    width: 11px;
    height: 11px;

    border-radius: 50%;

    border:
        2px solid
        rgba(
            73,
            218,
            249,
            .18
        );

    border-top-color: #56dcfa;

    animation:
        cp-location-spin
        .8s
        linear
        infinite;
}

@keyframes cp-location-spin {
    to {
        transform:
            rotate(360deg);
    }
}
"""


_LOCATION_JS = r"""
export default function(component) {
    const {
        data,
        setTriggerValue,
        parentElement
    } = component;

    const button =
        parentElement.querySelector(
            '#cp-location-button'
        );

    const progress =
        parentElement.querySelector(
            '#cp-location-progress'
        );

    const status =
        parentElement.querySelector(
            '#cp-location-status'
        );

    const title =
        parentElement.querySelector(
            '#cp-location-title'
        );

    const subtitle =
        parentElement.querySelector(
            '#cp-location-subtitle'
        );

    function showProgress(
        text
    ) {
        progress.classList.add(
            'visible'
        );

        status.textContent =
            text;
    }

    function hideProgress() {
        progress.classList.remove(
            'visible'
        );
    }

    function setIdleState() {
        button.disabled =
            false;

        title.textContent =
            'Use my location';

        subtitle.textContent =
            'Detect current conditions';

        hideProgress();
    }

    function setLoadedState() {
        const activeLabel =
            data?.active_label
            || '';

        button.disabled =
            false;

        title.textContent =
            activeLabel
            ? 'Location active'
            : 'Use my location';

        subtitle.textContent =
            activeLabel
            || 'Detect current conditions';

        hideProgress();
    }

    function requestLocation() {
        if (
            !navigator.geolocation
        ) {
            showProgress(
                'Location is not supported by this browser.'
            );

            return;
        }

        button.disabled =
            true;

        title.textContent =
            'Locating…';

        subtitle.textContent =
            'Waiting for browser permission';

        showProgress(
            'Detecting current coordinates…'
        );

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const coordinates =
                    position.coords;

                showProgress(
                    'Location found · updating ClimatePulse…'
                );

                setTriggerValue(
                    'location',
                    {
                        latitude:
                            coordinates.latitude,
                        longitude:
                            coordinates.longitude,
                        accuracy:
                            coordinates.accuracy
                            || null,
                        timestamp:
                            Date.now()
                    }
                );

                // The Python side will rerun after processing.
                // If the browser retains this DOM briefly, do not leave
                // an endless spinner visible.
                window.setTimeout(
                    () => {
                        setLoadedState();
                    },
                    1800
                );
            },

            function(error) {
                let message =
                    'Location could not be detected.';

                if (
                    error.code === 1
                ) {
                    message =
                        'Location permission was denied.';
                }

                else if (
                    error.code === 2
                ) {
                    message =
                        'Current location is temporarily unavailable.';
                }

                else if (
                    error.code === 3
                ) {
                    message =
                        'Location request timed out. Try again.';
                }

                button.disabled =
                    false;

                title.textContent =
                    'Try again';

                subtitle.textContent =
                    'Use browser location';

                showProgress(
                    message
                );
            },

            {
                // Desktop/laptop geolocation is much faster with a normal
                // accuracy request. ClimatePulse does not require metre-level
                // GPS precision for weather/climate context.
                enableHighAccuracy:
                    false,

                timeout:
                    8000,

                // Reuse a recent browser fix to avoid unnecessary delays.
                maximumAge:
                    300000
            }
        );
    }

    button.addEventListener(
        'click',
        requestLocation
    );

    if (
        data?.active_label
    ) {
        setLoadedState();
    }

    else {
        setIdleState();
    }

    return () => {};
}
"""


def _component_available():
    try:
        return bool(
            getattr(
                getattr(
                    st,
                    "components",
                    None,
                ),
                "v2",
                None,
            )
        )

    except Exception:
        return False


def _location_component():
    key = (
        "_climatepulse_location_component_v30"
    )

    if key not in st.session_state:
        renderer = (
            st.components.v2.component(
                "climatepulse_location_v30",
                html=
                    _LOCATION_HTML,
                css=
                    _LOCATION_CSS,
                js=
                    _LOCATION_JS,
                isolate_styles=True,
            )
        )

        st.session_state[
            key
        ] = renderer

    return st.session_state[
        key
    ]


def render_location_control(
    active_location=None,
):
    """
    One-click current-location control.

    Returns a newly-detected location only once for each browser acquisition.
    """

    if not _component_available():
        st.caption(
            "Location detection requires Streamlit Components v2."
        )

        return None

    active_label = ""

    if isinstance(
        active_location,
        dict,
    ):
        active_label = (
            active_location.get("label")
            or active_location.get("name")
            or ""
        )

    renderer = (
        _location_component()
    )

    result = renderer(
        data={
            "active_label":
                active_label,
        },
        key=
            "climatepulse_location_mount_v30",
        on_location_change=
            lambda: None,
    )

    payload = getattr(
        result,
        "location",
        None,
    )

    if not payload:
        return None

    latitude = float(
        payload["latitude"]
    )

    longitude = float(
        payload["longitude"]
    )

    timestamp = int(
        payload.get(
            "timestamp",
            0,
        )
    )

    signature = (
        round(
            latitude,
            5,
        ),
        round(
            longitude,
            5,
        ),
        timestamp,
    )

    if (
        st.session_state.get(
            "_cp_location_signature_v30"
        )
        == signature
    ):
        return None

    st.session_state[
        "_cp_location_signature_v30"
    ] = signature

    # Activate the coordinates regardless of reverse-geocoder availability.
    resolved = (
        reverse_geocode_location(
            latitude,
            longitude,
        )
    )

    resolved[
        "accuracy"
    ] = payload.get(
        "accuracy"
    )

    return resolved