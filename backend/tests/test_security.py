import os

import pytest

from mediacenter.db import connect
from mediacenter.security import validate_new_pin

PIN = "48151623"


def enable_lan(host, pin=PIN):
    assert host.post("/api/settings/pin", json={"pin": pin}).status_code == 200
    assert host.post("/api/settings/lan", json={"enabled": True}).json()["lan"]["enabled"] is True


def test_host_has_full_access(host, library):
    assert host.get("/api/auth/status").json()["role"] == "host"
    assert host.get("/api/movies").status_code == 200
    assert host.get("/api/system").status_code == 200


def test_lan_is_disabled_by_default(host, lan_client_factory, library):
    lan = lan_client_factory()
    assert host.get("/api/system").json()["lan"]["enabled"] is False
    assert lan.get("/api/movies").status_code == 403
    assert lan.get("/api/stream/1").status_code == 403
    assert lan.post("/api/auth/pair", json={"pin": PIN}).status_code == 403


def test_lan_cannot_be_enabled_without_pin(host):
    r = host.post("/api/settings/lan", json={"enabled": True})
    assert r.status_code == 400


@pytest.mark.parametrize("pin,ok", [
    ("1234567", False), ("12345678", False), ("87654321", False), ("11111111", False), ("abcdefgh", False),
    ("4815162342", True), (PIN, True),
])
def test_pin_rules(pin, ok):
    assert (validate_new_pin(pin) is None) is ok


def test_pairing_flow_and_device_access(host, lan_client_factory, library):
    enable_lan(host)
    lan = lan_client_factory()
    assert lan.get("/api/movies").status_code == 401
    assert lan.get("/api/auth/status").json()["role"] == "none"
    r = lan.post("/api/auth/pair", json={"pin": PIN, "device_name": "Xbox browser"})
    assert r.status_code == 200 and r.json()["token"]
    assert lan.get("/api/auth/status").json()["role"] == "device"
    movies = lan.get("/api/movies")
    assert movies.status_code == 200 and movies.json()
    fid = movies.json()[0]["file_id"]
    assert lan.get(f"/api/stream/{fid}", headers={"Range": "bytes=0-9"}).status_code == 206

    # devices may never use host-only administration endpoints
    for method, url in [("get", "/api/libraries"), ("get", "/api/fs/roots"), ("get", "/api/fs/list?path=/"),
                        ("get", "/api/system"), ("get", "/api/devices"), ("post", "/api/settings/lan"),
                        ("post", f"/api/libraries/{library['id']}/scan"), ("delete", f"/api/libraries/{library['id']}")]:
        assert getattr(lan, method)(url).status_code == 403, url


def test_bearer_token_for_native_clients(host, lan_client_factory, library):
    enable_lan(host)
    token = lan_client_factory().post("/api/auth/pair", json={"pin": PIN}).json()["token"]
    other = lan_client_factory("192.168.1.77")
    assert other.get("/api/movies").status_code == 401
    assert other.get("/api/movies", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_wrong_pin_lockout(host, lan_client_factory):
    enable_lan(host)
    lan = lan_client_factory("192.168.1.60")
    for _ in range(5):
        assert lan.post("/api/auth/pair", json={"pin": "00000001"}).status_code == 401
    r = lan.post("/api/auth/pair", json={"pin": PIN})
    assert r.status_code == 429 and "Retry-After" in r.headers
    # a different device on the LAN is not locked by someone else's mistakes
    assert lan_client_factory("192.168.1.61").post("/api/auth/pair", json={"pin": PIN}).status_code == 200


def test_revoke_and_pin_change_invalidate_devices(host, lan_client_factory, library):
    enable_lan(host)
    a = lan_client_factory("192.168.1.70")
    b = lan_client_factory("192.168.1.71")
    a.post("/api/auth/pair", json={"pin": PIN, "device_name": "A"})
    b.post("/api/auth/pair", json={"pin": PIN, "device_name": "B"})
    devices = {d["name"]: d for d in host.get("/api/devices").json()}
    assert host.delete(f"/api/devices/{devices['A']['id']}").status_code == 200
    assert a.get("/api/movies").status_code == 401
    assert b.get("/api/movies").status_code == 200
    host.post("/api/settings/pin", json={"pin": "90817263"})
    assert b.get("/api/movies").status_code == 401


def test_disabling_lan_blocks_paired_devices(host, lan_client_factory, library):
    enable_lan(host)
    lan = lan_client_factory()
    lan.post("/api/auth/pair", json={"pin": PIN})
    assert lan.get("/api/movies").status_code == 200
    host.post("/api/settings/lan", json={"enabled": False})
    assert lan.get("/api/movies").status_code == 403


def test_public_ip_always_refused(host, lan_client_factory, library):
    enable_lan(host)
    public = lan_client_factory("8.8.8.8")
    assert public.post("/api/auth/pair", json={"pin": PIN}).status_code == 403
    assert public.get("/api/movies").status_code == 403


def test_dns_rebinding_host_header_is_not_trusted(app, library):
    from fastapi.testclient import TestClient

    from tests.conftest import FixedClientIP
    evil = TestClient(FixedClientIP(app, "127.0.0.1"), base_url="http://attacker.example:8765")
    assert evil.get("/api/movies").status_code == 403
    assert evil.get("/api/fs/roots").status_code == 403


def test_state_changes_require_client_header(host):
    r = host.post("/api/settings/pin", json={"pin": PIN}, headers={"X-MC-Client": ""})
    assert r.status_code == 403


def test_pin_is_not_stored_in_plain_text(app, host):
    host.post("/api/settings/pin", json={"pin": PIN})
    conn = connect(app.state.config.db_path)
    stored = conn.execute("SELECT value FROM settings WHERE key='pin_hash'").fetchone()[0]
    conn.close()
    assert PIN not in stored and stored.startswith("pbkdf2_sha256$")


# --- media path authorization -------------------------------------------------

def _set_path(app, file_id, path):
    conn = connect(app.state.config.db_path)
    conn.execute("UPDATE media_files SET path = ? WHERE id = ?", (path, file_id))
    conn.commit()
    conn.close()


def test_stream_outside_library_is_forbidden(app, host, library, tmp_path):
    secret = tmp_path / "secret.mp4"
    secret.write_bytes(b"top secret")
    fid = host.get("/api/movies").json()[0]["file_id"]
    _set_path(app, fid, str(secret))
    assert host.get(f"/api/stream/{fid}").status_code == 403


def test_path_traversal_inside_db_is_forbidden(app, host, library, media_root, tmp_path):
    (tmp_path / "outside.mp4").write_bytes(b"x")
    fid = host.get("/api/movies").json()[0]["file_id"]
    _set_path(app, fid, str(media_root / ".." / "outside.mp4"))
    assert host.get(f"/api/stream/{fid}").status_code == 403


@pytest.mark.skipif(os.name == "nt", reason="symlink creation needs privileges on Windows")
def test_symlink_escape_is_forbidden(app, host, media_root, tmp_path):
    outside = tmp_path / "private"
    outside.mkdir()
    (outside / "Private Film (2020).mp4").write_bytes(b"private")
    os.symlink(outside, media_root / "Movies" / "link")
    lib = host.post("/api/libraries", json={"path": str(media_root)}).json()
    titles = {m["title"]: m for m in host.get("/api/movies").json()}
    # os.walk does not follow directory symlinks, so the file is never catalogued
    assert "Private Film" not in titles
    fid = titles["Sample Movie"]["file_id"]
    _set_path(app, fid, str(media_root / "Movies" / "link" / "Private Film (2020).mp4"))
    assert host.get(f"/api/stream/{fid}").status_code == 403
    assert lib["scan"]["errors"] == []


def test_artwork_outside_library_is_forbidden(app, host, library, tmp_path):
    img = tmp_path / "elsewhere.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    show = next(s for s in host.get("/api/shows").json() if s["poster_url"])
    assert host.get(show["poster_url"]).status_code == 200
    conn = connect(app.state.config.db_path)
    conn.execute("UPDATE shows SET poster_path = ? WHERE id = ?", (str(img), show["id"]))
    conn.commit()
    conn.close()
    assert host.get(show["poster_url"]).status_code == 403


def test_artwork_must_be_an_image(app, host, library, media_root):
    show = next(s for s in host.get("/api/shows").json() if s["poster_url"])
    conn = connect(app.state.config.db_path)
    conn.execute("UPDATE shows SET poster_path = ? WHERE id = ?", (str(media_root / "TV" / "Sample Show" / "tvshow.nfo"), show["id"]))
    conn.commit()
    conn.close()
    assert host.get(show["poster_url"]).status_code == 404


def test_removed_library_files_are_not_served(host, library):
    fid = host.get("/api/movies").json()[0]["file_id"]
    host.delete(f"/api/libraries/{library['id']}")
    assert host.get(f"/api/stream/{fid}").status_code == 404
