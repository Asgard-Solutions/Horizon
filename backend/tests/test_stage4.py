"""Stage 4: background scans, cancel/interrupt safety, unreachable sources, playback preferences, metadata reader control."""
import shutil
import threading
import time

from fastapi.testclient import TestClient

from tests.conftest import HOST_HEADERS, FixedClientIP
from mediacenter import paths
from mediacenter.app import create_app
from mediacenter.db import connect
from mediacenter.scanner import scan_library


def wait_idle(host, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        s = host.get("/api/scans").json()
        if not s["running"] and not s["queued"]:
            return s
        time.sleep(0.05)
    raise AssertionError("scans did not finish")


def titles(host):
    return {m["title"] for m in host.get("/api/movies").json()}


def lib_row(host, lib_id):
    return next(lib for lib in host.get("/api/libraries").json() if lib["id"] == lib_id)


def test_background_scan_reports_progress_and_success(host, media_root):
    lib = host.post("/api/libraries", json={"path": str(media_root), "scan": False}).json()
    assert lib["last_success_at"] is None and titles(host) == set()
    s = host.post("/api/scans", json={"library_id": lib["id"]}).json()
    assert (s["running"] or s["queued"])
    s = wait_idle(host)
    job = s["recent"][0]
    assert job["state"] == "done" and job["files_found"] == 7 and job["summary"]["status"] == "complete"
    row = lib_row(host, lib["id"])
    assert row["last_success_at"] and row["details"]["files"] == 7 and row["details"]["shows"] == 2
    assert "Sample Movie" in titles(host)


def test_rescan_all_queues_each_source_once(host, media_root, tmp_path):
    other = tmp_path / "other"
    shutil.copytree(media_root / "Movies", other / "Films")
    a = host.post("/api/libraries", json={"path": str(media_root), "scan": False}).json()
    b = host.post("/api/libraries", json={"path": str(other), "scan": False}).json()
    host.post("/api/scans", json={})
    host.post("/api/scans", json={})  # pressing Rescan All twice does not double-queue
    s = wait_idle(host)
    done = [j["library_id"] for j in s["recent"]]
    assert sorted(done) == sorted([a["id"], b["id"]])


def test_cancelled_scan_never_removes_titles(app, host, library, media_root):
    (media_root / "Movies" / "Another.Film.2019.1080p.BluRay.x264.mkv").unlink()
    cancel = threading.Event()
    conn = connect(app.state.config.db_path)
    row = dict(conn.execute("SELECT * FROM libraries WHERE id = ?", (library["id"],)).fetchone())
    summary = scan_library(conn, row, progress=lambda *_: cancel.set(), cancel=cancel)
    conn.close()
    assert summary["status"] == "cancelled" and summary["removed"] == 0
    assert "Another Film" in titles(host)  # only a complete scan may remove it
    host.post(f"/api/libraries/{library['id']}/scan")
    assert "Another Film" not in titles(host)


def test_interrupted_scan_keeps_catalog_and_progress(app, host, library, media_root, monkeypatch):
    m = next(m for m in host.get("/api/movies").json() if m["title"] == "Sample Movie")
    host.put(f"/api/progress/{m['file_id']}", json={"position": 30, "duration": 100})
    before = titles(host)
    for f in (media_root / "TV").rglob("*.mkv"):
        f.unlink()
    import mediacenter.scanjobs as sj

    def crash(conn, lib, progress=None, cancel=None):  # e.g. NAS dropped / process killed mid-walk
        raise OSError("network name is no longer available")
    monkeypatch.setattr(sj, "scan_library", crash)
    host.post("/api/scans", json={"library_id": library["id"]})
    job = wait_idle(host)["recent"][0]
    assert job["state"] == "failed" and "no longer available" in job["summary"]["errors"][0]
    assert titles(host) == before and host.get("/api/shows").json()
    p = host.get(f"/api/movies/{m['id']}").json()["progress"]
    assert p["position"] == 30


def test_unreachable_source_scan_keeps_everything(host, library, media_root, tmp_path):
    before = titles(host)
    first_success = lib_row(host, library["id"])["last_success_at"]
    media_root.rename(tmp_path / "nas-offline")
    host.post("/api/scans", json={"library_id": library["id"]})
    job = wait_idle(host)["recent"][0]
    assert job["state"] == "unreachable"
    row = lib_row(host, library["id"])
    assert row["reachable"] is False and row["last_success_at"] == first_success
    assert titles(host) == before
    (tmp_path / "nas-offline").rename(media_root)
    assert lib_row(host, library["id"])["reachable"] is True


def test_cancel_all_cancels_queued_jobs(host, media_root, tmp_path):
    libs = []
    for i in range(3):
        d = tmp_path / f"src{i}"
        shutil.copytree(media_root, d)
        libs.append(host.post("/api/libraries", json={"path": str(d), "scan": False}).json())
    host.post("/api/scans", json={})
    s = host.post("/api/scans/cancel", json={}).json()
    assert not s["queued"]
    s = wait_idle(host)
    assert all(j["state"] in ("cancelled", "done") for j in s["recent"])
    assert any(j["state"] == "cancelled" for j in s["recent"])


def test_remove_source_while_scanning_is_safe(host, library, media_root):
    files = sorted(p.name for p in media_root.rglob("*"))
    host.post("/api/scans", json={"library_id": library["id"]})
    assert host.delete(f"/api/libraries/{library['id']}").json() == {"ok": True}
    wait_idle(host)
    assert host.get("/api/libraries").json() == [] and titles(host) == set()
    assert sorted(p.name for p in media_root.rglob("*")) == files  # media files untouched


def test_slow_network_path_reports_unreachable_quickly(monkeypatch):
    monkeypatch.setattr(paths, "REACH_TIMEOUT_S", 0.3)
    monkeypatch.setattr(paths.os.path, "isdir", lambda p: time.sleep(2) or True)
    t = time.time()
    assert paths.dir_reachable("\\\\NAS-OFF\\Media") is False
    assert paths.dir_reachable("\\\\NAS-OFF\\Media") is False  # remembered; no second wait
    assert time.time() - t < 1.0


def test_preferences_defaults_validation_and_persistence(app, host):
    assert host.get("/api/preferences").json() == {"resume": "ask", "autoplay_next": False, "skip_seconds": 10,
                                                   "watched_threshold": "95"}
    assert host.put("/api/preferences", json={"skip_seconds": 15}).status_code == 422
    assert host.put("/api/preferences", json={"watched_threshold": "80"}).status_code == 422
    r = host.put("/api/preferences", json={"skip_seconds": 30, "autoplay_next": True}).json()
    assert r["skip_seconds"] == 30 and r["autoplay_next"] is True and r["resume"] == "ask"
    restarted = TestClient(FixedClientIP(create_app(app.state.config), "127.0.0.1"), base_url="http://localhost:8765")
    restarted.headers.update(HOST_HEADERS)
    assert restarted.get("/api/preferences").json()["skip_seconds"] == 30


def test_watched_threshold_applies_to_new_saves_only(host, library):
    movies = host.get("/api/movies").json()
    a, b = movies[0]["file_id"], movies[1]["file_id"]
    assert host.put(f"/api/progress/{a}", json={"position": 93, "duration": 100}).json()["watched"] is False  # 95% default
    assert host.put(f"/api/progress/{b}", json={"position": 96, "duration": 100}).json()["watched"] is True
    host.put("/api/preferences", json={"watched_threshold": "end"})
    assert host.get(f"/api/movies/{movies[1]['id']}").json()["progress"]["watched"] is True  # history not rewritten
    assert host.put(f"/api/progress/{a}", json={"position": 97, "duration": 100}).json()["watched"] is False
    assert host.put(f"/api/progress/{a}", json={"position": 98.5, "duration": 100}).json()["watched"] is True
    host.put("/api/preferences", json={"watched_threshold": "90"})
    ep = host.get("/api/shows").json()[0]
    show = host.get(f"/api/shows/{ep['id']}").json()
    efid = show["seasons"][0]["episodes"][0]["file_id"]
    assert host.put(f"/api/progress/{efid}", json={"position": 91, "duration": 100}).json()["watched"] is True


def test_metadata_reader_pause_persists_across_restart(app, host):
    s = host.post("/api/metadata/reader", json={"paused": True}).json()
    assert s["paused"] is True
    assert create_app(app.state.config).state.durations.paused is True
    assert host.post("/api/metadata/reader", json={"paused": False}).json()["paused"] is False
    assert host.post("/api/metadata/retry").status_code == 200


def test_restart_does_not_rescan_and_keeps_progress(app, host, library, media_root):
    m = host.get("/api/movies").json()[0]
    host.put(f"/api/progress/{m['file_id']}", json={"position": 12, "duration": 100})
    last = lib_row(host, library["id"])["last_scan_at"]
    app2 = create_app(app.state.config)
    with TestClient(FixedClientIP(app2, "127.0.0.1"), base_url="http://localhost:8765") as c:
        c.headers.update(HOST_HEADERS)
        assert c.get("/api/scans").json() == {"running": None, "queued": [], "recent": []}
        assert next(x for x in c.get("/api/libraries").json() if x["id"] == library["id"])["last_scan_at"] == last
        assert c.get(f"/api/movies/{m['id']}").json()["progress"]["position"] == 12
