"""Regression tests for the 2026-10-24 Claude evaluation's remaining P0s.

- PDF Library UI bug: the study_library route used to pass only `docs=`,
  while the template reads `documents` + `is_authed`, so the list always
  rendered empty even right after a successful upload.
- Overclaims: 'Running BERT semantic analysis' loading step, 'Trusted by
  students' + avatar social proof, and og/meta 'ATS resume scoring'.
- Landing numbers: previously hardcoded (339/320/132) and stale; the index
  route now computes them from the live banks, so this test derives the
  expected counts from the same loaders instead of hardcoding them.
"""
import io

from tests.conftest import login, make_pdf_bytes, register  # noqa: F401

from studybuddy import aptitude_test, dsa_practice, skill_quizzes
from studybuddy.mock_interview import interview_hub_data


def _authed(client):
    register(client)
    login(client)


def test_library_lists_uploaded_doc(client):
    _authed(client)
    data = {"file": (io.BytesIO(make_pdf_bytes([
        "The mitochondria is the powerhouse of the cell.",
    ])), "notes.pdf")}
    resp = client.post("/study/api/upload", data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 200, resp.get_data(as_text=True)[:300]
    page = client.get("/research/library")
    assert page.status_code == 200
    assert b"notes.pdf" in page.data
    assert b"No documents yet" not in page.data
    assert b"1 document" in page.data


def test_landing_counts_match_live_banks(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data
    num_interview = interview_hub_data()["total_questions"]
    num_aptitude = len(aptitude_test.all_questions())
    num_quiz = sum(c for _, c in skill_quizzes.quiz_skills())
    num_dsa = len(dsa_practice.a2z_problems())
    assert num_interview > 1000 and num_aptitude > 500
    assert num_quiz > 500 and num_dsa > 400
    for n in (num_interview, num_aptitude, num_quiz, num_dsa):
        assert f"<b>{n}</b>".encode() in html
    # The old hardcoded stats must be gone.
    assert b"<b>339</b>" not in html
    assert b"<b>338</b>" not in html
    assert b"<b>132</b>" not in html


def test_no_overclaim_copy(client):
    landing = client.get("/")
    assert landing.status_code == 200
    assert b"Trusted by students" not in landing.data
    assert b"ATS resume scoring" not in landing.data
    resume = client.get("/resume")
    assert resume.status_code == 200
    assert b"Running BERT" not in resume.data
    assert b"ATS resume scoring" not in resume.data
