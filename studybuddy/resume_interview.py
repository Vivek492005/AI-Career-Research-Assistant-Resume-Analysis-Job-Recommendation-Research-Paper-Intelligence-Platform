"""Resume-based mock interviews (user-requested feature, 2026-10-23).

The candidate uploads a resume; we extract a structured profile
(name, skills, projects, experience, education, public profiles)
and generate a personal mock of ~12 questions asked from THAT
resume — project deep-dives, skill probes grounded in their own
projects, experience STAR questions, personality/situational
questions and profile questions.

Generation is deterministic: every question is assembled from the
resume's own facts, and its rubric key points are built from those
same facts, so the shared rubric scorer (mock_interview.score_answer)
works unchanged — an answer scores by actually talking about the
candidate's real project, stack and outcomes. No LLM is required;
nothing about scoring depends on one.
"""

import re

from studybuddy.parsing import detect_fields

# ---------------------------------------------------------------------------
# Skill vocabulary (canonical display -> match patterns)
# ---------------------------------------------------------------------------

SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "C", "Go",
    "Rust", "Kotlin", "Swift", "PHP", "Ruby", "SQL", "HTML", "CSS",
    "React", "Angular", "Vue", "Next.js", "Node.js", "Express", "Django",
    "Flask", "FastAPI", "Spring Boot", "Spring", ".NET", "Laravel",
    "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy", "Keras",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Data Analysis", "Power BI", "Tableau", "Excel",
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQLite", "Firebase",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "GitHub",
    "Linux", "CI/CD", "Jenkins", "Terraform", "Kafka", "Spark", "Hadoop",
    "REST API", "GraphQL", "Microservices", "System Design", "DSA",
    "Data Structures", "Algorithms", "OOP", "DBMS", "Operating Systems",
    "Android", "Flutter", "React Native", "Figma", "Selenium", "Testing",
    "Agile", "Scrum", "Leadership", "Teamwork", "Communication",
]

_HEADINGS = {
    "projects": re.compile(r"^(personal\s+|key\s+|academic\s+)?projects?$", re.I),
    "experience": re.compile(r"^(work\s+|professional\s+)?experience$|^(employment|internships?)$", re.I),
    "education": re.compile(r"^education(al)?( background)?$|^academics$", re.I),
    "skills": re.compile(r"^(technical\s+)?skills$|^technologies$|^tech stack$", re.I),
    "achievements": re.compile(r"^achievements$|^awards$|^certifications?$", re.I),
    "summary": re.compile(r"^(professional\s+)?summary$|^objective$|^about( me)?$|^profile$", re.I),
}

_BULLET = re.compile(r"^\s*[•\-\*▪◦–]\s*")
_YEAR_RANGE = re.compile(r"(20\d{2})\s*[-–—to]+\s*(20\d{2}|present|current)", re.I)


def _split_sections(text):
    """Split resume text into {section_name: [lines]} preserving order."""
    sections = {"_top": []}
    current = "_top"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = None
        if len(line) <= 42 and not _BULLET.match(line):
            for name, rx in _HEADINGS.items():
                if rx.match(line.rstrip(":")):
                    heading = name
                    break
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _find_skills(text):
    found = []
    low = " " + re.sub(r"[^a-z0-9+#./ ]", " ", text.lower()) + " "
    for skill in SKILLS:
        pat = re.escape(skill.lower())
        if re.search(r"(?<![a-z0-9])" + pat + r"(?![a-z0-9])", low):
            found.append(skill)
    return found


def _project_entries(lines):
    """Heuristic project extraction from a PROJECTS section.

    An entry starts at a title-like line (short, not a bullet) and
    collects the bullet lines that follow it.
    """
    projects = []
    current = None
    for line in lines:
        is_bullet = bool(_BULLET.match(line))
        text = _BULLET.sub("", line).strip()
        if not text:
            continue
        if not is_bullet and len(text) <= 95 and not text.endswith("."):
            current = {"title": text, "lines": []}
            projects.append(current)
        elif current is not None:
            current["lines"].append(text)
        if len(projects) >= 6:
            break
    out = []
    for p in projects:
        title = re.split(r"\s*[|–—]\s*", p["title"])[0].strip(" :-")
        if len(title) < 3:
            continue
        blob = p["title"] + " " + " ".join(p["lines"])
        out.append({
            "title": title,
            "techs": _find_skills(blob),
            "points": p["lines"][:3],
        })
    return out[:4]


def _experience_entries(lines, full_text):
    entries = []
    pool = lines if lines else []
    for line in pool:
        if _YEAR_RANGE.search(line) or re.search(
                r"\b(intern|engineer|developer|analyst|designer|manager|consultant|trainee)\b",
                line, re.I):
            clean = _BULLET.sub("", line).strip()
            if 6 <= len(clean) <= 110:
                entries.append(clean)
        if len(entries) >= 3:
            break
    if not entries:
        for line in full_text.splitlines():
            if _YEAR_RANGE.search(line) and re.search(
                    r"\b(intern|engineer|developer|analyst)\b", line, re.I):
                entries.append(line.strip()[:110])
                if len(entries) >= 3:
                    break
    return entries


def extract_profile(text):
    """Structured profile from raw resume text (may be partial —
    generation adapts to whatever was found)."""
    text = (text or "")[:60000]
    fields = detect_fields(text)
    sections = _split_sections(text)
    skills = _find_skills(text)
    projects = _project_entries(sections.get("projects", []))
    if not projects:  # some resumes list projects without a heading
        projects = _project_entries(sections.get("_top", []))
    experience = _experience_entries(sections.get("experience", []), text)
    education = []
    for line in sections.get("education", []):
        clean = _BULLET.sub("", line).strip()
        if clean and len(clean) <= 120:
            education.append(clean)
        if len(education) >= 2:
            break
    links = fields.get("links", [])
    return {
        "name": fields.get("name"),
        "email": fields.get("email"),
        "skills": skills[:15],
        "projects": projects,
        "experience": experience,
        "education": education,
        "links": links,
        "has_github": any("github.com" in u for u in links),
        "has_linkedin": any("linkedin.com" in u for u in links),
    }


# ---------------------------------------------------------------------------
# Question generation — every key point is a resume fact
# ---------------------------------------------------------------------------

def _q(n, aspect, question, key_points, difficulty="Medium", minutes=4):
    return {
        "id": f"res-{n:02d}",
        "question": question,
        "companies": [],
        "roles": [],
        "category": "resume",
        "difficulty": difficulty,
        "key_points": key_points,
        "time_minutes": minutes,
        "aspect": aspect,
    }


def generate_resume_questions(profile, n=12):
    """Build up to ``n`` tailored questions from the profile.

    Returns [] when the resume carries too little signal (no
    projects, skills or experience) — the caller should ask for a
    more detailed resume rather than serve generic questions.
    """
    skills = profile.get("skills") or []
    projects = profile.get("projects") or []
    experience = profile.get("experience") or []
    education = profile.get("education") or []
    if not (skills or projects or experience):
        return []
    p1 = projects[0] if projects else None
    p2 = projects[1] if len(projects) > 1 else None
    top_skill = skills[0] if skills else None
    second_skill = skills[1] if len(skills) > 1 else None
    qs = []

    intro_points = ["A clear arc: background -> skills -> strongest work"]
    if education:
        intro_points.append(f"Education context: {education[0]}")
    if skills:
        intro_points.append("Names core skills: " + ", ".join(skills[:4]))
    if p1:
        intro_points.append(f"Highlights the flagship project: {p1['title']}")
    qs.append(_q(len(qs) + 1, "introduction",
                 "Walk me through your background and the work you are "
                 "most proud of so far.",
                 intro_points, "Easy", 3))

    if p1:
        tech_txt = ", ".join(p1["techs"][:4]) if p1["techs"] else "your chosen stack"
        points = [f"Names the problem {p1['title']} solves and who it is for",
                  f"Explains the architecture and where {tech_txt} fits"]
        points += [f"Covers a detail from the work: {pt[:80]}" for pt in p1["points"][:1]]
        points.append("States a measurable outcome: users, performance or accuracy")
        qs.append(_q(len(qs) + 1, "project deep-dive",
                     f"Your resume lists '{p1['title']}' built with {tech_txt}. "
                     "Walk me through its architecture — the main components, "
                     "how data flows between them, and one design decision you "
                     "would defend in a review.",
                     points, "Medium", 5))
        qs.append(_q(len(qs) + 1, "project challenge",
                     f"What was the hardest bug or bottleneck you hit while "
                     f"building '{p1['title']}', and how did you track it down "
                     "and fix it?",
                     ["Describes the symptom concretely, not vaguely",
                      "Explains the debugging process step by step",
                      "Names the root cause and the actual fix",
                      "Says how the fix was verified (test, metric, repro case)"],
                     "Medium", 4))

    if top_skill:
        anchor = f" in '{p1['title']}'" if p1 else ""
        qs.append(_q(len(qs) + 1, "skill probe",
                     f"Your resume highlights {top_skill}. Explain how you "
                     f"have actually used it{anchor} — go beyond the "
                     "definition: a real problem, your approach, and one "
                     "limitation you ran into.",
                     [f"Gives a concrete use of {top_skill}, not a textbook definition",
                      "Explains a real problem it solved and the outcome",
                      "Names a limitation or edge case of " + top_skill,
                      "Mentions an alternative considered and why it lost"],
                     "Medium", 4))

    if p2:
        tech_txt = ", ".join(p2["techs"][:3]) if p2["techs"] else "its stack"
        qs.append(_q(len(qs) + 1, "project deep-dive",
                     f"Tell me about '{p2['title']}' ({tech_txt}). What does "
                     "it do, what was your specific contribution, and what "
                     "would break first if its usage grew ten times?",
                     [f"Explains what {p2['title']} does in one clear sentence",
                      "Separates their own contribution from any team work",
                      "Identifies a real scaling bottleneck in " + tech_txt,
                      "Proposes a credible fix for that bottleneck"],
                     "Medium", 5))
    elif second_skill:
        qs.append(_q(len(qs) + 1, "skill probe",
                     f"How do {top_skill} and {second_skill} compare for the "
                     "kind of work on your resume — when would you pick one "
                     "over the other?",
                     [f"States a real difference between {top_skill} and {second_skill}",
                      "Gives a scenario favouring each one",
                      "Grounds the answer in their own project experience"],
                     "Medium", 4))

    if second_skill:
        qs.append(_q(len(qs) + 1, "skill probe",
                     f"{second_skill} is also on your resume. What is one "
                     f"concept in {second_skill} that most beginners get "
                     "wrong? Explain it with an example from your own work.",
                     [f"Names a specific {second_skill} concept, not a slogan",
                      "Explains the common misconception clearly",
                      "Uses a real example from their own projects",
                      "States the correct mental model in one line"],
                     "Medium", 4))

    if experience:
        exp = experience[0]
        qs.append(_q(len(qs) + 1, "experience",
                     f"Your experience includes: {exp}. Tell me about a time "
                     "there when a delivery was at risk — what was your "
                     "specific role in recovering it?",
                     ["Sets the situation with concrete stakes",
                      f"Names their personal actions in: {exp[:60]}",
                      "Quantifies the recovery: date, metric or scope saved",
                      "Reflects on what they would do earlier next time"],
                     "Medium", 4))

    qs.append(_q(len(qs) + 1, "personality",
                 "Tell me about a project or task that genuinely failed or "
                 "missed its goal. What happened, and what did you change "
                 "about how you work afterwards?",
                 ["Owns the failure without blaming tools or teammates",
                  "Explains the root cause honestly",
                  "Describes a specific change they made afterwards",
                  "Shows evidence the change worked later"],
                 "Medium", 4))
    qs.append(_q(len(qs) + 1, "personality",
                 "Describe a disagreement with a teammate or mentor about a "
                 "technical decision. How did you resolve it?",
                 ["States both positions fairly",
                  "Explains how the decision was actually made (data, prototype, escalation)",
                  "Shows the relationship survived the disagreement",
                  "Draws a lesson about collaboration"],
                 "Medium", 4))

    if profile.get("has_github"):
        qs.append(_q(len(qs) + 1, "profile",
                     "Your resume links your GitHub. Which repository there "
                     "best represents your engineering quality, and what "
                     "would a reviewer notice first about the code?",
                     ["Names a specific repository and what it does",
                      "Points to concrete quality signals: structure, tests, README",
                      "Admits one weakness in that codebase honestly",
                      "Connects the repo to the role they want"],
                     "Easy", 3))
    elif p1:
        qs.append(_q(len(qs) + 1, "engineering practice",
                     f"How did you test '{p1['title']}' before calling it "
                     "done — what kinds of tests or checks did you run, and "
                     "what did they catch?",
                     ["Names concrete test types they actually used",
                      "Gives an example of a bug the checks caught",
                      "Admits what was NOT tested and the risk that leaves"],
                     "Medium", 4))

    if p1:
        qs.append(_q(len(qs) + 1, "project deep-dive",
                     f"If you rebuilt '{p1['title']}' from scratch today, "
                     "what are the two things you would do differently, "
                     "and why?",
                     [f"Names specific weaknesses in the current {p1['title']} build",
                      "Justifies each change with a reason, not fashion",
                      "Shows awareness of cost: migration effort and risk"],
                     "Medium", 4))

    anchor_area = top_skill or (p1["techs"][0] if p1 and p1["techs"] else "software")
    qs.append(_q(len(qs) + 1, "career",
                 f"Why are you targeting roles around {anchor_area}, and "
                 "where do you want your skills to be two years from now?",
                 [f"Connects the goal to real evidence: their work with {anchor_area}",
                  "Names specific skills to build, not generic growth",
                  "Gives a believable near-term plan (projects, depth, exposure)"],
                 "Easy", 3))

    return qs[:n]
