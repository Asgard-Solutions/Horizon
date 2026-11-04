"""SMB adapter contract; every DNS, filesystem and Windows API is replaced.

No test may contact a NAS or access the user's Windows Credential Manager.
For the whole backend suite, load this module as a plugin with
``pytest -p tests.test_network_shares`` so legacy UNC-path tests also inherit
the native-access guard. Individual adapter tests replace it with owned fakes.
"""
import ctypes
import importlib
import importlib.util
import socket
import threading
from types import SimpleNamespace

import pytest


def test_adapter_module_exists():
    assert importlib.util.find_spec("mediacenter.network_shares") is not None


class NativeDouble:
    smb_supported = True
    credential_store_supported = True

    def __init__(self):
        self.entries = {}
        self.connections = []
        self.writes = []
        self.reads = []
        self.deletes = []
        self.code = 0

    def connect(self, path, username, password):
        self.connections.append((path, username, password))
        return self.code

    def saved(self, target):
        return target in self.entries

    def read(self, target):
        self.reads.append(target)
        entry = self.entries.get(target)
        return (entry[0], bytearray(entry[1])) if entry else None

    def write(self, target, username, secret):
        self.writes.append(target)
        self.entries[target] = (username, bytes(secret))

    def delete(self, target):
        self.deletes.append(target)
        self.entries.pop(target, None)


@pytest.fixture(autouse=True)
def offline_native_guard(monkeypatch):
    mod = importlib.import_module("mediacenter.network_shares")
    monkeypatch.setattr(mod, "_get_native", lambda: None)


@pytest.fixture
def adapter(monkeypatch):
    mod = importlib.import_module("mediacenter.network_shares")
    native = NativeDouble()
    monkeypatch.setattr(mod, "_get_native", lambda: native)
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 445)),
    ])
    monkeypatch.setattr(mod.os.path, "isdir", lambda path: True)
    return mod, native


def test_normalize_canonical_unc(adapter, monkeypatch):
    mod, _ = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: pytest.fail("DNS during normalization"))
    monkeypatch.setattr(mod.os.path, "isdir", lambda *a: pytest.fail("Filesystem IO during normalization"))
    assert mod.normalize_share(" NAS.Local ", "Media", "Movies/Kids") == {
        "server": "nas.local", "share": "Media", "folder": r"Movies\Kids",
        "share_path": r"\\nas.local\Media", "path": r"\\nas.local\Media\Movies\Kids",
    }


@pytest.mark.parametrize("server", ["Jakes_Laptop", "_MediaNAS", "MediaNAS_", "media_nas.local"])
def test_netbios_underscore_names_connect_only_to_pinned_private_ip(adapter, monkeypatch, server):
    mod, native = adapter
    lookups, checks = [], []
    def resolve(name, *args, **kwargs):
        lookups.append(name)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 445))]
    monkeypatch.setattr(mod.socket, "getaddrinfo", resolve)
    monkeypatch.setattr(mod.os.path, "isdir", lambda path: checks.append(path) or True)
    assert mod.normalize_share(server, "Media")["server"] == server.lower()
    assert not lookups and not checks
    result = mod.connect_share(server, "Media", "Movies", "fake-user", "fake-secret")
    assert lookups == [server.lower()]
    assert native.connections == [(r"\\192.168.1.20\Media", "fake-user", "fake-secret")]
    assert checks == [r"\\192.168.1.20\Media\Movies"]
    assert result["server"] == "192.168.1.20"
    assert result["share_path"] == r"\\192.168.1.20\Media"
    assert result["path"] == r"\\192.168.1.20\Media\Movies"


def test_netbios_underscore_name_cannot_bypass_private_address_validation(adapter, monkeypatch):
    mod, native = adapter
    lookups = []
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: lookups.append(a[0]) or [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 445))])
    with pytest.raises(mod.ShareError, match="private"):
        mod.connect_share("Jakes_Laptop", "Media", use_saved=True)
    assert lookups == ["jakes_laptop"]
    assert not native.reads and not native.connections and not native.writes


def test_capabilities_never_accesses_credentials_or_network(adapter, monkeypatch):
    mod, native = adapter
    def forbidden(*args, **kwargs):
        pytest.fail("Capability probe accessed credentials or the network")
    for name in ("saved", "read", "write", "delete", "connect"):
        monkeypatch.setattr(native, name, forbidden)
    monkeypatch.setattr(mod.socket, "getaddrinfo", forbidden)
    assert mod.capabilities() == {"smb_supported": True, "credential_store_supported": True}


@pytest.mark.parametrize("address", ["8.8.8.8", "127.0.0.1", "169.254.1.1", "172.15.255.255", "172.32.0.1"])
def test_public_literal_is_rejected_without_dns_or_credentials(adapter, monkeypatch, address):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: pytest.fail("DNS for literal IP"))
    with pytest.raises(mod.ShareError, match="private"):
        mod.connect_share(address, "Media", username="fake-user", password="fake-secret", remember=True)
    assert not native.connections and not native.writes and not native.reads


def test_metadata_and_forget_do_not_require_nas_to_be_online(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: pytest.fail("DNS for local store"))
    assert mod.credential_saved("192.168.1.20", "Media") is False
    mod.forget_credentials("192.168.1.20", "Media")
    assert len(native.deletes) == 1 and not native.connections


@pytest.mark.parametrize("server,share,folder", [
    ("", "Media", ""), ("\\\\nas", "Media", ""), ("//nas", "Media", ""),
    ("smb://nas", "Media", ""), ("user@nas", "Media", ""), ("nas:445", "Media", ""),
    ("nas\x00bad", "Media", ""), ("nas&whoami", "Media", ""), ("nas.", "Media", ""),
    ("127.1", "Media", ""), ("0x7f000001", "Media", ""), ("2130706433", "Media", ""),
    ("192.168.001.2", "Media", ""), ("[fd00::1]", "Media", ""),
    ("nas", "", ""), ("nas", "C$", ""), ("nas", "ADMIN$", ""), ("nas", "IPC$", ""),
    ("nas", "Media\\other", ""), ("nas", "Media/other", ""), ("nas", ".", ""),
    ("nas", "Media.", ""), ("nas", "CON", ""), ("nas", "a:stream", ""),
    ("nas", "Media", "../private"), ("nas", "Media", "Movies/../../private"),
    ("nas", "Media", "/absolute"), ("nas", "Media", "\\absolute"),
    ("nas", "Media", "C:\\other"), ("nas", "Media", "\\\\?\\C:\\other"),
    ("nas", "Media", "a\x00b"), ("nas", "Media", "a/./b"),
    ("nas", "Media", "a/NUL.txt"), ("nas", "Media", "a/COM1"),
    ("nas", "Media", "a|b"),
])
def test_rejects_unsafe_unc_before_native_or_dns(adapter, monkeypatch, server, share, folder):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: pytest.fail("DNS for invalid input"))
    with pytest.raises(mod.ShareError):
        mod.connect_share(server, share, folder, username="fake-user", password="fake-secret")
    assert native.connections == [] and native.reads == [] and native.writes == []


@pytest.mark.parametrize("share,folder,expected_path", [
    ("Media$", "Movies & TV", r"\\192.168.1.20\Media$\Movies & TV"),
    ("Family & Friends", "Jane; Doe", r"\\192.168.1.20\Family & Friends\Jane; Doe"),
    ("100% Media", "Kids@Home!", r"\\192.168.1.20\100% Media\Kids@Home!"),
    ("Media", "`Classics`/$5 Movies", r"\\192.168.1.20\Media\`Classics`\$5 Movies"),
    ("Media", "%USERPROFILE%", r"\\192.168.1.20\Media\%USERPROFILE%"),
    ("Media", " Classics", r"\\192.168.1.20\Media\ Classics"),
])
def test_legal_windows_names_are_literal_not_shell_input(adapter, share, folder, expected_path):
    mod, native = adapter
    result = mod.connect_share("nas", share, folder)
    assert result["path"] == expected_path and result["accessible"] is True
    assert native.connections == [("\\\\192.168.1.20\\" + share, None, None)]


@pytest.mark.parametrize("share", ["a$", "Z$", "admin$", "ipc$"])
def test_administrative_shares_are_specifically_denied(adapter, share):
    mod, native = adapter
    with pytest.raises(mod.ShareError):
        mod.connect_share("nas", share)
    assert not native.connections


@pytest.mark.parametrize("folder", ["CONIN$", "CONOUT$", "CONIN$.txt"])
def test_console_device_names_are_rejected(adapter, folder):
    mod, native = adapter
    with pytest.raises(mod.ShareError):
        mod.connect_share("nas", "Media", folder)
    assert not native.connections


@pytest.mark.parametrize("address", ["8.8.8.8", "127.0.0.1", "169.254.2.3", "100.64.0.1",
    "192.0.0.1", "0.0.0.0", "224.0.0.1", "198.18.0.1", "2001:db8::1", "::1", "fe80::1"])
def test_denies_non_lan_dns_answers_before_reading_saved_secrets(adapter, monkeypatch, address):
    mod, native = adapter
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (family, socket.SOCK_STREAM, 6, "", (address, 445)),
    ])
    with pytest.raises(mod.ShareError, match="private"):
        mod.connect_share("nas", "Media", use_saved=True)
    assert native.connections == [] and native.reads == []


def test_mixed_public_private_dns_is_denied(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 445)) for ip in ("10.1.2.3", "8.8.8.8")])
    with pytest.raises(mod.ShareError):
        mod.connect_share("nas", "Media", username="fake-user", password="fake-secret")
    assert not native.connections


@pytest.mark.parametrize("custom", [False, True])
def test_dns_rebinding_cannot_change_connection_or_library_path(adapter, monkeypatch, custom):
    mod, native = adapter
    lookups, accesses = [], []
    def rebinding_dns(server, *args, **kwargs):
        lookups.append(server)
        address = "192.168.1.20" if len(lookups) == 1 else "8.8.8.8"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 445))]
    def destination(path):
        server = path[2:].split("\\", 1)[0]
        return rebinding_dns(server)[0][4][0] if server == "nas" else server
    def connect(path, username, password):
        accesses.append(("connect", path, destination(path)))
        return 0
    def isdir(path):
        accesses.append(("isdir", path, destination(path)))
        return True
    monkeypatch.setattr(mod.socket, "getaddrinfo", rebinding_dns)
    monkeypatch.setattr(native, "connect", connect)
    monkeypatch.setattr(mod.os.path, "isdir", isdir)
    credentials = {"username": "fake-user", "password": "fake-secret"} if custom else {}
    result = mod.connect_share("nas", "Media", "Movies", **credentials)
    assert accesses == [("connect", r"\\192.168.1.20\Media", "192.168.1.20"),
                        ("isdir", r"\\192.168.1.20\Media\Movies", "192.168.1.20")]
    assert lookups == ["nas"]
    assert result["server"] == "192.168.1.20"
    assert result["share_path"] == r"\\192.168.1.20\Media"
    assert result["path"] == r"\\192.168.1.20\Media\Movies"


def test_hostname_saved_signin_reads_only_validated_ip_target(adapter):
    mod, native = adapter
    native.entries[r"Horizon:SMB:v1:\\192.168.1.20\media"] = (
        "fake-user", "fake-secret".encode("utf-16-le"))
    result = mod.connect_share("nas", "Media", "Movies", use_saved=True)
    assert native.reads == [r"Horizon:SMB:v1:\\192.168.1.20\media"]
    assert native.connections == [(r"\\192.168.1.20\Media", "fake-user", "fake-secret")]
    assert result["server"] == "192.168.1.20" and result["credential_saved"] is True


def test_restart_reconnect_uses_ip_record_without_dns(adapter, monkeypatch):
    mod, native = adapter
    record = mod.connect_share("nas", "Media", "Movies", "fake-user", "fake-secret", remember=True)
    native.connections.clear()
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("DNS after restart")))
    assert mod.credential_saved(record["server"], record["share"]) is True
    assert mod.ensure_saved_connection(record["path"]) is True
    assert native.reads == [r"Horizon:SMB:v1:\\192.168.1.20\media"]
    assert native.connections == [(r"\\192.168.1.20\Media", "fake-user", "fake-secret")]


def test_ipv6_only_dns_requires_actionable_ipv4_error(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fd12::1", 445, 0, 0))])
    with pytest.raises(mod.ShareError, match="IPv4"):
        mod.connect_share("nas", "Media", use_saved=True)
    assert not native.reads and not native.connections


def test_private_ipv4_selected_after_private_ipv6_answers(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fd12::1", 445, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.20.30.40", 445))])
    result = mod.connect_share("nas", "Media")
    assert result["server"] == "10.20.30.40"
    assert native.connections == [(r"\\10.20.30.40\Media", None, None)]


def test_legacy_hostname_credential_is_never_used_for_resolved_endpoint(adapter):
    mod, native = adapter
    native.entries[r"Horizon:SMB:v1:\\nas\media"] = ("legacy-user", "fake-secret".encode("utf-16-le"))
    with pytest.raises(mod.ShareError, match="saved"):
        mod.connect_share("nas", "Media", use_saved=True)
    assert native.reads == [r"Horizon:SMB:v1:\\192.168.1.20\media"]
    assert not native.connections


def test_pinned_credential_not_reused_for_changed_private_address(adapter, monkeypatch):
    mod, native = adapter
    mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
    native.connections.clear()
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.20.30.40", 445))])
    with pytest.raises(mod.ShareError, match="saved"):
        mod.connect_share("nas", "Media", use_saved=True)
    assert native.reads == [r"Horizon:SMB:v1:\\10.20.30.40\media"]
    assert not native.connections


def test_saved_ip_reachability_checks_the_pinned_source_only(adapter, monkeypatch):
    mod, native = adapter
    from mediacenter import paths
    native.entries[r"Horizon:SMB:v1:\\192.168.1.20\media"] = (
        "fake-user", "fake-secret".encode("utf-16-le"))
    accesses = []
    monkeypatch.setattr(mod.os.path, "isdir", lambda path: accesses.append(path) or True)
    assert paths.dir_reachable(r"\\192.168.1.20\Media\pinned-reachability") is True
    assert accesses == [r"\\192.168.1.20\Media\pinned-reachability"]
    assert native.connections == [(r"\\192.168.1.20\Media", "fake-user", "fake-secret")]


def test_legacy_hostname_library_does_not_report_ip_connection_as_reachable(adapter, monkeypatch):
    mod, native = adapter
    from mediacenter import paths
    native.entries[r"Horizon:SMB:v1:\\192.168.1.20\media"] = (
        "fake-user", "fake-secret".encode("utf-16-le"))
    original = r"\\nas\Media\legacy-source-actual-path"
    lookups, checks = [], []
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: lookups.append(a[0]) or [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 445))])
    monkeypatch.setattr(mod.os.path, "isdir", lambda path: checks.append(path) or path != original)
    assert paths.dir_reachable(original) is False
    assert checks == [original]
    assert not lookups and not native.reads and not native.connections


@pytest.mark.parametrize("address", ["10.1.2.3", "172.16.0.1", "172.31.255.254", "192.168.2.3"])
def test_lan_dns_allowed_with_integrated_current_account(adapter, monkeypatch, address):
    mod, native = adapter
    monkeypatch.setattr(mod.socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 445))])
    result = mod.connect_share("nas", "Media")
    share_path = "\\\\" + address + "\\Media"
    assert native.connections == [(share_path, None, None)]
    assert result == {"server": address, "share": "Media", "folder": "", "share_path": share_path,
                      "path": share_path, "username": None, "credential_saved": False, "accessible": True}
    assert not native.writes


def test_explicit_signin_is_transient_and_secret_never_returned(adapter):
    mod, native = adapter
    result = mod.connect_share("nas", "Media", "Movies", "fake-user", "fake-secret")
    assert native.connections == [(r"\\192.168.1.20\Media", "fake-user", "fake-secret")]
    assert result["path"] == r"\\192.168.1.20\Media\Movies" and result["accessible"] is True
    assert result["credential_saved"] is False
    assert "fake-secret" not in repr(result) and "password" not in result
    assert not native.writes


def test_remember_use_saved_case_insensitive_target_and_forget(adapter):
    mod, native = adapter
    record = mod.connect_share("NAS", "Media", username="fake-user", password="fake-secret", remember=True)
    assert len(native.writes) == 1
    target = native.writes[0]
    assert target == r"Horizon:SMB:v1:\\192.168.1.20\media"
    assert mod.credential_saved(record["server"], "MEDIA") is True
    assert mod.credential_saved(record["server"], "Other") is False
    native.entries["OtherApp:entry"] = ("other", b"other")
    result = mod.connect_share("nas", "MEDIA", "Kids", use_saved=True)
    assert result["credential_saved"] is True and result["username"] == "fake-user"
    assert native.reads == [target]
    assert native.connections[-1] == (r"\\192.168.1.20\MEDIA", "fake-user", "fake-secret")
    mod.forget_credentials(record["server"], "media")
    mod.forget_credentials(record["server"], "media")  # idempotent; never disconnect
    assert mod.credential_saved(record["server"], "Media") is False
    assert "OtherApp:entry" in native.entries and native.deletes == [target, target]
    assert len(native.connections) == 2


@pytest.mark.parametrize("kwargs", [
    {"password": "fake-secret"}, {"username": "fake-user"}, {"username": ""},
    {"remember": True}, {"username": "bad\x00user", "password": "fake-secret"},
    {"username": "fake-user", "password": "bad\x00secret"},
    {"use_saved": True, "username": "fake-user", "password": "fake-secret"},
])
def test_rejects_ambiguous_credentials(adapter, kwargs):
    mod, native = adapter
    with pytest.raises(mod.ShareError):
        mod.connect_share("nas", "Media", **kwargs)
    assert not native.connections and not native.writes and not native.reads


def test_no_saved_signin_does_not_fall_back_to_current_user(adapter):
    mod, native = adapter
    with pytest.raises(mod.ShareError, match="saved"):
        mod.connect_share("nas", "Media", use_saved=True)
    assert not native.connections


@pytest.mark.parametrize("code,fragment", [(5, "denied"), (53, "reach"), (67, "share"),
    (86, "sign"), (1326, "sign"), (1219, "Windows"), (9999, "Windows")])
def test_native_errors_are_actionable_and_no_failed_signin_is_saved(adapter, code, fragment):
    mod, native = adapter
    native.code = code
    with pytest.raises(mod.ShareError, match=fragment) as exc:
        mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
    assert "fake-secret" not in str(exc.value) and not native.writes


def test_inaccessible_subfolder_is_not_success_or_saved(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod.os.path, "isdir", lambda p: False)
    with pytest.raises(mod.ShareError, match="folder"):
        mod.connect_share("nas", "Media", "Missing", "fake-user", "fake-secret", remember=True)
    assert not native.writes


def test_unexpected_exception_cannot_leak_secrets(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(native, "connect", lambda *a: (_ for _ in ()).throw(OSError("fake-secret")))
    with pytest.raises(mod.ShareError) as exc:
        mod.connect_share("nas", "Media", username="fake-user", password="fake-secret")
    assert "fake-secret" not in str(exc.value)


def test_timeout_never_saves_after_native_operation_finishes_late(adapter, monkeypatch):
    mod, native = adapter
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def blocking_connect(*args):
        entered.set()
        release.wait(2)
        finished.set()
        return 0
    monkeypatch.setattr(native, "connect", blocking_connect)
    monkeypatch.setattr(mod, "CONNECT_TIMEOUT_S", 0.03)
    try:
        with pytest.raises(mod.ShareError) as exc:
            mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
        assert exc.value.status_code == 504 and entered.is_set()
    finally:
        release.set()
    assert finished.wait(1)
    assert not native.writes and not native.entries


def test_blocked_dns_has_bounded_wait_and_cannot_later_transmit_credentials(adapter, monkeypatch):
    mod, native = adapter
    release, finished = threading.Event(), threading.Event()
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(mod, "_operation_slots", slots)
    def slow_dns(*a, **kw):
        release.wait(2)
        finished.set()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", 445))]
    monkeypatch.setattr(mod.socket, "getaddrinfo", slow_dns)
    monkeypatch.setattr(mod, "CONNECT_TIMEOUT_S", 0.03)
    try:
        with pytest.raises(mod.ShareError) as exc:
            mod.connect_share("nas", "Media", username="fake-user", password="fake-secret")
        assert exc.value.status_code == 504
    finally:
        release.set()
    assert finished.wait(1)
    assert slots.acquire(timeout=1)  # the late worker completed every stage
    slots.release()
    assert not native.connections


def test_workers_have_no_unbounded_queue(adapter, monkeypatch):
    mod, native = adapter
    slots = threading.BoundedSemaphore(1)
    assert slots.acquire(False)
    monkeypatch.setattr(mod, "_operation_slots", slots)
    try:
        with pytest.raises(mod.ShareError) as exc:
            mod.connect_share("nas", "Media")
        assert exc.value.status_code == 503
    finally:
        slots.release()
    assert not native.connections


def test_unsupported_os_and_partial_native_support_are_honest(adapter, monkeypatch):
    mod, native = adapter
    monkeypatch.setattr(mod, "_get_native", lambda: None)
    assert mod.capabilities() == {"smb_supported": False, "credential_store_supported": False}
    assert mod.credential_saved("nas", "Media") is False
    with pytest.raises(mod.ShareError) as exc:
        mod.connect_share("nas", "Media")
    assert exc.value.status_code == 501
    with pytest.raises(mod.ShareError):
        mod.forget_credentials("nas", "Media")
    monkeypatch.setattr(mod, "_get_native", lambda: native)
    native.credential_store_supported = False
    assert mod.capabilities() == {"smb_supported": True, "credential_store_supported": False}
    assert mod.connect_share("nas", "Media")["accessible"] is True
    with pytest.raises(mod.ShareError):
        mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
    assert len(native.connections) == 1


def test_reconnect_only_known_horizon_target_without_startup_enumeration(adapter):
    mod, native = adapter
    assert mod.ensure_saved_connection(r"C:\Movies") is False
    assert mod.ensure_saved_connection(r"\\nas\Unknown\Kids") is False
    assert not native.reads and not native.connections
    assert mod.ensure_saved_connection(r"\\192.168.1.20\Unknown\Kids") is False
    assert not native.connections
    assert native.reads == [r"Horizon:SMB:v1:\\192.168.1.20\unknown"]
    mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
    native.connections.clear()
    assert mod.ensure_saved_connection(r"\\192.168.1.20\MEDIA\Kids") is True
    assert native.connections == [(r"\\192.168.1.20\MEDIA", "fake-user", "fake-secret")]
    assert mod.ensure_saved_connection("\\\\192.168.1.20\\Media\\") is True
    assert mod.ensure_saved_connection(r"\\?\UNC\nas\Media") is False


def test_path_reconnect_runs_in_reach_executor_before_stat(adapter, monkeypatch):
    mod, _ = adapter
    from mediacenter import paths
    caller = threading.get_ident()
    calls = []
    path = r"\\nas\Media\integration-unique"
    monkeypatch.setattr(mod, "ensure_saved_connection", lambda p: calls.append(("reconnect", p, threading.get_ident())))
    monkeypatch.setattr(paths.os.path, "isdir", lambda p: calls.append(("stat", p, threading.get_ident())) or True)
    assert paths.dir_reachable(path) is True
    assert [c[0] for c in calls] == ["reconnect", "stat"]
    assert all(c[1] == path and c[2] != caller for c in calls)


class FunctionDouble:
    def __init__(self, callback=lambda *args: 0):
        self.callback = callback
        self.argtypes = self.restype = None

    def __call__(self, *args):
        return self.callback(*args)


@pytest.fixture
def abi(adapter):
    mod, _ = adapter
    dll = SimpleNamespace(**{name: FunctionDouble() for name in (
        "WNetAddConnection2W", "CredReadW", "CredWriteW", "CredDeleteW", "CredFree")})
    native = mod._Native(loader=lambda *a, **kw: dll)
    return mod, native, dll


def test_native_deviceless_connection_and_secret_buffer_zeroing(abi):
    mod, native, dll = abi
    buffers = []
    def connect(resource, password, username, flags):
        value = ctypes.cast(resource, ctypes.POINTER(mod._NETRESOURCEW)).contents
        assert value.dwType == 1 and value.lpLocalName is None
        assert value.lpRemoteName == r"\\nas\Media"
        assert flags == 0  # no profile, drive mapping, UI, prompt or global credential save
        assert ctypes.wstring_at(password) == "fake-secret"
        assert ctypes.wstring_at(username) == "fake-user"
        buffers.append(password)
        return 0
    dll.WNetAddConnection2W.callback = connect
    assert native.connect(r"\\nas\Media", "fake-user", "fake-secret") == 0
    assert ctypes.wstring_at(buffers[0]) == ""
    assert len(dll.WNetAddConnection2W.argtypes) == 4
    assert dll.WNetAddConnection2W.restype is ctypes.c_uint32


def test_native_credential_blob_is_utf16_generic_local_machine_and_zeroed(abi):
    mod, native, dll = abi
    captured = []
    secret = bytearray("fake-secret\U0001f512".encode("utf-16-le"))
    def write(ptr, flags):
        cred = ctypes.cast(ptr, ctypes.POINTER(mod._CREDENTIALW)).contents
        assert cred.Type == 1 and cred.Persist == 2 and cred.TargetName == "Horizon:test"
        assert cred.UserName == "fake-user" and flags == 0
        assert ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize) == bytes(secret)
        captured.append((ctypes.cast(cred.CredentialBlob, ctypes.c_void_p).value, cred.CredentialBlobSize))
        return 1
    dll.CredWriteW.callback = write
    native.write("Horizon:test", "fake-user", secret)
    assert ctypes.string_at(*captured[0]) == b"\0" * len(secret)
    assert len(dll.CredReadW.argtypes) == 4 and len(dll.CredWriteW.argtypes) == 2
    assert len(dll.CredDeleteW.argtypes) == 3 and len(dll.CredFree.argtypes) == 1
    assert dll.CredFree.restype is None


def test_native_read_exact_target_and_frees_zeroed_blob(abi):
    mod, native, dll = abi
    blob = (ctypes.c_ubyte * 22).from_buffer_copy("fake-secret".encode("utf-16-le"))
    cred = mod._CREDENTIALW()
    cred.Type, cred.TargetName, cred.UserName = 1, "Horizon:test", "fake-user"
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
    freed = []
    def read(target, kind, flags, output):
        assert (target, kind, flags) == ("Horizon:test", 1, 0)
        ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(mod._CREDENTIALW)))[0] = ctypes.pointer(cred)
        return 1
    dll.CredReadW.callback = read
    dll.CredFree.callback = lambda ptr: freed.append(ptr)
    username, secret = native.read("Horizon:test")
    assert username == "fake-user" and secret == bytearray("fake-secret".encode("utf-16-le"))
    assert bytes(blob) == b"\0" * 22 and len(freed) == 1


def test_native_null_credentials_use_windows_without_empty_string_override(abi):
    _, native, dll = abi
    calls = []
    dll.WNetAddConnection2W.callback = lambda resource, password, username, flags: calls.append((password, username, flags)) or 0
    assert native.connect(r"\\nas\Media", None, None) == 0
    assert calls == [(None, None, 0)]


def test_native_missing_target_is_false_and_forget_is_idempotent(abi, monkeypatch):
    mod, native, dll = abi
    monkeypatch.setattr(mod.ctypes, "get_last_error", lambda: 1168, raising=False)
    assert native.saved("Horizon:missing") is False
    assert native.read("Horizon:missing") is None
    assert native.delete("Horizon:missing") is None
    freed = []
    dll.CredFree.callback = lambda ptr: freed.append(ptr)
    monkeypatch.setattr(mod.ctypes, "get_last_error", lambda: 5)
    for operation in (native.saved, native.read, native.delete):
        with pytest.raises(mod.ShareError):
            operation("Horizon:denied")
    assert not freed


def test_store_failure_zeroes_secret_and_returns_sanitized_error(adapter, monkeypatch):
    mod, native = adapter
    held = []
    def write(target, username, secret):
        held.append(secret)
        raise OSError("fake-secret")
    monkeypatch.setattr(native, "write", write)
    with pytest.raises(mod.ShareError) as exc:
        mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
    assert "fake-secret" not in str(exc.value)
    assert held == [bytearray(b"\0" * 22)]


def test_slow_folder_check_cannot_save_after_timeout(adapter, monkeypatch):
    mod, native = adapter
    release = threading.Event()
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(mod, "_operation_slots", slots)
    monkeypatch.setattr(mod, "CONNECT_TIMEOUT_S", 0.03)
    monkeypatch.setattr(mod.os.path, "isdir", lambda path: release.wait(2))
    try:
        with pytest.raises(mod.ShareError) as exc:
            mod.connect_share("nas", "Media", username="fake-user", password="fake-secret", remember=True)
        assert exc.value.status_code == 504
    finally:
        release.set()
    assert slots.acquire(timeout=1)
    slots.release()
    assert not native.writes
