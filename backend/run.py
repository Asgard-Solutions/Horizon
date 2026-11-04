"""Local launcher.

    python run.py                 start the server (127.0.0.1, or 0.0.0.0 only if LAN access is enabled in Settings)
    python run.py --check         check dependencies, initialise the SQLite database, report, exit (0 = OK)
    python run.py --open-browser  start and open the UI in the default browser
"""
import argparse
import importlib
from importlib import metadata
import os
import socket
import sqlite3
import sys
import threading
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mediacenter.config import BACKEND_DIR, load_config, load_env_file  # noqa: E402

MIN_PYTHON = (3, 11)
REQUIRED = ["fastapi", "starlette", "uvicorn", "pydantic", "pydantic_core", "anyio", "h11", "click"]


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


def _pinned_versions() -> dict[str, str]:
    pins = {}
    for line in (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if "==" in line:
            name, ver = line.strip().split("==", 1)
            pins[name.lower().replace("-", "_")] = ver
    return pins


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def run_checks(port: int) -> bool:
    ok = True

    def report(status: str, label: str, detail: str = ""):
        nonlocal ok
        if status == "FAIL":
            ok = False
        print(f"  [{status:4}] {label}{(' - ' + detail) if detail else ''}")

    print("REELHEIM Media Center - startup checks")
    v = sys.version_info
    report("OK" if v[:2] >= MIN_PYTHON else "FAIL", f"Python {v.major}.{v.minor}.{v.micro}",
           "" if v[:2] >= MIN_PYTHON else "Python 3.11 or newer is required")

    pins = _pinned_versions()
    for mod in REQUIRED:
        try:
            importlib.import_module(mod)
            try:
                ver = metadata.version(mod)
            except metadata.PackageNotFoundError:
                ver = ""
            pin = pins.get(mod)
            if pin and ver and str(ver) != pin:
                report("WARN", f"{mod} {ver}", f"requirements.txt pins {pin}")
            else:
                report("OK", f"{mod} {ver}".strip())
        except ImportError:
            report("FAIL", mod, "not installed - run scripts\\windows\\setup.bat")

    cfg = load_config()
    try:
        probe = cfg.data_dir / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report("OK", f"Data folder writable: {cfg.data_dir}")
    except OSError as exc:
        report("FAIL", f"Data folder not writable: {cfg.data_dir}", f"{exc}. Set MC_DATA_DIR to a folder you own.")

    try:
        from mediacenter.db import init_db

        init_db(cfg.db_path)
        conn = sqlite3.connect(cfg.db_path)
        result = conn.execute("PRAGMA quick_check").fetchone()[0]
        libs = conn.execute("SELECT COUNT(*) FROM libraries").fetchone()[0]
        conn.close()
        report("OK" if result == "ok" else "FAIL", f"SQLite database ready: {cfg.db_path}",
               f"SQLite {sqlite3.sqlite_version}, {libs} library folder(s)" if result == "ok" else result)
    except Exception as exc:  # noqa: BLE001 - report any DB problem
        report("FAIL", "SQLite database", str(exc))

    index = cfg.frontend_dist / "index.html"
    report("OK" if index.is_file() else "FAIL", f"Web UI build: {cfg.frontend_dist}",
           "" if index.is_file() else "missing - run scripts\\windows\\setup.bat -BuildUI (needs Node.js) or use the release zip")

    from mediacenter.probe import ffprobe_version, find_ffprobe

    ffprobe = find_ffprobe(cfg.ffprobe_path)
    report("OK" if ffprobe else "WARN", f"FFprobe: {ffprobe or 'not found'}",
           (ffprobe_version(ffprobe) or "") if ffprobe else "optional; codec inspection disabled")

    if cfg.admin_networks or cfg.allowed_hosts:
        report("WARN", "MC_ADMIN_NETWORKS / MC_ALLOWED_HOSTS are set", "development-only; they widen host-admin trust - remove them")

    lan = lan_setting(cfg.db_path)
    host = "0.0.0.0" if lan else "127.0.0.1"
    report("OK" if port_free(host, port) else "FAIL", f"Port {port} free on {host}",
           "" if port_free(host, port) else "another program (or a running copy of this server) uses it; set MC_PORT")
    report("OK", f"LAN access {'ON (binds 0.0.0.0)' if lan else 'OFF (binds 127.0.0.1 only)'}")
    print("All required checks passed." if ok else "Some required checks FAILED - see above.")
    return ok


def main():
    load_env_file(BACKEND_DIR / ".env")
    parser = argparse.ArgumentParser(description="REELHEIM Media Center - Phase 0 local server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MC_PORT") or "8765"))
    parser.add_argument("--check", action="store_true", help="run startup checks, initialise the database and exit")
    parser.add_argument("--open-browser", action="store_true", help="open the UI in the default browser after start")
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if run_checks(args.port) else 1)

    cfg = load_config()
    host = "0.0.0.0" if lan_setting(cfg.db_path) else "127.0.0.1"
    os.environ["MC_BIND_HOST"] = host
    os.environ["MC_PORT"] = str(args.port)

    import uvicorn

    url = f"http://127.0.0.1:{args.port}/"
    print(f"REELHEIM Media Center: {url}  (LAN access {'ON' if host == '0.0.0.0' else 'OFF'})")
    print(f"Data folder: {cfg.data_dir}")
    print("Press Ctrl+C or close this window to stop the server.")
    if not (cfg.frontend_dist / "index.html").is_file():
        print("WARNING: frontend/dist not found. Build the UI first (see README).")
    if args.open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":  # exclusive bind: no other process can hijack the port (Windows SO_REUSEADDR semantics)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, args.port))
    except OSError as exc:
        sys.exit(f"Cannot use port {args.port} on {host}: {exc}. Another program may be using it; set MC_PORT.")
    config = uvicorn.Config("mediacenter.app:create_app", factory=True, host=host, port=args.port, log_level="info")
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
