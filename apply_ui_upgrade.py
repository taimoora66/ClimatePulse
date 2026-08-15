from pathlib import Path
import shutil

APP = Path("app.py")
BACKUP = Path("app_before_ui_upgrade.py")

START_MARKER = """# =========================================================\n# TOP SEARCH BAR\n# =========================================================\n"""
END_MARKER = """# =========================================================\n# HANDLE SEARCH RESULT\n# =========================================================\n"""

REPLACEMENT = r'''# =========================================================
# GLOBAL PLACE SEARCH — CONTEXTUAL ONLY
# =========================================================
# Large global search is intentionally limited to Home + Map Explorer.
# Compare Places already has its own dedicated selectors.
# =========================================================

selected_search_result = None

SHOW_GLOBAL_SEARCH = nav_view in {
    "Home",
    "Map Explorer",
}

if SHOW_GLOBAL_SEARCH:
    st.markdown(
        '<div id="dashboard"></div>',
        unsafe_allow_html=True,
    )

    search_col, status_col = st.columns(
        [5.0, 1.35],
        gap="medium",
        vertical_alignment="center",
    )

    with search_col:
        st.markdown(
            """
<div class="cp-search-panel">
<div class="cp-search-kicker">GLOBAL PLACE SEARCH</div>
<div class="cp-search-title">Explore any city, place or country</div>
<div class="cp-search-help">Search globally to move ClimatePulse, load live conditions and connect historical climate context.</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        selected_search_result = st_searchbox(
            global_search,
            key="global_place_search",
            label=None,
            placeholder="Search Milan, Islamabad, Tokyo, Pakistan...",
            debounce=300,
            edit_after_submit="option",
            clear_on_submit=False,
            style_overrides=GLOBAL_SEARCHBOX_STYLE,
        )

    with status_col:
        developer_authenticated = bool(
            st.session_state.get(
                "cp_analytics_authenticated",
                False,
            )
        )

        if developer_authenticated and ANALYTICS_READY:
            try:
                active_visitors = int(
                    get_analytics_summary().get(
                        "active_now",
                        0,
                    )
                )
                audience_text = f"{active_visitors:,} active now"
                audience_sub = "Developer view"
            except Exception:
                audience_text = "Analytics unavailable"
                audience_sub = "Developer view"
        else:
            audience_text = "All systems normal"
            audience_sub = "Live Earth online"

        st.markdown(
            f"""
<div class="cp-audience-wrap">
    <div class="cp-audience-pill">
        <span class="cp-audience-dot"></span>
        <span>{audience_text}</span>
        <span class="cp-audience-sub">· {audience_sub}</span>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )

'''


def main():
    if not APP.exists():
        raise SystemExit("app.py not found. Run this from the ClimatePulse project root.")

    text = APP.read_text(encoding="utf-8")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)

    if start == -1 or end == -1 or end <= start:
        raise SystemExit("Expected TOP SEARCH BAR block not found. No changes made.")

    if not BACKUP.exists():
        shutil.copy2(APP, BACKUP)

    APP.write_text(text[:start] + REPLACEMENT + text[end:], encoding="utf-8")
    print("UI patch applied.")
    print("Global search now appears only on Home and Map Explorer.")
    print("Backup created at:", BACKUP)


if __name__ == "__main__":
    main()
