"""Merge the aptitude expansion clusters into data/aptitude_questions.json.

Reads the existing bank plus ~/workspace/aptitude-bank/cluster-{l1,l2,v1,v2}.json,
independently validates every new question (schema, unique options, answer
range, explanation length, company tags), drops exact/near duplicates
(against the existing bank and across clusters), assigns continuing
apt-XXXX ids, and writes the merged bank.

Usage: python scripts/merge_aptitude_bank.py [--dry-run]
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "data", "aptitude_questions.json")
SRC_DIR = os.path.expanduser("~/workspace/aptitude-bank")
CLUSTERS = ["cluster-l1.json", "cluster-l2.json",
            "cluster-v1.json", "cluster-v2.json"]
ALLOWED_COMPANIES = {"TCS NQT", "Infosys", "Accenture", "Wipro",
                     "Cognizant", "Capgemini", "Amazon"}
REQUIRED = {"category", "subcategory", "difficulty", "statement",
            "options", "answer", "explanation"}


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", text.lower())).strip()


def tokens(text):
    return set(norm(text).split())


def validate(q, where):
    errs = []
    if not REQUIRED <= set(q):
        errs.append(f"missing fields {REQUIRED - set(q)}")
    if q.get("category") not in ("quantitative", "logical", "verbal"):
        errs.append(f"bad category {q.get('category')}")
    if q.get("difficulty") not in ("Easy", "Medium", "Hard"):
        errs.append(f"bad difficulty {q.get('difficulty')}")
    opts = q.get("options") or []
    if len(opts) != 4 or len(set(opts)) != 4:
        errs.append("options must be 4 and unique")
    if not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < 4:
        errs.append("answer index out of range")
    if len(q.get("explanation") or "") < 40:
        errs.append("explanation too short")
    for c in q.get("companies") or []:
        if c not in ALLOWED_COMPANIES:
            errs.append(f"unknown company tag {c}")
    if errs:
        raise SystemExit(f"{where}: {errs} :: {str(q)[:160]}")


def main():
    dry = "--dry-run" in sys.argv
    with open(BANK, encoding="utf-8") as f:
        bank = json.load(f)
    seen_norm = {norm(q["statement"]) for q in bank}
    seen_tokens = [(tokens(q["statement"]), q["subcategory"]) for q in bank]
    next_id = max(int(q["id"].split("-")[1]) for q in bank) + 1

    added, dropped = [], []
    for name in CLUSTERS:
        path = os.path.join(SRC_DIR, name)
        with open(path, encoding="utf-8") as f:
            questions = json.load(f)["questions"]
        for i, q in enumerate(questions):
            validate(q, f"{name}[{i}]")
            n = norm(q["statement"])
            if n in seen_norm:
                dropped.append((name, q["subcategory"], "exact dup"))
                continue
            t = tokens(q["statement"])
            near = False
            # Reading-comprehension questions share one embedded passage
            # per set, so token overlap is meaningless there; the exact
            # check above still guards true duplicates.
            for t2, sub2 in seen_tokens:
                if sub2 != q["subcategory"] or sub2 == "reading_comprehension":
                    continue
                union = t | t2
                if union and len(t & t2) / len(union) >= 0.92:
                    near = True
                    break
            if near:
                dropped.append((name, q["subcategory"], "near dup"))
                continue
            q = dict(q)
            q["id"] = f"apt-{next_id:04d}"
            next_id += 1
            q.setdefault("trick", "")
            q.setdefault("companies", [])
            added.append(q)
            seen_norm.add(n)
            seen_tokens.append((t, q["subcategory"]))

    print(f"existing: {len(bank)} | added: {len(added)} | dropped: {len(dropped)}")
    for d in dropped:
        print("  DROPPED:", d)
    merged = bank + added
    print("merged total:", len(merged))
    print("categories:", Counter(q["category"] for q in merged))
    print("new per subcategory:", Counter(q["subcategory"] for q in added))
    print("answer positions (new):", Counter(q["answer"] for q in added))
    if not dry:
        with open(BANK, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
        print("written:", BANK)


if __name__ == "__main__":
    main()
