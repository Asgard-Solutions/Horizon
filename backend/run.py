"""Local launcher: `python run.py`.

Binds to 127.0.0.1 unless LAN access has been explicitly enabled in Settings, in which case it binds 0.0.0.0.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mediacenter.config import load_config  # noqa: E402


def lan_setting(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT value FROM settings WHERE key = 'lan_enabled'").fetchone()
        conn.close()
        return bool(row and row[0] == "1")
    except sqlite3.Error:
        return False


def main():
    parser = argparse.ArgumentParser(description="Open Media Center - Phase 0 local server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MC_PORT", "8765")))
    args = parser.parse_args()

    cfg = load_config()
    host = "0.0.0.0" if lan_setting(cfg.db_path) else "127.0.0.1"
    os.environ["MC_BIND_HOST"] = host
    os.environ["MC_PORT"] = str(args.port)

    import uvicorn

    print(f"Open Media Center: http://127.0.0.1:{args.port}  (LAN access {'ON' if host == '0.0.0.0' else 'OFF'})")
    print(f"Data folder: {cfg.data_dir}")
    if not (cfg.frontend_dist / "index.html").is_file():
        print("WARNING: frontend/dist not found. Build the UI first (see README).")
    uvicorn.run("mediacenter.app:create_app", factory=True, host=host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
