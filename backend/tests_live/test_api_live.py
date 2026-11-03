# Live-server API checks (written by the QA run in the dev environment). Needs a running server that already has
# the synthetic sample library added, plus `pip install requests`. Not part of the offline unit suite.
# Run: MC_LIVE_URL=http://127.0.0.1:8765 python -m pytest tests_live -n 0
import os

import pytest

requests = pytest.importorskip("requests")
BASE = (os.environ.get("MC_LIVE_URL") or os.environ.get("REACT_APP_BACKEND_URL", "")).rstrip("/")
H = {"X-MC-Client": "pytest"}
pytestmark = pytest.mark.skipif(not BASE, reason="MC_LIVE_URL not set")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _movie(s, title):
    return next(m for m in s.get(f"{BASE}/api/movies").json() if m["title"] == title)


# --- catalog ---
def test_home_counts(s):
    d = s.get(f"{BASE}/api/home").json()
    assert d["counts"]["movies"] == 3 and d["counts"]["shows"] == 2 and d["counts"]["episodes"] == 3


def test_movies_list(s):
    titles = {m["title"] for m in s.get(f"{BASE}/api/movies").json()}
    assert {"Sample Movie", "Legacy Clip", "Big Test Pattern"} <= titles


def test_movie_detail_nfo(s):
    m = _movie(s, "Sample Movie")
    d = s.get(f"{BASE}/api/movies/{m['id']}").json()
    assert d["year"] == 2024 and d["plot"]


def test_movie_404(s):
    assert s.get(f"{BASE}/api/movies/999999").status_code == 404


def test_shows(s):
    shows = {x["title"]: x for x in s.get(f"{BASE}/api/shows").json()}
    assert "Sample Show" in shows and "Other Series" in shows
    assert shows["Sample Show"]["poster_url"]
    d = s.get(f"{BASE}/api/shows/{shows['Sample Show']['id']}").json()
    eps = d["seasons"][0]["episodes"]
    assert d["seasons"][0]["season_number"] == 1 and [e["episode_number"] for e in eps] == [1, 2]
    o = s.get(f"{BASE}/api/shows/{shows['Other Series']['id']}").json()
    assert o["seasons"][0]["season_number"] == 2 and o["seasons"][0]["episodes"][0]["episode_number"] == 5


def test_art(s):
    shows = {x["title"]: x for x in s.get(f"{BASE}/api/shows").json()}
    r = s.get(BASE + shows["Sample Show"]["poster_url"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/")
    assert s.get(f"{BASE}/api/art/bogus/1").status_code == 404


# --- playback / compatibility ---
def test_playback_supported(s):
    m = _movie(s, "Sample Movie")
    d = s.get(f"{BASE}/api/files/{m['file_id']}/playback").json()
    assert d["compatibility"]["status"] != "unsupported"
    assert d["stream_url"] == f"/api/stream/{m['file_id']}"


def test_playback_avi_unsupported(s):
    m = _movie(s, "Legacy Clip")
    d = s.get(f"{BASE}/api/files/{m['file_id']}/playback").json()
    assert d["compatibility"]["status"] == "unsupported" and d["compatibility"]["reasons"]


# --- streaming ---
def test_stream_range(s):
    m = _movie(s, "Sample Movie")
    r = s.get(f"{BASE}/api/stream/{m['file_id']}", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100
    assert r.headers["Content-Range"].startswith("bytes 0-99/")


def test_stream_head_and_416(s):
    m = _movie(s, "Sample Movie")
    h = s.head(f"{BASE}/api/stream/{m['file_id']}")
    assert h.status_code == 200 and int(h.headers["Content-Length"]) == m["size"]
    r = s.get(f"{BASE}/api/stream/{m['file_id']}", headers={"Range": f"bytes={m['size'] + 10}-"})
    assert r.status_code == 416 and r.headers["Content-Range"] == f"bytes */{m['size']}"


def test_stream_suffix_range(s):
    m = _movie(s, "Sample Movie")
    r = s.get(f"{BASE}/api/stream/{m['file_id']}", headers={"Range": "bytes=-50"})
    assert r.status_code == 206 and len(r.content) == 50


# --- progress ---
def test_progress_roundtrip_and_csrf(s):
    m = _movie(s, "Big Test Pattern")
    fid = m["file_id"]
    assert s.put(f"{BASE}/api/progress/{fid}", json={"position": 20, "duration": 100}).status_code == 403
    r = s.put(f"{BASE}/api/progress/{fid}", json={"position": 20, "duration": 100}, headers=H)
    assert r.status_code == 200 and r.json()["watched"] is False
    assert s.get(f"{BASE}/api/files/{fid}/playback").json()["progress"]["position"] == 20
    assert any(c["file_id"] == fid for c in s.get(f"{BASE}/api/home").json()["continue_watching"])
    assert s.put(f"{BASE}/api/progress/{fid}", json={"position": -1}, headers=H).status_code == 422
    assert s.delete(f"{BASE}/api/progress/{fid}", headers=H).status_code == 200
    assert s.get(f"{BASE}/api/files/{fid}/playback").json()["progress"] is None


# --- admin ---
def test_rescan_no_duplicates(s):
    lib = next(l for l in s.get(f"{BASE}/api/libraries").json() if l["path"] == "/app/sample_media")
    r = s.post(f"{BASE}/api/libraries/{lib['id']}/scan", headers=H).json()
    assert r["scan"]["added"] == 0 and r["scan"]["files_found"] == 6
    assert s.get(f"{BASE}/api/home").json()["counts"]["movies"] == 3


def test_add_library_errors(s):
    for path, code in [("/app/sample_media", 409), ("/app/sample_media/Movies", 409), ("/app", 409),
                       ("/nope", 400), ("relative/path", 400), ("", 422)]:
        r = s.post(f"{BASE}/api/libraries", json={"path": path}, headers=H)
        assert r.status_code == code, (path, r.status_code, r.text)


def test_fs_browser(s):
    roots = s.get(f"{BASE}/api/fs/roots").json()["roots"]
    assert any(r["path"] == "/" for r in roots)
    d = s.get(f"{BASE}/api/fs/list", params={"path": "/app"}).json()
    assert any(x["name"] == "sample_media" for x in d["dirs"]) and d["parent"] == "/"
    assert s.get(f"{BASE}/api/fs/list", params={"path": "/nope"}).status_code == 404
    assert s.get(f"{BASE}/api/fs/list", params={"path": "x"}).status_code == 400


def test_pin_validation_and_lan(s):
    assert s.post(f"{BASE}/api/settings/pin", json={"pin": "1234567"}, headers=H).status_code == 400
    assert s.post(f"{BASE}/api/settings/pin", json={"pin": "12345678"}, headers=H).status_code == 400
    assert s.post(f"{BASE}/api/settings/pin", json={"pin": "11111111"}, headers=H).status_code == 400
    assert s.post(f"{BASE}/api/settings/pin", json={"pin": "abcdefgh"}, headers=H).status_code == 400
    assert s.post(f"{BASE}/api/settings/lan", json={"enabled": True}).status_code == 403  # CSRF
    r = s.post(f"{BASE}/api/settings/lan", json={"enabled": False}, headers=H)
    assert r.status_code == 200 and r.json()["lan"]["enabled"] is False
    assert isinstance(s.get(f"{BASE}/api/devices").json(), list)
