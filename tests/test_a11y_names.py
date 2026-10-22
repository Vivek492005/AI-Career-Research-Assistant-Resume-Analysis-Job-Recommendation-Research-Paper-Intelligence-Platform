"""#4: every button/link on the dashboard surfaces has an accessible
name (axe-core "button-name" / "link-name" rules).

Audit note (2026-10-22): the shared chrome was already labelled (nav
toggle has aria-label="Toggle navigation", bookmark buttons carry
text, the flashcard card has aria-label="Flip card"), and rendered
/dashboard, /results/<id> and /tracker pages scan clean. These tests
pin that state so a future icon-only control without a name fails CI
instead of reaching users.
"""
import io
import re

from tests.conftest import login, register


def _nameless(html):
    """Interactive elements with no accessible name in rendered HTML."""
    bad = []
    for tag in ("button", "a"):
        for m in re.finditer(rf"<{tag}\b([^>]*)>(.*?)</{tag}>",
                             html, re.S | re.I):
            attrs, inner = m.group(1), m.group(2)
            label = re.search(r'aria-label="([^"]+)"', attrs)
            if label or "aria-labelledby" in attrs:
                continue
            title = re.search(r'title="([^"]+)"', attrs)
            if title:
                continue
            text = re.sub(r"<svg.*?</svg>", "", inner, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", "", text)
            if not re.sub(r"\s+", " ", text).strip():
                bad.append((tag, re.sub(r"\s+", " ", m.group(0))[:100]))
    return bad


def test_user_dashboard_buttons_have_names(client):
    register(client)
    login(client)
    html = client.get("/dashboard").get_data(as_text=True)
    assert _nameless(html) == []


def test_results_dashboard_buttons_have_names(client, sample_pdf):
    resp = client.post(
        "/analyze",
        data={"resume": (io.BytesIO(sample_pdf), "resume.pdf")},
        content_type="multipart/form-data")
    payload = resp.get_json()
    assert payload["success"] is True
    html = client.get(payload["redirect"]).get_data(as_text=True)
    assert _nameless(html) == []


def test_tracker_buttons_have_names(client):
    register(client)
    login(client)
    html = client.get("/tracker").get_data(as_text=True)
    assert _nameless(html) == []
