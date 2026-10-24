"""Practice hub served from the JSON mock-interview bank (not the legacy CSV).

Regression coverage for the 2026-10-24 hub unification: the /practice
page must show every bank company with real counts (no CSV-only
companies like IBM), and /api/interview-questions must return bank rows
with rubric key points and working category/difficulty filters.
"""

from collections import Counter

from studybuddy.mock_interview import _load_bank, interview_hub_data


def _bank_counts():
    counts = Counter()
    for q in _load_bank():
        for comp in q.get("companies", []):
            counts[comp] += 1
    return counts


def test_practice_page_shows_bank_companies_not_csv_only(client):
    resp = client.get("/practice")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    counts = _bank_counts()
    for comp in counts:
        assert f'data-company="{comp}"' in html, f"missing hub card: {comp}"
    # IBM exists only in the legacy interview CSV, never in the JSON
    # bank — so it must not appear in the INTERVIEW grid. (It still
    # appears in the separate Coding Practice tab, which is untouched
    # by this change, so scope the check to the interview grid.)
    interview_grid = html.split('id="interviewCompanyGrid"')[1].split(
        'id="content-coding"')[0]
    assert 'data-company="IBM"' not in interview_grid
    # Stat strip reflects the live bank, not hardcoded numbers.
    hub = interview_hub_data()
    assert str(hub["total_questions"]) in html
    assert str(hub["total_companies"]) in html
    assert 'id="interviewCompanySearch"' in html


def test_practice_companies_sorted_by_count_desc(client):
    hub = interview_hub_data()
    totals = [hub["stats"][c]["total"] for c in hub["companies"]]
    assert totals == sorted(totals, reverse=True)
    assert hub["total_questions"] == len(_load_bank())
    assert hub["total_companies"] == len(_bank_counts())


def test_api_interview_questions_returns_bank_rows(client):
    resp = client.get("/api/interview-questions/Google")
    assert resp.status_code == 200
    rows = resp.get_json()
    assert rows, "Google must have bank rows"
    counts = _bank_counts()
    assert len(rows) == counts["Google"]
    for row in rows:
        assert row["company"] == "Google"
        assert row["question"]
        assert len(row["key_points"]) >= 3
        assert row["time_minutes"] is not None


def test_api_interview_questions_filters(client):
    resp = client.get("/api/interview-questions/Google",
                      query_string={"category": "System Design"})
    rows = resp.get_json()
    assert rows
    assert all(r["category"] == "System Design" for r in rows)
    resp = client.get("/api/interview-questions/Google",
                      query_string={"difficulty": "Hard"})
    rows = resp.get_json()
    assert rows
    assert all(r["difficulty"] == "Hard" for r in rows)
    # Bank category values are accepted too.
    resp = client.get("/api/interview-questions/Google",
                      query_string={"category": "system_design"})
    assert resp.get_json()
    # Unknown company: empty list, not an error.
    assert client.get("/api/interview-questions/NotACompany").get_json() == []


def test_api_companies_interview_matches_hub(client):
    resp = client.get("/api/companies")
    assert resp.status_code == 200
    assert resp.get_json()["interview"] == interview_hub_data()["companies"]
