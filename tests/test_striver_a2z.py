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
    # A classic problem with no A2Z counterpart, so the two sets count
    # independently here (shared problems are covered by the merge
    # tests below).
    classic_id = next(p["id"] for p in all_problems()
                      if not counterpart_ids(p["id"]))
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
    # Clean layout: stats row + module grid, no scroll-box list.
    assert "dt-embed-stats" in body and "dt-module-grid" in body
    assert "dt-modules" not in body


def test_dsa_home_tracker_reflects_saved_progress(authed_client):
    classic_id = next(p["id"] for p in all_problems()
                      if not counterpart_ids(p["id"]))
    assert authed_client.post(
        "/dsa/a2z-0100/status", json={"status": "solved"}).status_code == 200
    assert authed_client.post(
        f"/dsa/{classic_id}/status", json={"status": "solved"}).status_code == 200
    body = authed_client.get("/dsa").get_data(as_text=True)
    assert 'id="progress-tracker"' in body
    assert "1/495" in body
    assert f"1/{len(all_problems())} solved" in body


def test_progress_api_anonymous_gets_zeroed_summary(client):
    r = client.get("/api/dsa/progress")
    assert r.status_code == 200
    d = r.get_json()
    assert d["is_authed"] is False
    assert d["a2z"]["total"] == 495 and d["a2z"]["solved"] == 0
    assert d["classic"]["total"] == len(all_problems())


def test_progress_api_reflects_marks(authed_client):
    """Regression (2026-10-23): marks must show up in the data the
    embedded tracker refreshes from."""
    classic_id = next(p["id"] for p in all_problems()
                      if not counterpart_ids(p["id"]))
    authed_client.post("/dsa/a2z-0001/status", json={"status": "solved"})
    authed_client.post(f"/dsa/{classic_id}/status", json={"status": "solved"})
    d = authed_client.get("/api/dsa/progress").get_json()
    assert d["is_authed"] is True
    assert d["a2z"]["solved"] == 1
    assert d["a2z"]["by_step"][0]["solved"] == 1
    assert d["classic"]["solved"] == 1


def test_session_survives_client_ip_change(authed_client):
    """Regression (2026-10-23): with ProxyFix the session identifier
    includes the real client IP; users on CGNAT/mobile networks rotate
    IPs between requests and 'strong' protection silently logged them
    out — marks then failed with 401 and the tracker showed the
    anonymous zeros. The session must survive an IP change."""
    page = authed_client.get("/dsa/a2z",
                             environ_base={"REMOTE_ADDR": "203.0.113.99"})
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert 'id="az-solved-count"' in body  # still logged in, not anon
    r = authed_client.post("/dsa/a2z-0007/status", json={"status": "solved"},
                           environ_base={"REMOTE_ADDR": "198.51.100.7"})
    assert r.status_code == 200  # the mark must save from the new IP too


def test_dsa_home_has_live_refresh_hooks(client):
    body = client.get("/dsa").get_data(as_text=True)
    assert "dsa_tracker_embed.js" in body
    assert 'data-stat="solved"' in body
    assert 'data-diff="Easy"' in body
    assert 'data-step="1"' in body
    assert 'id="classic-strong"' in body


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


# --- Cross-set progress merge (classic <-> A2Z share problems) ---

from studybuddy.dsa_practice import counterpart_ids, expand_statuses  # noqa: E402


def test_counterpart_two_sum_links_both_sets():
    assert counterpart_ids("dsa-arrays-01") == ["a2z-0111"]
    assert "dsa-arrays-01" in counterpart_ids("a2z-0111")


def test_classic_solve_counts_in_a2z_tracker():
    summary = progress_summary([("dsa-arrays-01", "solved")])
    assert summary["classic"]["solved"] >= 1
    assert summary["a2z"]["solved"] == 1
    arrays = next(s for s in summary["a2z"]["by_step"] if s["step"] == 3)
    assert arrays["solved"] == 1
    easy = next(d for d in summary["a2z"]["by_difficulty"]
                if d["difficulty"] == "Easy")
    assert easy["solved"] == 1


def test_a2z_solve_counts_in_classic_set():
    summary = progress_summary([("a2z-0111", "solved")])
    assert summary["a2z"]["solved"] == 1
    assert summary["classic"]["solved"] == 2  # both classic Two Sum drills


def test_merge_never_double_counts_or_downgrades():
    both = progress_summary([("dsa-arrays-01", "solved"),
                             ("a2z-0111", "solved")])
    assert both["a2z"]["solved"] == 1
    expanded = expand_statuses([("dsa-arrays-01", "stuck"),
                                ("a2z-0111", "solved")])
    assert expanded["dsa-arrays-01"] == "solved"
    assert expanded["a2z-0111"] == "solved"


# --- Every row has a destination; wrong-platform links removed ---

def test_every_row_has_a_solve_or_learn_destination():
    for e in a2z_problems():
        assert e["url"] or e["tuf_url"], f"dead-end row: {e['id']} {e['title']}"
        if e["tuf_url"]:
            assert e["tuf_url"].startswith("https://takeuforward.org/")
            assert e["tuf_kind"] in ("practice", "learning")


# Rows whose sheet-supplied LeetCode link pointed at a DIFFERENT
# problem (verified by title/slug audit, 2026-10-23). Their Solve
# button must fall back to the row's own takeUforward practice page.
MISLINKED_TITLES = (
    "Highest Occurring Element in an Array",
    "Leaders in an Array",
    "Deletion of the head of LL",
    "Flattening of LL",
    "Minimum number of platforms required for a railway",
    "Detect a cycle in an undirected graph",
    "Kosaraju's algorithm",
    "Minimum number of bracket reversals to make an expression balanced",
)


def test_known_wrong_leetcode_links_removed():
    by_title = {e["title"]: e for e in a2z_problems()}
    for title in MISLINKED_TITLES:
        entry = by_title[title]
        assert entry["url"] is None, f"{title} still mislinked: {entry['url']}"
        assert entry["tuf_kind"] == "practice", title


def test_patterns_have_descriptive_names():
    pats = [e for e in a2z_problems() if e["subtopic"] == "Patterns"]
    assert len(pats) == 22
    for i, e in enumerate(pats, start=1):
        assert e["title"].startswith(f"Pattern {i} — "), e["title"]
    titles = {e["title"] for e in pats}
    assert "Pattern 7 — Star Pyramid" in titles
    assert "Pattern 12 — Number Crown Pattern" in titles
    assert "Pattern 22 — Number Pattern" in titles


def test_sheet_page_gives_every_row_a_button(client):
    html = client.get("/dsa/a2z").get_data(as_text=True)
    # Rows that used to be dead ends now carry links.
    assert "sum-of-first-n-numbers" in html  # TUF practice fallback
    assert "breaking-the-myth" in html or "/dsa/a2z/a2z-0001/learn" in html
    assert "Pattern 7 — Star Pyramid" in html


# --- In-app lessons (theory topics + patterns) ---

from studybuddy.a2z_lessons import get_lesson, lesson_ids  # noqa: E402


def test_lessons_cover_patterns_and_theory_rows():
    entries = {e["id"]: e for e in a2z_problems()}
    ids = lesson_ids()
    pattern_ids = {e["id"] for e in entries.values()
                   if e["subtopic"] == "Patterns"}
    learning_ids = {e["id"] for e in entries.values()
                    if e["tuf_kind"] == "learning"}
    assert pattern_ids <= ids, "every pattern needs a lesson"
    assert learning_ids <= ids, "every theory row needs a lesson"
    for lid in ids:
        lesson = get_lesson(lid)
        assert lesson["intro"] and lesson["sections"] and lesson["key_points"]
        for item in lesson["suggested"]:
            target = item.get("a2z_id") or item.get("problem_id")
            assert target and get_problem(target), f"{lid} -> {target}"


def test_pattern_lesson_code_reproduces_diagram():
    import contextlib
    import io

    for e in a2z_problems():
        if e["subtopic"] != "Patterns":
            continue
        lesson = get_lesson(e["id"])
        assert lesson and lesson.get("diagram"), e["id"]
        code = next(s["code"] for s in lesson["sections"] if s.get("code"))
        namespace = {}
        exec(code, namespace)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            namespace["pattern"](lesson["diagram_n"])
        got = [line.rstrip() for line in buf.getvalue().strip("\n").split("\n")]
        want = [line.rstrip() for line in lesson["diagram"].strip("\n").split("\n")]
        assert got == want, e["id"]


def test_lesson_page_renders_and_unknown_404(client):
    pat = next(e for e in a2z_problems() if e["subtopic"] == "Patterns")
    r = client.get(f"/dsa/a2z/{pat['id']}/learn")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert pat["title"] in html and "Suggested questions" in html
    assert client.get("/dsa/a2z/a2z-9999/learn").status_code == 404
    plain = next(e for e in a2z_problems()
                 if e["tuf_kind"] == "practice" and e["id"] not in lesson_ids())
    assert client.get(f"/dsa/a2z/{plain['id']}/learn").status_code == 404
