"""AI-era roadmap expansion (2026-10-24): 6 new skills, 8 new roles.

Every new skill/role is verified here so the bank cannot silently
regress: counts, stage shape, role references, gap analysis, and the
free-and-live resource rule (all URLs https; dead 404s fixed at merge).
"""

from studybuddy.learning_roadmaps import (
    analyze_gap,
    get_role,
    get_skill,
    list_roles,
    list_skills,
)

NEW_SKILLS = ["nlp", "generative-ai", "agentic-ai",
              "computer-vision", "mlops", "reinforcement-learning"]
NEW_ROLES = ["ai-engineer", "genai-engineer", "agentic-ai-engineer",
             "nlp-engineer", "cv-engineer", "mlops-engineer",
             "cloud-engineer", "sre-engineer"]


def test_expansion_counts():
    skills = list_skills()
    roles = list_roles()
    assert len(skills) == 30
    assert len(roles) == 20
    assert set(s["id"] for s in skills) >= set(NEW_SKILLS)
    assert set(r["id"] for r in roles) >= set(NEW_ROLES)


def test_new_skills_shape_and_free_resources():
    for skill_id in NEW_SKILLS:
        skill = get_skill(skill_id)
        assert skill is not None
        assert skill["domain"] == "AI/ML"
        assert [st["stage"] for st in skill["stages"]] == [
            "beginner", "intermediate", "advanced"]
        for st in skill["stages"]:
            assert len(st["topics"]) >= 6
            assert len(st["resources"]) >= 4
            assert len(st["practice_tasks"]) >= 3
            assert st["checkpoint"]
            for res in st["resources"]:
                assert res["url"].startswith("https://")
                assert res["free"] is True


def test_new_roles_reference_real_skills_and_analyze():
    valid = {s["id"] for s in list_skills()}
    for role_id in NEW_ROLES:
        role = get_role(role_id)
        assert role is not None
        assert 5 <= len(role["required_skills"]) <= 8
        for req in role["required_skills"]:
            assert req["skill_id"] in valid
            assert req["min_stage"] in (
                "beginner", "intermediate", "advanced")
            assert 1 <= req["priority"] <= 5
        gaps, found = analyze_gap([], role_id)
        assert found is not None and gaps


def test_all_resources_free_and_https():
    for skill in list_skills():
        full = get_skill(skill["id"])
        for st in full["stages"]:
            for res in st["resources"]:
                assert res["free"] is True, res["url"]
                assert res["url"].startswith("https://"), res["url"]
