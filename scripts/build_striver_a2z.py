"""Build data/striver_a2z.json from data/striver_a2z_raw.txt.

The raw file is the sheet as extracted from Striver's A2Z page on
takeUforward (2026-10-23): one line per row,
``step | step name | subtopic | title | difficulty | practice url``.
The live sheet carries Basic / Core / Pro badges, mapped to
Easy / Medium / Hard; rows without a badge (mostly theory and
lesson rows) get a null difficulty. A row is a ``learn`` row when it
has neither a difficulty nor a practice link; everything else is a
``problem`` row.
"""
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "striver_a2z_raw.txt")
OUT = os.path.join(ROOT, "data", "striver_a2z.json")
DIFFICULTIES = {"Easy", "Medium", "Hard"}


def main():
    entries = []
    seen_steps = {}
    with open(RAW, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("==="):
                continue
            parts = [p.strip() for p in line.split(" | ")]
            assert len(parts) == 6, f"bad line: {line!r}"
            step, step_name, subtopic, title, difficulty, url = parts
            step = int(step)
            seen_steps.setdefault(step, step_name)
            assert seen_steps[step] == step_name, f"step name drift: {line!r}"
            if difficulty not in DIFFICULTIES:
                difficulty = None  # '-' and stray markers (e.g. 'Theory')
            if url == "-":
                url = None
            if url is not None:
                assert url.startswith("https://"), f"bad url: {line!r}"
            entries.append({
                "id": f"a2z-{len(entries) + 1:04d}",
                "step": step,
                "step_name": step_name,
                "subtopic": subtopic,
                "title": title,
                "difficulty": difficulty,
                "url": url,
                "kind": "learn" if difficulty is None and url is None else "problem",
            })
    assert len(entries) == 495, f"expected 495 rows, got {len(entries)}"
    assert len(seen_steps) == 20, f"expected 20 steps, got {len(seen_steps)}"
    tally = Counter(e["difficulty"] for e in entries)
    print("difficulty tally:", dict(tally))
    per_step = Counter(e["step"] for e in entries)
    print("per-step:", [per_step[s] for s in sorted(per_step)])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
