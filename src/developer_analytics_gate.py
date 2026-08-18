from __future__ import annotations

import hmac
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

DEV_SESSION_KEY = "_orbidense_developer_mode"
DEV_UNLOCKED_AT_KEY = "_orbidense_developer_unlocked_at"
DEV_LAST_ACTIVITY_KEY = "_orbidense_developer_last_activity"
ANALYTICS_OPEN_KEY = "_orbidense_dev_analytics_open"
ANALYTICS_AUTH_KEY = "_orbidense_dev_analytics_authenticated"
DEV_FAIL_COUNT_KEY = "_orbidense_dev_fail_count"
DEV_LOCK_UNTIL_KEY = "_orbidense_dev_lock_until"
ANALYTICS_FAIL_COUNT_KEY = "_orbidense_analytics_fail_count"
ANALYTICS_LOCK_UNTIL_KEY = "_orbidense_analytics_lock_until"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

DEV_IDLE_TIMEOUT_SECONDS = 60 * 60
DEV_MAX_SESSION_SECONDS = 6 * 60 * 60
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60
OWNER_TRIGGER_PARAM_SECRET = "OWNER_TRIGGER_PARAM"
OWNER_TRIGGER_VALUE_SECRET = "OWNER_TRIGGER_VALUE"

def _load_project_env() -> None:
    if not ENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        return
    except Exception:
        pass

    try:
        for raw_line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value
    except Exception:
        return


_load_project_env()


def _secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return str(value).strip()
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return ""


def _query_value(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
    except Exception:
        return ""
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else ""
    return str(value or "").strip()


def _remove_query_param(name: str) -> None:
    try:
        if name in st.query_params:
            del st.query_params[name]
    except Exception:
        pass


def _now() -> float:
    return time.time()


def _locked(lock_key: str) -> tuple[bool, int]:
    until = float(st.session_state.get(lock_key, 0) or 0)
    remaining = max(0, int(until - _now()))
    return remaining > 0, remaining


def _record_failure(count_key: str, lock_key: str) -> None:
    count = int(st.session_state.get(count_key, 0) or 0) + 1
    st.session_state[count_key] = count
    if count >= MAX_FAILED_ATTEMPTS:
        st.session_state[lock_key] = _now() + LOCKOUT_SECONDS
        st.session_state[count_key] = 0


def _clear_failures(count_key: str, lock_key: str) -> None:
    st.session_state.pop(count_key, None)
    st.session_state.pop(lock_key, None)


def _clear_developer_state() -> None:
    for key in (
        DEV_SESSION_KEY,
        DEV_UNLOCKED_AT_KEY,
        DEV_LAST_ACTIVITY_KEY,
        ANALYTICS_OPEN_KEY,
        ANALYTICS_AUTH_KEY,
    ):
        st.session_state.pop(key, None)


def _session_expired() -> bool:
    if not st.session_state.get(DEV_SESSION_KEY):
        return False
    now = _now()
    last_activity = float(st.session_state.get(DEV_LAST_ACTIVITY_KEY, now) or now)
    unlocked_iso = st.session_state.get(DEV_UNLOCKED_AT_KEY)
    unlocked_ts = now
    if unlocked_iso:
        try:
            unlocked_ts = datetime.fromisoformat(str(unlocked_iso)).timestamp()
        except Exception:
            pass
    return (
        now - last_activity > DEV_IDLE_TIMEOUT_SECONDS
        or now - unlocked_ts > DEV_MAX_SESSION_SECONDS
    )


def developer_mode_active() -> bool:
    if _session_expired():
        _clear_developer_state()
        return False
    active = bool(st.session_state.get(DEV_SESSION_KEY, False))
    if active:
        st.session_state[DEV_LAST_ACTIVITY_KEY] = _now()
    return active


def developer_unlocked_at() -> str | None:
    value = st.session_state.get(DEV_UNLOCKED_AT_KEY)
    return str(value) if value else None


def process_developer_gate() -> None:
    """Secure private developer entry. No authentication secret is stored in the URL source code."""

    _remove_query_param("cp_gate")
    _remove_query_param("cp_debug")

    # Read the private trigger configuration from environment/secrets.
    owner_trigger_param = _secret(OWNER_TRIGGER_PARAM_SECRET)
    owner_trigger_value = _secret(OWNER_TRIGGER_VALUE_SECRET)

    # If private trigger configuration is missing, developer entry stays disabled.
    if not owner_trigger_param or not owner_trigger_value:
        return

    # Existing authenticated developer session does not need the URL trigger again.
    if developer_mode_active():
        _remove_query_param(owner_trigger_param)
        return

    # Only show the owner gate when the private trigger matches.
    if _query_value(owner_trigger_param) != owner_trigger_value:
        return

    expected = _secret("ANALYTICS_DEV_KEY")

    _, center, _ = st.columns([1.05, 1.55, 1.05])

    with center:
        st.markdown("### ORBIDENSE Owner Access")

        st.caption(
            "Private developer access for this browser session. "
            "The developer key never appears in the URL."
        )

        if not expected:
            st.error("ANALYTICS_DEV_KEY is not configured.")
            st.stop()

        locked, remaining = _locked(DEV_LOCK_UNTIL_KEY)

        if locked:
            st.error(
                f"Too many failed attempts. Try again in about "
                f"{max(1, math.ceil(remaining / 60))} minute(s)."
            )
            st.stop()

        with st.form(
            "orbidense_owner_unlock_form",
            clear_on_submit=True,
            border=True,
        ):
            entered = st.text_input(
                "Developer key",
                type="password",
                autocomplete="off",
            )

            left, right = st.columns(2)

            with left:
                unlock = st.form_submit_button(
                    "Unlock Developer Mode",
                    type="primary",
                    width="stretch",
                )

            with right:
                cancel = st.form_submit_button(
                    "Cancel",
                    width="stretch",
                )

        if cancel:
            _remove_query_param(owner_trigger_param)
            st.rerun()

        if unlock:
            candidate = str(entered or "").strip()

            if hmac.compare_digest(candidate, expected):
                _clear_failures(
                    DEV_FAIL_COUNT_KEY,
                    DEV_LOCK_UNTIL_KEY,
                )

                now = datetime.now(timezone.utc).isoformat()

                st.session_state[DEV_SESSION_KEY] = True
                st.session_state[DEV_UNLOCKED_AT_KEY] = now
                st.session_state[DEV_LAST_ACTIVITY_KEY] = _now()

                st.session_state.pop(
                    ANALYTICS_OPEN_KEY,
                    None,
                )

                st.session_state.pop(
                    ANALYTICS_AUTH_KEY,
                    None,
                )

                _remove_query_param(owner_trigger_param)
                st.rerun()

            _record_failure(
                DEV_FAIL_COUNT_KEY,
                DEV_LOCK_UNTIL_KEY,
            )

            st.error("Developer key is incorrect.")

    st.stop()


def open_developer_analytics() -> None:
    if developer_mode_active():
        st.session_state[ANALYTICS_OPEN_KEY] = True


def close_developer_analytics() -> None:
    st.session_state.pop(ANALYTICS_OPEN_KEY, None)


def developer_analytics_requested() -> bool:
    return developer_mode_active() and bool(st.session_state.get(ANALYTICS_OPEN_KEY, False))


def analytics_authenticated() -> bool:
    return developer_mode_active() and bool(st.session_state.get(ANALYTICS_AUTH_KEY, False))


def logout_analytics() -> None:
    st.session_state.pop(ANALYTICS_AUTH_KEY, None)


def exit_developer_mode() -> None:
    _clear_developer_state()


def render_analytics_password_gate() -> bool:
    if analytics_authenticated():
        return True

    password = _secret("ANALYTICS_PASSWORD")
    if not password:
        st.error("ANALYTICS_PASSWORD is not configured.")
        return False

    _, center, _ = st.columns([1.05, 1.55, 1.05])
    with center:
        st.markdown("### Developer Analytics")
        st.caption(
            "Enter the separate analytics password to access private "
            "ORBIDENSE product intelligence."
        )

        locked, remaining = _locked(ANALYTICS_LOCK_UNTIL_KEY)
        if locked:
            st.error(
                f"Too many failed attempts. Try again in about "
                f"{max(1, math.ceil(remaining / 60))} minute(s)."
            )
            return False

        with st.form("orbidense_analytics_password_form", clear_on_submit=True, border=True):
            entered = st.text_input(
                "Analytics password", type="password", autocomplete="current-password"
            )
            unlock = st.form_submit_button(
                "Unlock Analytics", type="primary", width="stretch"
            )

        if unlock:
            if hmac.compare_digest(str(entered or ""), password):
                _clear_failures(ANALYTICS_FAIL_COUNT_KEY, ANALYTICS_LOCK_UNTIL_KEY)
                st.session_state[ANALYTICS_AUTH_KEY] = True
                st.rerun()
            _record_failure(ANALYTICS_FAIL_COUNT_KEY, ANALYTICS_LOCK_UNTIL_KEY)
            st.error("Incorrect analytics password.")

    return False


def developer_gate_status() -> dict:
    return {
        "env_file_exists": ENV_PATH.exists(),
        "dev_key_configured": bool(_secret("ANALYTICS_DEV_KEY")),
        "analytics_password_configured": bool(_secret("ANALYTICS_PASSWORD")),
        "developer_mode": developer_mode_active(),
        "analytics_requested": developer_analytics_requested(),
        "analytics_authenticated": analytics_authenticated(),
    }
