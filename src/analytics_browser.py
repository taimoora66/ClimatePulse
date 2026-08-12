"""Deprecated compatibility shim for ClimatePulse analytics.

V37 no longer mounts a custom browser component. Browser/session context is
captured with Streamlit's native ``st.context`` API from ``src.analytics``.
This file is retained only so an accidental stale import cannot crash the app.
"""

from __future__ import annotations

from typing import Any


def capture_browser_analytics_context(
    *,
    persistent_id_enabled: bool = False,
) -> tuple[dict[str, Any] | None, bool]:
    """Return a harmless no-op result for backward compatibility."""
    return None, False
