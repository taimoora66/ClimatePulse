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
    temporarily unavailable, ORBIDENSE AI still activates the coordinates
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
                    "ORBIDENSE-AI/1.0 environmental-data application"
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

    const button = parentElement.querySelector('#cp-location-button');
    const progress = parentElement.querySelector('#cp-location-progress');
    const status = parentElement.querySelector('#cp-location-status');
    const title = parentElement.querySelector('#cp-location-title');
    const subtitle = parentElement.querySelector('#cp-location-subtitle');

    const STORAGE_KEY = 'orbidense_browser_location_v1';
    const AUTO_ATTEMPT_KEY = 'orbidense_geo_auto_attempted_v1';
    const CACHE_MAX_AGE_MS = 10 * 60 * 1000;

    let disposed = false;
    let requestInFlight = false;

    function showProgress(text) {
        progress.classList.add('visible');
        status.textContent = text;
    }

    function hideProgress() {
        progress.classList.remove('visible');
    }

    function setButtonState(mainText, subText, disabled=false) {
        button.disabled = disabled;
        title.textContent = mainText;
        subtitle.textContent = subText;
    }

    function setIdleState() {
        setButtonState('Use my location', 'Detect current conditions', false);
        hideProgress();
    }

    function setLoadedState(label='') {
        setButtonState(
            'Current location',
            label || 'Live conditions active',
            false
        );
        hideProgress();
    }

    function setDeniedState() {
        setButtonState('Enable location', 'Allow location in your browser', false);
        showProgress('Location access is off. Enable it or search for a place.');
    }

    function setUnavailableState(message='Location is unavailable. Search for a place instead.') {
        setButtonState('Try location again', 'Or use global search', false);
        showProgress(message);
    }

    function emitCoordinates(latitude, longitude, accuracy, timestamp, source='browser_geolocation') {
        if (disposed) return;

        setTriggerValue('location', {
            latitude: Number(latitude),
            longitude: Number(longitude),
            accuracy: accuracy == null ? null : Number(accuracy),
            timestamp: Number(timestamp || Date.now()),
            source: source
        });
    }

    function saveCoordinates(coords) {
        try {
            sessionStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    latitude: coords.latitude,
                    longitude: coords.longitude,
                    accuracy: coords.accuracy || null,
                    timestamp: Date.now()
                })
            );
        } catch (_) {}
    }

    function loadRecentCoordinates() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            if (!raw) return null;
            const cached = JSON.parse(raw);
            if (!cached?.latitude || !cached?.longitude || !cached?.timestamp) return null;
            if ((Date.now() - cached.timestamp) > CACHE_MAX_AGE_MS) return null;
            return cached;
        } catch (_) {
            return null;
        }
    }

    function requestLocation({ automatic=false, highAccuracy=false }={}) {
        if (requestInFlight || disposed) return;

        if (!window.isSecureContext) {
            setUnavailableState('Location requires HTTPS (or localhost).');
            return;
        }

        if (!navigator.geolocation) {
            setUnavailableState('This browser does not provide location access.');
            return;
        }

        requestInFlight = true;
        setButtonState('Locating…', automatic ? 'Preparing your local dashboard' : 'Waiting for browser location', true);
        showProgress(automatic ? 'Detecting your current location…' : 'Detecting current coordinates…');

        navigator.geolocation.getCurrentPosition(
            (position) => {
                requestInFlight = false;
                const coords = position.coords;
                saveCoordinates(coords);
                showProgress('Location found · loading local weather…');
                setButtonState('Current location', 'Loading live conditions', true);

                emitCoordinates(
                    coords.latitude,
                    coords.longitude,
                    coords.accuracy || null,
                    Date.now(),
                    automatic ? 'browser_geolocation_auto' : 'browser_geolocation_manual'
                );

                window.setTimeout(() => {
                    if (!disposed) setLoadedState(data?.active_label || 'Live conditions active');
                }, 1600);
            },
            (error) => {
                requestInFlight = false;

                if (error.code === 1) {
                    setDeniedState();
                    return;
                }

                if (error.code === 3 && !highAccuracy) {
                    // One quiet retry can help laptops that need a little longer.
                    requestLocation({ automatic, highAccuracy: true });
                    return;
                }

                if (error.code === 2) {
                    setUnavailableState('Current location is temporarily unavailable.');
                } else if (error.code === 3) {
                    setUnavailableState('Location request timed out. Try again or search for a place.');
                } else {
                    setUnavailableState();
                }
            },
            {
                enableHighAccuracy: Boolean(highAccuracy),
                timeout: highAccuracy ? 15000 : 9000,
                maximumAge: 300000
            }
        );
    }

    async function automaticBootstrap() {
        // If Python already has an active browser-derived location, don't ask again.
        if (data?.active_label) {
            setLoadedState(data.active_label);
            return;
        }

        // Fast path after Streamlit reruns within the same browser tab.
        const cached = loadRecentCoordinates();
        if (cached) {
            setButtonState('Current location', 'Restoring local conditions', true);
            showProgress('Restoring your current location…');
            emitCoordinates(
                cached.latitude,
                cached.longitude,
                cached.accuracy,
                cached.timestamp,
                'browser_geolocation_cache'
            );
            return;
        }

        // Avoid triggering a permission prompt on every Streamlit rerun.
        let attempted = false;
        try {
            attempted = sessionStorage.getItem(AUTO_ATTEMPT_KEY) === '1';
        } catch (_) {}

        if (attempted) {
            setIdleState();
            return;
        }

        try {
            sessionStorage.setItem(AUTO_ATTEMPT_KEY, '1');
        } catch (_) {}

        if (!window.isSecureContext || !navigator.geolocation) {
            setUnavailableState(
                !window.isSecureContext
                    ? 'Location requires HTTPS (or localhost).'
                    : 'This browser does not provide location access.'
            );
            return;
        }

        // Permissions API lets us avoid repeatedly prompting visitors who denied it.
        if (navigator.permissions?.query) {
            try {
                const permission = await navigator.permissions.query({ name: 'geolocation' });

                if (permission.state === 'denied') {
                    setDeniedState();
                    return;
                }

                // Both "granted" and "prompt" proceed. For "prompt", the browser
                // displays its normal permission dialog; ORBIDENSE AI cannot and
                // should not bypass that browser privacy control.
                requestLocation({ automatic: true });
                return;
            } catch (_) {
                // Safari and some browsers may not expose geolocation permission
                // through navigator.permissions. Fall back to getCurrentPosition.
            }
        }

        requestLocation({ automatic: true });
    }

    const manualHandler = () => {
        try {
            sessionStorage.removeItem(AUTO_ATTEMPT_KEY);
        } catch (_) {}
        requestLocation({ automatic: false });
    };

    button.addEventListener('click', manualHandler);
    automaticBootstrap();

    return () => {
        disposed = true;
        button.removeEventListener('click', manualHandler);
    };
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
        "_orbidense_location_component_v31"
    )

    if key not in st.session_state:
        renderer = (
            st.components.v2.component(
                "orbidense_location_v31",
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
            "orbidense_location_mount_v31",
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
            "_orbidense_location_signature_v31"
        )
        == signature
    ):
        return None

    st.session_state[
        "_orbidense_location_signature_v31"
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