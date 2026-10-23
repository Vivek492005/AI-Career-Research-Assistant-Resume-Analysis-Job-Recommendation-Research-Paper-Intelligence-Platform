"""In-app lessons for Striver A2Z theory topics and pattern problems.

Most A2Z rows are practice problems solved on an external platform,
but theory rows (time complexity, STL, recursion theory, graph intro,
...) and the 22 pattern problems carry full lesson content inside
Study-Buddy itself (data/a2z_lessons.json): an introduction, teaching
sections with code, key points, and suggested follow-up practice.
Content is original Study-Buddy material keyed by A2Z entry id.
"""

import json
import os

LESSONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "a2z_lessons.json")

_lessons = None


def _load_lessons():
    global _lessons
    if _lessons is None:
        try:
            with open(LESSONS_PATH, encoding="utf-8") as f:
                _lessons = json.load(f)
        except FileNotFoundError:
            _lessons = {}
    return _lessons


def lesson_ids():
    """Ids of A2Z entries that have an in-app lesson."""
    return set(_load_lessons())


def get_lesson(entry_id):
    return _load_lessons().get(entry_id)


def resolve_suggested(lesson, by_id):
    """Resolve a lesson's suggested-practice items to linkable rows.

    Each item references either another A2Z entry (``a2z_id``) or a
    classic problem (``problem_id``); ``by_id`` is the merged DSA
    lookup. Items whose target no longer exists are dropped so a
    lesson never links to a dead end. Each result gains ``href``
    (in-app lesson page when the target has one, else its external
    practice link, else the classic problem page) and ``external``.
    """
    from studybuddy.dsa_practice import _load_a2z

    a2z_by_id = {e["id"]: e for e in _load_a2z()}
    have_lesson = lesson_ids()
    out = []
    for item in (lesson or {}).get("suggested", []):
        target_id = item.get("a2z_id") or item.get("problem_id")
        if not target_id:
            continue
        entry = a2z_by_id.get(target_id)
        classic = None if entry else by_id.get(target_id)
        if entry is None and classic is None:
            continue
        title = (entry or classic)["title"]
        if entry is not None and target_id in have_lesson:
            href, external = f"/dsa/a2z/{target_id}/learn", False
        elif entry is not None:
            href = entry.get("url") or entry.get("tuf_url")
            external = True
        else:
            href, external = f"/dsa/{target_id}", False
        if not href:
            continue
        out.append({"title": title, "note": item.get("note", ""),
                    "href": href, "external": external})
    return out
