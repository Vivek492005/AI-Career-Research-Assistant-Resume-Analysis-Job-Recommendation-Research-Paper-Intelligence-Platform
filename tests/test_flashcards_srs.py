"""Tests for SM-2-lite flashcard scheduling (2026-10-24).

Before this, progress was only {known, reviews} — reviews were never
actually spaced. srs_update now maintains ease/interval/due/lapses.
"""
from datetime import date, timedelta

import pytest

from studybuddy.flashcards import (
    card_due_state,
    due_count,
    mastery_stats,
    srs_update,
)

TODAY = date(2026, 10, 24)


@pytest.fixture
def authed_client(client, app):
    from werkzeug.security import generate_password_hash

    from unified_app import User, db
    with app.app_context():
        u = User(email="srs@test.com", name="Scheduler",
                 password_hash=generate_password_hash("password123"))
        db.session.add(u)
        db.session.commit()
    client.post("/login", data={"email": "srs@test.com",
                                "password": "password123"})
    return client


def _entry(**kw):
    e = {"known": False, "reviews": 1}
    e.update(kw)
    return e


def test_first_success_schedules_tomorrow():
    e = srs_update(_entry(), True, today=TODAY)
    assert e["interval"] == 1
    assert e["due"] == "2026-10-25"
    assert e["ease"] >= 2.5


def test_interval_progression_and_ease_growth():
    e = _entry()
    e = srs_update(e, True, today=TODAY)          # -> 1 day
    e = srs_update(e, True, today=TODAY)          # -> 3 days
    assert e["interval"] == 3
    e = srs_update(e, True, today=TODAY)          # -> round(3 * ease)
    assert e["interval"] >= 7
    assert e["due"] == (TODAY + timedelta(days=e["interval"])).isoformat()


def test_lapse_resets_interval_and_drops_ease():
    e = _entry(ease=2.6, interval=8, due="2026-10-20")
    e = srs_update(e, False, today=TODAY)
    assert e["interval"] == 1
    assert e["due"] == "2026-10-25"
    assert e["lapses"] == 1
    assert abs(e["ease"] - 2.4) < 1e-9


def test_ease_floor():
    e = _entry(ease=1.35, interval=5)
    for _ in range(5):
        e = srs_update(e, False, today=TODAY)
    assert e["ease"] >= 1.3


def test_due_states():
    assert card_due_state(None, today=TODAY) == "new"
    assert card_due_state({"reviews": 0}, today=TODAY) == "new"
    # Legacy reviewed card without a schedule counts as due.
    assert card_due_state({"reviews": 2}, today=TODAY) == "due"
    assert card_due_state({"reviews": 2, "due": "2026-10-24"},
                          today=TODAY) == "due"
    assert card_due_state({"reviews": 2, "due": "2026-10-20"},
                          today=TODAY) == "due"
    assert card_due_state({"reviews": 2, "due": "2026-11-01"},
                          today=TODAY) == "scheduled"


def _deck(entries):
    cards = [{"id": f"c{i}"} for i in range(len(entries))]
    return {"cards": cards,
            "progress": {f"c{i}": e for i, e in enumerate(entries)}}


def test_due_count_and_mastery_due():
    deck = _deck([
        None,                                        # new
        {"reviews": 1, "due": "2026-10-24"},         # due today
        {"reviews": 1, "due": "2026-12-01"},         # scheduled
        {"reviews": 3, "known": True},               # legacy -> due
    ])
    deck["progress"] = {k: v for k, v in deck["progress"].items()
                        if v is not None}
    assert due_count(deck, today=TODAY) == 3
    stats = mastery_stats(deck)
    assert stats["due"] >= 0  # mastery uses real today; key exists


def test_progress_endpoint_persists_schedule(authed_client, app):
    """End-to-end: generate a deck from an uploaded doc is heavy, so
    seed a deck row directly and exercise the progress endpoint."""
    import io

    from unified_app import FlashcardSet, StudyDoc, db

    # authed_client's app context: find the user via a fresh request.
    r = authed_client.post("/study/api/upload", data={
        "file": (io.BytesIO(_tiny_pdf()), "notes.pdf"),
        "title": "SRS deck source",
    }, content_type="multipart/form-data")
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    doc_id = r.get_json()["doc"]["id"]
    r = authed_client.post("/research/api/flashcards/generate",
                           json={"doc_id": doc_id})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    set_id = r.get_json()["id"]

    with app.app_context():
        fs = db.session.get(FlashcardSet, set_id)
        card_id = fs.data["cards"][0]["id"]
        doc = db.session.get(StudyDoc, doc_id)
        assert doc is not None

    r = authed_client.post(
        f"/research/api/flashcards/{set_id}/progress",
        json={"card_id": card_id, "known": True})
    assert r.status_code == 200
    assert r.get_json()["stats"]["due"] >= 0

    with app.app_context():
        fs = db.session.get(FlashcardSet, set_id)
        entry = fs.data["progress"][card_id]
        assert entry["interval"] == 1
        assert entry["due"] > "2026-01-01"  # an ISO date was stored
        assert entry["reviews"] == 1

    # Review page renders with the due UI.
    r = authed_client.get(f"/research/flashcards/{set_id}")
    assert r.status_code == 200
    assert "fc-due-toggle" in r.get_data(as_text=True)


def test_research_hub_anonymous_has_no_strip(client):
    r = client.get("/research")
    assert r.status_code == 200
    assert "Cards due for review" not in r.get_data(as_text=True)


def test_research_hub_personal_strip(authed_client):
    r = authed_client.get("/research")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Cards due for review" in html
    assert "Papers in your library" in html


def _tiny_pdf():
    """Minimal valid one-page PDF with extractable text."""
    text = ("Photosynthesis converts sunlight water and carbon dioxide "
            "into oxygen and glucose in the chloroplasts of plant cells.")
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        ("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = [b"%PDF-1.4"]
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(sum(len(x) + 1 for x in out))
        out.append(b"%d 0 obj\n%s\nendobj" % (i, body))
    xref_at = sum(len(x) + 1 for x in out)
    xref = [b"xref\n0 6\n0000000000 65535 f "]
    for off in offsets:
        xref.append(("%010d 00000 n " % off).encode())
    out.append(b"".join(xref))
    out.append(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % xref_at)
    return b"\n".join(out)
