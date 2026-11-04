"""Structured editing of existing local NFOs. No catalog, network or artwork IO.

Unknown XML survives DOM serialization (formatting/encoding may change). Windows
directory handles deny write/delete sharing while held; POSIX walks use no-follow
directory descriptors. Revision checks detect external edits, but POSIX has no
portable compare-and-swap rename against an uncooperative external writer. On
Windows file read handles must close immediately before replacement; directory
guards remain held. External replacement in that final interval cannot be
excluded with the portable atomic-replace API.
"""
from contextlib import ExitStack, contextmanager
from datetime import date
import errno
import hashlib
import math
import os
import re
import stat
import threading
import uuid
import weakref
from xml.dom import Node, minidom
from xml.parsers import expat
from typing import Literal


MAX_BYTES = 1024 * 1024
_ROOTS = {"movie", "tvshow", "episodedetails"}
_STRINGS = {"title": 500, "sort_title": 500, "plot": 50000, "tagline": 500,
            "premiered": 10, "set": 120}
_TAGS = {"sort_title": "sorttitle", "genres": "genre", "cast": "actor"}
_ID_TAGS = {"tmdb": "tmdbid", "tvdb": "tvdbid", "imdb": "imdbid"}
_locks = weakref.WeakValueDictionary()
_locks_guard = threading.Lock()


class NfoError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _invalid(message):
    raise NfoError(message, 422)


def _conflict():
    raise NfoError("The NFO changed in another application. Reload it before saving.", 409)


@contextmanager
def _io_errors():
    try:
        yield
    except NfoError:
        raise
    except OSError as error:
        if getattr(error, "winerror", 0) == 206:
            raise NfoError("The NFO or recovery filename is too long for this filesystem.", 422) from error
        if getattr(error, "winerror", 0) in (21, 53, 54, 55, 59, 64, 67, 121, 1201, 1231, 1232, 2250):
            raise NfoError("The NFO drive/share is offline or unavailable. Reconnect it before trying again.", 503) from error
        if error.errno in (errno.ENOENT, errno.ENOTDIR):
            raise NfoError("The existing NFO or its folder is missing. Check the library location.", 404) from error
        if error.errno in (errno.EACCES, errno.EPERM, errno.EROFS) or getattr(error, "winerror", 0) in (5, 32, 33):
            raise NfoError("Cannot access or write the NFO. Check read-only permissions and close other editors.", 403) from error
        if error.errno == errno.ELOOP:
            raise NfoError("Symbolic links and reparse points are not supported for NFO editing.", 422) from error
        raise NfoError("NFO storage is unavailable or the write failed. Reconnect the drive/share and check free space and permissions.", 503) from error


def _path(path, roots):
    if not isinstance(path, str) or not path or "\0" in path or not os.path.isabs(path):
        _invalid("An absolute path to an existing NFO is required.")
    # No Windows device namespaces, alternate data streams, or ambiguous Win32 names.
    if os.name == "nt":
        if path.startswith(("\\\\?\\", "\\\\.\\")):
            _invalid("Device namespace paths are not supported.")
        _, tail = os.path.splitdrive(path)
        if any(":" in part or part.endswith((".", " ")) for part in re.split(r"[\\/]", tail) if part):
            _invalid("Ambiguous Windows paths and alternate streams are not supported.")
    target = os.path.abspath(path)
    if not isinstance(roots, list) or not roots:
        _invalid("The NFO must be under a configured library root.")
    allowed = False
    for root in roots:
        if not isinstance(root, str) or not root or "\0" in root or not os.path.isabs(root):
            continue
        try:
            key = os.path.normcase(os.path.abspath(root))
            candidate = os.path.normcase(target)
            if os.path.commonpath([key, candidate]) == key:
                allowed = True
                break
        except ValueError:
            continue
    if not allowed:
        _invalid("The NFO is outside the configured library roots.")
    return target


def _safe_stat(info, directory=False):
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        _invalid("Symbolic links, junctions and reparse points are not supported for NFO editing.")
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            _invalid("The NFO parent must be a regular directory.")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _invalid("The NFO must be a regular file with no hard links.")


def _identity(info):
    return info.st_dev, info.st_ino


def _win_handle(path, directory, *, removable=False):
    """Hold directories without write/delete sharing; file reads deny writes.

    OPEN_REPARSE_POINT inspects the entry itself. Ancestors are already pinned
    when opening the next entry, so a path traversal cannot follow a swapped
    junction. Windows/SMB must honor normal CreateFile sharing semantics.
    """
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    access = 0x80 if directory else 0x80000000  # READ_ATTRIBUTES / GENERIC_READ
    if removable:
        access |= 0x10000  # DELETE, required for a rename through this handle.
    sharing = 1 if directory or removable else 1 | 4  # removal denies WRITE and DELETE sharing.
    handle = create(path, access, sharing, None, 3, 0x00200000 | 0x02000000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    try:
        # Inspect the opened handle, not a path that another process can replace.
        class Info(ctypes.Structure):
            _fields_ = [("attributes", wintypes.DWORD), ("creation", wintypes.FILETIME),
                        ("access", wintypes.FILETIME), ("write", wintypes.FILETIME),
                        ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                        ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                        ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

        query = kernel.GetFileInformationByHandle
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
        query.restype = wintypes.BOOL
        info = Info()
        if not query(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.attributes & 0x400:
            _invalid("Symbolic links, junctions and reparse points are not supported for NFO editing.")
        if bool(info.attributes & 0x10) != directory:
            _invalid("The NFO must be a regular file inside a directory.")
        if not directory and info.links != 1:
            _invalid("Hardlinked NFO files cannot be edited.")
        if directory:
            return handle, lambda: close(handle)
        import msvcrt
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        return fd, lambda: os.close(fd)
    except BaseException:
        close(handle)
        raise


def _win_extended_path(path):
    if path.startswith("\\\\?\\"):
        return path
    return "\\\\?\\UNC\\" + path[2:] if path.startswith("\\\\") else "\\\\?\\" + path


def _win_archive_handle(fd, destination):
    """Rename the verified, still-open file; never reopen its pathname."""
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class RenameInfo(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD), ("FileName", wintypes.WCHAR * 1)]

    # This path is generated inside the already guarded parent, never supplied
    # by a request. Win32 rename path conversion otherwise retains MAX_PATH.
    encoded = _win_extended_path(destination).encode("utf-16-le")
    # The Win32 path conversion also needs a terminating WCHAR, although the
    # FileNameLength field itself excludes that terminator.
    size = max(ctypes.sizeof(RenameInfo), RenameInfo.FileName.offset + len(encoded) + 2)
    buffer = ctypes.create_string_buffer(size)
    info = RenameInfo.from_buffer(buffer)
    info.Flags = 0  # FileRenameInfo ReplaceIfExists=FALSE: no prior backup can be overwritten.
    info.FileNameLength = len(encoded)
    ctypes.memmove(ctypes.addressof(buffer) + RenameInfo.FileName.offset, encoded, len(encoded))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    rename = kernel.SetFileInformationByHandle
    rename.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    rename.restype = wintypes.BOOL
    if not rename(msvcrt.get_osfhandle(fd), 3, buffer, size):
        raise ctypes.WinError(ctypes.get_last_error())


def _posix_archive_atomic(directory_fd, source, destination):
    """Linux atomic no-replace rename, with no link/unlink fallback."""
    import ctypes
    import sys
    if not sys.platform.startswith("linux"):
        raise NfoError("Safe NFO removal is unavailable on this host platform.", 503)
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise NfoError("Safe NFO removal requires renameat2 support on this host.", 503)
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(directory_fd, os.fsencode(source), directory_fd, os.fsencode(destination), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def _win_preserve_security(source, replacement):
    """Copy and verify owner/group/DACL, including protected inheritance state.

    Do this on the owned temp, never on the original. Do not use ReplaceFileW:
    its documented 1176/1177 failures can remove/rename the original. There is
    deliberately no fallback if the share cannot preserve Windows security.
    SACLs (audit policy), named streams and extended attributes are not copied.
    """
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("advapi32", use_last_error=True)
    pointer = ctypes.c_void_p
    get = api.GetNamedSecurityInfoW
    get.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD] + [ctypes.POINTER(pointer)] * 5
    get.restype = wintypes.DWORD
    set_info = api.SetNamedSecurityInfoW
    set_info.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD] + [pointer] * 4
    set_info.restype = wintypes.DWORD
    control = api.GetSecurityDescriptorControl
    control.argtypes = [pointer, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD)]
    control.restype = wintypes.BOOL
    equal_sid = api.EqualSid
    equal_sid.argtypes = [pointer, pointer]
    equal_sid.restype = wintypes.BOOL
    free = ctypes.WinDLL("kernel32").LocalFree
    free.argtypes = [pointer]
    free.restype = pointer

    def failure(code=None):
        raise NfoError("Cannot preserve Windows owner/group/ACL security on this drive/share. "
                       "Check permissions or save using the application that created the NFO"
                       + (f" (Windows error {code})." if code else "."), 503)

    @contextmanager
    def security(path):
        owner, group, dacl, descriptor = pointer(), pointer(), pointer(), pointer()
        code = get(path, 1, 7, ctypes.byref(owner), ctypes.byref(group), ctypes.byref(dacl),
                   None, ctypes.byref(descriptor))
        if code:
            failure(code)
        try:
            flags, version = wintypes.WORD(), wintypes.DWORD()
            if not control(descriptor, ctypes.byref(flags), ctypes.byref(version)):
                failure(ctypes.get_last_error())
            yield owner, group, dacl, bool(flags.value & 0x1000)
        finally:
            free(descriptor)

    def acl_bytes(acl):
        # ACL header's AclSize includes all ACEs; preserve their order and flags.
        if not acl:
            return None
        length = ctypes.c_ushort.from_address(acl.value + 2).value
        return ctypes.string_at(acl, length)

    def same_sid(left, right):
        return bool(equal_sid(left, right)) if left and right else not left and not right

    with security(source) as original:
        owner, group, dacl, protected = original
        code = set_info(replacement, 1, 7 | (0x80000000 if protected else 0x20000000),
                        owner, group, dacl, None)
        if code:
            failure(code)
        with security(replacement) as copied:
            if (not same_sid(owner, copied[0]) or not same_sid(group, copied[1])
                    or acl_bytes(dacl) != acl_bytes(copied[2]) or protected != copied[3]):
                failure()


class _Guard:
    def __init__(self, path):
        self.path = path
        self.parent, self.name = os.path.split(path)
        self.stack = ExitStack()
        self.files = ExitStack()
        self.stack.callback(self.files.close)
        self.parents = []
        self.dir_fd = None
        self.removal_fd = None

    def __enter__(self):
        try:
            drive, rest = os.path.splitdrive(self.parent)
            anchor = drive + os.path.sep
            parts = rest.strip(os.path.sep).split(os.path.sep) if rest.strip(os.path.sep) else []
            current = anchor
            if os.name == "nt":
                handle, close = _win_handle(current, True)
                self.stack.callback(close)
            else:
                self.dir_fd = os.open(anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                self.stack.callback(os.close, self.dir_fd)
            self.parents.append((current, os.lstat(current)))
            for part in parts:
                current = os.path.join(current, part)
                if os.name == "nt":
                    handle, close = _win_handle(current, True)
                    self.stack.callback(close)
                else:
                    entry = os.stat(part, dir_fd=self.dir_fd, follow_symlinks=False)
                    _safe_stat(entry, directory=True)
                    descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.dir_fd)
                    self.stack.callback(os.close, descriptor)
                    self.dir_fd = descriptor
                info = os.lstat(current) if os.name == "nt" else os.fstat(self.dir_fd)
                _safe_stat(info, directory=True)
                self.parents.append((current, info))
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def verify(self):
        for path, previous in self.parents:
            current = os.lstat(path)
            _safe_stat(current, directory=True)
            if _identity(current) != _identity(previous):
                _conflict()

    def read(self, *, removable=False):
        if os.name == "nt":
            fd, close = _win_handle(self.path, False, removable=True) if removable else _win_handle(self.path, False)
            self.files.callback(close)
            if removable:
                self.removal_fd = fd
        else:
            fd = os.open(self.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.dir_fd)
            self.stack.callback(os.close, fd)
        before = os.fstat(fd)
        _safe_stat(before)
        if not self.name.lower().endswith(".nfo"):
            _invalid("Only existing .nfo files can be edited.")
        if before.st_size > MAX_BYTES:
            _invalid("The NFO is larger than the 1 MiB editing limit.")
        chunks, length = [], 0
        while length <= MAX_BYTES:
            chunk = os.read(fd, min(65536, MAX_BYTES + 1 - length))
            if not chunk:
                break
            chunks.append(chunk)
            length += len(chunk)
        if length > MAX_BYTES:
            _invalid("The NFO is larger than the 1 MiB editing limit.")
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            _conflict()
        self.verify()
        return b"".join(chunks), after

    def create(self, name, mode):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        if os.name == "nt":
            return os.open(os.path.join(self.parent, name), flags, mode)
        return os.open(name, flags | os.O_NOFOLLOW, mode, dir_fd=self.dir_fd)

    def replace(self, name):
        if os.name == "nt":
            # MoveFileEx (os.replace) needs the destination's read handles closed.
            # Keep all parent guards held through this last, atomic operation.
            self.files.close()
            os.replace(os.path.join(self.parent, name), self.path)
        else:
            os.replace(name, self.name, src_dir_fd=self.dir_fd, dst_dir_fd=self.dir_fd)

    def archive(self, name, info):
        """Retain the original inode/security under a distinct, non-NFO name."""
        if os.name == "nt":
            if self.removal_fd is None or _identity(os.fstat(self.removal_fd)) != _identity(info):
                _conflict()
            _win_archive_handle(self.removal_fd, os.path.join(self.parent, name))
        else:
            # A link/check/unlink sequence could permanently delete a replacement.
            _posix_archive_atomic(self.dir_fd, self.name, name)
            backup = os.stat(name, dir_fd=self.dir_fd, follow_symlinks=False)
            if (_identity(backup), backup.st_size, backup.st_mtime_ns) != (_identity(info), info.st_size, info.st_mtime_ns):
                raise NfoError("The NFO changed during removal. Its current file was retained at "
                               + os.path.join(self.parent, name) + ". Restore that backup before retrying.", 409)

    def remove_temp(self, name, owned):
        path = os.path.join(self.parent, name) if os.name == "nt" else name
        current = os.stat(path, follow_symlinks=False, **({} if os.name == "nt" else {"dir_fd": self.dir_fd}))
        # Do not delete a different entry if an external process reused our name.
        def snapshot(info):
            # Windows may finalize LastWriteTime only when the final write handle
            # closes; creation time remains stable across that close.
            stamp = getattr(info, "st_birthtime_ns", info.st_ctime_ns) if os.name == "nt" else info.st_ctime_ns
            return _identity(info), info.st_size, stamp

        if snapshot(current) != snapshot(owned):
            return
        if os.name == "nt":
            os.unlink(path)
        else:
            os.unlink(name, dir_fd=self.dir_fd)


def _parse(content, expected_root):
    if not isinstance(expected_root, str) or expected_root not in _ROOTS:
        _invalid("Unsupported NFO root type.")
    # Kodi combination NFOs append HTTP(S) scraper URLs after their XML. Keep
    # those bytes without following the links; the preceding XML still passes
    # every DTD/entity/depth/root check below. Arbitrary trailing data is rejected.
    boundary = content.rfind(b">") + 1
    trailer = content[boundary:]
    combined = bool(re.fullmatch(rb"\s*https?://[^\s<>]+(?:\s+https?://[^\s<>]+)*\s*", trailer))
    xml = content[:boundary] if combined else content
    parser = expat.ParserCreate()

    def reject(*args):
        _invalid("DTD and entity declarations are not supported in NFO files.")

    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    depth = 0

    def start(*args):
        nonlocal depth
        depth += 1
        if depth > 128:
            _invalid("The NFO XML nesting is too deep to edit safely (maximum 128).")

    def end(*args):
        nonlocal depth
        depth -= 1

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    try:
        parser.Parse(xml, True)
        document = minidom.parseString(xml)
    except (expat.ExpatError, ValueError) as error:
        if isinstance(error, NfoError):
            raise
        raise NfoError("The NFO is not valid XML. Repair it in the application that created it.", 422) from error
    if document.documentElement.tagName != expected_root:
        _invalid(f"Expected a {expected_root} NFO root.")
    document.nfo_trailer = trailer if combined else b""
    return document


def _children(node, tag):
    return [child for child in node.childNodes if child.nodeType == Node.ELEMENT_NODE and child.tagName == tag]


def _text(node):
    return "".join(child.data for child in node.childNodes if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


def _value(node, tag):
    children = _children(node, tag)
    return _text(children[0]) if children else ""


def _number(value, integer=False):
    try:
        result = int(value) if integer else float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _ratings(root):
    return [rating for container in _children(root, "ratings") for rating in _children(container, "rating")]


def _primary_rating(root):
    ratings = _ratings(root)
    return next((r for r in ratings if r.getAttribute("default").lower() in ("true", "1")), ratings[0] if ratings else None)


def _fields(root):
    values = {key: _value(root, _TAGS.get(key, key)) for key in ("title", "sort_title", "plot", "tagline", "premiered")}
    if not values["premiered"]:
        values["premiered"] = _value(root, "aired" if root.tagName == "episodedetails" else "releasedate")
    year = _number(_value(root, "year"), True)
    if year is None and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", values["premiered"]):
        year = int(values["premiered"][:4])
    values["year"] = year if year is not None and 1800 <= year <= 2200 else None
    values["genres"] = [_text(node) for node in _children(root, "genre")]
    values["cast"] = [{"name": _value(node, "name"), "role": _value(node, "role")} for node in _children(root, "actor")]
    rating = _primary_rating(root)
    if rating is not None:
        value = _number(_value(rating, "value"))
        maximum = _number(rating.getAttribute("max")) or 10
        number = value * 10 / maximum if value is not None and maximum > 0 else None
    else:
        number = _number(_value(root, "rating"))
    values["rating"] = number if number is not None and 0 <= number <= 10 else None
    ids = {provider: _value(root, tag) for provider, tag in _ID_TAGS.items() if _value(root, tag)}
    for node in _children(root, "uniqueid"):
        provider = node.getAttribute("type").lower()
        if provider in _ID_TAGS:
            ids[provider] = _text(node)
    # Kodi's legacy <id> normally contains the IMDb ID.
    if "imdb" not in ids and re.fullmatch(r"tt[0-9]+", _value(root, "id")):
        ids["imdb"] = _value(root, "id")
    values["ids"] = ids
    if root.tagName == "movie":
        sets = _children(root, "set")
        values["set"] = (_value(sets[0], "name") if _children(sets[0], "name") else _text(sets[0])) if sets else ""
    return values


def parse_fields(content: bytes, expected_root: str) -> dict:
    """Shared read-only projection keeps the catalog and editor's Kodi field interpretation identical."""
    return _fields(_parse(content, expected_root).documentElement)


def _string(value, limit, label):
    if not isinstance(value, str) or len(value) > limit:
        _invalid(f"{label} must be text of at most {limit} characters.")
    if any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        _invalid(f"{label} contains characters XML cannot store.")


def _validate(fields, old):
    if not isinstance(fields, dict) or set(fields) - set(old):
        _invalid("Unknown or unsupported editable NFO fields.")
    if "title" not in fields:
        _invalid("A nonblank title is required.")
    result = {**old, **fields}
    for key, limit in _STRINGS.items():
        if key in result:
            _string(result[key], limit, key)
    if not result["title"].strip():
        _invalid("A nonblank title is required.")
    year = result["year"]
    if year is not None and (type(year) is not int or not 1800 <= year <= 2200):
        _invalid("Year must be an integer between 1800 and 2200, or null.")
    premiered = result["premiered"]
    if premiered:
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", premiered):
                raise ValueError()
            parsed = date.fromisoformat(premiered)
        except ValueError:
            _invalid("Premiered must be a real date in YYYY-MM-DD format, or empty.")
        if year is not None and parsed.year != year:
            _invalid("Year and premiered date must agree.")
    for key, count in (("genres", 12), ("cast", 30)):
        if not isinstance(result[key], list) or len(result[key]) > count:
            _invalid(f"{key} must be a list with at most {count} entries.")
    for genre in result["genres"]:
        _string(genre, 60, "Genre")
    for actor in result["cast"]:
        if not isinstance(actor, dict) or set(actor) != {"name", "role"}:
            _invalid("Each cast member must contain only name and role.")
        for value in actor.values():
            _string(value, 200, "Cast name/role")
    rating = result["rating"]
    if rating is not None and (type(rating) not in (int, float) or not 0 <= rating <= 10 or not math.isfinite(rating)):
        _invalid("Rating must be a finite number from 0 to 10, or null.")
    ids = result["ids"]
    if not isinstance(ids, dict) or set(ids) - set(_ID_TAGS):
        _invalid("IDs support only tmdb, tvdb and imdb.")
    for provider, value in ids.items():
        if not isinstance(value, str) or not re.fullmatch(r"tt[0-9]+" if provider == "imdb" else r"[0-9]+", value):
            _invalid("TMDB/TVDB IDs must be digits; IMDb IDs must be tt followed by digits.")
        _string(value, MAX_BYTES, "ID")
    return result


def _set_text(node, value):
    # Retain attributes, comments, and unknown nested elements.
    for child in list(node.childNodes):
        if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
            node.removeChild(child)
    if value != "":
        node.insertBefore(node.ownerDocument.createTextNode(str(value)), node.firstChild)


def _new(parent, tag):
    node = parent.ownerDocument.createElement(tag)
    parent.appendChild(node)
    return node


def _scalar(parent, tag, value):
    nodes = _children(parent, tag)
    # Empty nodes retain any uneditable attributes or nested XML.
    for node in nodes or [_new(parent, tag)]:
        _set_text(node, "" if value is None else value)


def _apply(root, old, values):
    for key, value in values.items():
        if value == old[key]:
            continue
        if key in ("genres", "cast"):
            nodes = _children(root, _TAGS[key])
            for index, entry in enumerate(value):
                node = nodes[index] if index < len(nodes) else _new(root, _TAGS[key])
                if key == "genres":
                    _set_text(node, entry)
                else:
                    _scalar(node, "name", entry["name"])
                    _scalar(node, "role", entry["role"])
            for node in nodes[len(value):]:
                root.removeChild(node)
        elif key == "ids":
            for provider, tag in _ID_TAGS.items():
                if value.get(provider) == old[key].get(provider):
                    continue
                matching = [node for node in _children(root, "uniqueid") if node.getAttribute("type").lower() == provider]
                if provider in value and not matching:
                    node = _new(root, "uniqueid")
                    node.setAttribute("type", provider)
                    matching = [node]
                for node in matching:
                    if provider in value:
                        _set_text(node, value[provider])
                    else:
                        root.removeChild(node)
                if _children(root, tag):
                    _scalar(root, tag, value.get(provider, ""))
                if provider == "imdb" and re.fullmatch(r"tt[0-9]+", _value(root, "id")):
                    _scalar(root, "id", value.get(provider, ""))
        elif key == "rating":
            _scalar(root, "rating", "" if value is None else format(value, ".15g"))
            primary = _primary_rating(root)
            if primary is not None:
                # Keep other providers' independent ratings and all vote counts.
                maximum = _number(primary.getAttribute("max")) or 10
                _scalar(primary, "value", "" if value is None else format(value * maximum / 10, ".15g"))
        elif key == "set":
            nodes = _children(root, "set") or [_new(root, "set")]
            for node in nodes:
                if _children(node, "name") or any(c.nodeType == Node.ELEMENT_NODE for c in node.childNodes):
                    _scalar(node, "name", value)
                else:
                    _set_text(node, value)
        elif key == "premiered":
            _scalar(root, "premiered", value)
            for tag in ("aired", "releasedate"):
                if _children(root, tag) or tag == "aired" and root.tagName == "episodedetails":
                    _scalar(root, tag, value)
        else:
            _scalar(root, _TAGS.get(key, key), value)


def _revision(content):
    return hashlib.sha256(content).hexdigest()


def read_document(path: str, roots: list[str], expected_root: Literal["movie", "tvshow", "episodedetails"]) -> dict:
    with _io_errors():
        target = _path(path, roots)
        with _Guard(target) as guard:
            content, _ = guard.read()
            document = _parse(content, expected_root)
            return {"revision": _revision(content), "fields": _fields(document.documentElement)}


def inspect_document(path: str, roots: list[str]) -> dict:
    """Allow safe identification/removal even when XML cannot be edited."""
    with _io_errors():
        with _Guard(_path(path, roots)) as guard:
            content, _ = guard.read()
            return {"revision": _revision(content), "size": len(content)}


def remove_document(path: str, roots: list[str], revision: str) -> dict:
    with _io_errors():
        target = _path(path, roots)
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision):
            _invalid("A SHA-256 revision from the NFO read is required.")
        with _locks_guard:
            lock = _locks.get(os.path.normcase(target))
            if lock is None:
                lock = threading.Lock()
                _locks[os.path.normcase(target)] = lock
        with lock, _Guard(target) as guard:
            content, info = guard.read(removable=True)
            if _revision(content) != revision:
                _conflict()
            backup_name = guard.name + ".horizon-deleted-" + uuid.uuid4().hex + ".bak"
            guard.verify()
            guard.archive(backup_name, info)
            backup_path = os.path.join(guard.parent, backup_name)
            if os.name == "nt" and len(backup_path) >= 260:
                backup_path = _win_extended_path(backup_path)
            return {"backup_path": backup_path}


def _write(fd, content):
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def save_document(path: str, roots: list[str], revision: str, fields: dict,
                  expected_root: Literal["movie", "tvshow", "episodedetails"]) -> dict:
    with _io_errors():
        target = _path(path, roots)
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{64}", revision):
            _invalid("A SHA-256 revision from the NFO read is required.")
        with _locks_guard:
            lock = _locks.get(os.path.normcase(target))
            if lock is None:
                lock = threading.Lock()
                _locks[os.path.normcase(target)] = lock
        with lock, _Guard(target) as guard:
            content, info = guard.read()
            if _revision(content) != revision:
                _conflict()
            document = _parse(content, expected_root)
            old = _fields(document.documentElement)
            values = _validate(fields, old)
            _apply(document.documentElement, old, values)
            replacement = document.toxml(encoding="utf-8") + document.nfo_trailer
            if len(replacement) > MAX_BYTES:
                _invalid("The edited NFO would exceed the 1 MiB limit.")
            if not info.st_mode & 0o222:
                raise NfoError("The NFO is read-only. Enable write permission before saving.", 403)
            backup_name = guard.name + ".horizon-" + uuid.uuid4().hex + ".bak"
            temp_name = ".horizon-" + uuid.uuid4().hex + ".tmp"
            # A failed/partial backup is retained for diagnosis; never overwritten
            # or removed. The original is untouched until a completed backup exists.
            guard.verify()
            _write(guard.create(backup_name, 0o600), content)
            owned_temp = False
            owned_fd = None
            temp_info = None
            try:
                fd = guard.create(temp_name, stat.S_IMODE(info.st_mode))
                owned_temp = True
                try:
                    owned_fd = os.dup(fd)
                except BaseException:
                    os.close(fd)
                    raise
                _write(fd, replacement)
                if os.name == "nt":
                    _win_preserve_security(target, os.path.join(guard.parent, temp_name))
                latest, latest_info = guard.read()
                if _identity(latest_info) != _identity(info) or _revision(latest) != revision:
                    _conflict()
                guard.verify()
                temp_info = os.fstat(owned_fd)
                os.close(owned_fd)
                owned_fd = None
                guard.replace(temp_name)
                owned_temp = False
            finally:
                if owned_fd is not None:
                    temp_info = os.fstat(owned_fd)
                    os.close(owned_fd)
                if owned_temp:
                    try:
                        if temp_info is not None:
                            guard.remove_temp(temp_name, temp_info)
                    except OSError:
                        pass  # Never mask the original failure or remove other files.
            return {"revision": _revision(replacement), "fields": _fields(document.documentElement),
                    "backup_path": os.path.join(guard.parent, backup_name)}
