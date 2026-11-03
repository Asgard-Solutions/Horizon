import hashlib
import os
import shutil

from mediacenter.db import connect


def snapshot(root):
    """Content hash, size and mtime of every file + the directory listing."""
    state = {}
    for dirpath, dirnames, filenames in os.walk(root):
        state[dirpath] = sorted(dirnames + filenames)
        for name in filenames:
            p = os.path.join(dirpath, name)
            st = os.stat(p)
            with open(p, "rb") as fh:
                state[p] = (hashlib.sha256(fh.read()).hexdigest(), st.st_size, st.st_mtime_ns)
    return state


def counts(app):
    conn = connect(app.state.config.db_path)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("media_files", "movies", "shows", "seasons", "episodes")}
    finally:
        conn.close()


def test_scan_builds_library_structure(host, library):
    summary = library["scan"]
    assert summary["files_found"] == 7
    assert summary["movies"] == 3 and summary["episodes"] == 4
    assert summary["errors"] == []

    movies = {m["title"]: m for m in host.get("/api/movies").json()}
    assert set(movies) == {"Sample Movie", "Another Film", "Old Classic"}
    assert movies["Sample Movie"]["year"] == 2024 and movies["Sample Movie"]["plot"] == "Plot text"
    assert movies["Old Classic"]["poster_url"]  # dedicated folder -> poster.jpg used
    assert movies["Sample Movie"]["poster_url"] is None  # shared folder -> no stray poster

    shows = {s["title"]: s for s in host.get("/api/shows").json()}
    assert set(shows) == {"Sample Show", "Flat Show"}
    sample = host.get(f"/api/shows/{shows['Sample Show']['id']}").json()
    assert sample["plot"] == "Show plot" and sample["poster_url"]
    assert [s["season_number"] for s in sample["seasons"]] == [1, 2]
    assert [e["episode_number"] for e in sample["seasons"][0]["episodes"]] == [1, 2]
    assert sample["seasons"][1]["episodes"][0]["title"] == "The Return"
    flat = host.get(f"/api/shows/{shows['Flat Show']['id']}").json()
    assert flat["seasons"][0]["season_number"] == 3
    assert flat["seasons"][0]["episodes"][0]["episode_number"] == 7


def test_rescan_does_not_duplicate(app, host, library):
    before = counts(app)
    ids_before = sorted(m["file_id"] for m in host.get("/api/movies").json())
    for _ in range(3):
        res = host.post(f"/api/libraries/{library['id']}/scan").json()
        assert res["scan"]["added"] == 0 and res["scan"]["unchanged"] == 7 and res["scan"]["removed"] == 0
    assert counts(app) == before
    assert sorted(m["file_id"] for m in host.get("/api/movies").json()) == ids_before


def test_adding_same_or_nested_folder_is_rejected(host, library, media_root):
    assert host.post("/api/libraries", json={"path": str(media_root)}).status_code == 409
    assert host.post("/api/libraries", json={"path": str(media_root) + os.sep}).status_code == 409
    assert host.post("/api/libraries", json={"path": str(media_root / "Movies")}).status_code == 409
    assert host.post("/api/libraries", json={"path": str(media_root.parent)}).status_code == 409


def test_rescan_picks_up_removed_and_new_files(app, host, library, media_root, tmp_path):
    # Simulate the *user* changing their folder outside the app.
    shutil.move(str(media_root / "Movies" / "Another.Film.2019.1080p.BluRay.x264.mkv"), str(tmp_path / "moved.mkv"))
    (media_root / "TV" / "Sample Show" / "Season 01" / "Sample Show - S01E03.mkv").write_bytes(b"\x00" * 10)
    res = host.post(f"/api/libraries/{library['id']}/scan").json()["scan"]
    assert res["removed"] == 1 and res["added"] == 1
    titles = {m["title"] for m in host.get("/api/movies").json()}
    assert "Another Film" not in titles
    assert counts(app)["episodes"] == 5


def test_unreachable_folder_keeps_catalog(app, host, library, media_root, tmp_path):
    before = counts(app)
    media_root.rename(tmp_path / "offline")
    res = host.post(f"/api/libraries/{library['id']}/scan").json()
    assert res["scan"]["errors"] and res["scan"]["removed"] == 0
    assert res["reachable"] is False
    assert counts(app) == before


def test_scanning_never_modifies_source_files(host, media_root):
    before = snapshot(media_root)
    lib = host.post("/api/libraries", json={"path": str(media_root)}).json()
    host.post(f"/api/libraries/{lib['id']}/scan")
    for m in host.get("/api/movies").json():
        host.get(f"/api/files/{m['file_id']}/playback")
        host.get(f"/api/stream/{m['file_id']}", headers={"Range": "bytes=0-99"})
    host.delete(f"/api/libraries/{lib['id']}")
    assert snapshot(media_root) == before


def test_remove_library_clears_catalog_only(app, host, library, media_root):
    assert host.delete(f"/api/libraries/{library['id']}").status_code == 200
    assert counts(app) == {"media_files": 0, "movies": 0, "shows": 0, "seasons": 0, "episodes": 0}
    assert (media_root / "Movies" / "Sample Movie (2024).mp4").is_file()


def test_invalid_paths_are_rejected(host, tmp_path):
    assert host.post("/api/libraries", json={"path": "relative/path"}).status_code == 400
    assert host.post("/api/libraries", json={"path": str(tmp_path / "missing")}).status_code == 400
    f = tmp_path / "file.mp4"
    f.write_bytes(b"x")
    assert host.post("/api/libraries", json={"path": str(f)}).status_code == 400


def test_progress_save_and_restore(host, library):
    movie = next(m for m in host.get("/api/movies").json() if m["title"] == "Sample Movie")
    r = host.put(f"/api/progress/{movie['file_id']}", json={"position": 42.5, "duration": 100})
    assert r.status_code == 200 and r.json()["watched"] is False
    info = host.get(f"/api/files/{movie['file_id']}/playback").json()
    assert info["progress"]["position"] == 42.5
    home = host.get("/api/home").json()
    assert [c["file_id"] for c in home["continue_watching"]] == [movie["file_id"]]
    assert host.put(f"/api/progress/{movie['file_id']}", json={"position": 95, "duration": 100}).json()["watched"]
    assert host.get("/api/home").json()["continue_watching"] == []
    # progress survives a rescan
    host.post(f"/api/libraries/{library['id']}/scan")
    assert host.get(f"/api/files/{movie['file_id']}/playback").json()["progress"]["position"] == 95
