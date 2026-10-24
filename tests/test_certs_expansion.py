"""Tests for the 2026-10-25 certification bank expansion (44 -> 110).

The bank now covers the world's most-enrolled AI + non-AI certifications:
Coursera professional certificates, Udemy best-sellers, NPTEL/IIT courses
and missing vendor flagships. Counts below are floors, not exact pins,
so future additions don't break the suite.
"""
from studybuddy.cert_guide import all_certs, domains, recommend
from studybuddy.learning_roadmaps import list_roles


def _bank():
    return all_certs()


def test_bank_total_and_domains():
    certs = _bank()
    assert len(certs) >= 110, f"need 110+ certs, got {len(certs)}"
    names = {d for d, _ in domains()}
    assert names == {"Cloud", "Data", "Programming", "Cybersecurity",
                     "Project Management", "Networking", "DevOps", "AI/ML"}


def test_ai_ml_is_the_biggest_growth_area():
    certs = _bank()
    ai = [c for c in certs if c["domain"] == "AI/ML"]
    assert len(ai) >= 20, f"need 20+ AI/ML certs, got {len(ai)}"
    names = " ".join(c["name"] for c in ai)
    for needle in ("Azure AI Fundamentals", "AI Practitioner",
                   "Generative AI Leader", "Machine Learning Specialization",
                   "Deep Learning Specialization"):
        assert needle in names, f"missing flagship AI cert: {needle}"


def test_mass_enrollment_sources_present():
    certs = _bank()
    by_provider = {}
    for c in certs:
        by_provider.setdefault(c["provider"], 0)
        by_provider[c["provider"]] += 1
    coursera = sum(n for p, n in by_provider.items() if "Coursera" in p)
    udemy = by_provider.get("Udemy", 0)
    nptel = by_provider.get("NPTEL", 0)
    assert coursera >= 15, f"need 15+ Coursera certs, got {coursera}"
    assert udemy >= 5, f"need 5+ Udemy certs, got {udemy}"
    assert nptel >= 10, f"need 10+ NPTEL certs, got {nptel}"
    # Spot-check the most-enrolled names are actually in the bank.
    names = {c["name"] for c in certs}
    for needle in ("Google AI Essentials",
                   "Machine Learning Specialization (DeepLearning.AI + Stanford)",
                   "NPTEL: Programming in Python",
                   "Complete Python Bootcamp (Udemy)",
                   "freeCodeCamp Responsive Web Design Certification",
                   "CS50's Introduction to Computer Science (Harvard)"):
        assert needle in names, f"missing mass-enrollment cert: {needle}"


def test_free_certs_are_honestly_priced():
    free = [c for c in _bank() if c["cost_inr"] == 0]
    assert len(free) >= 4, f"need 4+ free certs, got {len(free)}"
    for c in free:
        assert "Free" in c["cost_note"]
        assert "exam fee" in c["cost_note"] or "certificate of completion" in c["cost_note"]


def test_retired_and_renamed_certs_corrected():
    ids = {c["id"] for c in _bank()}
    assert "ms-dp-203" not in ids, "DP-203 retired Mar 2025 — must not stay in the bank"
    assert "ms-dp-700" in ids, "DP-700 (Fabric Data Engineer) replaces DP-203"
    assert "aws-soa" not in ids, "SysOps renamed to CloudOps — old id must go"
    assert "aws-cloudops" in ids
    assert "ibm-applied-ai" not in ids, "Applied AI renamed to AI Developer"
    assert "ibm-ai-developer" in ids


def test_cert_roles_map_to_real_roadmap_roles():
    valid = {r["id"] for r in list_roles()}
    assert valid, "roadmap roles must load"
    for c in _bank():
        assert c["roles"], f"{c['id']} needs at least one role"
        bad = [r for r in c["roles"] if r not in valid]
        assert not bad, f"{c['id']} has unknown roles: {bad}"


def test_recommender_surfaces_new_ai_certs():
    recs = recommend(skills=["python"], target_role="genai-engineer",
                     budget_inr=50000, top_n=8)
    assert len(recs) == 8
    ids = {r["cert"]["id"] for r in recs}
    assert ids & {"gcp-genai-leader", "databricks-genai-assoc",
                  "dlai-genai-llms", "google-ai-essentials"}, \
        "genai-engineer recommendations must include new GenAI certs"


def test_recommender_surfaces_free_certs_on_tiny_budget():
    recs = recommend(skills=[], target_role=None, budget_inr=1000, top_n=8)
    assert any(r["cert"]["cost_inr"] == 0 for r in recs), \
        "a Rs 1,000 budget must surface free certs"
