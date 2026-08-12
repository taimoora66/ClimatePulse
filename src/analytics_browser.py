from __future__ import annotations

from typing import Any

import streamlit as st


_BROWSER_HTML = """
<div id="cp-analytics-probe" aria-hidden="true"></div>
"""

_BROWSER_CSS = """
#cp-analytics-probe {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
"""

_BROWSER_JS = r"""
export default function(component) {
    const {
        data,
        setTriggerValue,
        parentElement
    } = component;

    if (parentElement) {
        parentElement.style.display = 'none';
        parentElement.style.width = '0px';
        parentElement.style.height = '0px';
        parentElement.style.overflow = 'hidden';
    }

    if (data?.already_captured) {
        return () => {};
    }

    function randomId(prefix) {
        try {
            if (window.crypto && crypto.randomUUID) {
                return prefix + '_' + crypto.randomUUID().replaceAll('-', '');
            }
        } catch (e) {}

        const value =
            Date.now().toString(36)
            + Math.random().toString(36).slice(2)
            + Math.random().toString(36).slice(2);

        return prefix + '_' + value;
    }

    function browserFamily(ua) {
        ua = String(ua || '');

        if (/Edg\//i.test(ua)) return 'Edge';
        if (/OPR\//i.test(ua)) return 'Opera';
        if (/Firefox\//i.test(ua)) return 'Firefox';
        if (/Chrome\//i.test(ua) && !/Edg\//i.test(ua)) return 'Chrome';
        if (/Safari\//i.test(ua) && !/Chrome\//i.test(ua)) return 'Safari';

        return 'Other';
    }

    function osFamily(ua) {
        ua = String(ua || '');

        if (/Windows NT/i.test(ua)) return 'Windows';
        if (/Android/i.test(ua)) return 'Android';
        if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS / iPadOS';
        if (/Mac OS X|Macintosh/i.test(ua)) return 'macOS';
        if (/Linux/i.test(ua)) return 'Linux';

        return 'Other';
    }

    function deviceCategory() {
        const width = window.innerWidth || 0;
        const touch = (
            ('ontouchstart' in window)
            || (navigator.maxTouchPoints || 0) > 0
        );

        if (width <= 767) return 'Mobile';
        if (width <= 1180 && touch) return 'Tablet';
        return 'Desktop';
    }

    function safeReferrerDomain() {
        try {
            if (!document.referrer) return '';
            return new URL(document.referrer).hostname || '';
        } catch (e) {
            return '';
        }
    }

    function utmValue(params, name) {
        const value = params.get(name);
        if (!value) return '';
        return String(value).slice(0, 240);
    }

    const dnt = (
        navigator.doNotTrack === '1'
        || window.doNotTrack === '1'
        || navigator.msDoNotTrack === '1'
    );

    const gpc = Boolean(
        navigator.globalPrivacyControl === true
    );

    // If the browser explicitly asks not to be tracked, send only the
    // opt-out flags so the Python side can stop analytics for this session.
    if (dnt || gpc) {
        setTriggerValue(
            'browser_context',
            {
                do_not_track: dnt,
                global_privacy_control: gpc
            }
        );
        return () => {};
    }

    const persistentEnabled = Boolean(
        data?.persistent_id_enabled
    );

    const visitorStorage = persistentEnabled
        ? window.localStorage
        : window.sessionStorage;

    const visitorKey = persistentEnabled
        ? 'climatepulse_analytics_visitor_v35'
        : 'climatepulse_analytics_session_visitor_v35';

    let visitorId = visitorStorage.getItem(visitorKey);
    if (!visitorId) {
        visitorId = randomId('visitor');
        visitorStorage.setItem(visitorKey, visitorId);
    }

    const sessionKey = 'climatepulse_analytics_session_v35';
    let sessionId = window.sessionStorage.getItem(sessionKey);
    if (!sessionId) {
        sessionId = randomId('session');
        window.sessionStorage.setItem(sessionKey, sessionId);
    }

    const params = new URLSearchParams(window.location.search || '');
    const ua = navigator.userAgent || '';

    let timezone = '';
    try {
        timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    } catch (e) {}

    let orientation = '';
    try {
        orientation = screen.orientation?.type || '';
    } catch (e) {}

    let colorScheme = 'unknown';
    try {
        colorScheme = window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'dark'
            : 'light';
    } catch (e) {}

    const payload = {
        visitor_id: String(visitorId).slice(0, 96),
        session_id: String(sessionId).slice(0, 96),
        persistent_id: persistentEnabled,

        referrer_domain: safeReferrerDomain().slice(0, 240),

        utm_source: utmValue(params, 'utm_source'),
        utm_medium: utmValue(params, 'utm_medium'),
        utm_campaign: utmValue(params, 'utm_campaign'),
        utm_content: utmValue(params, 'utm_content'),
        utm_term: utmValue(params, 'utm_term'),

        device_category: deviceCategory(),
        browser_family: browserFamily(ua),
        os_family: osFamily(ua),

        language: String(navigator.language || '').slice(0, 40),
        timezone: String(timezone || '').slice(0, 120),

        viewport_width: Number(window.innerWidth || 0),
        viewport_height: Number(window.innerHeight || 0),
        screen_width: Number(screen.width || 0),
        screen_height: Number(screen.height || 0),
        orientation: String(orientation || '').slice(0, 60),
        color_scheme: String(colorScheme || '').slice(0, 20),
        touch_capable: Boolean(
            ('ontouchstart' in window)
            || (navigator.maxTouchPoints || 0) > 0
        ),

        do_not_track: false,
        global_privacy_control: false
    };

    setTriggerValue(
        'browser_context',
        payload
    );

    return () => {};
}
"""


def _component_available() -> bool:
    try:
        return bool(
            getattr(
                getattr(st, "components", None),
                "v2",
                None,
            )
        )
    except Exception:
        return False


def _browser_component():
    key = "_climatepulse_analytics_browser_renderer_v35"

    if key not in st.session_state:
        renderer = st.components.v2.component(
            "climatepulse_analytics_browser_v35",
            html=_BROWSER_HTML,
            css=_BROWSER_CSS,
            js=_BROWSER_JS,
            isolate_styles=True,
        )
        st.session_state[key] = renderer

    return st.session_state[key]


def capture_browser_analytics_context(
    *,
    persistent_id_enabled: bool = False,
) -> tuple[dict[str, Any] | None, bool]:
    """
    Collect coarse browser/session analytics context once per Streamlit session.

    Returns
    -------
    (payload, component_supported)
    """
    if not _component_available():
        return None, False

    already_captured = bool(
        st.session_state.get("cp_analytics_browser_context_captured")
    )

    renderer = _browser_component()

    result = renderer(
        data={
            "already_captured": already_captured,
            "persistent_id_enabled": bool(persistent_id_enabled),
        },
        key="climatepulse_analytics_browser_mount_v35",
        on_browser_context_change=lambda: None,
    )

    payload = getattr(result, "browser_context", None)

    if isinstance(payload, dict):
        st.session_state["cp_analytics_browser_context_captured"] = True
        return payload, True

    return None, True