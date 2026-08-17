from pathlib import Path
import ast


def main():
    router = Path("src/orbidense_router.py").read_text(
        encoding="utf-8-sig"
    )
    app = Path("app.py").read_text(
        encoding="utf-8-sig"
    )

    ast.parse(router)
    ast.parse(app)

    # Current single-router architecture
    assert "render_site_router" in app
    assert "def render_site_router" in router
    assert "def request_route" in router

    # No duplicate experimental top navigation
    assert "render_orbidense_top_nav(nav_view)" not in app

    # Canonical public labels remain present
    assert '"Climate Outlook"' in router
    assert '"Climate Action"' in router
    assert '"Compare"' in router
    assert '"Global Insights"' in router

    # Current internal route mappings remain present
    assert '"Climate Outlook": "Country Climate Outlook"' in router
    assert '"Climate Action": "Climate Action & Progress"' in router
    assert '"Compare": "Compare Places"' in router
    assert '"Global Insights": "Global Rankings"' in router

    # App normalizes legacy/internal route values into canonical public routes
    assert '"Country Climate Outlook": "Climate Outlook"' in app
    assert '"Climate Action & Progress": "Climate Action"' in app
    assert '"Compare Places": "Compare"' in app
    assert '"Global Rankings": "Global Insights"' in app

    # Final canonical route rendering
    assert 'if nav_view == "Climate Outlook":' in app
    assert 'if nav_view == "Climate Action":' in app
    assert 'if nav_view == "Compare":' in app
    assert 'if nav_view == "Global Insights":' in app

    print("ORBIDENSE ROUTER BACKTEST: PASS")
    print("Single-router architecture: PRESENT")
    print("Canonical public routes: PRESENT")
    print("Legacy/internal route normalization: PRESENT")
    print("Duplicate experimental top-nav hook: ABSENT")


if __name__ == "__main__":
    main()