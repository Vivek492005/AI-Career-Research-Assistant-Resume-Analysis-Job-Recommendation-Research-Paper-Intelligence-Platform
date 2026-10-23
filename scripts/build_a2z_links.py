"""Build data/striver_a2z_extra.json: every A2Z row's own page on
takeUforward (its practice page or theory lesson page).

The A2Z sheet page embeds its full syllabus tree (module -> subtopic
-> row) as JSON in the page payload. Each row node carries the href
of that row's own page on takeUforward — a /practice/dsa/ page with
an in-browser judge, or a /learning/dsa/ theory page. The original
sheet extraction kept only LeetCode practice links, which left 206
rows with no destination at all; this script recovers the sheet's
own links so no row is a dead end.

Alignment is positional per module and fully verified: after dropping
the tree's per-module "Contest" nodes (contests are not sheet rows),
each module's row count and ordered titles must match the dataset
exactly (a single in-place title rename is tolerated and reported).
Re-running this script re-fetches and re-verifies everything.
"""
import difflib
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(ROOT, "data", "striver_a2z.json")
OUT = os.path.join(ROOT, "data", "striver_a2z_extra.json")
SHEET_URL = "https://takeuforward.org/prep-hub/strivers-a2z-dsa-sheet"
BASE = "https://takeuforward.org"


def fetch_tree():
    req = urllib.request.Request(SHEET_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    i = html.find("syllabusOutline")
    assert i >= 0, "syllabusOutline not found - page structure changed"
    seg = html[i:i + 900000]
    seg = seg.replace("\\u0026", "&").replace('\\"', '"').replace("\\\\", "\\")
    j = seg.find('"nodes":')
    start = seg.find("[", j)
    depth = 0
    for k in range(start, len(seg)):
        if seg[k] == "[":
            depth += 1
        elif seg[k] == "]":
            depth -= 1
            if depth == 0:
                return json.loads(seg[start:k + 1])
    raise AssertionError("nodes array not closed")


def problem_rows(module_node):
    out = []

    def walk(node):
        if node.get("kind") == "problem":
            href = node.get("href") or ""
            if "/contest/" not in href:  # contests are not sheet rows
                out.append(node)
        for child in node.get("children") or []:
            walk(child)

    walk(module_node)
    return out


def norm(text):
    return " ".join((text or "").lower().split()).strip(" |")


def main():
    with open(DATASET, encoding="utf-8") as f:
        entries = json.load(f)
    tree = fetch_tree()
    assert len(tree) == 20, f"expected 20 modules, got {len(tree)}"

    extra = {}
    warnings = []
    pos = 0
    for module in tree:
        rows = problem_rows(module)
        ours = entries[pos:pos + len(rows)]
        assert len(ours) == len(rows), (
            f"module {module['label']!r}: tree has {len(rows)} rows, "
            f"dataset slice has {len(ours)}")
        matcher = difflib.SequenceMatcher(
            None, [norm(e["title"]) for e in ours],
            [norm(n["label"]) for n in rows], autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            assert tag == "equal" or (i2 - i1) == (j2 - j1) == 1, (
                f"module {module['label']!r}: structural drift {tag}: "
                f"{[e['title'] for e in ours[i1:i2]]} vs "
                f"{[n['label'] for n in rows[j1:j2]]}")
            if tag != "equal":
                warnings.append(
                    f"title drift in {module['label']!r}: dataset "
                    f"{ours[i1]['title']!r} vs sheet {rows[j1]['label']!r} "
                    "(aligned positionally)")
        for entry, node in zip(ours, rows):
            href = (node.get("href") or "").split("?")[0]
            assert href.startswith("/practice/") or href.startswith("/learning/"), \
                f"unexpected href for {entry['title']!r}: {href!r}"
            extra[entry["id"]] = {
                "tuf_url": BASE + href,
                "tuf_kind": "practice" if href.startswith("/practice/") else "learning",
            }
        pos += len(rows)
    assert pos == len(entries) == 495, f"aligned {pos} of {len(entries)} rows"

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(extra, f, indent=1, ensure_ascii=False)
    kinds = {}
    for v in extra.values():
        kinds[v["tuf_kind"]] = kinds.get(v["tuf_kind"], 0) + 1
    print(f"wrote {OUT}: {len(extra)} rows linked ({kinds})")
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
