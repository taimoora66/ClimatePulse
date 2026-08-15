from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
import traceback
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import streamlit as st

from src.db import get_connection


# =========================================================
# ORBIDENSE AI FIRST-PARTY ANALYTICS
# =========================================================
#
# Design goals
# ------------
# * private developer dashboard
# * first-party PostgreSQL / Neon storage
# * anonymous session/visitor identifiers
# * active-now heartbeat
# * page views + events + acquisition + device context
# * no names, email addresses, raw IP addresses, GPS coordinates,
#   raw user-agent strings, advertising IDs, or message contents
#
# Visitor identifiers are session-scoped in this build. Cross-visit
# fingerprinting is intentionally not implemented. This keeps the tracker
# first-party and privacy-conscious while still supporting live audience,
# traffic, acquisition and product-usage analytics.
# =========================================================

ACTIVE_WINDOW_MINUTES = 2

VISITOR_KEY = "cp_analytics_visitor_id"
SESSION_KEY = "cp_analytics_session_id"
LAST_PAGE_KEY = "cp_analytics_last_page"
BROWSER_CONTEXT_KEY = "cp_analytics_browser_context"
EVENT_SIGNATURE_PREFIX = "cp_analytics_event_signature::"


def _anonymous_id(prefix: str) -> str:
    raw = f"{prefix}:{uuid.uuid4().hex}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:32]}"


def get_visitor_id() -> str:
    if VISITOR_KEY not in st.session_state:
        st.session_state[VISITOR_KEY] = _anonymous_id("visitor")
    return str(st.session_state[VISITOR_KEY])


def get_session_id() -> str:
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = _anonymous_id("session")
    return str(st.session_state[SESSION_KEY])


def _env_bool(name: str, default: bool = False) -> bool:
    value = None
    try:
        if name in st.secrets:
            value = st.secrets[name]
    except Exception:
        pass
    if value is None:
        value = os.getenv(name, str(default))
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def track_local_sessions_enabled() -> bool:
    """Localhost traffic is excluded by default so development does not pollute analytics."""
    return _env_bool("ANALYTICS_TRACK_LOCAL", False)


def persistent_visitor_id_enabled() -> bool:
    """
    Backwards-compatible analytics API.

    ORBIDENSE AI V2 intentionally uses session-scoped anonymous visitor IDs
    and does not implement persistent browser fingerprinting. Older dashboard
    builds imported this function, so it remains available and always returns
    False. Keeping this compatibility shim prevents mixed-version deployments
    from crashing while preserving the privacy-conscious V37+ behaviour.
    """
    return False


def _query_param(name: str) -> str | None:
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            value = value[0] if value else None
        if value is None:
            return None
        text = str(value).strip()
        return text[:240] if text else None
    except Exception:
        return None


def _header(headers: Any, name: str) -> str | None:
    try:
        value = headers.get(name)
        if value is None:
            value = headers.get(name.lower())
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None
    except Exception:
        return None


def _browser_family(user_agent: str | None) -> str:
    ua = user_agent or ""
    checks = (
        (r"Edg/", "Edge"),
        (r"OPR/|Opera", "Opera"),
        (r"SamsungBrowser/", "Samsung Internet"),
        (r"Firefox/|FxiOS/", "Firefox"),
        (r"CriOS/", "Chrome iOS"),
        (r"Chrome/|Chromium/", "Chrome"),
        (r"Version/.+Safari/", "Safari"),
    )
    for pattern, label in checks:
        if re.search(pattern, ua, re.I):
            return label
    return "Other / unknown"


def _os_family(user_agent: str | None, client_platform: str | None = None) -> str:
    ua = user_agent or ""
    platform = (client_platform or "").strip('"')
    combined = f"{ua} {platform}"
    checks = (
        (r"Windows", "Windows"),
        (r"Android", "Android"),
        (r"iPhone|iPad|iPod|iOS", "iOS / iPadOS"),
        (r"Macintosh|Mac OS X|macOS", "macOS"),
        (r"CrOS", "ChromeOS"),
        (r"Linux", "Linux"),
    )
    for pattern, label in checks:
        if re.search(pattern, combined, re.I):
            return label
    return "Other / unknown"


def _device_category(user_agent: str | None, mobile_hint: str | None = None) -> str:
    ua = user_agent or ""
    mobile = (mobile_hint or "").strip().lower() in {"?1", "1", "true"}
    if re.search(r"iPad|Tablet|Kindle|Silk", ua, re.I):
        return "Tablet"
    if re.search(r"Android", ua, re.I) and not re.search(r"Mobile", ua, re.I):
        return "Tablet"
    if mobile or re.search(r"Mobile|iPhone|iPod|Android.*Mobile", ua, re.I):
        return "Mobile"
    return "Desktop"


def _referrer_domain(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value)
        return (parsed.hostname or "")[:240] or None
    except Exception:
        return None


def _country_hint(headers: Any) -> str | None:
    # Hosting/CDN country hints are accepted only when already supplied by
    # infrastructure. ORBIDENSE AI never geolocates or stores the raw IP.
    for name in (
        "cf-ipcountry",
        "cloudfront-viewer-country",
        "x-vercel-ip-country",
        "x-appengine-country",
    ):
        value = _header(headers, name)
        if value and re.fullmatch(r"[A-Za-z]{2}", value):
            return value.upper()
    return None


def is_local_session() -> bool:
    try:
        url = str(getattr(st.context, "url", "") or "")
        host = (urlparse(url).hostname or "").lower()
        return host in {"localhost", "127.0.0.1", "::1"}
    except Exception:
        return False


def capture_streamlit_context() -> bool:
    """
    Capture privacy-conscious browser/session context using Streamlit's native
    ``st.context`` API. No custom JavaScript component is mounted.

    Returns False when DNT/GPC requests analytics opt-out.
    """
    if st.session_state.get("cp_analytics_context_captured"):
        return analytics_tracking_allowed()

    try:
        context = getattr(st, "context", None)
        headers = getattr(context, "headers", {}) if context is not None else {}

        dnt = str(_header(headers, "dnt") or "").strip() == "1"
        gpc = str(_header(headers, "sec-gpc") or "").strip() == "1"

        st.session_state["cp_analytics_privacy_opt_out"] = bool(dnt or gpc)
        st.session_state["cp_analytics_context_captured"] = True

        if dnt or gpc:
            return False

        user_agent = _header(headers, "user-agent")
        client_platform = _header(headers, "sec-ch-ua-platform")
        mobile_hint = _header(headers, "sec-ch-ua-mobile")
        referer = _header(headers, "referer") or _header(headers, "referrer")

        locale = None
        timezone = None
        timezone_offset = None
        theme_type = None
        is_embedded = False
        app_url = None

        if context is not None:
            try:
                locale = getattr(context, "locale", None)
            except Exception:
                pass
            try:
                timezone = getattr(context, "timezone", None)
            except Exception:
                pass
            try:
                timezone_offset = getattr(context, "timezone_offset", None)
            except Exception:
                pass
            try:
                theme = getattr(context, "theme", None)
                theme_type = getattr(theme, "type", None) if theme is not None else None
            except Exception:
                pass
            try:
                is_embedded = bool(getattr(context, "is_embedded", False))
            except Exception:
                pass
            try:
                app_url = str(getattr(context, "url", "") or "")
            except Exception:
                pass

        app_host = None
        if app_url:
            try:
                app_host = (urlparse(app_url).hostname or "")[:240] or None
            except Exception:
                pass

        payload = {
            "referrer_domain": _referrer_domain(referer),
            "utm_source": _query_param("utm_source"),
            "utm_medium": _query_param("utm_medium"),
            "utm_campaign": _query_param("utm_campaign"),
            "utm_content": _query_param("utm_content"),
            "utm_term": _query_param("utm_term"),
            "device_category": _device_category(user_agent, mobile_hint),
            "browser_family": _browser_family(user_agent),
            "os_family": _os_family(user_agent, client_platform),
            "language": str(locale or _header(headers, "accept-language") or "")[:80] or None,
            "timezone": str(timezone or "")[:120] or None,
            "timezone_offset_minutes": int(timezone_offset) if timezone_offset is not None else None,
            "theme_type": str(theme_type or "")[:20] or None,
            "is_embedded": bool(is_embedded),
            "app_host": app_host,
            "country_hint": _country_hint(headers),
            "do_not_track": False,
            "global_privacy_control": False,
            "persistent_id": False,
        }

        st.session_state[BROWSER_CONTEXT_KEY] = payload
        return True

    except Exception as error:
        # Context enrichment must never break the app. Basic session analytics
        # can still proceed with anonymous IDs and page/event data.
        print("ClimatePulse native analytics context error:", error)
        st.session_state["cp_analytics_context_captured"] = True
        st.session_state.setdefault(BROWSER_CONTEXT_KEY, {})
        return True


# =========================================================
# DATABASE INITIALIZATION / MIGRATION
# =========================================================


def initialize_analytics() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS analytics_visitors (
            visitor_id TEXT PRIMARY KEY,
            first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            total_sessions BIGINT NOT NULL DEFAULT 0,
            total_pageviews BIGINT NOT NULL DEFAULT 0,
            total_events BIGINT NOT NULL DEFAULT 0,
            first_entry_page TEXT,
            first_referrer_domain TEXT,
            first_utm_source TEXT,
            first_utm_medium TEXT,
            first_utm_campaign TEXT,
            latest_device_category TEXT,
            latest_browser_family TEXT,
            latest_os_family TEXT,
            latest_language TEXT,
            latest_timezone TEXT,
            latest_theme_type TEXT,
            latest_country_hint TEXT,
            latest_is_embedded BOOLEAN,
            persistent_id BOOLEAN NOT NULL DEFAULT FALSE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_sessions (
            session_id TEXT PRIMARY KEY,
            visitor_id TEXT NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            current_page TEXT,
            entry_page TEXT,
            pageviews BIGINT NOT NULL DEFAULT 0,
            events BIGINT NOT NULL DEFAULT 0,
            referrer_domain TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_content TEXT,
            utm_term TEXT,
            device_category TEXT,
            browser_family TEXT,
            os_family TEXT,
            language TEXT,
            timezone TEXT,
            timezone_offset_minutes INTEGER,
            theme_type TEXT,
            is_embedded BOOLEAN,
            app_host TEXT,
            country_hint TEXT,
            viewport_width INTEGER,
            viewport_height INTEGER,
            screen_width INTEGER,
            screen_height INTEGER,
            orientation TEXT,
            color_scheme TEXT,
            touch_capable BOOLEAN,
            do_not_track BOOLEAN,
            global_privacy_control BOOLEAN,
            persistent_id BOOLEAN NOT NULL DEFAULT FALSE,
            CONSTRAINT fk_analytics_visitor
                FOREIGN KEY (visitor_id)
                REFERENCES analytics_visitors(visitor_id)
                ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_pageviews (
            pageview_id BIGSERIAL PRIMARY KEY,
            visitor_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            page_name TEXT NOT NULL,
            viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            event_id BIGSERIAL PRIMARY KEY,
            visitor_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            page_name TEXT,
            event_name TEXT NOT NULL,
            event_category TEXT NOT NULL DEFAULT 'interaction',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            event_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_errors (
            error_id BIGSERIAL PRIMARY KEY,
            session_id TEXT,
            page_name TEXT,
            component TEXT NOT NULL,
            operation TEXT,
            severity TEXT NOT NULL DEFAULT 'error',
            error_type TEXT NOT NULL,
            error_hash TEXT NOT NULL,
            message_redacted TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_performance (
            performance_id BIGSERIAL PRIMARY KEY,
            session_id TEXT,
            page_name TEXT,
            operation TEXT NOT NULL,
            duration_ms DOUBLE PRECISION NOT NULL,
            success BOOLEAN NOT NULL DEFAULT TRUE,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_ai_usage (
            ai_usage_id BIGSERIAL PRIMARY KEY,
            session_id TEXT,
            page_name TEXT,
            request_category TEXT,
            model_name TEXT,
            duration_ms DOUBLE PRECISION,
            success BOOLEAN NOT NULL DEFAULT TRUE,
            input_chars INTEGER,
            output_chars INTEGER,
            error_type TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics_data_quality (
            quality_id BIGSERIAL PRIMARY KEY,
            source_name TEXT NOT NULL,
            check_name TEXT NOT NULL,
            status TEXT NOT NULL,
            affected_records BIGINT,
            freshness_seconds BIGINT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        # Safe migrations for older analytics tables already created.
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS total_events BIGINT NOT NULL DEFAULT 0;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS first_entry_page TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS first_referrer_domain TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS first_utm_source TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS first_utm_medium TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS first_utm_campaign TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_device_category TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_browser_family TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_os_family TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_language TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_timezone TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_theme_type TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_country_hint TEXT;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS latest_is_embedded BOOLEAN;",
        "ALTER TABLE analytics_visitors ADD COLUMN IF NOT EXISTS persistent_id BOOLEAN NOT NULL DEFAULT FALSE;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS entry_page TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS events BIGINT NOT NULL DEFAULT 0;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS referrer_domain TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS utm_source TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS utm_medium TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS utm_campaign TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS utm_content TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS utm_term TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS device_category TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS browser_family TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS os_family TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS language TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS timezone TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS timezone_offset_minutes INTEGER;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS theme_type TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS is_embedded BOOLEAN;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS app_host TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS country_hint TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS viewport_width INTEGER;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS viewport_height INTEGER;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS screen_width INTEGER;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS screen_height INTEGER;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS orientation TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS color_scheme TEXT;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS touch_capable BOOLEAN;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS do_not_track BOOLEAN;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS global_privacy_control BOOLEAN;",
        "ALTER TABLE analytics_sessions ADD COLUMN IF NOT EXISTS persistent_id BOOLEAN NOT NULL DEFAULT FALSE;",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_last_seen ON analytics_sessions(last_seen);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_visitor ON analytics_sessions(visitor_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_device ON analytics_sessions(device_category);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_country_hint ON analytics_sessions(country_hint);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_referrer ON analytics_sessions(referrer_domain);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_sessions_utm_source ON analytics_sessions(utm_source);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_pageviews_viewed_at ON analytics_pageviews(viewed_at);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_pageviews_page_name ON analytics_pageviews(page_name);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_pageviews_visitor ON analytics_pageviews(visitor_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_pageviews_session ON analytics_pageviews(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_event_at ON analytics_events(event_at);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_event_name ON analytics_events(event_name);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_session ON analytics_events(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_events_visitor ON analytics_events(visitor_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_errors_recorded_at ON analytics_errors(recorded_at);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_errors_component ON analytics_errors(component);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_errors_hash ON analytics_errors(error_hash);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_performance_recorded_at ON analytics_performance(recorded_at);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_performance_operation ON analytics_performance(operation);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_ai_usage_recorded_at ON analytics_ai_usage(recorded_at);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_data_quality_recorded_at ON analytics_data_quality(recorded_at);",
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)


@st.cache_resource(show_spinner=False)
def ensure_analytics_database() -> bool:
    initialize_analytics()
    return True


# =========================================================
# SESSION CONTEXT
# =========================================================


def analytics_tracking_allowed() -> bool:
    return not bool(st.session_state.get("cp_analytics_privacy_opt_out"))


def _browser_context() -> dict[str, Any]:
    value = st.session_state.get(BROWSER_CONTEXT_KEY, {})
    return value if isinstance(value, dict) else {}


# =========================================================
# SESSION / PAGE VIEW / EVENT TRACKING
# =========================================================


def register_session(page_name: str = "Home") -> tuple[str, str]:
    visitor_id = get_visitor_id()
    session_id = get_session_id()
    context = _browser_context()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_visitors (
                    visitor_id,
                    first_seen,
                    last_seen,
                    total_sessions,
                    total_pageviews,
                    total_events,
                    first_entry_page,
                    first_referrer_domain,
                    first_utm_source,
                    first_utm_medium,
                    first_utm_campaign,
                    latest_device_category,
                    latest_browser_family,
                    latest_os_family,
                    latest_language,
                    latest_timezone,
                    latest_theme_type,
                    latest_country_hint,
                    latest_is_embedded,
                    persistent_id
                )
                VALUES (
                    %s, NOW(), NOW(), 0, 0, 0,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (visitor_id)
                DO UPDATE SET
                    last_seen = NOW(),
                    latest_device_category = COALESCE(EXCLUDED.latest_device_category, analytics_visitors.latest_device_category),
                    latest_browser_family = COALESCE(EXCLUDED.latest_browser_family, analytics_visitors.latest_browser_family),
                    latest_os_family = COALESCE(EXCLUDED.latest_os_family, analytics_visitors.latest_os_family),
                    latest_language = COALESCE(EXCLUDED.latest_language, analytics_visitors.latest_language),
                    latest_timezone = COALESCE(EXCLUDED.latest_timezone, analytics_visitors.latest_timezone),
                    latest_theme_type = COALESCE(EXCLUDED.latest_theme_type, analytics_visitors.latest_theme_type),
                    latest_country_hint = COALESCE(EXCLUDED.latest_country_hint, analytics_visitors.latest_country_hint),
                    latest_is_embedded = COALESCE(EXCLUDED.latest_is_embedded, analytics_visitors.latest_is_embedded),
                    persistent_id = EXCLUDED.persistent_id;
                """,
                (
                    visitor_id,
                    page_name,
                    context.get("referrer_domain"),
                    context.get("utm_source"),
                    context.get("utm_medium"),
                    context.get("utm_campaign"),
                    context.get("device_category"),
                    context.get("browser_family"),
                    context.get("os_family"),
                    context.get("language"),
                    context.get("timezone"),
                    context.get("theme_type"),
                    context.get("country_hint"),
                    context.get("is_embedded"),
                    bool(context.get("persistent_id")),
                ),
            )

            cur.execute(
                """
                INSERT INTO analytics_sessions (
                    session_id,
                    visitor_id,
                    started_at,
                    last_seen,
                    current_page,
                    entry_page,
                    pageviews,
                    events,
                    referrer_domain,
                    utm_source,
                    utm_medium,
                    utm_campaign,
                    utm_content,
                    utm_term,
                    device_category,
                    browser_family,
                    os_family,
                    language,
                    timezone,
                    timezone_offset_minutes,
                    theme_type,
                    is_embedded,
                    app_host,
                    country_hint,
                    viewport_width,
                    viewport_height,
                    screen_width,
                    screen_height,
                    orientation,
                    color_scheme,
                    touch_capable,
                    do_not_track,
                    global_privacy_control,
                    persistent_id
                )
                VALUES (
                    %s, %s, NOW(), NOW(), %s, %s, 0, 0,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (session_id)
                DO NOTHING
                RETURNING session_id;
                """,
                (
                    session_id,
                    visitor_id,
                    page_name,
                    page_name,
                    context.get("referrer_domain"),
                    context.get("utm_source"),
                    context.get("utm_medium"),
                    context.get("utm_campaign"),
                    context.get("utm_content"),
                    context.get("utm_term"),
                    context.get("device_category"),
                    context.get("browser_family"),
                    context.get("os_family"),
                    context.get("language"),
                    context.get("timezone"),
                    context.get("timezone_offset_minutes"),
                    context.get("theme_type"),
                    context.get("is_embedded"),
                    context.get("app_host"),
                    context.get("country_hint"),
                    context.get("viewport_width"),
                    context.get("viewport_height"),
                    context.get("screen_width"),
                    context.get("screen_height"),
                    context.get("orientation"),
                    context.get("color_scheme"),
                    context.get("touch_capable"),
                    context.get("do_not_track"),
                    context.get("global_privacy_control"),
                    bool(context.get("persistent_id")),
                ),
            )

            new_session = cur.fetchone()

            if new_session:
                cur.execute(
                    """
                    UPDATE analytics_visitors
                    SET total_sessions = total_sessions + 1,
                        last_seen = NOW()
                    WHERE visitor_id = %s;
                    """,
                    (visitor_id,),
                )
            else:
                cur.execute(
                    """
                    UPDATE analytics_sessions
                    SET
                        last_seen = NOW(),
                        current_page = %s,
                        device_category = COALESCE(%s, device_category),
                        browser_family = COALESCE(%s, browser_family),
                        os_family = COALESCE(%s, os_family),
                        language = COALESCE(%s, language),
                        timezone = COALESCE(%s, timezone),
                        timezone_offset_minutes = COALESCE(%s, timezone_offset_minutes),
                        theme_type = COALESCE(%s, theme_type),
                        is_embedded = COALESCE(%s, is_embedded),
                        app_host = COALESCE(%s, app_host),
                        country_hint = COALESCE(%s, country_hint)
                    WHERE session_id = %s;
                    """,
                    (
                        page_name,
                        context.get("device_category"),
                        context.get("browser_family"),
                        context.get("os_family"),
                        context.get("language"),
                        context.get("timezone"),
                        context.get("timezone_offset_minutes"),
                        context.get("theme_type"),
                        context.get("is_embedded"),
                        context.get("app_host"),
                        context.get("country_hint"),
                        session_id,
                    ),
                )

    return visitor_id, session_id


def heartbeat(page_name: str | None = None) -> None:
    if not analytics_tracking_allowed():
        return

    visitor_id, session_id = register_session(page_name or "Home")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE analytics_visitors SET last_seen = NOW() WHERE visitor_id = %s;",
                (visitor_id,),
            )
            cur.execute(
                """
                UPDATE analytics_sessions
                SET last_seen = NOW(),
                    current_page = COALESCE(%s, current_page)
                WHERE session_id = %s;
                """,
                (page_name, session_id),
            )


def track_pageview(page_name: str) -> None:
    if not analytics_tracking_allowed():
        return

    page_name = str(page_name or "Unknown").strip()[:160]
    visitor_id, session_id = register_session(page_name)

    last_page = st.session_state.get(LAST_PAGE_KEY)
    if last_page == page_name:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_pageviews (
                    visitor_id, session_id, page_name, viewed_at
                ) VALUES (%s, %s, %s, NOW());
                """,
                (visitor_id, session_id, page_name),
            )
            cur.execute(
                """
                UPDATE analytics_visitors
                SET last_seen = NOW(), total_pageviews = total_pageviews + 1
                WHERE visitor_id = %s;
                """,
                (visitor_id,),
            )
            cur.execute(
                """
                UPDATE analytics_sessions
                SET last_seen = NOW(), current_page = %s, pageviews = pageviews + 1
                WHERE session_id = %s;
                """,
                (page_name, session_id),
            )

    st.session_state[LAST_PAGE_KEY] = page_name


def _json_safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}

    cleaned: dict[str, Any] = {}

    for key, value in metadata.items():
        key_text = str(key)[:80]
        if value is None or isinstance(value, (bool, int, float)):
            cleaned[key_text] = value
        elif isinstance(value, str):
            cleaned[key_text] = value[:500]
        elif isinstance(value, (list, tuple)):
            cleaned[key_text] = [str(item)[:200] for item in value[:25]]
        elif isinstance(value, dict):
            cleaned[key_text] = {
                str(k)[:80]: str(v)[:300]
                for k, v in list(value.items())[:25]
            }
        else:
            cleaned[key_text] = str(value)[:300]

    return cleaned


def track_event(
    event_name: str,
    *,
    category: str = "interaction",
    page_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not analytics_tracking_allowed():
        return

    event_name = str(event_name or "event").strip()[:120]
    category = str(category or "interaction").strip()[:80]
    page_name = str(page_name or st.session_state.get("main_navigation") or "Unknown")[:160]
    clean_metadata = _json_safe_metadata(metadata)

    visitor_id, session_id = register_session(page_name)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics_events (
                    visitor_id, session_id, page_name,
                    event_name, event_category, metadata, event_at
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW());
                """,
                (
                    visitor_id,
                    session_id,
                    page_name,
                    event_name,
                    category,
                    json.dumps(clean_metadata),
                ),
            )
            cur.execute(
                """
                UPDATE analytics_visitors
                SET last_seen = NOW(), total_events = total_events + 1
                WHERE visitor_id = %s;
                """,
                (visitor_id,),
            )
            cur.execute(
                """
                UPDATE analytics_sessions
                SET last_seen = NOW(), events = events + 1
                WHERE session_id = %s;
                """,
                (session_id,),
            )


def track_event_once(
    signature: str,
    event_name: str,
    *,
    category: str = "interaction",
    page_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Prevent Streamlit reruns from recording the same logical event repeatedly."""
    key = f"{EVENT_SIGNATURE_PREFIX}{signature}"
    if st.session_state.get(key):
        return

    track_event(
        event_name,
        category=category,
        page_name=page_name,
        metadata=metadata,
    )
    st.session_state[key] = True


@st.fragment(run_every=60)
def render_analytics_heartbeat(page_name: str) -> None:
    try:
        heartbeat(page_name)
    except Exception as error:
        print("ORBIDENSE AI analytics heartbeat error:", error)


# =========================================================
# QUERY HELPERS
# =========================================================


def _fetchone(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone() or {}


def _fetchall(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def get_analytics_summary() -> dict[str, Any]:
    row = _fetchone(
        """
        SELECT
            (SELECT COUNT(*) FROM analytics_sessions
             WHERE last_seen >= NOW() - (%s * INTERVAL '1 minute')) AS active_now,
            (SELECT COUNT(DISTINCT visitor_id) FROM analytics_pageviews
             WHERE viewed_at >= CURRENT_DATE) AS visitors_today,
            (SELECT COUNT(DISTINCT visitor_id) FROM analytics_pageviews
             WHERE viewed_at >= NOW() - INTERVAL '7 days') AS visitors_7d,
            (SELECT COUNT(DISTINCT visitor_id) FROM analytics_pageviews
             WHERE viewed_at >= NOW() - INTERVAL '30 days') AS visitors_30d,
            (SELECT COUNT(*) FROM analytics_visitors) AS unique_visitors,
            (SELECT COUNT(*) FROM analytics_visitors WHERE total_sessions > 1) AS returning_visitors,
            (SELECT COUNT(*) FROM analytics_sessions) AS total_sessions,
            (SELECT COUNT(*) FROM analytics_pageviews) AS total_pageviews,
            (SELECT COUNT(*) FROM analytics_events) AS total_events,
            (SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (last_seen - started_at)) / 60.0), 0)
             FROM analytics_sessions) AS avg_session_minutes,
            (SELECT COALESCE(AVG(pageviews::numeric), 0) FROM analytics_sessions) AS avg_pages_per_session,
            (SELECT COALESCE(AVG(events::numeric), 0) FROM analytics_sessions) AS avg_events_per_session,
            (SELECT COUNT(*) FROM analytics_sessions WHERE pageviews <= 1) AS single_page_sessions;
        """,
        (ACTIVE_WINDOW_MINUTES,),
    )

    numeric_ints = {
        "active_now",
        "visitors_today",
        "visitors_7d",
        "visitors_30d",
        "unique_visitors",
        "returning_visitors",
        "total_sessions",
        "total_pageviews",
        "total_events",
        "single_page_sessions",
    }

    result: dict[str, Any] = {}
    for key, value in row.items():
        if key in numeric_ints:
            result[key] = int(value or 0)
        else:
            result[key] = float(value or 0.0)

    for key in numeric_ints:
        result.setdefault(key, 0)
    result.setdefault("avg_session_minutes", 0.0)
    result.setdefault("avg_pages_per_session", 0.0)
    result.setdefault("avg_events_per_session", 0.0)

    total_sessions = result.get("total_sessions", 0) or 0
    result["single_page_rate_pct"] = (
        result.get("single_page_sessions", 0) / total_sessions * 100.0
        if total_sessions
        else 0.0
    )

    return result


def get_daily_traffic(days: int = 30) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        WITH days AS (
            SELECT generate_series(
                CURRENT_DATE - (%s * INTERVAL '1 day'),
                CURRENT_DATE,
                INTERVAL '1 day'
            )::date AS date
        ),
        pv AS (
            SELECT viewed_at::date AS date,
                   COUNT(*) AS pageviews,
                   COUNT(DISTINCT visitor_id) AS visitors,
                   COUNT(DISTINCT session_id) AS sessions
            FROM analytics_pageviews
            WHERE viewed_at >= CURRENT_DATE - (%s * INTERVAL '1 day')
            GROUP BY viewed_at::date
        ),
        ev AS (
            SELECT event_at::date AS date, COUNT(*) AS events
            FROM analytics_events
            WHERE event_at >= CURRENT_DATE - (%s * INTERVAL '1 day')
            GROUP BY event_at::date
        )
        SELECT d.date,
               COALESCE(pv.pageviews, 0) AS pageviews,
               COALESCE(pv.visitors, 0) AS visitors,
               COALESCE(pv.sessions, 0) AS sessions,
               COALESCE(ev.events, 0) AS events
        FROM days d
        LEFT JOIN pv USING (date)
        LEFT JOIN ev USING (date)
        ORDER BY d.date;
        """,
        (days, days, days),
    )


def get_popular_pages(limit: int = 15) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    return _fetchall(
        """
        SELECT page_name,
               COUNT(*) AS pageviews,
               COUNT(DISTINCT visitor_id) AS visitors,
               COUNT(DISTINCT session_id) AS sessions
        FROM analytics_pageviews
        GROUP BY page_name
        ORDER BY pageviews DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_top_events(limit: int = 20) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    return _fetchall(
        """
        SELECT event_name, event_category,
               COUNT(*) AS event_count,
               COUNT(DISTINCT visitor_id) AS visitors,
               COUNT(DISTINCT session_id) AS sessions
        FROM analytics_events
        GROUP BY event_name, event_category
        ORDER BY event_count DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_device_breakdown() -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(device_category, 'Unknown') AS label,
               COUNT(*) AS sessions,
               COUNT(DISTINCT visitor_id) AS visitors
        FROM analytics_sessions
        GROUP BY COALESCE(device_category, 'Unknown')
        ORDER BY sessions DESC;
        """
    )


def get_browser_breakdown(limit: int = 12) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(browser_family, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(browser_family, 'Unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_os_breakdown(limit: int = 12) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(os_family, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(os_family, 'Unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_language_breakdown(limit: int = 12) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(language, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(language, 'Unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_timezone_breakdown(limit: int = 15) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(timezone, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(timezone, 'Unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_country_hint_breakdown(limit: int = 20) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(country_hint, 'Unknown / unavailable') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(country_hint, 'Unknown / unavailable')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_theme_breakdown() -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(theme_type, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(theme_type, 'Unknown')
        ORDER BY sessions DESC;
        """
    )


def get_entry_pages(limit: int = 15) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(entry_page, 'Unknown') AS label,
               COUNT(*) AS sessions
        FROM analytics_sessions
        GROUP BY COALESCE(entry_page, 'Unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_referrer_breakdown(limit: int = 15) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT COALESCE(NULLIF(referrer_domain, ''), 'Direct / unknown') AS label,
               COUNT(*) AS sessions,
               COUNT(DISTINCT visitor_id) AS visitors
        FROM analytics_sessions
        GROUP BY COALESCE(NULLIF(referrer_domain, ''), 'Direct / unknown')
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_campaign_breakdown(limit: int = 20) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT
            COALESCE(NULLIF(utm_source, ''), 'No UTM') AS source,
            COALESCE(NULLIF(utm_medium, ''), '—') AS medium,
            COALESCE(NULLIF(utm_campaign, ''), '—') AS campaign,
            COUNT(*) AS sessions,
            COUNT(DISTINCT visitor_id) AS visitors
        FROM analytics_sessions
        GROUP BY 1, 2, 3
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_hourly_activity() -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT EXTRACT(HOUR FROM viewed_at)::int AS hour,
               COUNT(*) AS pageviews,
               COUNT(DISTINCT visitor_id) AS visitors
        FROM analytics_pageviews
        GROUP BY EXTRACT(HOUR FROM viewed_at)
        ORDER BY hour;
        """
    )


def get_recent_activity(limit: int = 30) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    return _fetchall(
        """
        SELECT
            session_id,
            current_page,
            entry_page,
            started_at,
            last_seen,
            ROUND((EXTRACT(EPOCH FROM (last_seen - started_at)) / 60.0)::numeric, 1) AS duration_minutes,
            pageviews,
            events,
            device_category,
            browser_family,
            os_family,
            language,
            timezone,
            timezone_offset_minutes,
            theme_type,
            is_embedded,
            app_host,
            country_hint,
            referrer_domain,
            utm_source,
            utm_medium,
            utm_campaign
        FROM analytics_sessions
        ORDER BY last_seen DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 300))
    return _fetchall(
        """
        SELECT event_at, page_name, event_name, event_category, metadata
        FROM analytics_events
        ORDER BY event_at DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_search_destinations(limit: int = 25) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT
            COALESCE(metadata->>'label', 'Unknown') AS label,
            COALESCE(metadata->>'result_type', 'Unknown') AS result_type,
            COUNT(*) AS selections
        FROM analytics_events
        WHERE event_name = 'search_select'
        GROUP BY 1, 2
        ORDER BY selections DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_live_sessions(limit: int = 50) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT
            current_page,
            started_at,
            last_seen,
            pageviews,
            events,
            device_category,
            browser_family,
            os_family,
            language,
            timezone,
            country_hint
        FROM analytics_sessions
        WHERE last_seen >= NOW() - (%s * INTERVAL '1 minute')
        ORDER BY last_seen DESC
        LIMIT %s;
        """,
        (ACTIVE_WINDOW_MINUTES, limit),
    )


# =========================================================
# ORBIDENSE AI V2 — DEVELOPER OBSERVABILITY
# =========================================================
# These functions intentionally keep technical details out of the public UI.
# Error messages are redacted before storage. No traceback is stored by default.

_SENSITIVE_PATTERNS = (
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,;]+"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+\-/=]+"), "Bearer [REDACTED]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?i)(postgres(?:ql)?://)[^\s]+"), r"\1[REDACTED]"),
)


def _redact_text(value: Any, max_len: int = 900) -> str:
    text = str(value or "")
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:max_len]


def _optional_session_id() -> str | None:
    # Respect privacy opt-out. Operational errors can still be counted without
    # attaching them to a visitor/session identity.
    if not analytics_tracking_allowed():
        return None
    try:
        return str(st.session_state.get(SESSION_KEY) or "") or None
    except Exception:
        return None


def record_error(
    error: BaseException,
    *,
    component: str,
    operation: str | None = None,
    page_name: str | None = None,
    severity: str = "error",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a redacted technical error for the private developer console."""
    try:
        error_type = type(error).__name__
        redacted = _redact_text(error)
        digest_source = f"{component}|{operation or ''}|{error_type}|{redacted}"
        error_hash = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:24]
        clean_metadata = _json_safe_metadata(metadata)
        session_id = _optional_session_id()
        current_page = str(page_name or st.session_state.get("main_navigation") or "Unknown")[:160]

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_errors (
                        session_id, page_name, component, operation, severity,
                        error_type, error_hash, message_redacted, metadata, recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW());
                    """,
                    (
                        session_id,
                        current_page,
                        str(component)[:160],
                        str(operation or "")[:160] or None,
                        str(severity or "error")[:32],
                        error_type[:120],
                        error_hash,
                        redacted,
                        json.dumps(clean_metadata),
                    ),
                )
    except Exception as logging_error:
        # Observability must never break the public application.
        print("ORBIDENSE AI observability logging failure:", logging_error)


def record_performance(
    operation: str,
    duration_ms: float,
    *,
    success: bool = True,
    page_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not analytics_tracking_allowed():
        return
    try:
        session_id = _optional_session_id()
        current_page = str(page_name or st.session_state.get("main_navigation") or "Unknown")[:160]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_performance (
                        session_id, page_name, operation, duration_ms, success,
                        metadata, recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW());
                    """,
                    (
                        session_id,
                        current_page,
                        str(operation)[:180],
                        float(duration_ms),
                        bool(success),
                        json.dumps(_json_safe_metadata(metadata)),
                    ),
                )
    except Exception as logging_error:
        print("ORBIDENSE AI performance logging failure:", logging_error)


def record_ai_usage(
    *,
    request_category: str | None = None,
    model_name: str | None = None,
    duration_ms: float | None = None,
    success: bool = True,
    input_chars: int | None = None,
    output_chars: int | None = None,
    error_type: str | None = None,
    page_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store AI usage telemetry without storing prompt or response text."""
    if not analytics_tracking_allowed():
        return
    try:
        session_id = _optional_session_id()
        current_page = str(page_name or st.session_state.get("main_navigation") or "Unknown")[:160]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_ai_usage (
                        session_id, page_name, request_category, model_name,
                        duration_ms, success, input_chars, output_chars, error_type,
                        metadata, recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW());
                    """,
                    (
                        session_id,
                        current_page,
                        str(request_category or "uncategorized")[:120],
                        str(model_name or "unknown")[:160],
                        float(duration_ms) if duration_ms is not None else None,
                        bool(success),
                        int(input_chars) if input_chars is not None else None,
                        int(output_chars) if output_chars is not None else None,
                        str(error_type or "")[:120] or None,
                        json.dumps(_json_safe_metadata(metadata)),
                    ),
                )
    except Exception as logging_error:
        print("ORBIDENSE AI AI-usage logging failure:", logging_error)


def record_data_quality(
    source_name: str,
    check_name: str,
    status: str,
    *,
    affected_records: int | None = None,
    freshness_seconds: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """System-level data-quality telemetry; contains no user identity."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_data_quality (
                        source_name, check_name, status, affected_records,
                        freshness_seconds, metadata, recorded_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW());
                    """,
                    (
                        str(source_name)[:160],
                        str(check_name)[:160],
                        str(status)[:64],
                        int(affected_records) if affected_records is not None else None,
                        int(freshness_seconds) if freshness_seconds is not None else None,
                        json.dumps(_json_safe_metadata(metadata)),
                    ),
                )
    except Exception as logging_error:
        print("ORBIDENSE AI data-quality logging failure:", logging_error)


# =========================================================
# ORBIDENSE AI V2 — ADVANCED DEVELOPER QUERIES
# =========================================================

def get_journey_edges(days: int = 30, limit: int = 40) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    limit = max(1, min(int(limit), 200))
    return _fetchall(
        """
        WITH ordered AS (
            SELECT session_id, page_name, viewed_at,
                   LAG(page_name) OVER (
                       PARTITION BY session_id ORDER BY viewed_at, pageview_id
                   ) AS previous_page
            FROM analytics_pageviews
            WHERE viewed_at >= NOW() - (%s * INTERVAL '1 day')
        )
        SELECT previous_page AS source, page_name AS target,
               COUNT(*) AS transitions,
               COUNT(DISTINCT session_id) AS sessions
        FROM ordered
        WHERE previous_page IS NOT NULL AND previous_page <> page_name
        GROUP BY previous_page, page_name
        ORDER BY transitions DESC
        LIMIT %s;
        """,
        (days, limit),
    )


def get_exit_pages(days: int = 30, limit: int = 15) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        WITH ranked AS (
            SELECT session_id, page_name, viewed_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY session_id ORDER BY viewed_at DESC, pageview_id DESC
                   ) AS rn
            FROM analytics_pageviews
            WHERE viewed_at >= NOW() - (%s * INTERVAL '1 day')
        )
        SELECT page_name AS label, COUNT(*) AS sessions
        FROM ranked
        WHERE rn = 1
        GROUP BY page_name
        ORDER BY sessions DESC
        LIMIT %s;
        """,
        (days, limit),
    )


def get_session_depth_distribution(days: int = 30) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        SELECT
            CASE
                WHEN pageviews <= 1 THEN '1 page'
                WHEN pageviews <= 3 THEN '2–3 pages'
                WHEN pageviews <= 6 THEN '4–6 pages'
                ELSE '7+ pages'
            END AS label,
            COUNT(*) AS sessions
        FROM analytics_sessions
        WHERE started_at >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY 1
        ORDER BY MIN(pageviews);
        """,
        (days,),
    )


def get_feature_usage(days: int = 30, limit: int = 30) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        SELECT event_name AS feature,
               event_category AS category,
               COUNT(*) AS events,
               COUNT(DISTINCT session_id) AS sessions
        FROM analytics_events
        WHERE event_at >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY event_name, event_category
        ORDER BY events DESC
        LIMIT %s;
        """,
        (days, limit),
    )


def get_performance_summary(days: int = 7, limit: int = 30) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        SELECT operation,
               COUNT(*) AS samples,
               ROUND(AVG(duration_ms)::numeric, 1) AS avg_ms,
               ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms)::numeric, 1) AS p50_ms,
               ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)::numeric, 1) AS p95_ms,
               ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms)::numeric, 1) AS p99_ms,
               ROUND((100.0 * AVG(CASE WHEN success THEN 1 ELSE 0 END))::numeric, 2) AS success_pct
        FROM analytics_performance
        WHERE recorded_at >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY operation
        ORDER BY p95_ms DESC NULLS LAST
        LIMIT %s;
        """,
        (days, limit),
    )


def get_error_summary(days: int = 7, limit: int = 30) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        SELECT component, operation, error_type, error_hash, severity,
               COUNT(*) AS occurrences,
               MAX(recorded_at) AS last_seen
        FROM analytics_errors
        WHERE recorded_at >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY component, operation, error_type, error_hash, severity
        ORDER BY occurrences DESC, last_seen DESC
        LIMIT %s;
        """,
        (days, limit),
    )


def get_recent_errors(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    return _fetchall(
        """
        SELECT recorded_at, page_name, component, operation, severity,
               error_type, error_hash, message_redacted, metadata
        FROM analytics_errors
        ORDER BY recorded_at DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_ai_usage_summary(days: int = 30) -> dict[str, Any]:
    days = max(1, min(int(days), 3650))
    return _fetchone(
        """
        SELECT COUNT(*) AS requests,
               COUNT(*) FILTER (WHERE success) AS successful,
               COUNT(*) FILTER (WHERE NOT success) AS failed,
               ROUND(COALESCE(AVG(duration_ms), 0)::numeric, 1) AS avg_ms,
               ROUND(COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 0)::numeric, 1) AS p95_ms,
               COALESCE(SUM(input_chars), 0) AS input_chars,
               COALESCE(SUM(output_chars), 0) AS output_chars
        FROM analytics_ai_usage
        WHERE recorded_at >= NOW() - (%s * INTERVAL '1 day');
        """,
        (days,),
    )


def get_ai_category_breakdown(days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
    days = max(1, min(int(days), 3650))
    return _fetchall(
        """
        SELECT COALESCE(request_category, 'uncategorized') AS label,
               COUNT(*) AS requests,
               COUNT(*) FILTER (WHERE success) AS successful
        FROM analytics_ai_usage
        WHERE recorded_at >= NOW() - (%s * INTERVAL '1 day')
        GROUP BY 1
        ORDER BY requests DESC
        LIMIT %s;
        """,
        (days, limit),
    )


def get_data_quality_latest(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    return _fetchall(
        """
        SELECT DISTINCT ON (source_name, check_name)
               source_name, check_name, status, affected_records,
               freshness_seconds, metadata, recorded_at
        FROM analytics_data_quality
        ORDER BY source_name, check_name, recorded_at DESC
        LIMIT %s;
        """,
        (limit,),
    )


def get_privacy_summary() -> dict[str, Any]:
    row = _fetchone(
        """
        SELECT
            COUNT(*) AS sessions,
            COUNT(*) FILTER (WHERE do_not_track IS TRUE) AS dnt_sessions,
            COUNT(*) FILTER (WHERE global_privacy_control IS TRUE) AS gpc_sessions,
            COUNT(*) FILTER (WHERE persistent_id IS TRUE) AS persistent_sessions
        FROM analytics_sessions;
        """
    )
    return {k: int(v or 0) for k, v in row.items()}
