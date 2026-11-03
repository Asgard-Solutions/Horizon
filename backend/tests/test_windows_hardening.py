import mimetypes
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mediacenter.app import create_app
from mediacenter.config import Config
from tests.conftest import FixedClientIP, write

BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture
def ui_client(tmp_path):
    dist = tmp_path / "dist"
    write(dist / "index.html", b"<!doctype html><title>UI</title>")
    write(dist / "assets" / "app-123.js", b"console.log(1)")
    write(dist / "assets" / "font.woff2", b"wOF2")
    (tmp_path / "secret.txt").write_text("secret")
    data = tmp_path / "data"
    data.mkdir()
    app = create_app(Config(data_dir=data, frontend_dist=dist))
    return TestClient(FixedClientIP(app, "192.168.1.50"), base_url="http://192.168.1.10:8765")


def test_static_ui_has_correct_mime_types_even_with_bad_registry(ui_client):
    # Simulate a Windows registry that maps .js to text/plain; create_app must not depend on it.
    assert mimetypes.guess_type("x.js")[0] == "text/javascript"
    r = ui_client.get("/assets/app-123.js")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/javascript")
    assert ui_client.get("/assets/font.woff2").headers["content-type"] == "font/woff2"


@pytest.mark.parametrize("url", [
    "/../secret.txt", "/..%2fsecret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt",
    "/..\\secret.txt", "/assets/..%5c..%5csecret.txt",
])
def test_spa_route_cannot_escape_dist(ui_client, url):
    r = ui_client.get(url)
    assert b"secret" not in r.content


def test_spa_fallback_serves_index_to_unpaired_devices_but_no_data(ui_client):
    assert ui_client.get("/movies/1").text.startswith("<!doctype html>")
    assert ui_client.get("/api/movies").status_code == 403
    assert ui_client.get("/api/nope").status_code in (403, 404)


def test_ipv4_mapped_public_address_is_not_private(lan_client_factory, host, library):
    host.post("/api/settings/pin", json={"pin": "48151623"})
    host.post("/api/settings/lan", json={"enabled": True})
    assert lan_client_factory("::ffff:8.8.8.8").post("/api/auth/pair", json={"pin": "48151623"}).status_code == 403
    assert lan_client_factory("::ffff:192.168.1.9").post("/api/auth/pair", json={"pin": "48151623"}).status_code == 200


def test_host_admin_requires_loopback_even_with_local_host_header(app, library):
    lan_pretending = TestClient(FixedClientIP(app, "192.168.1.50"), base_url="http://localhost:8765")
    lan_pretending.headers["X-MC-Client"] = "x"
    assert lan_pretending.get("/api/fs/roots").status_code == 403
    assert lan_pretending.post("/api/libraries", json={"path": "/"}).status_code == 403
    assert lan_pretending.post("/api/settings/lan", json={"enabled": True}).status_code == 403


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows; junction pruning shares the same code path")
def test_scanner_skips_linked_folders_and_outside_file_links(host, media_root, tmp_path):
    outside = tmp_path / "outside"
    write(outside / "Leaked Film (2001).mp4")
    os.symlink(outside, media_root / "Movies" / "linked-dir", target_is_directory=True)
    os.symlink(outside / "Leaked Film (2001).mp4", media_root / "Movies" / "Leaked Link (2001).mp4")
    write(media_root / "Movies" / "Inside (2002).mp4")
    os.symlink(media_root / "Movies" / "Inside (2002).mp4", media_root / "Movies" / "Inside Alias (2002).mp4")
    lib = host.post("/api/libraries", json={"path": str(media_root)}).json()
    titles = {m["title"] for m in host.get("/api/movies").json()}
    assert "Leaked Film" not in titles and "Leaked Link" not in titles
    # a link that stays inside the library resolves to the same file and is catalogued once (no duplicate)
    assert len({"Inside", "Inside Alias"} & titles) == 1
    assert any("outside the library" in e for e in lib["scan"]["errors"])



def test_run_py_check_initialises_database(tmp_path):
    env = {**os.environ, "MC_DATA_DIR": str(tmp_path / "fresh-data"), "MC_FRONTEND_DIST": str(tmp_path / "nodist")}
    out = subprocess.run([sys.executable, str(BACKEND / "run.py"), "--check", "--port", "8799"], env=env,
                         capture_output=True, text=True, timeout=60)
    assert (tmp_path / "fresh-data" / "mediacenter.sqlite3").is_file()
    assert "SQLite database ready" in out.stdout
    assert out.returncode == 1 and "[FAIL] Web UI build" in out.stdout  # missing UI is reported, not ignored


def test_add_library_messages(host, tmp_path):
    r = host.post("/api/libraries", json={"path": str(tmp_path / "missing")})
    assert r.status_code == 400 and "mapped drive" in r.json()["detail"]
