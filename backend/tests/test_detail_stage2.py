# Horizon Stage 2: movie/show detail API fields (runtime, progress, art) and progress round-trip (public URL)
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="no public URL")


@pytest.fixture(scope="module")
def s():
    x = requests.Session()
    x.headers.update({"X-MC-Client": "web"})
    return x


# Movie detail
def test_movie_detail_sample(s):
    r = s.get(f"{BASE_URL}/api/movies/2")
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Sample Movie"
    assert d["fanart_url"]
    assert "runtime" in d
    assert d["progress"] is None or isinstance(d["progress"]["position"], (int, float))


def test_movie_poster_only(s):
    d = s.get(f"{BASE_URL}/api/movies/3").json()
    assert d["poster_url"] and not d["fanart_url"]


def test_movie_404(s):
    assert s.get(f"{BASE_URL}/api/movies/99999").status_code == 404


# Show detail structure
def test_show_detail_northern_survey(s):
    r = s.get(f"{BASE_URL}/api/shows/3")
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Northern Survey"
    counts = {x["season_number"]: len(x["episodes"]) for x in d["seasons"]}
    assert counts == {1: 3, 2: 2}
    for season in d["seasons"]:
        for ep in season["episodes"]:
            assert "runtime" in ep and "progress" in ep and "file_id" in ep


def test_art_served(s):
    for path in ["/api/art/movie-fanart/2", "/api/art/movie-poster/3", "/api/art/show-fanart/3"]:
        r = s.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, path
        assert r.headers["content-type"].startswith("image/")


# Progress round-trip on an episode (restored afterwards)
def test_progress_watched_roundtrip(s):
    show = s.get(f"{BASE_URL}/api/shows/3").json()
    ep = show["seasons"][1]["episodes"][1]  # S2E2
    original = ep["progress"]
    fid = ep["file_id"]
    try:
        r = s.put(f"{BASE_URL}/api/progress/{fid}", json={"position": 37, "duration": 40})
        assert r.status_code in (200, 204)
        show2 = s.get(f"{BASE_URL}/api/shows/3").json()
        ep2 = [e for se in show2["seasons"] for e in se["episodes"] if e["file_id"] == fid][0]
        assert ep2["progress"]["watched"] is True
        assert ep2["runtime"] == 40
    finally:
        if original:
            s.put(f"{BASE_URL}/api/progress/{fid}", json={"position": original["position"], "duration": original["duration"]})
        else:
            s.delete(f"{BASE_URL}/api/progress/{fid}")
