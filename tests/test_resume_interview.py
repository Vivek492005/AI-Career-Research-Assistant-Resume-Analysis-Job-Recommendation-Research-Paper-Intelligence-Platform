"""Tests for the resume-based mock interview (2026-10-23 feature)."""

import pytest

from studybuddy.resume_interview import extract_profile, generate_resume_questions

SAMPLE_RESUME = """Aarav Sharma
aarav.sharma@example.com | github.com/aaravsharma | linkedin.com/in/aaravsharma

Summary
Final-year B.Tech student focused on backend systems and machine learning.

Technical Skills
Python, Flask, PostgreSQL, React, Docker, Machine Learning, Git, REST API

Projects
ShopKart Price Tracker | Python, Flask, PostgreSQL
- Built a price-tracking service that scrapes 40+ stores and alerts users on drops
- Designed the PostgreSQL schema and a Celery-style job queue for scraping
- Cut alert latency from 30 minutes to under 2 minutes

Campus Notes AI | React, Python, TensorFlow
- Summarizes lecture PDFs into flashcards using an NLP pipeline
- Led a team of 3 and shipped to 400+ students in the first semester

Experience
Backend Developer Intern at Finlytics | Jun 2025 - Dec 2025
- Built REST APIs for transaction reports used by the support team
- Wrote integration tests that caught two payment rounding bugs

Education
B.Tech, Computer Science, Graphic Era University, 2022 - 2026
"""


@pytest.fixture
def authed_client(client, app):
    from werkzeug.security import generate_password_hash

    from unified_app import User, db
    with app.app_context():
        u = User(email="resmock@test.com", name="Resume Tester",
                 password_hash=generate_password_hash("password123"))
        db.session.add(u)
        db.session.commit()
    client.post("/login", data={"email": "resmock@test.com",
                                "password": "password123"})
    return client


def test_extract_profile_finds_the_facts():
    p = extract_profile(SAMPLE_RESUME)
    assert p["name"] == "Aarav Sharma"
    assert p["has_github"] and p["has_linkedin"]
    for skill in ("Python", "Flask", "PostgreSQL", "React", "Docker"):
        assert skill in p["skills"], p["skills"]
    titles = [pr["title"] for pr in p["projects"]]
    assert any("ShopKart" in t for t in titles), titles
    assert any("Campus Notes" in t for t in titles), titles
    assert p["projects"][0]["techs"], "project techs should be detected"
    assert len(p["experience"]) >= 1
    assert any("Graphic Era" in e for e in p["education"])


def test_generate_questions_are_personal_and_complete():
    p = extract_profile(SAMPLE_RESUME)
    qs = generate_resume_questions(p, n=12)
    assert len(qs) == 12
    assert [q["id"] for q in qs] == [f"res-{i:02d}" for i in range(1, 13)]
    blob = " ".join(q["question"] for q in qs)
    assert "ShopKart Price Tracker" in blob
    assert "Campus Notes AI" in blob
    aspects = {q["aspect"] for q in qs}
    for want in ("introduction", "project deep-dive", "project challenge",
                 "skill probe", "experience", "personality", "profile",
                 "career"):
        assert want in aspects, aspects
    for q in qs:
        assert q["category"] == "resume"
        assert len(q["key_points"]) >= 3
        assert q["difficulty"] in ("Easy", "Medium", "Hard")
    # Key points must carry resume facts, not generic filler.
    kp_blob = " ".join(kp for q in qs for kp in q["key_points"])
    assert "ShopKart" in kp_blob


def test_generate_questions_empty_for_empty_resume():
    p = extract_profile("Just a name and nothing else of substance.")
    assert generate_resume_questions(p) == []


def test_generate_questions_sparse_resume_still_works():
    p = extract_profile("Skills\nPython, SQL, Excel\n")
    qs = generate_resume_questions(p, n=12)
    assert 4 <= len(qs) <= 12
    assert any(q["aspect"] == "skill probe" for q in qs)


def test_resume_start_route_with_pasted_text(authed_client):
    r = authed_client.post("/interview/resume/start",
                           data={"resume_text": SAMPLE_RESUME})
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] and data["session_id"]
    assert len(data["questions"]) == 12
    assert "ShopKart Price Tracker" in data["profile"]["projects"][0]
    # The generated session submits and scores like any other mock.
    answers = [{"question_id": q["id"],
                "answer": "In ShopKart Price Tracker I used Python and "
                          "Flask with PostgreSQL. The architecture has a "
                          "scraper queue and an alert service. The hardest "
                          "part was cutting latency, which I verified with "
                          "timing metrics and tests."}
               for q in data["questions"]]
    r2 = authed_client.post(f"/interview/{data['session_id']}/submit",
                            json={"answers": answers})
    assert r2.status_code == 200
    assert r2.get_json()["total_score"] > 0


def test_resume_start_rejects_thin_text(authed_client):
    r = authed_client.post("/interview/resume/start",
                           data={"resume_text": "too short"})
    assert r.status_code == 400


def test_resume_start_requires_login(client):
    r = client.post("/interview/resume/start",
                    data={"resume_text": SAMPLE_RESUME})
    assert r.status_code == 401
