"""#6: scripts/check_lang.py — every full-page template declares lang."""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_lang.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_lang", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_repo_templates_all_declare_lang():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK" in proc.stdout


def test_flags_full_page_without_lang(tmp_path):
    mod = _load_module()
    (tmp_path / "page.html").write_text(
        "<!DOCTYPE html>\n<html>\n<body>x</body>\n</html>\n")
    (tmp_path / "ok.html").write_text(
        "<!DOCTYPE html>\n<html lang=\"en\">\n<body>x</body>\n</html>\n")
    assert mod.find_missing_lang(tmp_path) == ["page.html"]


def test_partials_and_fragments_are_skipped(tmp_path):
    mod = _load_module()
    (tmp_path / "_partial.html").write_text("<html>\n<body>x</body>\n")
    (tmp_path / "fragment.html").write_text("<div>no html tag</div>\n")
    sub = tmp_path / "partials"
    sub.mkdir()
    (sub / "bit.html").write_text("<html>\n<body>x</body>\n")
    assert mod.find_missing_lang(tmp_path) == []
