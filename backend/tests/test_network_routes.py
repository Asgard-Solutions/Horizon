"""Network setup contracts: all remote/native operations are replaced with owned fakes."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from mediacenter import routes_network
from mediacenter.db import connect, get_setting
from mediacenter.db import set_setting

SECRET = "test-only-do-not-store"


@pytest.fixture(autouse=True)
def local_network(monkeypatch):
    monkeypatch.setattr(routes_network, "_addresses", lambda: [])
    monkeypatch.setattr(routes_network.smb, "capabilities", lambda: {"smb_supported": True, "credential_store_supported": True})
    monkeypatch.setattr(routes_network.smb, "credential_saved", lambda *_: False)


def fake_connect(**kwargs):
    return {"server": "nas", "share": "Media", "folder": kwargs.get("folder", ""),
            "share_path": r"\\nas\Media", "path": r"\\nas\Media\Movies", "username": kwargs.get("username"),
            "credential_saved": kwargs.get("remember", False), "accessible": True}


def test_connect_is_host_only_and_never_returns_or_stores_password(app, host, lan_client_factory, monkeypatch):
    calls = []
    monkeypatch.setattr(routes_network.smb, "connect_share", lambda **kwargs: calls.append(kwargs) or fake_connect(**kwargs))
    body = {"server": "nas", "share": "Media", "folder": "Movies", "account": "custom", "username": "viewer", "password": SECRET}
    assert lan_client_factory().post("/api/network/shares/connect", json=body).status_code == 403
    response = host.post("/api/network/shares/connect", json=body)
    assert response.status_code == 200, response.text
    assert len(calls) == 1 and calls[0]["password"] == SECRET and calls[0]["remember"] is False
    assert SECRET not in response.text and "password" not in response.json()
    with connect(app.state.config.db_path) as conn:
        stored = get_setting(conn, "network_locations")
    assert SECRET not in stored and "password" not in stored
    network = host.get("/api/network").json()
    assert network["connections"][0]["path"] == r"\\nas\Media\Movies"
    assert SECRET not in json.dumps(network)


@pytest.mark.parametrize("body", [
    {"server": "nas", "share": "Media", "account": "windows", "password": SECRET},
    {"server": "nas", "share": "Media", "account": "custom", "password": SECRET},
    {"server": "nas", "share": "Media", "account": "saved", "remember": True},
    {"server": 12, "share": "Media", "password": SECRET},
    {"server": "nas", "share": "Media", "account": "custom", "username": "a", "password": [SECRET]},
])
def test_invalid_connection_input_never_echoes_secrets(host, monkeypatch, body):
    monkeypatch.setattr(routes_network.smb, "connect_share", lambda **_: pytest.fail("native operation must not run"))
    response = host.post("/api/network/shares/connect", json=body)
    assert response.status_code == 422, response.text
    assert SECRET not in response.text


def test_connection_error_is_actionable_and_redacted(host, monkeypatch):
    def fail(**kwargs):
        raise routes_network.smb.ShareError("Sign-in failed: " + SECRET, 401)
    monkeypatch.setattr(routes_network.smb, "connect_share", fail)
    response = host.post("/api/network/shares/connect", json={"server": "nas", "share": "Media", "account": "custom", "username": "viewer", "password": SECRET})
    assert response.status_code == 401 and "Sign-in failed" in response.text and SECRET not in response.text
    assert host.get("/api/network").json()["connections"] == []


def test_forget_only_removes_own_saved_signin_not_source_or_location(host, monkeypatch):
    monkeypatch.setattr(routes_network.smb, "connect_share", fake_connect)
    host.post("/api/network/shares/connect", json={"server": "nas", "share": "Media"})
    called = []
    monkeypatch.setattr(routes_network.smb, "forget_credentials", lambda server, share: called.append((server, share)))
    before = host.get("/api/libraries").json()
    response = host.post("/api/network/shares/forget", json={"server": "nas", "share": "Media"})
    assert response.status_code == 200 and called == [("nas", "Media")]
    assert len(host.get("/api/network").json()["connections"]) == 1
    assert host.get("/api/libraries").json() == before


def test_saved_account_uses_only_saved_native_credentials(host, monkeypatch):
    called = []
    monkeypatch.setattr(routes_network.smb, "connect_share", lambda **kwargs: called.append(kwargs) or fake_connect(**kwargs))
    response = host.post("/api/network/shares/connect", json={"server": "nas", "share": "Media", "account": "saved"})
    assert response.status_code == 200
    assert called[0]["use_saved"] is True and called[0]["password"] is None and called[0]["username"] is None


def test_network_status_separates_saved_policy_from_actual_listener(host, monkeypatch):
    monkeypatch.setattr(routes_network, "_addresses", lambda: ["192.168.1.50"])
    monkeypatch.setattr(routes_network, "_can_reach", lambda *_: False)
    network = host.get("/api/network").json()
    assert network["listener"]["lan_reachable"] is False
    assert network["addresses"] == [{"url": "http://192.168.1.50:8765", "reachable": False}]


def test_oversized_or_invalid_json_is_rejected_without_native_calls(host, monkeypatch):
    monkeypatch.setattr(routes_network.smb, "connect_share", lambda **_: pytest.fail("must not run"))
    assert host.post("/api/network/shares/connect", content="x" * 9000).status_code == 413
    assert host.post("/api/network/shares/connect", content="{broken").status_code == 422


def test_metadata_lock_wait_does_not_block_other_requests(host, monkeypatch):
    monkeypatch.setattr(routes_network.smb, "connect_share", fake_connect)
    started, release = threading.Event(), threading.Event()
    original = routes_network._save_location
    def blocked(*args):
        started.set()
        release.wait(3)
        return original(*args)
    monkeypatch.setattr(routes_network, "_save_location", blocked)
    with host as client, ThreadPoolExecutor(max_workers=2) as pool:
        saving = pool.submit(client.post, "/api/network/shares/connect", json={"server": "nas", "share": "Media"})
        assert started.wait(2)
        try:
            assert pool.submit(client.get, "/api/health").result(timeout=1).status_code == 200
        finally:
            release.set()
        assert saving.result(timeout=2).status_code == 200


def test_known_loopback_listener_is_never_reported_lan_ready(app, host, monkeypatch):
    from dataclasses import replace
    app.state.config = replace(app.state.config, bind_host="127.0.0.1")
    monkeypatch.setattr(routes_network, "_addresses", lambda: ["192.168.1.50"])
    monkeypatch.setattr(routes_network, "_can_reach", lambda *_: True)
    assert host.get("/api/network").json()["listener"]["lan_reachable"] is False


def test_connection_probe_requires_matching_horizon_instance(monkeypatch):
    class Response:
        status = 200
        def read(self, _): return json.dumps({"ok": True, "instance_matches": False}).encode()
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): pass
        def getresponse(self): return Response()
        def close(self): pass
    monkeypatch.setattr(routes_network.http.client, "HTTPConnection", Connection)
    assert routes_network._can_reach("192.168.1.50", 8765, "own-instance") is False
    monkeypatch.setattr(Response, "read", lambda *_: b'{"ok":true,"instance_matches":true}')
    assert routes_network._can_reach("192.168.1.50", 8765, "own-instance") is True
    monkeypatch.setattr(Response, "read", lambda *_: b'[]')
    assert routes_network._can_reach("192.168.1.50", 8765, "own-instance") is False


def test_readiness_identity_does_not_change_normal_health_or_authentication(app, host):
    plain = host.get("/api/health").json()
    assert plain["ok"] is True and "instance_matches" not in plain
    assert host.get("/api/health", headers={"X-Horizon-Instance": "another-process"}).json()["instance_matches"] is False
    assert host.get("/api/health", headers={"X-Horizon-Instance": app.state.instance_id}).json()["instance_matches"] is True


def scoped_connection(**kwargs):
    server, share, folder = kwargs["server"], kwargs["share"], kwargs.get("folder", "")
    root = f"\\\\{server}\\{share}"
    return {"server": server, "share": share, "folder": folder, "share_path": root,
            "path": root + ("\\" + folder if folder else ""), "username": kwargs.get("username"),
            "credential_saved": False, "accessible": True}


def add_location(host, server="192.168.50.10", share="Media", folder="Movies"):
    response = host.post("/api/network/shares/connect", json={"server": server, "share": share, "folder": folder})
    assert response.status_code == 200, response.text
    return response.json()


def test_multiple_nas_shares_and_subfolders_survive_reload(app, host, monkeypatch):
    from fastapi.testclient import TestClient
    from mediacenter.app import create_app
    from tests.conftest import FixedClientIP
    monkeypatch.setattr(routes_network.smb, "connect_share", scoped_connection)
    rows = [add_location(host), add_location(host, server="192.168.50.11"),
            add_location(host, share="Archive"), add_location(host, folder="TV Shows")]
    assert len({row["id"] for row in rows}) == 4
    assert {row["path"] for row in host.get("/api/network").json()["connections"]} == {row["path"] for row in rows}
    restarted = TestClient(FixedClientIP(create_app(app.state.config), "127.0.0.1"), base_url="http://localhost:8765")
    assert {row["path"] for row in restarted.get("/api/network").json()["connections"]} == {row["path"] for row in rows}
    assert host.get("/api/libraries").json() == []


def test_reconnecting_same_windows_path_updates_one_entry(host, monkeypatch):
    monkeypatch.setattr(routes_network.smb, "connect_share", scoped_connection)
    first = add_location(host)
    second = add_location(host, share="MEDIA", folder="movies\\")
    assert first["id"] == second["id"]
    assert len(host.get("/api/network").json()["connections"]) == 1


def test_old_share_based_id_keeps_existing_folder_when_another_is_added(app, host, monkeypatch):
    import hashlib
    old = scoped_connection(server="192.168.50.10", share="Media", folder="Movies")
    old["id"] = hashlib.sha256(old["share_path"].casefold().encode()).hexdigest()
    with connect(app.state.config.db_path) as conn:
        set_setting(conn, "network_locations", json.dumps([old]))
    monkeypatch.setattr(routes_network.smb, "connect_share", scoped_connection)
    new = add_location(host, folder="TV Shows")
    rows = host.get("/api/network").json()["connections"]
    assert {row["path"] for row in rows} == {old["path"], new["path"]}
    assert len({row["id"] for row in rows}) == 2


def test_locations_on_one_share_receive_one_consistent_saved_signin_state(app, host, monkeypatch):
    rows = [scoped_connection(server="192.168.50.10", share="Media", folder=folder) for folder in ("Movies", "TV Shows")]
    for index, row in enumerate(rows): row["id"] = str(index)
    with connect(app.state.config.db_path) as conn:
        set_setting(conn, "network_locations", json.dumps(rows))
    calls = []
    monkeypatch.setattr(routes_network.smb, "credential_saved", lambda *target: calls.append(target) or True)
    result = host.get("/api/network").json()["connections"]
    assert len(result) == 2 and all(row["credential_saved"] for row in result)
    assert calls == [("192.168.50.10", "Media")]


def test_full_location_list_does_not_silently_remove_an_existing_location(app, host, monkeypatch):
    rows = [scoped_connection(server="192.168.50.10", share="Media", folder=f"Folder {index}") for index in range(64)]
    for index, row in enumerate(rows): row["id"] = str(index)
    original = json.dumps(rows)
    with connect(app.state.config.db_path) as conn:
        set_setting(conn, "network_locations", original)
    monkeypatch.setattr(routes_network.smb, "connect_share", scoped_connection)
    response = host.post("/api/network/shares/connect", json={"server": "192.168.50.10", "share": "Media", "folder": "Another"})
    assert response.status_code == 409, response.text
    with connect(app.state.config.db_path) as conn:
        assert get_setting(conn, "network_locations") == original
