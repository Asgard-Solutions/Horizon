"""Create a portable zip of the whole project (no Emergent tooling needed).

Usage:  python scripts/export_project.py [--no-dist] [--out DIR]
Excludes local data, secrets (.env), virtualenvs, node_modules and generated sample media.
Writes a SHA-256 manifest next to the zip.
"""
import argparse
import fnmatch
import hashlib
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "data", "export",
                "sample_media", "test_reports", ".emergent", "memory", ".ruff_cache", ".mypy_cache", ".vite"}
EXCLUDE_FILES = {".env", "*.pyc", "*.sqlite3", "*.sqlite3-*", "test_result.md", ".DS_Store", "test-results-*.xml",
                 "yarn-error.log"}
EXCLUDE_TOP = {"tests"}  # empty template folder of the development environment


def included(rel: Path, with_dist: bool) -> bool:
    parts = rel.parts
    if len(parts) > 1 and parts[0] in EXCLUDE_TOP:
        return False
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return False
    if not with_dist and parts[:2] == ("frontend", "dist"):
        return False
    return not any(fnmatch.fnmatch(parts[-1], pat) for pat in EXCLUDE_FILES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-dist", action="store_true", help="do not include the prebuilt frontend/dist")
    ap.add_argument("--out", default=str(ROOT / "export"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    zip_path = out_dir / f"open-media-center-phase0.5-{stamp}.zip"
    manifest = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
            for name in sorted(filenames):
                full = Path(dirpath) / name
                rel = full.relative_to(ROOT)
                if full == zip_path or not included(rel, not args.no_dist):
                    continue
                data = full.read_bytes()
                zf.writestr(f"open-media-center/{rel.as_posix()}", data)
                manifest.append(f"{hashlib.sha256(data).hexdigest()}  {rel.as_posix()}")
    (out_dir / f"{zip_path.stem}.sha256.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Wrote {zip_path} ({len(manifest)} files, {zip_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
