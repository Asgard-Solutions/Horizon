"""Host-only administration API: library folders, folder browser, LAN access, PIN and paired devices."""
import ipaddress
import json
import os
import platform
import socket
import stat

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import paths
from .config import APP_VERSION
from .db import get_setting, now_iso, set_setting
from .parser import is_video
from .probe import ffprobe_version, find_ffprobe
from .scanner import cleanup_orphans, path_key, scan_library
from .security import hash_pin, lan_enabled, require_host, validate_new_pin
from .winfs import list_windows_drives

router = APIRouter(prefix="/api", dependencies=[Depends(require_host)])
MAX_DIR_ENTRIES = 3000


def _library(row) -> dict:
    return {"id": row["id"], "path": row["path"], "name": row["name"], "created_at": row["created_at"],
            "last_scan_at": row["last_scan_at"],
            "last_scan_summary": json.loads(row["last_scan_summary"]) if row["last_scan_summary"] else None,
            "reachable": os.path.isdir(row["path"])}


def _counts(conn, library_id: int) -> dict:
    r = conn.execute("SELECT SUM(kind='movie') AS movies, SUM(kind='episode') AS episodes FROM media_files"
                     " WHERE library_id = ?", (library_id,)).fetchone()
    return {"movies": r["movies"] or 0, "episodes": r["episodes"] or 0}


@router.get("/libraries")
def list_libraries(request: Request):
    conn = request.state.db
    return [{**_library(r), "counts": _counts(conn, r["id"])}
            for r in conn.execute("SELECT * FROM libraries ORDER BY name")]


class LibraryIn(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    name: str | None = Field(default=None, max_length=120)
    scan: bool = True


def normalize_user_path(raw: str) -> str:
    try:
        return paths.normalize_user_path(raw)
    except paths.PathError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


UNREACHABLE_HINT = (" If this is a network share or mapped drive: check it opens in File Explorer for the same Windows user that runs"
                    r" the server (mapped drive letters are not visible to elevated/admin or service processes - use \\SERVER\Share).")


def _read_error(exc: OSError) -> str:
    if isinstance(exc, PermissionError):
        return "Access denied: the Windows account running the server cannot read this folder."
    return f"Folder cannot be read: {exc.strerror or exc}"


def _run_scan(conn, row) -> dict:
    summary = scan_library(conn, dict(row))
    conn.execute("UPDATE libraries SET last_scan_at = ?, last_scan_summary = ? WHERE id = ?",
                 (now_iso(), json.dumps(summary), row["id"]))
    conn.commit()
    return summary


@router.post("/libraries")
def add_library(body: LibraryIn, request: Request):
    conn = request.state.db
    path = normalize_user_path(body.path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Folder not found or not reachable: {path}." + UNREACHABLE_HINT)
    try:
        with os.scandir(path) as it:
            next(it, None)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=_read_error(exc))
    key = path_key(path)
    for lib in conn.execute("SELECT path, path_key FROM libraries"):
        other = lib["path_key"]
        if key == other:
            raise HTTPException(status_code=409, detail="This folder is already in the library.")
        if paths.is_within(key, other) or paths.is_within(other, key):
            raise HTTPException(status_code=409, detail=f"This folder overlaps an existing library folder: {lib['path']}")
    name = (body.name or "").strip() or os.path.basename(path.rstrip("\\/")) or path
    cur = conn.execute("INSERT INTO libraries (path, path_key, name, created_at) VALUES (?,?,?,?)",
                       (path, key, name, now_iso()))
    conn.commit()
    row = conn.execute("SELECT * FROM libraries WHERE id = ?", (cur.lastrowid,)).fetchone()
    summary = _run_scan(conn, row) if body.scan else None
    row = conn.execute("SELECT * FROM libraries WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {**_library(row), "counts": _counts(conn, row["id"]), "scan": summary}


@router.delete("/libraries/{library_id}")
def remove_library(library_id: int, request: Request):
    """Removes the folder from the catalog only. Files on disk are never touched."""
    conn = request.state.db
    cur = conn.execute("DELETE FROM libraries WHERE id = ?", (library_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Library not found")
    cleanup_orphans(conn)
    conn.commit()
    return {"ok": True}


@router.post("/libraries/{library_id}/scan")
def rescan_library(library_id: int, request: Request):
    conn = request.state.db
    row = conn.execute("SELECT * FROM libraries WHERE id = ?", (library_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Library not found")
    summary = _run_scan(conn, row)
    return {**_library(conn.execute("SELECT * FROM libraries WHERE id = ?", (library_id,)).fetchone()),
            "counts": _counts(conn, library_id), "scan": summary}


def _is_hidden(entry: os.DirEntry) -> bool:
    if entry.name.startswith(".") or entry.name.startswith("$"):
        return True
    attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attrs & (getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0) | getattr(stat, "FILE_ATTRIBUTE_SYSTEM", 0)))


@router.get("/fs/roots")
def fs_roots(request: Request):
    roots = []
    if os.name == "nt":
        for d in list_windows_drives():
            label = {"network": "Network drive", "removable": "Removable drive", "optical": "Disc drive"}.get(d["type"], "Drive")
            name = f"{label} {d['path']}" + (f" -> {d['target']}" if d["target"] else "")
            roots.append({"name": name, "path": d["path"], "type": "drive", "drive_type": d["type"], "target": d["target"]})
    else:
        roots.append({"name": "/", "path": "/", "type": "drive"})
    home = os.path.expanduser("~")
    roots.append({"name": "Home folder", "path": home, "type": "home"})
    for v in ("Videos", "Movies"):
        p = os.path.join(home, v)
        if os.path.isdir(p):
            roots.append({"name": v, "path": p, "type": "folder"})
    for lib in request.state.db.execute("SELECT name, path FROM libraries"):
        roots.append({"name": lib["name"], "path": lib["path"], "type": "library"})
    return {"roots": roots, "platform": platform.system(),
            "hint": r"Network shares: type a UNC path such as \\NAS\Media or a mapped drive letter like Z:\ ."}


@router.get("/fs/list")
def fs_list(path: str, request: Request):
    path = normalize_user_path(path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail=f"Folder not found or not reachable: {path}." + UNREACHABLE_HINT)
    dirs, videos = [], 0
    try:
        with os.scandir(path) as it:
            for i, entry in enumerate(it):
                if i > MAX_DIR_ENTRIES:
                    break
                try:
                    if entry.is_dir(follow_symlinks=False) and not _is_hidden(entry):
                        dirs.append({"name": entry.name, "path": entry.path})
                    elif entry.is_file() and is_video(entry.name):
                        videos += 1
                except OSError:
                    continue
    except OSError as exc:
        raise HTTPException(status_code=400, detail=_read_error(exc))
    parent = paths.parent_dir(path)
    return {"path": path, "parent": parent, "dirs": sorted(dirs, key=lambda d: d["name"].lower()),
            "video_files_here": videos}


def lan_addresses() -> list[str]:
    found = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass
    try:  # UDP connect sends no packets; it only selects the outbound interface.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            found.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(a for a in found if ipaddress.ip_address(a).is_private and not ipaddress.ip_address(a).is_loopback)


@router.get("/system")
def system_info(request: Request):
    cfg = request.app.state.config
    conn = request.state.db
    ffprobe = find_ffprobe(cfg.ffprobe_path)
    enabled = lan_enabled(conn)
    bind = cfg.bind_host
    port = cfg.port or request.url.port or (443 if request.url.scheme == "https" else 80)
    restart_required = bind is not None and ((enabled and bind in ("127.0.0.1", "localhost")) or
                                             (not enabled and bind not in ("127.0.0.1", "localhost")))
    return {
        "version": APP_VERSION, "platform": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(), "data_dir": str(cfg.data_dir),
        "ffprobe": {"path": ffprobe, "version": ffprobe_version(ffprobe)},
        "lan": {"enabled": enabled, "pin_configured": bool(get_setting(conn, "pin_hash")),
                "bind_host": bind, "port": port, "restart_required": restart_required,
                "addresses": [f"http://{a}:{port}" for a in lan_addresses()]},
    }


class LanIn(BaseModel):
    enabled: bool


@router.post("/settings/lan")
def set_lan(body: LanIn, request: Request):
    conn = request.state.db
    if body.enabled and not get_setting(conn, "pin_hash"):
        raise HTTPException(status_code=400, detail="Set an access PIN (8+ digits) before enabling LAN access.")
    set_setting(conn, "lan_enabled", "1" if body.enabled else "0")
    conn.commit()
    return system_info(request)


class PinIn(BaseModel):
    pin: str = Field(max_length=64)
    revoke_devices: bool = True


@router.post("/settings/pin")
def set_pin(body: PinIn, request: Request):
    error = validate_new_pin(body.pin)
    if error:
        raise HTTPException(status_code=400, detail=error)
    conn = request.state.db
    set_setting(conn, "pin_hash", hash_pin(body.pin))
    revoked = 0
    if body.revoke_devices:
        revoked = conn.execute("UPDATE devices SET revoked = 1 WHERE revoked = 0").rowcount
    conn.commit()
    return {"ok": True, "revoked_devices": revoked}


@router.get("/devices")
def list_devices(request: Request):
    return [dict(r) for r in request.state.db.execute(
        "SELECT id, name, created_at, last_seen_at, last_ip, revoked FROM devices ORDER BY revoked, created_at DESC")]


@router.delete("/devices/{device_id}")
def revoke_device(device_id: int, request: Request):
    cur = request.state.db.execute("UPDATE devices SET revoked = 1 WHERE id = ?", (device_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    request.state.db.commit()
    return {"ok": True}
