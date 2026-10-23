"""Tests for Wave 2 #14: communication coach."""
import os

import pytest

from studybuddy.communication_coach import (
    analyze_transcript,
    coach_questions,
    find_filler_hits,
    get_coach_question,
    validate_coach_extras,
    validate_coach_inputs,
    video_presence_checklist,
)


@pytest.fixture
def authed_client(client, app):
    import sys

    from werkzeug.security import generate_password_hash
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from unified_app import User, db
    with app.app_context():
        u = User(email="coach@test.com", name="Coach Tester",
                 password_hash=generate_password_hash("password123"))
        db.session.add(u)
        db.session.commit()
    client.post("/login", data={"email": "coach@test.com",
                                "password": "password123"})
    return client


RICH_TEXT = (
    "Um, so basically I think I would say that I actually led a project, "
    "you know, and it was basically very, very successful. "
    "The system was built by our team and it was deployed quickly. "
    "I sort of managed the stakeholders and stuff, and things went well, "
    "very well indeed. I literally worked on it for like six months, "
    "and I think probably it was the best project ever, to be honest."
)


def test_filler_bank_loads():
    hits = find_filler_hits("um uh like basically actually")
    words = {h["word"] for h in hits}
    assert {"um", "uh", "like", "basically", "actually"} <= words
    for h in hits:
        assert h["severity"] in (1, 2, 3)
        assert isinstance(h["alternatives"], list)


def test_filler_positions_usable_for_highlighting():
    hits = find_filler_hits("um hello um")
    um = [h for h in hits if h["word"] == "um"][0]
    assert um["count"] == 2
    assert len(um["positions"]) == 2
    for pos in um["positions"]:
        assert "um hello um"[pos:pos + 2].lower() == "um"


def test_analyze_structure():
    r = analyze_transcript(RICH_TEXT)
    assert 0 <= r["clarity_score"] <= 100
    assert set(r["breakdown"]) == {"filler_load", "pacing",
                                   "voice_and_hedges", "structure"}
    assert r["metrics"]["word_count"] > 40
    assert r["metrics"]["filler_events"] > 5
    assert r["metrics"]["passive_constructions"] >= 1
    assert r["metrics"]["hedge_events"] >= 1
    assert r["suggestions"]
    assert r["cleaned_version"]
    assert r["drills"]


def test_clean_text_scores_higher():
    clean = ("I led a migration project for our checkout service. The team "
             "replaced a monolithic deploy with a canary pipeline. Error rates "
             "dropped from eight percent to one tenth of a percent within a week. "
             "I coordinated four engineers and presented the results to leadership.")
    messy = ("Um, so basically I think I sort of led like a project, you know, "
             "and it was basically very very successful and stuff. The system was "
             "built by us and it was deployed, and I literally think it was "
             "probably the best thing ever, to be honest.")
    assert analyze_transcript(clean)["clarity_score"] > \
        analyze_transcript(messy)["clarity_score"]


def test_cleaned_version_removes_severe_fillers():
    r = analyze_transcript(RICH_TEXT)
    low = r["cleaned_version"].lower()
    assert "um," not in low and " um " not in low
    assert "you know" not in low


def test_validation():
    t, e = validate_coach_inputs({"text": "too short"})
    assert t is None and e
    t, e = validate_coach_inputs({"text": "x" * 60})
    assert t and e is None
    t, e = validate_coach_inputs({"text": "x" * 10001})
    assert t is None and e


def test_coach_home_unauth_ok(client):
    r = client.get("/coach")
    assert r.status_code == 200
    assert b"Log in" in r.data


def test_analyze_requires_login(client):
    r = client.post("/coach/analyze", json={"text": "x" * 60})
    assert r.status_code == 401


def test_analyze_rejects_short(client, authed_client):
    r = authed_client.post("/coach/analyze", json={"text": "short"})
    assert r.status_code == 400


def test_analyze_flow(authed_client, app):
    from unified_app import CommunicationAnalysis, db
    r = authed_client.post("/coach/analyze", json={"text": RICH_TEXT})
    assert r.status_code == 200, r.data[:300]
    d = r.get_json()
    assert d["success"] and d["report"]["clarity_score"] < 75
    assert d["report_url"].startswith("/coach/")
    with app.app_context():
        row = db.session.get(CommunicationAnalysis, d["analysis_id"])
        assert row is not None
        assert abs(row.clarity_score - d["report"]["clarity_score"]) < 0.01
    # saved report page
    r = authed_client.get(d["report_url"])
    assert r.status_code == 200
    assert b"Communication Coach Report" in r.data


def test_coach_isolation(client, authed_client, app):
    from werkzeug.security import generate_password_hash

    from unified_app import CommunicationAnalysis, User, db
    with app.app_context():
        u2 = User(email="coach2@test.com", name="Other",
                  password_hash=generate_password_hash("password123"))
        db.session.add(u2)
        db.session.commit()
        row = CommunicationAnalysis(user_id=u2.id, clarity_score=10.0,
                                    analysis_json={"clarity_score": 10.0})
        db.session.add(row)
        db.session.commit()
        other_id = row.id
    r = authed_client.get(f"/coach/{other_id}")
    assert r.status_code == 404


def test_xss_safe_report(authed_client):
    payload = ("This is a reasonable length answer with some content in it, "
               "<script>alert(1)</script> and more words to reach the minimum "
               "length requirement for the coach analysis endpoint.")
    r = authed_client.post("/coach/analyze", json={"text": payload})
    assert r.status_code == 200
    d = r.get_json()
    r = authed_client.get(d["report_url"])
    assert r.status_code == 200
    assert b"<script>alert(1)</script>" not in r.data


# ---------------- Analyzer v2 dimensions ----------------

STAR_TEXT = (
    "During my internship last summer, our project had a serious problem "
    "because the dashboard was loading very slowly and users were "
    "complaining every day. My task was to make it faster, and I was "
    "responsible for the backend queries. I analyzed the slow endpoints, "
    "I implemented caching, and I optimized the database indexes. As a "
    "result, the load time reduced by 60 percent and complaints dropped "
    "sharply within two weeks of the release."
)


def test_dimensions_present_and_bounded():
    r = analyze_transcript(RICH_TEXT)
    assert r["question_type"] == "general"
    dims = r["dimensions"]
    assert set(dims) == {"star", "impact", "confidence", "delivery",
                         "vocabulary"}
    for d in dims.values():
        assert 0 <= d["score"] <= 100


def test_star_complete_answer_scores_full():
    r = analyze_transcript(STAR_TEXT, question_type="behavioral")
    star = r["dimensions"]["star"]
    assert star["missing"] == []
    assert star["score"] == 100
    assert star["parts"]["result"] is True


def test_star_missing_parts_flagged_with_suggestion():
    plain = ("I am a hardworking person and I like coding a lot. I have "
             "done many projects in college and I am good at Python and "
             "Java. I want to join your company because it is a great "
             "company and I will work very hard for the team always.")
    r = analyze_transcript(plain, question_type="behavioral")
    star = r["dimensions"]["star"]
    assert star["score"] < 100 and star["missing"]
    assert any("STAR" in s for s in r["suggestions"])


def test_impact_finds_metrics_and_ownership():
    r = analyze_transcript(STAR_TEXT)
    impact = r["dimensions"]["impact"]
    assert impact["metrics_found"], "the 60 percent metric must be found"
    assert impact["action_verbs"] >= 3
    assert impact["ownership_ratio"] > 0.5
    no_metric = analyze_transcript(RICH_TEXT)["dimensions"]["impact"]
    assert no_metric["score"] < impact["score"]


def test_delivery_spoken_seconds_gives_real_wpm():
    # STAR_TEXT is ~73 words: 20s of speech is far too fast, 32s is calm.
    r = analyze_transcript(STAR_TEXT, question_type="behavioral",
                           spoken_seconds=20)
    d = r["dimensions"]["delivery"]
    assert d["wpm"] and d["wpm"] > 170
    assert d["pace_verdict"] == "rushed"
    assert any("wpm" in s for s in r["suggestions"])
    calm = analyze_transcript(STAR_TEXT, question_type="behavioral",
                              spoken_seconds=32)
    assert calm["dimensions"]["delivery"]["pace_verdict"] == "good pace"
    long_text = STAR_TEXT + " " + STAR_TEXT.replace("dashboard", "portal") \
        + " " + STAR_TEXT.replace("dashboard", "mobile app")
    est = analyze_transcript(long_text, question_type="behavioral")
    assert est["dimensions"]["delivery"]["length_verdict"] == "in range"


def test_delivery_targets_depend_on_question_type():
    short = analyze_transcript(STAR_TEXT, question_type="behavioral")
    assert short["dimensions"]["delivery"]["target_seconds"] == [90, 150]
    hr = analyze_transcript(STAR_TEXT, question_type="hr")
    assert hr["dimensions"]["delivery"]["target_seconds"] == [45, 90]
    bogus = analyze_transcript(STAR_TEXT, question_type="nonsense")
    assert bogus["question_type"] == "general"


def test_vocabulary_repetition_detected():
    repetitive = ("The project was good and the project was fast and the "
                  "project was clean and the project shipped on time. "
                  "The project team liked the project outcome a lot.")
    r = analyze_transcript(repetitive)
    words = {d["word"] for d in r["dimensions"]["vocabulary"]["repeated_words"]}
    assert "project" in words


def test_drills_carry_target_rewrites():
    r = analyze_transcript(RICH_TEXT)
    assert r["drills"]
    for d in r["drills"]:
        assert "after" in d


def test_question_bank_loads():
    qs = coach_questions()
    assert len(qs) >= 40
    types = {q["type"] for q in qs}
    assert types == {"hr", "behavioral", "technical"}
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids))
    for q in qs:
        assert q["question"] and q["framework"] and q["tips"]
        assert q["target_seconds"] >= 30
    assert get_coach_question(ids[0])["id"] == ids[0]
    assert get_coach_question("no-such-id") is None


def test_validate_coach_extras():
    qtype, question, spoken, err = validate_coach_extras({})
    assert (qtype, question, spoken, err) == ("general", None, None, None)
    _, _, _, err = validate_coach_extras({"question_id": "nope"})
    assert err
    _, _, _, err = validate_coach_extras({"spoken_seconds": "abc"})
    assert err
    _, _, _, err = validate_coach_extras({"spoken_seconds": 2})
    assert err
    _, _, spoken, err = validate_coach_extras({"spoken_seconds": 95})
    assert spoken == 95 and err is None
    qs = coach_questions()
    if qs:
        qtype, question, _, err = validate_coach_extras(
            {"question_id": qs[0]["id"]})
        assert err is None and question["id"] == qs[0]["id"]
        assert qtype == qs[0]["type"]


def test_video_checklist_scoring():
    assert video_presence_checklist({})["score"] == 0
    full = {c: True for c in ("eye_contact", "framing", "background",
                              "posture", "gestures", "audio", "attire")}
    r = video_presence_checklist(full)
    assert r["score"] == 100 and r["priority_fixes"] == []


def test_analyze_with_v2_fields(authed_client):
    r = authed_client.post("/coach/analyze", json={
        "text": STAR_TEXT, "question_type": "behavioral",
        "spoken_seconds": 120})
    assert r.status_code == 200, r.data[:300]
    report = r.get_json()["report"]
    assert report["question_type"] == "behavioral"
    assert report["dimensions"]["delivery"]["wpm"]
    page = authed_client.get(r.get_json()["report_url"])
    assert b"Delivery &amp; depth" in page.data
    assert b"Situation" in page.data


def test_analyze_rejects_bad_question(authed_client):
    r = authed_client.post("/coach/analyze", json={
        "text": STAR_TEXT, "question_id": "does-not-exist"})
    assert r.status_code == 400


def test_video_checklist_route(app, authed_client):
    fresh = app.test_client()
    r = fresh.post("/coach/video-checklist", json={"scores": {}})
    assert r.status_code == 401
    r = authed_client.post("/coach/video-checklist",
                           json={"scores": {"eye_contact": True}})
    assert r.status_code == 200
    assert r.get_json()["result"]["score"] == 20


def test_coach_page_sections_and_history(authed_client):
    r = authed_client.get("/coach")
    assert r.status_code == 200
    assert b"Pick a question" in r.data
    assert b"Video presence" in r.data
    authed_client.post("/coach/analyze", json={"text": STAR_TEXT})
    r = authed_client.get("/coach")
    assert b"Your progress" in r.data
