"""Background media-length reading: read-only, cached, resumable, prioritized, concurrency-limited."""
import hashlib
import json
import shutil
import subprocess
import threading
import time

import pytest

from mediacenter import durations as dmod
from mediacenter.db import connect
from mediacenter.durations import DurationWorker

needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not installed")


def make_clip(path, seconds):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size=160x90:rate=10",
                    "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime, path.stat().st_size


@pytest.fixture
def clips(tmp_path):
    root = tmp_path / "lib"
    make_clip(root / "Movies" / "Short Film (2020).mp4", 3)
    make_clip(root / "TV" / "Demo" / "Season 01" / "Demo - S01E01.mp4", 2)
    make_clip(root / "TV" / "Demo" / "Season 01" / "Demo - S01E02.mp4", 4)
    (root / "Movies" / "Broken (2001).mkv").write_bytes(b"not really a video" * 100)
    return root


def worker_for(app, workers=1):
    cfg = app.state.config
    return DurationWorker(cfg.db_path, shutil.which("ffprobe"), workers)


def rows(app):
    conn = connect(app.state.config.db_path)
    try:
        return {r["filename"]: r["probe_json"] for r in conn.execute("SELECT filename, probe_json FROM media_files")}
    finally:
        conn.close()


@needs_ffmpeg
def test_scan_stays_fast_and_lengths_arrive_after(app, host, clips):
    lib = host.post("/api/libraries", json={"path": str(clips)}).json()
    assert lib["counts"]["movies"] == 2
    # The scan itself never runs FFprobe: everything is pending afterwards.
    assert all(v is None for v in rows(app).values())
    show = host.get("/api/shows").json()[0]
    eps = host.get(f"/api/shows/{show['id']}").json()["seasons"][0]["episodes"]
    assert {e["runtime_status"] for e in eps} == {"pending"}
    assert all(e["runtime"] is None for e in eps)
    app.state.durations = w = worker_for(app)
    assert w.run_until_idle() == 4
    eps = host.get(f"/api/shows/{show['id']}").json()["seasons"][0]["episodes"]
    assert [round(e["runtime"]) for e in eps] == [2, 4]
    assert {e["runtime_status"] for e in eps} == {"known"}
    status = host.get("/api/metadata/status").json()
    assert status["pending"] == 0 and status["known"] == 3 and status["unknown"] == 1


@needs_ffmpeg
def test_unreadable_file_is_cached_as_unknown_not_retried(app, host, clips):
    host.post("/api/libraries", json={"path": str(clips)})
    app.state.durations = w = worker_for(app)
    w.run_until_idle()
    broken = next(m for m in host.get("/api/movies").json() if m["title"] == "Broken")
    assert broken["runtime"] is None and broken["runtime_status"] == "unknown"
    assert json.loads(rows(app)["Broken (2001).mkv"]).get("error")
    assert w.run_until_idle() == 0  # cached failure: no repeated processing


@needs_ffmpeg
def test_media_files_are_never_modified(app, host, clips):
    files = sorted(p for p in clips.rglob("*") if p.is_file())
    before = {p: digest(p) for p in files}
    host.post("/api/libraries", json={"path": str(clips)})
    worker_for(app).run_until_idle()
    assert sorted(p for p in clips.rglob("*") if p.is_file()) == files
    assert {p: digest(p) for p in files} == before


@needs_ffmpeg
def test_resumes_after_restart(app, host, clips, monkeypatch):
    host.post("/api/libraries", json={"path": str(clips)})
    first = worker_for(app)
    real_claim = first._claim
    calls = {"n": 0}

    def stop_after_two(conn, block):
        calls["n"] += 1
        return real_claim(conn, block) if calls["n"] <= 2 else None
    monkeypatch.setattr(first, "_claim", stop_after_two)
    assert first.run_until_idle() == 2  # "app closed" mid-way
    assert sum(v is None for v in rows(app).values()) == 2
    assert worker_for(app).run_until_idle() == 2  # a fresh process picks up the rest from SQLite
    assert all(v is not None for v in rows(app).values())


@needs_ffmpeg
def test_changed_file_is_read_again(app, host, clips):
    lib = host.post("/api/libraries", json={"path": str(clips)}).json()
    w = worker_for(app)
    w.run_until_idle()
    make_clip(clips / "Movies" / "Short Film (2020).mp4", 5)
    host.post(f"/api/libraries/{lib['id']}/scan")
    assert rows(app)["Short Film (2020).mp4"] is None
    assert w.run_until_idle() == 1
    film = next(m for m in host.get("/api/movies").json() if m["title"] == "Short Film")
    assert round(film["runtime"]) == 5


@needs_ffmpeg
def test_visible_items_are_read_first(app, host, clips):
    host.post("/api/libraries", json={"path": str(clips)})
    app.state.durations = w = worker_for(app)
    show = host.get("/api/shows").json()[0]
    host.get(f"/api/shows/{show['id']}")  # viewer opens the show page
    conn = connect(app.state.config.db_path)
    try:
        first = w._next(conn)
        names = {r["id"]: r["filename"] for r in conn.execute("SELECT id, filename FROM media_files")}
    finally:
        conn.close()
    assert names[first["id"]].startswith("Demo - S01E")


def test_missing_file_is_skipped_not_cached(app, host, media_root):
    host.post("/api/libraries", json={"path": str(media_root)})
    (media_root / "TV" / "Flat.Show.S03E07.720p.WEB-DL.mp4").unlink()  # e.g. NAS went offline after the scan
    w = DurationWorker(app.state.config.db_path, shutil.which("ffprobe") or "/bin/false", 1)
    w.run_until_idle()
    assert rows(app)["Flat.Show.S03E07.720p.WEB-DL.mp4"] is None  # still pending: retried after a rescan/restart
    assert w.status(connect(app.state.config.db_path))["unreachable"] >= 1


def test_no_ffprobe_means_unknown_not_pending(app, host, media_root, monkeypatch):
    monkeypatch.setattr(dmod, "find_ffprobe", lambda _p: None)
    app.state.durations = DurationWorker(app.state.config.db_path, None, 2)
    host.post("/api/libraries", json={"path": str(media_root)})
    assert {m["runtime_status"] for m in host.get("/api/movies").json()} == {"unknown"}
    assert host.get("/api/metadata/status").json()["available"] is False


def test_concurrency_is_limited(app, host, media_root, monkeypatch):
    host.post("/api/libraries", json={"path": str(media_root)})
    lock, active, peak = threading.Lock(), [0], [0]

    def slow_probe(_ffprobe, _path, background=False):
        assert background
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.15)
        with lock:
            active[0] -= 1
        return {"duration": 12.0, "video": [], "audio": [], "subtitles": []}
    monkeypatch.setattr(dmod, "probe_file", slow_probe)
    w = DurationWorker(app.state.config.db_path, shutil.which("ffprobe") or "/bin/true", 2)
    w.ffprobe = w.ffprobe or "/bin/true"
    w.start()
    try:
        deadline = time.time() + 10
        while any(v is None for v in rows(app).values()) and time.time() < deadline:
            time.sleep(0.05)
    finally:
        w.stop()
    assert all(v is not None for v in rows(app).values())
    assert peak[0] == 2
