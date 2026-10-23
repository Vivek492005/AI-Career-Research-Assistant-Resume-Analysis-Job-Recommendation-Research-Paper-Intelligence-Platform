"""Tests for Wave 2 feature #16: timed aptitude and reasoning tests."""
from datetime import UTC, datetime, timedelta

import pytest

from studybuddy.aptitude_test import (
    COMPANY_TESTS,
    all_questions,
    categories,
    check_answer,
    get_question,
    mastery_from_attempts,
    mistakes_from_attempts,
    pick_for_setup,
    pick_questions,
    public_question,
    score_attempt,
    topics,
    track_counts,
    validate_test_setup,
)
from tests.conftest import login, register
from unified_app import AptitudeAttempt, db


@pytest.fixture()
def authed_client(client):
    register(client)
    login(client)
    return client


# ---------- content bank sanity ----------

def test_bank_loads_with_required_fields():
    bank = all_questions()
    assert len(bank) >= 300, f"bank too small: {len(bank)}"
    required = {"id", "category", "subcategory", "difficulty",
                "statement", "options", "answer", "explanation"}
    for q in bank:
        assert required <= set(q.keys()), q.get("id")
        assert q["category"] in ("quantitative", "logical", "verbal")
        assert q["difficulty"] in ("Easy", "Medium", "Hard")
        assert len(q["options"]) == 4
        assert len(set(q["options"])) == 4
        assert 0 <= q["answer"] < 4


def test_bank_ids_unique():
    bank = all_questions()
    ids = [q["id"] for q in bank]
    assert len(ids) == len(set(ids))


def test_bank_covers_all_categories():
    cats = {c for c, _ in categories()}
    assert cats == {"quantitative", "logical", "verbal"}
    for _, count in categories():
        assert count >= 50, f"category too small: {count}"


def test_public_question_hides_answer():
    q = all_questions()[0]
    pub = public_question(q)
    assert "answer" not in pub and "explanation" not in pub
    assert pub["id"] == q["id"]


def test_pick_questions_filters_and_count():
    qs = pick_questions("quantitative", n=8, seed=42)
    assert len(qs) == 8
    assert all(q["category"] == "quantitative" for q in qs)
    mixed = pick_questions("mixed", n=12, seed=42)
    assert len(mixed) == 12
    assert len({q["category"] for q in mixed}) > 1


# ---------- setup validation ----------

def test_validate_setup_ok():
    cleaned, err = validate_test_setup(
        {"category": "logical", "num_questions": 15, "time_limit": 900})
    assert err is None
    assert cleaned == {"mode": "category", "category": "logical",
                       "n": 15, "time_limit": 900}


def test_validate_setup_rejects_bad():
    for payload in ({"category": "nope", "num_questions": 10, "time_limit": 600},
                    {"category": "mixed", "num_questions": 2, "time_limit": 600},
                    {"category": "mixed", "num_questions": 10, "time_limit": 30},
                    {"category": "mixed", "num_questions": 100, "time_limit": 600},
                    "not-a-dict"):
        cleaned, err = validate_test_setup(payload)
        assert cleaned is None and err, payload


# ---------- engine scoring ----------

def test_score_attempt_all_correct():
    qs = pick_questions("mixed", n=6, seed=3)
    ids = [q["id"] for q in qs]
    answers = {qid: get_question(qid)["answer"] for qid in ids}
    results, summary = score_attempt(ids, answers)
    assert summary["total"] == 6
    assert summary["correct"] == 6
    assert summary["score_pct"] == 100.0
    assert all(r["correct"] for r in results)
    assert summary["weak_areas"] == []


def test_score_attempt_blank_and_wrong():
    qs = pick_questions("mixed", n=6, seed=4)
    ids = [q["id"] for q in qs]
    results, summary = score_attempt(ids, {})
    assert summary["correct"] == 0
    assert summary["score_pct"] == 0.0
    # wrong index
    wrong = {ids[0]: (get_question(ids[0])["answer"] + 1) % 4}
    results, summary = score_attempt(ids, wrong)
    assert summary["correct"] == 0
    assert results[0]["chosen"] == wrong[ids[0]]


def test_score_attempt_analytics_shape():
    qs = pick_questions("quantitative", n=5, seed=5)
    ids = [q["id"] for q in qs]
    results, summary = score_attempt(ids, {})
    assert set(summary["by_category"]) == {"quantitative"}
    assert summary["by_category"]["quantitative"]["total"] == 5
    assert summary["by_difficulty"]


# ---------- routes ----------

def _start(client, **kw):
    payload = {"category": "mixed", "num_questions": 5, "time_limit": 300}
    payload.update(kw)
    return client.post("/aptitude/start", json=payload,
                       headers={"X-CSRFToken": "test"})


def test_start_requires_login(client):
    r = client.post("/aptitude/start", json={"category": "mixed",
                                             "num_questions": 5,
                                             "time_limit": 300})
    assert r.status_code == 401


def test_start_and_submit_happy_path(authed_client):
    r = _start(authed_client)
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"]
    assert len(data["questions"]) == 5
    assert not any("answer" in q for q in data["questions"])
    attempt_id = data["attempt_id"]

    # answer everything correctly (server scores from bank, not client)
    answers = {q["id"]: get_question(q["id"])["answer"]
               for q in data["questions"]}
    r2 = authed_client.post(f"/aptitude/{attempt_id}/submit",
                            json={"answers": answers},
                            headers={"X-CSRFToken": "test"})
    assert r2.status_code == 200
    rep = r2.get_json()
    assert rep["success"] and not rep["expired"]
    assert rep["summary"]["score_pct"] == 100.0
    assert len(rep["results"]) == 5

    # saved report page renders
    r3 = authed_client.get(f"/aptitude/{attempt_id}")
    assert r3.status_code == 200
    assert b'saved-data' in r3.data

    # double submit rejected
    r4 = authed_client.post(f"/aptitude/{attempt_id}/submit",
                            json={"answers": {}},
                            headers={"X-CSRFToken": "test"})
    assert r4.status_code == 400


def test_submit_validates_time_window(authed_client, app):
    r = _start(authed_client, time_limit=300)
    attempt_id = r.get_json()["attempt_id"]
    # rewind the server start timestamp to simulate expiry
    with app.app_context():
        row = db.session.get(AptitudeAttempt, attempt_id)
        row.started_at = datetime.now(UTC) - timedelta(seconds=9999)
        db.session.commit()
    r2 = authed_client.post(f"/aptitude/{attempt_id}/submit",
                            json={"answers": {}},
                            headers={"X-CSRFToken": "test"})
    assert r2.status_code == 200
    assert r2.get_json()["expired"] is True


def test_submit_rejects_tampered_question_ids(authed_client):
    r = _start(authed_client)
    attempt_id = r.get_json()["attempt_id"]
    # client invents question ids — server only scores its own stored set
    r2 = authed_client.post(f"/aptitude/{attempt_id}/submit",
                            json={"answers": {"apt-9999": 0, "bogus": 2}},
                            headers={"X-CSRFToken": "test"})
    assert r2.status_code == 200
    rep = r2.get_json()
    assert rep["summary"]["total"] == 5
    assert rep["summary"]["correct"] == 0


def test_report_isolation(authed_client, app):
    r = _start(authed_client)
    attempt_id = r.get_json()["attempt_id"]
    answers = {q["id"]: 0 for q in r.get_json()["questions"]}
    authed_client.post(f"/aptitude/{attempt_id}/submit", json={"answers": answers},
                       headers={"X-CSRFToken": "test"})
    # anonymous user cannot view (login_required -> redirect)
    anon = app.test_client()
    r2 = anon.get(f"/aptitude/{attempt_id}")
    assert r2.status_code in (302, 401)
    # second user cannot view
    other = app.test_client()
    register(other, email="other@x.com")
    login(other, email="other@x.com")
    r3 = other.get(f"/aptitude/{attempt_id}")
    assert r3.status_code == 404


def test_dashboard_lists_attempts(authed_client):
    r = _start(authed_client)
    attempt_id = r.get_json()["attempt_id"]
    authed_client.post(f"/aptitude/{attempt_id}/submit", json={"answers": {}},
                       headers={"X-CSRFToken": "test"})
    r2 = authed_client.get("/dashboard")
    assert r2.status_code == 200
    assert b"Aptitude Tests" in r2.data


def test_aptitude_home_renders(client):
    r = client.get("/aptitude")
    assert r.status_code == 200
    assert b"Timed" in r.data


# ---------- expansion: tracks, topics, company mocks, mistakes ----------

def test_tracks_cover_the_whole_bank():
    total = len(all_questions())
    counts = {name: n for name, _label, n in track_counts()}
    assert counts["logical"] + counts["verbal"] == total
    assert counts["logical"] > counts["verbal"] > 150


def test_topics_by_track_are_consistent():
    verbal_topics = topics("verbal")
    assert verbal_topics
    assert all(cat == "verbal" for _sub, cat, _n in verbal_topics)
    logical_subs = {sub for sub, _cat, _n in topics("logical")}
    for expected in ("seating_arrangement", "data_interpretation",
                     "time_work", "percentages"):
        assert expected in logical_subs


def test_validate_new_modes():
    cleaned, err = validate_test_setup(
        {"track": "verbal", "num_questions": 10, "time_limit": 600})
    assert err is None and cleaned["mode"] == "track"
    cleaned, err = validate_test_setup(
        {"topic": "percentages", "num_questions": 10, "time_limit": 600})
    assert err is None and cleaned["mode"] == "topic"
    assert cleaned["category"] == "quantitative"
    cleaned, err = validate_test_setup({"company": "TCS NQT"})
    assert err is None and cleaned["mode"] == "company"
    assert cleaned["n"] == 30 and cleaned["time_limit"] == 1800
    qid = all_questions()[0]["id"]
    cleaned, err = validate_test_setup({"question_ids": [qid]})
    assert err is None and cleaned["mode"] == "retest"
    for bad in ({"track": "nope"}, {"topic": "nope"}, {"company": "Nope Co"},
                {"question_ids": ["apt-9999"]}, {"question_ids": []}):
        cleaned, err = validate_test_setup(bad)
        assert cleaned is None and err, bad


def test_pick_for_setup_modes():
    cleaned, _ = validate_test_setup({"company": "Infosys"})
    qs = pick_for_setup(cleaned, seed=7)
    assert len(qs) == sum(COMPANY_TESTS["Infosys"]["blueprint"].values())
    from collections import Counter
    got = Counter(q["category"] for q in qs)
    for cat, n in COMPANY_TESTS["Infosys"]["blueprint"].items():
        assert got[cat] == n
    cleaned, _ = validate_test_setup(
        {"topic": "blood_relations", "num_questions": 8, "time_limit": 480})
    qs = pick_for_setup(cleaned, seed=7)
    assert len(qs) == 8
    assert all(q["subcategory"] == "blood_relations" for q in qs)
    ids = [q["id"] for q in all_questions()[:3]]
    cleaned, _ = validate_test_setup({"question_ids": ids})
    qs = pick_for_setup(cleaned, seed=7)
    assert {q["id"] for q in qs} == set(ids)


def test_score_attempt_has_topic_breakdown():
    bank = all_questions()[:6]
    ids = [q["id"] for q in bank]
    answers = {q["id"]: q["answer"] for q in bank[:3]}
    results, summary = score_attempt(ids, answers)
    assert summary["by_subcategory"]
    assert "weak_topics" in summary
    assert all("trick" in r for r in results)


def test_check_answer_practice_mode():
    q = all_questions()[0]
    r = check_answer(q["id"], q["answer"])
    assert r["correct"] is True and r["explanation"]
    r = check_answer(q["id"], (q["answer"] + 1) % 4)
    assert r["correct"] is False
    assert check_answer("apt-9999", 0) is None


def _fake_result(qid, sub, correct, chosen=0):
    return {"id": qid, "category": "logical", "subcategory": sub,
            "difficulty": "Easy", "statement": "s", "options": ["a"] * 4,
            "chosen": chosen, "correct_index": 1, "correct": correct,
            "explanation": "e", "trick": "", "companies": []}


def test_mistakes_and_mastery_helpers():
    newest = [_fake_result("q1", "percentages", False),
              _fake_result("q2", "percentages", True)]
    older = [_fake_result("q1", "percentages", True),
             _fake_result("q3", "idioms", False)]
    wrong, by_sub = mistakes_from_attempts([newest, older])
    # q1 was fixed in the newest attempt? No: newest has q1 wrong -> stays.
    assert {r["id"] for r in wrong} == {"q1", "q3"}
    assert by_sub == {"percentages": 1, "idioms": 1}
    mastery = mastery_from_attempts([newest, older])
    assert mastery["percentages"]["total"] == 3
    assert mastery["percentages"]["correct"] == 2


def test_company_start_route(authed_client):
    r = authed_client.post("/aptitude/start", json={"company": "TCS NQT"},
                           headers={"X-CSRFToken": "test"})
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert len(d["questions"]) == 30
    assert d["time_limit_sec"] == 1800


def test_practice_flow(authed_client, app):
    fresh = app.test_client()
    r = fresh.post("/aptitude/practice/check",
                   json={"question_id": "apt-0001", "chosen": 0})
    assert r.status_code == 401
    page = authed_client.get("/aptitude/practice/logical/percentages")
    assert page.status_code == 200
    assert b"Practice" in page.data
    q = next(q for q in all_questions()
             if q["subcategory"] == "percentages")
    r = authed_client.post("/aptitude/practice/check",
                           json={"question_id": q["id"],
                                 "chosen": q["answer"]},
                           headers={"X-CSRFToken": "test"})
    assert r.status_code == 200
    assert r.get_json()["result"]["correct"] is True
    assert authed_client.get(
        "/aptitude/practice/verbal/percentages").status_code == 404
    assert authed_client.get(
        "/aptitude/practice/logical/nope").status_code == 404


def test_mistake_book_flow(authed_client):
    r = authed_client.post(
        "/aptitude/start",
        json={"category": "logical", "num_questions": 5,
              "time_limit": 300},
        headers={"X-CSRFToken": "test"})
    d = r.get_json()
    # answer everything wrong on purpose
    answers = {}
    for pub in d["questions"]:
        q = get_question(pub["id"])
        answers[pub["id"]] = (q["answer"] + 1) % 4
    r = authed_client.post(f"/aptitude/{d['attempt_id']}/submit",
                           json={"answers": answers},
                           headers={"X-CSRFToken": "test"})
    assert r.status_code == 200
    page = authed_client.get("/aptitude/mistakes")
    assert page.status_code == 200
    assert b"open mistakes" in page.data
    assert b"Retest These Mistakes" in page.data
    # fix them all in a retest -> book empties
    ids = [pub["id"] for pub in d["questions"]]
    r = authed_client.post("/aptitude/start",
                           json={"question_ids": ids},
                           headers={"X-CSRFToken": "test"})
    d2 = r.get_json()
    answers = {pub["id"]: get_question(pub["id"])["answer"]
               for pub in d2["questions"]}
    authed_client.post(f"/aptitude/{d2['attempt_id']}/submit",
                       json={"answers": answers},
                       headers={"X-CSRFToken": "test"})
    page = authed_client.get("/aptitude/mistakes")
    assert b"mistake book is empty" in page.data
