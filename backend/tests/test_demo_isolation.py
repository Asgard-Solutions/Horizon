"""Demo content stays out of production: nothing in the app creates libraries or demo titles by itself."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_MARKERS = ("Northern Survey", "horizon_demo", "test_media", "sample_media", "make_sample_media")


def test_fresh_install_has_an_empty_library(host):
    d = host.get("/api/home").json()
    assert d["counts"] == {"movies": 0, "shows": 0, "episodes": 0, "libraries": 0}
    assert host.get("/api/libraries").json() == []


def test_app_code_never_references_demo_content():
    sources = list((ROOT / "backend" / "mediacenter").glob("*.py")) + [ROOT / "backend" / "server.py"]
    sources += [p for p in (ROOT / "frontend" / "src").rglob("*") if p.suffix in (".ts", ".tsx", ".css", ".json")]
    hits = [(p.name, m) for p in sources for m in DEMO_MARKERS if m in p.read_text(encoding="utf-8")]
    assert hits == []


def test_launch_scripts_do_not_generate_demo_media():
    scripts = [p for p in (ROOT / "scripts" / "windows").iterdir() if p.is_file() and "test" not in p.name.lower()]
    assert scripts
    for p in scripts:
        assert "make_sample_media" not in p.read_text(encoding="utf-8", errors="replace"), p.name


def test_demo_series_requires_its_own_folder():
    src = (ROOT / "scripts" / "make_sample_media.py").read_text(encoding="utf-8")
    assert "--demo-series" in src and "must be a separate folder" in src
    base = src.split("DEMO_FILES")[0]
    assert "Northern Survey - S0" not in base  # demo episodes are never part of the base sample library
