"""Path helpers with explicit Windows (ntpath) semantics so they can be unit-tested on any OS."""
import os
import re
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

_DRIVE_ONLY = re.compile(r"^[A-Za-z]:$")


class PathError(ValueError):
    pass


def normalize_user_path(raw: str, pathmod=os.path) -> str:
    """Validate a folder path typed by the user. Accepts D:\\Movies, D:, d:/movies, \\\\NAS\\Share\\sub, /mnt/x."""
    path = (raw or "").strip().strip('"').strip("'").strip()
    if not path or "\x00" in path:
        raise PathError("Enter a folder path.")
    if pathmod.__name__ == "ntpath":
        path = path.replace("/", "\\")
        if _DRIVE_ONLY.match(path):
            path += "\\"
        if path.startswith("\\\\") and not path.startswith("\\\\?\\"):
            parts = [p for p in path[2:].split("\\") if p]
            if len(parts) < 2:
                raise PathError(r"Network paths need a share name, e.g. \\NAS\Media (not just \\NAS).")
        drive, _ = pathmod.splitdrive(path)
        if not drive:
            raise PathError(r"Use a full path with a drive letter or share, e.g. D:\Movies or \\NAS\Media.")
    if not pathmod.isabs(path):
        raise PathError(r"Use a full path, e.g. D:\Movies or \\NAS\Media.")
    return pathmod.normpath(path)


def parent_dir(path: str, pathmod=os.path) -> str | None:
    """Parent folder, or None at a drive root / UNC share root / filesystem root."""
    norm = pathmod.normpath(path)
    drive, rest = pathmod.splitdrive(norm)
    if rest in ("", "\\", "/"):
        return None
    parent = pathmod.dirname(norm.rstrip("\\/"))
    return parent if parent and parent != norm else None


def is_within(root_key: str, path_key: str, pathmod=os.path) -> bool:
    """Both arguments must already be normalized keys (normcase + realpath)."""
    root_key, path_key = _with_root(root_key, pathmod), _with_root(path_key, pathmod)
    try:
        return pathmod.commonpath([root_key, path_key]) == root_key
    except ValueError:  # different drives / mixed absolute+relative
        return False


def library_real_path(conn, path: str) -> str | None:
    """Resolved path if it lies inside a configured library folder, else None."""
    real = os.path.realpath(path)
    key = os.path.normcase(real)
    for lib in conn.execute("SELECT path FROM libraries"):
        if is_within(os.path.normcase(os.path.realpath(lib["path"])), key):
            return real
    return None


def _with_root(p: str, pathmod) -> str:
    """'\\\\NAS\\Share' -> '\\\\NAS\\Share\\' so share roots compare like drive roots."""
    drive, rest = pathmod.splitdrive(p)
    return p + pathmod.sep if drive and not rest else p


def is_link_or_junction(path: str) -> bool:
    """Symlinks, NTFS junctions and other reparse points are never followed by the scanner."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    # Windows: only symlinks and junctions/mount points count. Other reparse points (e.g. OneDrive cloud files) are normal.
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if not getattr(st, "st_file_attributes", 0) & reparse:
        return False
    return getattr(st, "st_reparse_tag", 0) in LINK_TAGS


LINK_TAGS = (getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C), getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003))


# An offline NAS can make os.path.isdir block for tens of seconds on Windows. Status checks therefore wait at most
# REACH_TIMEOUT_S; a path that did not answer is reported unreachable and not re-tried for REACH_RETRY_S.
REACH_TIMEOUT_S = 2.5
REACH_RETRY_S = 15
_reach_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="reach-check")
_reach_slow: dict[str, float] = {}
_reach_lock = threading.Lock()


def _dir_reachable(path: str) -> bool:
    from .network_shares import ensure_saved_connection

    # A successful reconnect already checked this same pinned IPv4 folder.
    # Hostname sources skip automatic IP reconnect and check their actual path.
    if ensure_saved_connection(path):
        return True
    return os.path.isdir(path)


def dir_reachable(path: str) -> bool:
    with _reach_lock:
        since = _reach_slow.get(path)
        if since is not None and time.monotonic() - since < REACH_RETRY_S:
            return False
    try:
        ok = _reach_pool.submit(_dir_reachable, path).result(timeout=REACH_TIMEOUT_S)
    except FutureTimeout:
        with _reach_lock:
            _reach_slow[path] = time.monotonic()
        return False
    with _reach_lock:
        _reach_slow.pop(path, None)
    return ok
