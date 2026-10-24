#!/usr/bin/env python3
"""Merge validated quiz-question clusters into data/skill_quizzes.json.

Independent validation gate (validate_generated_banks skill):
  1. Schema: every row has all fields, 4 distinct options, answer 0-3,
     difficulty in {easy, medium, hard}, explanation non-empty.
  2. Dedup by normalized question text vs the live bank AND within the
     incoming set — collisions abort the merge for manual review.
  3. IDs are assigned here (prefix per skill, next free number) — the
     cluster files carry the placeholder id "TMP".

Usage: python scripts/merge_quiz_bank.py <cluster.json> [more.json ...]
       [--dry-run]
Prints a validation log; only writes on full pass.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "skill_quizzes.json"

PREFIX = {
    "python": "py", "javascript": "js", "java": "jv", "cpp": "cp",
    "html-css": "hc", "react": "rx", "nodejs": "nj", "typescript": "ts",
    "sql": "sql", "dsa": "dsa", "system-design": "sd", "git-github": "gg",
    "linux": "lx", "data-analysis": "da", "machine-learning": "ml",
    "statistics": "st",
}
FIELDS = {"id", "skill", "topic", "difficulty", "question", "options",
          "answer", "explanation"}


def norm(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def load_bank():
    raw = json.loads(BANK.read_text())
    if isinstance(raw, dict):
        return raw, raw.get("questions", [])
    return raw, raw


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if not args:
        print("no cluster files given")
        return 1
    bank_raw, bank = load_bank()
    print(f"bank before: {len(bank)}")
    seen = {norm(q["question"]) for q in bank}
    incoming = []
    for path in args:
        rows = json.loads(Path(path).read_text())
        assert isinstance(rows, list), f"{path}: not a list"
        incoming.extend(rows)
        print(f"{path}: {len(rows)} rows")
    print(f"incoming total: {len(incoming)}")

    errors = []
    for i, q in enumerate(incoming):
        if set(q.keys()) != FIELDS:
            errors.append(f"row {i}: fields {sorted(q.keys())}")
            continue
        if q["skill"] not in PREFIX:
            errors.append(f"row {i}: unknown skill {q['skill']!r}")
        if q["difficulty"] not in ("easy", "medium", "hard"):
            errors.append(f"row {i}: bad difficulty {q['difficulty']!r}")
        if len(q["options"]) != 4 or len(set(q["options"])) != 4:
            errors.append(f"row {i}: options must be 4 distinct")
        if not isinstance(q["answer"], int) or not 0 <= q["answer"] <= 3:
            errors.append(f"row {i}: bad answer index")
        if len((q["explanation"] or "").strip()) < 20:
            errors.append(f"row {i}: explanation too short")
        if len((q["question"] or "").strip()) < 15:
            errors.append(f"row {i}: question too short")
    if errors:
        print("SCHEMA ERRORS:")
        for e in errors[:20]:
            print(" -", e)
        return 1

    dupes = []
    local = set()
    for q in incoming:
        n = norm(q["question"])
        if n in seen:
            dupes.append(("vs bank", q["question"][:80]))
        elif n in local:
            dupes.append(("within incoming", q["question"][:80]))
        local.add(n)
    if dupes:
        print(f"DUPLICATES: {len(dupes)}")
        for kind, text in dupes[:20]:
            print(f" - [{kind}] {text}")
        return 1

    # Assign ids: next free number per prefix.
    used = Counter()
    for q in bank:
        m = re.match(r"([a-z]+)-(\d+)$", q["id"])
        if m:
            used[m.group(1)] = max(used[m.group(1)], int(m.group(2)))
    for q in incoming:
        p = PREFIX[q["skill"]]
        used[p] += 1
        q["id"] = f"{p}-{used[p]:03d}"

    per_skill = Counter(q["skill"] for q in incoming)
    print("per skill:", dict(sorted(per_skill.items())))
    print("difficulty:", dict(Counter(q["difficulty"] for q in incoming)))
    if dry:
        print("DRY RUN — nothing written")
        return 0
    bank.extend(incoming)
    if isinstance(bank_raw, dict):
        bank_raw["questions"] = bank
        out = bank_raw
    else:
        out = bank
    BANK.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"bank after: {len(bank)} — written to {BANK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
