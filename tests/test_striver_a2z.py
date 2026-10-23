"""Tests for the Striver A2Z sheet import + progress tracker."""

import pytest

from studybuddy.dsa_practice import (
    all_problems,
    a2z_problems,
    a2z_tracker,
    get_problem,
    progress_summary,
    sheet_structure,
)


@pytest.fixture
def authed_client(client, app):
    from werkzeug.security import generate_password_hash

    from unified_app import User, db
    with app.app_context():
        u = User(email="a2z@test.com", name="A2Z Tester",
                 password_hash=generate_password_hash("password123"))
        db.session.add(u)
        db.session.commit()
    client.post("/login", data={"email": "a2z@test.com",
                                "password": "password123"})
    return client


def test_dataset_complete_and_wellformed():
    entries = a2z_problems()
    assert len(entries) == 495, f"sheet should have 495 rows, got {len(entries)}"
    steps = {e["step"] for e in entries}
    assert steps == set(range(1, 21)), f"expected steps 1..20, got {sorted(steps)}"
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    assert ids[0] == "a2z-0001" and ids[-1] == "a2z-0495"
    for e in entries:
        assert e["title"] and e["step_name"] and e["subtopic"]
        assert e["difficulty"] in ("Easy", "Medium", "Hard", None)
        if e["url"] is not None:
            assert e["url"].startswith("https://leetcode.com/")
        assert e["kind"] in ("problem", "learn")
        if e["kind"] == "learn":
            assert e["difficulty"] is None and e["url"] is None


def test_dataset_difficulty_tally():
    entries = a2z_problems()
    tally = {}
    for e in entries:
        tally[e["difficulty"]] = tally.get(e["difficulty"], 0) + 1
    # The sheet's unbadged (theory/lesson) rows are a small minority.
    assert tally[None] == 15
    assert tally["Hard"] == 109
    assert sum(tally.values()) == 495


def test_sheet_structure_groups_and_counts():
    steps = sheet_structure()
    assert len(steps) == 20
    assert sum(s["total"] for s in steps) == 495
    assert steps[0]["step_name"] == "Beginner Problems"
    names = [s["step_name"] for s in steps]
    for expected in ("Arrays", "Greedy Algorithms", "Dynamic Programming",
                     "Graphs", "Binary Trees"):
        assert expected in names
    marked = sheet_structure({"a2z-0001": "solved", "a2z-0002": "attempted"})
    assert marked[0]["solved"] == 1
    assert marked[0]["rows"][0]["status"] == "solved"
    assert marked[0]["rows"][1]["status"] == "attempted"
    assert marked[0]["rows"][2]["status"] is None


def test_a2z_ids_resolve_in_shared_lookup():
    p = get_problem("a2z-0001")
    assert p is not None and p["a2z"] is True
    assert p["topics"] == ["beginner problems"]
    # Classic problems still resolve.
    assert get_problem("dsa-arrays-01") is not None


def test_tracker_math():
    rows = [("a2z-0001", "solved"), ("a2z-0002", "solved"),
            ("a2z-0003", "attempted"), ("a2z-0004", "stuck"),
            ("dsa-arrays-01", "solved")]  # classic id must be ignored
    t = a2z_tracker(rows)
    assert t["total"] == 495
    assert t["solved"] == 2 and t["attempted"] == 1 and t["stuck"] == 1
    assert t["tracked"] == 4
    assert t["pct"] == 0  # 2/495 rounds to 0
    first = t["by_step"][0]
    assert first["step_name"] == "Beginner Problems"
    assert first["solved"] == 2 and first["attempted"] == 4
    diffs = {d["difficulty"]: d for d in t["by_difficulty"]}
    assert sum(d["total"] for d in diffs.values()) == 480  # 495 - 15 theory
    empty = a2z_tracker([])
    assert empty["solved"] == 0 and empty["pct"] == 0


def test_sheet_page_renders_anonymously(client):
    r = client.get("/dsa/a2z")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Striver" in body and "Kadane" in body
    assert "leetcode.com/problems/maximum-subarray/" in body
    assert "Mark as solved" not in body  # marking needs an account


def test_progress_summary_combines_a2z_and_classic():
    classic_id = all_problems()[0]["id"]
    summary = progress_summary([
        ("a2z-0001", "solved"),
        ("a2z-0002", "attempted"),
        (classic_id, "solved"),
    ])
    assert summary["a2z"]["total"] == 495
    assert summary["a2z"]["solved"] == 1
    assert summary["classic"]["total"] == len(all_problems())
    assert summary["classic"]["solved"] == 1


def test_dsa_home_embeds_built_in_progress_tracker(client):
    r = client.get("/dsa")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'id="progress-tracker"' in body
    assert "Your A2Z progress" in body
    assert "0/495" in body
    assert "By difficulty" in body and "By module" in body
    assert "liquid_gauge.js" in body


def test_dsa_home_tracker_reflects_saved_progress(authed_client):
    classic_id = all_problems()[0]["id"]
    assert authed_client.post(
        "/dsa/a2z-0100/status", json={"status": "solved"}).status_code == 200
    assert authed_client.post(
        f"/dsa/{classic_id}/status", json={"status": "solved"}).status_code == 200
    body = authed_client.get("/dsa").get_data(as_text=True)
    assert 'id="progress-tracker"' in body
    assert "1/495" in body
    assert f"1/{len(all_problems())} solved" in body


def test_tracker_requires_login(client):
    r = client.get("/dsa/tracker")
    assert r.status_code in (301, 302)


def test_mark_solved_then_untrack_flow(authed_client):
    r = authed_client.post("/dsa/a2z-0100/status", json={"status": "solved"})
    assert r.status_code == 200
    page = authed_client.get("/dsa/a2z").get_data(as_text=True)
    assert 'id="az-solved-count">1<' in page
    tracker = authed_client.get("/dsa/tracker").get_data(as_text=True)
    assert "1/495" in tracker
    r = authed_client.post("/dsa/a2z-0100/untrack", json={})
    assert r.status_code == 200
    tracker = authed_client.get("/dsa/tracker").get_data(as_text=True)
    assert "0/495" in tracker


def test_untrack_unknown_problem_404(authed_client):
    r = authed_client.post("/dsa/a2z-9999/untrack", json={})
    assert r.status_code == 404


def test_sheet_structure_preserves_sheet_order():
    steps = sheet_structure()
    first = steps[0]
    subs = [g["subtopic"] for g in first["groups"]]
    assert subs[0] == "Fundamentals of Programming"
    assert subs.index("Patterns") < subs.index("Basic Maths")
    assert sum(len(g["rows"]) for g in first["groups"]) == first["total"] == 83
