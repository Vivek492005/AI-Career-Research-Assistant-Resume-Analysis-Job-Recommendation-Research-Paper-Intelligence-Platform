#!/usr/bin/env python3
"""HTML lang attribute check (#6).

Every full-page template must declare the document language on its
<html> tag (WCAG 3.1.1 — screen readers need it to pick the right
speech synthesis). Fragment templates (partials, files starting with
"_") render inside another page's <html> element and are skipped, as
are templates with no <html> tag at all.

Usage:
    python scripts/check_lang.py [templates_dir]

Exit code 0 when every full-page template declares lang, 1 otherwise.
Standard library only, so CI can run it with the system Python.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_HTML_TAG = re.compile(r"<html\b[^>]*>", re.IGNORECASE)
_LANG_ATTR = re.compile(r"""\blang\s*=\s*["'][^"']+["']""", re.IGNORECASE)


def is_full_page(path: Path, text: str) -> bool:
    """A template is a full page when it owns the <html> element."""
    if path.name.startswith("_") or "partials" in path.parts:
        return False
    return bool(_HTML_TAG.search(text))


def find_missing_lang(templates_dir: Path) -> list[str]:
    """Relative paths of full-page templates whose <html> lacks lang."""
    missing = []
    for path in sorted(templates_dir.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not is_full_page(path, text):
            continue
        tag = _HTML_TAG.search(text).group(0)
        if not _LANG_ATTR.search(tag):
            missing.append(str(path.relative_to(templates_dir)))
    return missing


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(__file__).resolve().parent.parent
    templates_dir = Path(argv[0]) if argv else root / "templates"
    if not templates_dir.is_dir():
        print(f"check_lang: no templates directory at {templates_dir}")
        return 1
    missing = find_missing_lang(templates_dir)
    total = sum(
        1 for p in templates_dir.rglob("*.html")
        if is_full_page(p, p.read_text(encoding="utf-8", errors="replace"))
    )
    if missing:
        print(f"check_lang: {len(missing)} full-page template(s) missing "
              "a lang attribute on <html>:")
        for rel in missing:
            print(f"  - {rel}")
        return 1
    print(f"check_lang: OK — all {total} full-page templates declare lang.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
