"""Smoke test: every dashboard page must render without an exception or error box."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"

ENTRY = next(p for p in (DASHBOARD / "Home.py", DASHBOARD / "app.py") if p.exists())
PAGES = [ENTRY, *sorted((DASHBOARD / "pages").glob("*.py"))]


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_page_renders(page):
    app = AppTest.from_file(str(page), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.error, [e.value for e in app.error]
