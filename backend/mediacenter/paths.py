"""Path helpers with explicit Windows (ntpath) semantics so they can be unit-tested on any OS."""
import os
import re
import stat

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
