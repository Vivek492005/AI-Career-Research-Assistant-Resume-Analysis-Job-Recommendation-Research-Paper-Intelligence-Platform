"""Tests for Wave 3 #19: skill quizzes."""
import pytest

from studybuddy.skill_quizzes import (
    build_quiz,
    check_answer,
    get_question,
    grade_quiz,
    public_question,
    quiz_skills,
    validate_start_payload,
)


def test_bank_size_and_schema():
    from studybuddy.skill_quizzes import _load
    bank = _load()
    assert len(bank) >= 300, f"need 300+ questions, got {len(bank)}"
    skills = {s for s, _ in quiz_skills()}
    assert len(skills) >= 15, f"need 15+ skills, got {len(skills)}"
    required = {"id", "skill", "topic", "difficulty", "question",
                "options", "answer", "explanation"}
    for q in bank:
        assert required <= set(q), q.get("id")
        assert q["difficulty"] in ("easy", "medium", "hard")
        assert len(q["options"]) == 4
        assert 0 <= q["answer"] <= 3
        assert len(q["explanation"]) > 10
        assert len(q["question"]) > 10


def test_bank_id_uniqueness():
    from studybuddy.skill_quizzes import _load
    ids = [q["id"] for q in _load()]
    assert len(ids) == len(set(ids))


def test_per_skill_counts():
    # Bank expanded 20 -> 30 per skill on 2026-10-24 (160 validated rows).
    for skill, n in quiz_skills():
        assert 25 <= n <= 35, f"{skill}: {n} questions"


def test_build_quiz_stratified():
    skill = quiz_skills()[0][0]
    qs = build_quiz(skill, n=12)
    assert len(qs) == 12
    assert {q["skill"] for q in qs} == {skill}
    diffs = {q["difficulty"] for q in qs}
    assert len(diffs) >= 2, "stratified quiz should mix difficulties"
    ids = [q["id"] for q in qs]
    assert len(ids) == len(set(ids))


def test_build_quiz_difficulty_filter():
    skill = quiz_skills()[0][0]
    qs = build_quiz(skill, n=5, difficulties=["easy"])
    assert qs and all(q["difficulty"] == "easy" for q in qs)


def test_public_question_hides_answer():
    q = get_question(build_quiz(quiz_skills()[0][0], n=1)[0]["id"])
    pub = public_question(q)
    assert "answer" not in pub and "explanation" not in pub
    assert len(pub["options"]) == 4


def test_check_answer():
    q = build_quiz(quiz_skills()[0][0], n=1)[0]
    right = check_answer(q, q["answer"])
    assert right["correct"] is True
    assert right["explanation"] == q["explanation"]
    wrong_idx = (q["answer"] + 1) % 4
    wrong = check_answer(q, wrong_idx)
    assert wrong["correct"] is False
    assert wrong["correct_index"] == q["answer"]


def test_grade_quiz_analytics():
    skill = quiz_skills()[0][0]
    qs = build_quiz(skill, n=10, seed=42)
    # answer everything correctly
    answers = {q["id"]: q["answer"] for q in qs}
    results, summary = grade_quiz(qs, answers)
    assert summary["score"] == 10 and summary["pct"] == 100
    assert summary["weak_topics"] == []
    assert "verdict" in summary
    # answer everything wrong
    wrong = {q["id"]: (q["answer"] + 1) % 4 for q in qs}
    _, summary2 = grade_quiz(qs, wrong)
    assert summary2["score"] == 0
    assert summary2["weak_topics"], "all-wrong should flag weak topics"


def test_validate_start_payload():
    skill = quiz_skills()[0][0]
    good, err = validate_start_payload(
        {"skill": skill, "num_questions": 10, "difficulties": ["easy"],
         "timed": True, "time_limit_sec": 600})
    assert err is None and good["timed"] and good["time_limit_sec"] == 600
    _, err = validate_start_payload({"skill": "nope"})
    assert err


# ---------- route tests ----------

@pytest.fixture
def authed_client(client, app):
    from werkzeug.security import generate_password_hash

    from unified_app import User, db
    with app.app_context():
        u = User(email="learn19@test.com", name="Quizzer",
                 password_hash=generate_password_hash("password123"))
        db.session.add(u)
        db.session.commit()
    client.post("/login", data={"email": "learn19@test.com", "password": "password123"})
    return client


def _bento_ok(html):
    return 'bento.css' in html and 'b-card' in html


def test_quizzes_home_renders(client):
    r = client.get("/learn/quizzes")
    assert r.status_code == 200
    assert _bento_ok(r.get_data(as_text=True))


def test_quiz_start_requires_login(client):
    skill = quiz_skills()[0][0]
    r = client.post("/learn/quizzes/start", json={"skill": skill})
    assert r.status_code == 401


def test_quiz_full_flow(authed_client):
    skill = quiz_skills()[0][0]
    # start
    r = authed_client.post("/learn/quizzes/start", json={
        "skill": skill, "num_questions": 5, "difficulties": [], "timed": False})
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"]
    aid = data["attempt_id"]
    assert len(data["questions"]) == 5
    assert all("answer" not in q for q in data["questions"])
    # instant check on first question
    q0 = data["questions"][0]
    full = get_question(q0["id"])
    r = authed_client.post(f"/learn/quizzes/{aid}/check", json={
        "question_id": q0["id"], "answer": full["answer"]})
    assert r.status_code == 200
    chk = r.get_json()
    assert chk["correct"] is True and chk["explanation"]
    # submit all correct
    answers = {q["id"]: get_question(q["id"])["answer"] for q in data["questions"]}
    r = authed_client.post(f"/learn/quizzes/{aid}/submit", json={"answers": answers})
    assert r.status_code == 200
    sub = r.get_json()
    assert sub["success"] and sub["summary"]["pct"] == 100
    assert "report_url" in sub
    # report page renders
    r = authed_client.get(sub["report_url"])
    assert r.status_code == 200
    assert _bento_ok(r.get_data(as_text=True))
    # double submit rejected
    r = authed_client.post(f"/learn/quizzes/{aid}/submit", json={"answers": answers})
    assert r.status_code == 404


def test_quiz_check_rejects_foreign_question(authed_client):
    skill = quiz_skills()[0][0]
    r = authed_client.post("/learn/quizzes/start", json={"skill": skill, "num_questions": 5})
    aid = r.get_json()["attempt_id"]
    other_skill = [s for s, _ in quiz_skills() if s != skill][0]
    foreign = build_quiz(other_skill, n=1)[0]["id"]
    r = authed_client.post(f"/learn/quizzes/{aid}/check", json={
        "question_id": foreign, "answer": 0})
    assert r.status_code == 400


def test_quiz_history_anonymous_redirect(client):
    assert client.get("/learn/quizzes/history").status_code in (301, 302)


def test_quiz_history(authed_client):
    r = authed_client.get("/learn/quizzes/history")
    assert r.status_code == 200
    assert _bento_ok(r.get_data(as_text=True))


# ------- 2026-10-24: weakness-drill fix + Mistake Book -------

def test_weakness_drill_targets_weak_topics():
    """Regression: the drill used to filter on a nonexistent "topics"
    list field, so weak-topic targeting silently never matched."""
    from studybuddy.skill_quizzes import _load, weakness_drill
    skill = "python"
    topics = {}
    for q in _load():
        if q["skill"] == skill:
            topics.setdefault(q["topic"], []).append(q)
    topic, qs = max(topics.items(), key=lambda kv: len(kv[1]))
    past = [{"question_id": q["id"], "topic": topic, "correct": False}
            for q in qs]
    drill = weakness_drill(skill, past, n=10, seed=7)
    assert topic in drill["target_topics"]
    drilled_topics = [q["topic"] for q in drill["questions"]]
    # Every available question from the weak topic is pulled into the
    # drill before any general fill (pool is smaller than the drill size).
    assert drilled_topics.count(topic) == len(qs)


def test_quiz_mistakes_latest_state_wins():
    from studybuddy.skill_quizzes import quiz_mistakes
    base = {"question": "Q?", "options": ["a", "b", "c", "d"],
            "topic": "T", "difficulty": "easy", "explanation": "why"}
    a1 = {"skill": "python", "submitted_at": "2026-10-01T10:00:00",
          "attempt_id": 1, "results": [
              dict(base, question_id="py-001", chosen_index=0,
                   correct_index=1, correct=False),
              dict(base, question_id="py-002", chosen_index=2,
                   correct_index=1, correct=False)]}
    a2 = {"skill": "python", "submitted_at": "2026-10-02T10:00:00",
          "attempt_id": 2, "results": [
              dict(base, question_id="py-001", chosen_index=1,
                   correct_index=1, correct=True)]}
    book = quiz_mistakes([a2, a1])  # input order must not matter
    assert book["total"] == 1
    assert book["skills"][0]["skill"] == "python"
    assert book["skills"][0]["mistakes"][0]["question_id"] == "py-002"
    assert book["skills"][0]["mistakes"][0]["attempt_id"] == 1


def test_learn_hub_anonymous_has_search_no_strip(client):
    r = client.get("/learn")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Continue where you left off" not in html  # anon: no strip
    assert "learn-search" in html                      # search for everyone


def test_learn_hub_personalization(authed_client):
    r = authed_client.get("/learn")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Continue where you left off" in html
    assert "stages done" in html


def test_drill_route_requires_login(client):
    r = client.post("/learn/quizzes/drill", json={"skill": "python"})
    assert r.status_code == 401


def test_drill_route_and_mistakes_page(authed_client):
    # Submit a quiz with every answer deliberately wrong.
    r = authed_client.post("/learn/quizzes/start", json={
        "skill": "python", "num_questions": 5})
    assert r.status_code == 200
    start = r.get_json()
    answers = {}
    for q in start["questions"]:
        full = get_question(q["id"])
        answers[q["id"]] = (full["answer"] + 1) % 4
    r = authed_client.post(
        f"/learn/quizzes/{start['attempt_id']}/submit",
        json={"answers": answers})
    assert r.status_code == 200
    # Mistake Book lists the wrong questions.
    r = authed_client.get("/learn/quizzes/mistakes")
    assert r.status_code == 200
    assert "Mistake Book" in r.get_data(as_text=True)
    # Drill starts a fresh attempt.
    r = authed_client.post("/learn/quizzes/drill", json={"skill": "python"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] and data["attempt_id"] != start["attempt_id"]
    assert len(data["questions"]) >= 3
    # Unknown skill is rejected.
    r = authed_client.post("/learn/quizzes/drill", json={"skill": "nope"})
    assert r.status_code == 400
