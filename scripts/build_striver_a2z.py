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
EXTRA = os.path.join(ROOT, "data", "striver_a2z_extra.json")
OUT = os.path.join(ROOT, "data", "striver_a2z.json")
DIFFICULTIES = {"Easy", "Medium", "Hard"}

# The sheet names its pattern rows only "Pattern 1".."Pattern 22";
# these are the descriptive names from Striver's pattern series, so
# students can tell the patterns apart (user request, 2026-10-23).
PATTERN_NAMES = {
    1: "Rectangular Star Pattern",
    2: "Right-Angled Triangle Pattern",
    3: "Right-Angled Number Pyramid",
    4: "Right-Angled Number Pyramid II",
    5: "Inverted Right Pyramid",
    6: "Inverted Numbered Right Pyramid",
    7: "Star Pyramid",
    8: "Inverted Star Pyramid",
    9: "Diamond Star Pattern",
    10: "Half Diamond Star Pattern",
    11: "Binary Number Triangle Pattern",
    12: "Number Crown Pattern",
    13: "Increasing Number Triangle Pattern",
    14: "Increasing Letter Triangle Pattern",
    15: "Reverse Letter Triangle Pattern",
    16: "Alpha-Ramp Pattern",
    17: "Alpha-Hill Pattern",
    18: "Alpha-Triangle Pattern",
    19: "Symmetric-Void Pattern",
    20: "Symmetry Pattern",
    21: "Hollow Rectangle Pattern",
    22: "Number Pattern",
}


def main():
    extra = {}
    if os.path.exists(EXTRA):
        with open(EXTRA, encoding="utf-8") as f:
            extra = json.load(f)
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
            entry_id = f"a2z-{len(entries) + 1:04d}"
            if subtopic == "Patterns" and title.startswith("Pattern "):
                num = int(title.split()[1])
                if num in PATTERN_NAMES:
                    title = f"Pattern {num} — {PATTERN_NAMES[num]}"
            links = extra.get(entry_id, {})
            entries.append({
                "id": entry_id,
                "step": step,
                "step_name": step_name,
                "subtopic": subtopic,
                "title": title,
                "difficulty": difficulty,
                "url": url,
                "tuf_url": links.get("tuf_url"),
                "tuf_kind": links.get("tuf_kind"),
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
