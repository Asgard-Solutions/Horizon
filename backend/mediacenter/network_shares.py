"""Windows SMB sessions and REELHEIM-owned, per-user Credential Manager entries.

No drive mappings, shell commands, profile updates, store enumeration or session
disconnects. Native network calls cannot be cancelled: daemon workers are capped,
and a timed-out worker is never allowed to save a password. Python strings cannot
be reliably erased; native password buffers and mutable credential blobs are
zeroed as soon as possible. Loading capabilities does not read credentials.
"""
import ctypes
import ipaddress
import os
import queue
import re
import socket
import sys
import threading
from functools import lru_cache


class ShareError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


CONNECT_TIMEOUT_S = 8.0
_operation_slots = threading.BoundedSemaphore(4)
_PRIVATE_NETWORKS = tuple(ipaddress.ip_network(net) for net in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))
# Windows NetBIOS server names can contain underscores.
_HOST_LABEL = re.compile(r"[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?", re.ASCII)
_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", re.I)
_FORBIDDEN = frozenset('\\/:*?"<>|')
_ADMIN_SHARE = re.compile(r"(?:[a-z]|admin|ipc)\$", re.I | re.ASCII)
_MAX_BLOB = 2560  # CRED_MAX_CREDENTIAL_BLOB_SIZE on supported Windows versions


def _component(value):
    if (not isinstance(value, str) or not value or len(value) > 255
            or value in (".", "..") or value.endswith((".", " "))
            or _RESERVED.fullmatch(value)
            or any(c in _FORBIDDEN or ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ShareError("Use share and folder names without escapes, device names or invalid Windows characters.")
    try:
        value.encode("utf-16-le")
    except UnicodeError:
        raise ShareError("Share and folder names contain an invalid character.") from None
    return value


def normalize_share(server: str, share: str, folder: str = "") -> dict:
    """Validate components without DNS/IO; produce one ordinary canonical UNC.

    Server input is a plain IPv4 address or DNS/NetBIOS name. IPv6 literals are
    deliberately unsupported because Windows UNC requires a different spelling.
    Case is preserved for folder/share display; credential keys ignore UNC case.
    """
    if not isinstance(server, str):
        raise ShareError("Enter a server name or private IPv4 address.")
    server = server.strip().lower()
    if (not server or len(server) > 253 or not all(_HOST_LABEL.fullmatch(label) for label in server.split("."))
            or server.endswith(".ipv6-literal.net")):
        raise ShareError("Enter just a server name or private IPv4 address, without a URL, account or port.")
    # Windows accepts ambiguous inet_aton spellings (integer, octal, hex, short).
    # Do not let DNS validation and the SMB redirector interpret different hosts.
    try:
        address = ipaddress.IPv4Address(server)
    except ipaddress.AddressValueError:
        if re.fullmatch(r"[0-9.]+", server) or any(label.startswith("0x") for label in server.split(".")):
            raise ShareError("Use a full IPv4 address with four decimal numbers.") from None
    else:
        server = str(address)
    share = _component(share)
    if _ADMIN_SHARE.fullmatch(share):
        raise ShareError("Choose a media share instead of a Windows administrative share.")
    if not isinstance(folder, str):
        raise ShareError("Enter a relative subfolder inside the share.")
    folder = folder.replace("/", "\\")
    if folder:
        folder = "\\".join(_component(part) for part in folder.split("\\"))
    share_path = f"\\\\{server}\\{share}"
    path = share_path + ("\\" + folder if folder else "")
    if len(path) > 2048:
        raise ShareError("Choose a shorter share and subfolder path.")
    return dict(server=server, share=share, folder=folder, share_path=share_path, path=path)


def _target(location):
    # GENERIC names are private to the signed-in Windows user. Never use a raw
    # server/DomainPassword target that Windows or another application may own.
    # Preserve the original namespace so REELHEIM retains existing saved sign-ins.
    return "Horizon:SMB:v1:" + location["share_path"].casefold()


def _validate_lan(server) -> str:
    """Return the selected private IPv4 endpoint, never a DNS name.

    Check every answer before selecting one. All subsequent authenticated IO
    must use this literal, so the redirector cannot resolve the name again.
    """
    def allowed(raw):
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            return False
        return any(address.version == net.version and address in net for net in _PRIVATE_NETWORKS)

    try:
        literal = ipaddress.IPv4Address(server)
    except ipaddress.AddressValueError:
        literal = None
    if literal is not None:
        if not allowed(str(literal)):
            raise ShareError("SMB connections require a private LAN address (RFC1918 IPv4 or IPv6 ULA).")
        return str(literal)
    try:
        answers = socket.getaddrinfo(server, 445, type=socket.SOCK_STREAM)
    except OSError:
        raise ShareError("Cannot resolve the NAS. Check its server name and your LAN connection.", 502) from None
    if not answers or any(not allowed(answer[4][0]) for answer in answers):
        raise ShareError("Every server address must be a private LAN address (RFC1918 IPv4 or IPv6 ULA).")
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0])
        if answer[0] == socket.AF_INET and address.version == 4:
            return str(address)
    raise ShareError("This NAS has no private IPv4 address. Enable IPv4 on the NAS or enter its private IPv4 address.")


def _check_cancel(cancelled):
    if cancelled.is_set():
        raise ShareError("The NAS connection timed out. Check that it is online and try again.", 504)


def _bounded(operation):
    """No waiting queue and at most four uninterruptible native/DNS operations."""
    if not _operation_slots.acquire(blocking=False):
        raise ShareError("Network share checks are busy. Wait for the NAS to respond and retry.", 503)
    cancelled = threading.Event()
    outcome = queue.Queue(maxsize=1)
    slots = _operation_slots  # keep the matching semaphore even during teardown

    def worker():
        try:
            outcome.put((True, operation(cancelled)))
        except Exception as exc:
            # Do not retain arbitrary native exception messages or tracebacks.
            error = exc if isinstance(exc, ShareError) else ShareError(
                "Windows could not complete the share operation. Check the NAS and sign-in details.", 502)
            outcome.put((False, error))
        finally:
            slots.release()

    try:
        thread = threading.Thread(target=worker, name="horizon-smb", daemon=True)
        thread.start()
    except Exception:
        slots.release()
        raise ShareError("Cannot start a network share check. Try again.", 503) from None
    try:
        ok, result = outcome.get(timeout=CONNECT_TIMEOUT_S)
    except queue.Empty:
        cancelled.set()
        raise ShareError("The NAS connection timed out. Check that it is online and try again.", 504) from None
    if not ok:
        raise result from None
    return result


def _connection_error(code):
    messages = {
        5: "Access denied. Check that this account can read the share and folder.",
        53: "Cannot reach the NAS. Check that it is online and available on your LAN.",
        64: "The NAS connection was lost. Check your LAN and try again.",
        67: "The share was not found. Check the share name on the NAS.",
        86: "Windows rejected the sign-in. Check your username and password.",
        1219: "Windows already has a session to this server with another account. Close that session in Windows or use the same account; REELHEIM will not disconnect it.",
        1231: "Cannot reach the NAS network. Check your LAN connection.",
        1326: "Windows rejected the sign-in. Check your username and password.",
        1909: "The NAS account is locked. Unlock it before trying to sign in again.",
    }
    return ShareError(messages.get(code, "Windows could not connect to the share. Check NAS access and sign-in details."), 400)


def capabilities() -> dict:
    """Probe API availability only. No DNS, connections or credential reads."""
    native = _get_native()
    return dict(smb_supported=bool(native and native.smb_supported),
                credential_store_supported=bool(native and native.credential_store_supported))


def _require_native(credentials=False):
    native = _get_native()
    if not native or not native.smb_supported:
        raise ShareError("Native SMB connections require Windows with the SMB networking API available.", 501)
    if credentials and not native.credential_store_supported:
        raise ShareError("Windows Credential Manager is unavailable. Use a temporary sign-in without Remember.", 501)
    return native


def _credentials(username, password, remember, use_saved):
    if not isinstance(remember, bool) or not isinstance(use_saved, bool):
        raise ShareError("Remember and saved sign-in options must be true or false.")
    if use_saved and (username is not None or password is not None):
        raise ShareError("Choose either the saved sign-in or supplied credentials.")
    if username is None and password is None:
        if remember and not use_saved:
            raise ShareError("Supply a username and password to remember a sign-in.")
        return
    if (not isinstance(username, str) or not username.strip() or len(username) > 513
            or any(ord(c) < 32 for c in username) or not isinstance(password, str) or "\0" in password):
        raise ShareError("Supply both a valid username and password, or use the current Windows account.")
    try:
        size = len(password.encode("utf-16-le"))
        username.encode("utf-16-le")
    except UnicodeError:
        raise ShareError("The sign-in contains an invalid character.") from None
    if size > _MAX_BLOB:
        raise ShareError("This password exceeds the Windows credential size limit.")


def connect_share(server, share, folder="", username=None, password=None, remember=False, use_saved=False) -> dict:
    """Connect and return IP-based paths/credential identity for future use.

    Hostname-based Kerberos/SPN behavior must be verified in the deployment's
    Windows/NAS environment; no authentication policy is configured here.
    """
    location = normalize_share(server, share, folder)
    _credentials(username, password, remember, use_saved)
    native = _require_native(credentials=remember or use_saved)

    def connect(cancelled):
        saved_secret = None
        login, secret = username, password
        try:
            address = _validate_lan(location["server"])
            _check_cancel(cancelled)
            endpoint = normalize_share(address, location["share"], location["folder"])
            target = _target(endpoint)
            if use_saved:
                entry = native.read(target)
                if entry is None:
                    raise ShareError("No saved REELHEIM sign-in exists for this share. Supply credentials first.")
                login, saved_secret = entry
                secret = saved_secret.decode("utf-16-le")
                _credentials(login, secret, False, False)
            _check_cancel(cancelled)
            code = native.connect(endpoint["share_path"], login, secret)
            _check_cancel(cancelled)
            if code:
                raise _connection_error(code)
            if not os.path.isdir(endpoint["path"]):
                raise ShareError("The folder is not accessible. Check its name and this account's read permissions.")
            _check_cancel(cancelled)
            return endpoint, login
        finally:
            if saved_secret is not None:
                _zero(saved_secret)
            secret = None

    endpoint, login = _bounded(connect)
    target = _target(endpoint)
    # Deliberately outside the worker. Only the waiting caller may persist a
    # password, after accepting a timely successful connection and folder check.
    # CredWrite is a local OS-store operation, never a network task.
    if remember and not use_saved:
        blob = bytearray(password, "utf-16-le")
        try:
            native.write(target, login, blob)
        except Exception:
            raise ShareError("The share connected, but Windows could not save the sign-in. Retry without Remember.", 502) from None
        finally:
            _zero(blob)
    try:
        saved = bool(native.credential_store_supported and native.saved(target))
    except Exception:
        raise ShareError("The share connected, but Windows could not check its saved sign-in.", 502) from None
    return {**endpoint, "username": login, "credential_saved": saved, "accessible": True}


def credential_saved(server, share) -> bool:
    """Check only the supplied record's exact target, with no DNS/network IO.

    New connection records supply the pinned IPv4 server returned by connect.
    """
    location = normalize_share(server, share)
    native = _get_native()
    if not native or not native.credential_store_supported:
        return False
    try:
        return bool(native.saved(_target(location)))
    except Exception:
        raise ShareError("Windows could not check the saved REELHEIM sign-in. Check Credential Manager.", 502) from None


def forget_credentials(server, share) -> None:
    location = normalize_share(server, share)
    native = _get_native()
    if not native or not native.credential_store_supported:
        raise ShareError("Windows Credential Manager is unavailable on this system.", 501)
    try:
        native.delete(_target(location))
    except Exception:
        raise ShareError("Windows could not remove the saved REELHEIM sign-in. Check Credential Manager.", 502) from None


def ensure_saved_connection(path) -> bool:
    """Best effort on demand, called inside paths.dir_reachable's executor.

    Reconnect only a pinned IPv4 UNC with an exact REELHEIM-owned saved target.
    An IP session cannot prove an unchanged hostname source is reachable; older
    hostname sources keep their ordinary path checks until re-added by IP.
    No store listing, no local-path IO, and no interference with Windows sessions.
    """
    if not isinstance(path, str) or not path.startswith("\\\\"):
        return False
    parts = path[2:].rstrip("\\").split("\\", 2)
    if len(parts) < 2:
        return False
    try:
        location = normalize_share(parts[0], parts[1], parts[2] if len(parts) > 2 else "")
        try:
            ipaddress.IPv4Address(location["server"])
        except ipaddress.AddressValueError:
            return False
        # A missing entry never falls back to an older hostname credential.
        connect_share(location["server"], location["share"], location["folder"], use_saved=True)
        return True
    except ShareError:
        return False


def _zero(buffer):
    if buffer:
        ctypes.memset(ctypes.addressof((ctypes.c_ubyte * len(buffer)).from_buffer(buffer)), 0, len(buffer))


# Fixed-width Win32 fields avoid host ABI differences in offline tests.
_DWORD = ctypes.c_uint32
_BOOL = ctypes.c_int32
_LPBYTE = ctypes.POINTER(ctypes.c_ubyte)


class _NETRESOURCEW(ctypes.Structure):
    _fields_ = [("dwScope", _DWORD), ("dwType", _DWORD), ("dwDisplayType", _DWORD), ("dwUsage", _DWORD),
                ("lpLocalName", ctypes.c_wchar_p), ("lpRemoteName", ctypes.c_wchar_p),
                ("lpComment", ctypes.c_wchar_p), ("lpProvider", ctypes.c_wchar_p)]


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", _DWORD), ("dwHighDateTime", _DWORD)]


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [("Flags", _DWORD), ("Type", _DWORD), ("TargetName", ctypes.c_wchar_p),
                ("Comment", ctypes.c_wchar_p), ("LastWritten", _FILETIME),
                ("CredentialBlobSize", _DWORD), ("CredentialBlob", _LPBYTE), ("Persist", _DWORD),
                ("AttributeCount", _DWORD), ("Attributes", ctypes.c_void_p),
                ("TargetAlias", ctypes.c_wchar_p), ("UserName", ctypes.c_wchar_p)]


class _Native:
    def __init__(self, loader=None):
        loader = loader or ctypes.WinDLL
        self.smb_supported = self.credential_store_supported = False
        try:
            # Resolve system libraries only; do not search the working directory.
            mpr = loader("mpr.dll", use_last_error=True, winmode=0x800)
            self._connect = mpr.WNetAddConnection2W
            self._connect.argtypes = [ctypes.POINTER(_NETRESOURCEW), ctypes.c_wchar_p, ctypes.c_wchar_p, _DWORD]
            self._connect.restype = _DWORD
            self.smb_supported = True
        except (OSError, AttributeError):
            pass
        try:
            advapi = loader("advapi32.dll", use_last_error=True, winmode=0x800)
            self._read = advapi.CredReadW
            self._read.argtypes = [ctypes.c_wchar_p, _DWORD, _DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
            self._read.restype = _BOOL
            self._write = advapi.CredWriteW
            self._write.argtypes = [ctypes.POINTER(_CREDENTIALW), _DWORD]
            self._write.restype = _BOOL
            self._delete = advapi.CredDeleteW
            self._delete.argtypes = [ctypes.c_wchar_p, _DWORD, _DWORD]
            self._delete.restype = _BOOL
            self._free = advapi.CredFree
            self._free.argtypes = [ctypes.c_void_p]
            self._free.restype = None
            self.credential_store_supported = True
        except (OSError, AttributeError):
            pass

    def connect(self, path, username, password):
        resource = _NETRESOURCEW()
        resource.dwType = 1  # RESOURCETYPE_DISK
        resource.lpRemoteName = path
        # NULL lpLocalName makes a deviceless session. Flags 0 never saves a
        # profile or invokes a credential prompt; NULL credentials use Windows.
        user_buffer = ctypes.create_unicode_buffer(username) if username is not None else None
        password_buffer = ctypes.create_unicode_buffer(password) if password is not None else None
        try:
            return self._connect(ctypes.byref(resource), password_buffer, user_buffer, 0)
        finally:
            for buffer in (password_buffer, user_buffer):
                if buffer is not None:
                    ctypes.memset(ctypes.addressof(buffer), 0, ctypes.sizeof(buffer))

    def _entry(self, target, metadata_only):
        pointer = ctypes.POINTER(_CREDENTIALW)()
        if not self._read(target, 1, 0, ctypes.byref(pointer)):  # CRED_TYPE_GENERIC
            if ctypes.get_last_error() == 1168:  # ERROR_NOT_FOUND
                return None
            raise ShareError("Windows could not read the saved REELHEIM sign-in.", 502)
        try:
            entry = pointer.contents
            if entry.Type != 1 or entry.TargetName != target:
                raise ShareError("The saved REELHEIM sign-in is invalid. Forget it and sign in again.")
            if metadata_only:
                return True
            size = entry.CredentialBlobSize
            if size > _MAX_BLOB or size % 2 or (size and not entry.CredentialBlob):
                raise ShareError("The saved REELHEIM sign-in is invalid. Forget it and sign in again.")
            blob = bytearray(size)
            if size:
                ctypes.memmove((ctypes.c_ubyte * size).from_buffer(blob), entry.CredentialBlob, size)
            return entry.UserName, blob
        finally:
            if pointer:
                entry = pointer.contents
                if entry.CredentialBlob and 0 < entry.CredentialBlobSize <= _MAX_BLOB:
                    ctypes.memset(entry.CredentialBlob, 0, entry.CredentialBlobSize)
                self._free(pointer)

    def read(self, target):
        return self._entry(target, False)

    def saved(self, target):
        return bool(self._entry(target, True))

    def write(self, target, username, secret):
        # Borrow the caller's mutable blob instead of making another secret
        # copy. Both this method and its caller clear it even on failure.
        buffer = ((ctypes.c_ubyte * len(secret)).from_buffer(secret) if secret
                  else (ctypes.c_ubyte * 1)())
        entry = _CREDENTIALW()
        entry.Type, entry.TargetName, entry.UserName = 1, target, username
        entry.CredentialBlobSize, entry.CredentialBlob = len(secret), ctypes.cast(buffer, _LPBYTE)
        # LOCAL_MACHINE persistence survives this user's logon/restarts; it is
        # still scoped to this Windows user's credential set, not all users.
        entry.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        try:
            if not self._write(ctypes.byref(entry), 0):
                raise ShareError("Windows could not save the REELHEIM sign-in.", 502)
        finally:
            ctypes.memset(buffer, 0, ctypes.sizeof(buffer))

    def delete(self, target):
        if not self._delete(target, 1, 0) and ctypes.get_last_error() != 1168:
            raise ShareError("Windows could not remove the saved REELHEIM sign-in.", 502)


@lru_cache(maxsize=1)
def _get_native():
    if sys.platform != "win32":
        return None
    try:
        return _Native()
    except (OSError, AttributeError):
        return None
