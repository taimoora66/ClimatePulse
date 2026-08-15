from pathlib import Path
import re
import shutil

APP = Path("app.py")
BACKUP = Path("app_before_final_search_fix.py")

SEARCH_BLOCK = '# =========================================================\n# TOP SEARCH BAR — CONTEXTUAL\n# =========================================================\n\nselected_search_result = None\n\nSHOW_GLOBAL_PLACE_SEARCH = (\n    nav_view in {\n        "Home",\n        "Map Explorer",\n    }\n)\n\nif SHOW_GLOBAL_PLACE_SEARCH:\n\n    st.markdown(\n        \'<div id="dashboard"></div>\',\n        unsafe_allow_html=True,\n    )\n\n    search_col, status_col = st.columns(\n        [5.0, 1.35],\n        gap="medium",\n        vertical_alignment="center",\n    )\n\n    with search_col:\n        st.markdown(\n            """\n<div class="cp-search-panel">\n<div class="cp-search-kicker">GLOBAL PLACE SEARCH</div>\n<div class="cp-search-title">Explore any city, place or country</div>\n<div class="cp-search-help">Search globally to move ClimatePulse, load live conditions and connect historical climate context.</div>\n</div>\n            """,\n            unsafe_allow_html=True,\n        )\n\n        selected_search_result = st_searchbox(\n            global_search,\n            key="global_place_search",\n            label=None,\n            placeholder="Search Milan, Islamabad, Tokyo, Pakistan...",\n            debounce=300,\n            edit_after_submit="option",\n            clear_on_submit=False,\n            style_overrides=GLOBAL_SEARCHBOX_STYLE,\n        )\n\n    with status_col:\n        developer_authenticated = bool(\n            st.session_state.get(\n                "cp_analytics_authenticated",\n                False,\n            )\n        )\n\n        if developer_authenticated and ANALYTICS_READY:\n            try:\n                active_visitors = int(\n                    get_analytics_summary().get(\n                        "active_now",\n                        0,\n                    )\n                )\n                audience_text = f"{active_visitors:,} active now"\n                audience_sub = "Developer view"\n            except Exception:\n                audience_text = "Analytics unavailable"\n                audience_sub = "Developer view"\n        else:\n            audience_text = "All systems normal"\n            audience_sub = "Live Earth online"\n\n        st.markdown(\n            f"""\n<div class="cp-audience-wrap">\n    <div class="cp-audience-pill">\n        <span class="cp-audience-dot"></span>\n        <span>{audience_text}</span>\n        <span class="cp-audience-sub">· {audience_sub}</span>\n    </div>\n</div>\n            """,\n            unsafe_allow_html=True,\n        )\n\n'
EARLY_ABOUT = '# =========================================================\n# EARLY STANDALONE ROUTE — ABOUT\n# =========================================================\n\nif nav_view == "About":\n    render_about_page()\n    st.stop()\n\n'

def find_search_block(text):
    start_match = re.search(
        r"(?m)^# ={10,}\n# TOP SEARCH BAR[^\n]*\n# ={10,}\n",
        text,
    )
    if not start_match:
        raise RuntimeError("TOP SEARCH BAR marker not found.")

    handle_match = re.search(
        r"(?m)^# ={10,}\n# HANDLE SEARCH RESULT[^\n]*\n# ={10,}\n",
        text[start_match.end():],
    )
    if not handle_match:
        raise RuntimeError("HANDLE SEARCH RESULT marker not found.")

    start = start_match.start()
    end = start_match.end() + handle_match.start()
    return start, end

def remove_old_early_about(text):
    pattern = (
        r"(?ms)^# ={10,}\n# EARLY [^\n]*ABOUT[^\n]*\n"
        r"# ={10,}\n.*?st\.stop\(\)\n\n"
    )
    return re.sub(pattern, "", text)

def main():
    if not APP.exists():
        raise SystemExit("app.py not found. Run this from the ClimatePulse project root.")
