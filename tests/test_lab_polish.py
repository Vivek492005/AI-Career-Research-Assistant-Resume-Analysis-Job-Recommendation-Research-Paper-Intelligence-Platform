"""Tests for the 2026-10-24 ULTIMATE LAB polish pass.

Audit finding: the three JD tools (prescreen / keyword-plan /
offer-odds) take a `report` argument their handlers treat as a dict,
but the typed registry validated it as any JsonValue. A plain
non-JSON string therefore passed validation untouched and the handler
died with AttributeError, surfaced to users as an opaque
"Tool failed: AttributeError". The report fields now require a JSON
object, so bad input produces field-level guidance instead.
"""
import json

from studybuddy.ultimate_routes import ALL_TOOLS, public_tools, run_tool

REPORT = {
    "score": 72,
    "matched_skills": ["python", "flask"],
    "matched_keywords": ["python"],
    "missing_keywords": ["docker", "ci/cd"],
}

TEXT = (
    "I built a REST API in Python with Flask and PostgreSQL serving "
    "500 users daily and reduced response time by 40 percent."
)


def test_jd_tools_accept_json_string_report():
    report = json.dumps(REPORT)
    res, err = run_tool(
        "jd/prescreen", {"resume_text": TEXT, "report": report})
    assert err is None and "score" in res

    res, err = run_tool(
        "jd/keyword-plan", {"resume_text": TEXT, "report": report})
    assert err is None and res  # non-empty action plan

    res, err = run_tool(
        "jd/offer-odds", {"report": report, "applicants_estimate": 120})
    assert err is None and res


def test_jd_tools_reject_non_object_report_cleanly():
    for bad in ("not json at all", "[1, 2, 3]", "42"):
        res, err = run_tool(
            "jd/prescreen", {"resume_text": TEXT, "report": bad})
        assert res is None
        assert err is not None
        assert "report" in err
        assert "JSON object" in err
        assert not err.startswith("Tool failed")


def test_jd_tools_accept_dict_report_directly():
    res, err = run_tool(
        "jd/offer-odds", {"report": REPORT, "applicants_estimate": 10})
    assert err is None and res


def _sample_value(field):
    if field.get("options"):
        opt = field["options"][0]
        return opt.get("value") if isinstance(opt, dict) else opt
    if field.get("json"):
        return json.dumps(REPORT)
    ftype = (field.get("type") or "text").lower()
    label = (field.get("label") or "").lower()
    if ftype in ("number", "int", "float"):
        return 3
    if ftype == "checkbox":
        return True
    if "one per line" in label:
        return "python\nflask"
    if "comma" in label:
        return "python, flask"
    if field["name"].endswith("_date") or field["name"] == "date":
        return "2026-10-01"
    return TEXT


def test_full_catalog_never_crashes_with_tool_failed():
    """Smoke-audit all 91 registered tools: with schema-derived sample
    payloads, a tool may legitimately ask for better input (a clean
    validation error) but must never die with 'Tool failed'."""
    assert len(public_tools()) == len(ALL_TOOLS) == 91
    crashed = []
    for tool in ALL_TOOLS:
        payload = {f["name"]: _sample_value(f)
                   for f in tool.get("fields", [])}
        result, err = run_tool(tool["id"], payload)
        if err and err.startswith("Tool failed"):
            crashed.append((tool["id"], err))
    assert crashed == []
