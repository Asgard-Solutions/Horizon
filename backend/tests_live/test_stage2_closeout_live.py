# Stage 2 closeout: background duration reader, demo-series isolation, runtime_status (live, via public URL)
# Adds and removes a temporary library, so run the live suite serially: python -m pytest tests_live -n 0
import os
import shutil
import time
import uuid

import pytest
import requests

BASE_URL = (os.environ.get("MC_LIVE_URL") or os.environ["REACT_APP_BACKEND_URL"]).rstrip("/")
H = {"X-MC-Client": "web"}
SAMPLE = os.environ.get("MC_LIVE_SAMPLE") or "/app/sample_media"
DEMO = os.environ.get("MC_LIVE_DEMO") or "/app/test_media/horizon_demo"


@pytest.fixture(scope="module")
def s():
    x = requests.Session()
    x.headers.update(H)
    return x


def _show(s, title):
    shows = s.get(f"{BASE_URL}/api/shows").json()
    return next((x for x in shows if x["title"] == title), None)


# metadata status endpoint
def test_metadata_status_shape(s):
    r = s.get(f"{BASE_URL}/api/metadata/status")
    assert r.status_code == 200
    d = r.json()
    for k in ["available", "workers", "pending", "known", "unknown", "active", "unreachable"]:
        assert k in d
    assert d["available"] is True and d["workers"] == 2
    assert d["pending"] == 0 and d["known"] >= 11


# libraries: production vs test-only demo library
def test_library_isolation(s):
    libs = {l["path"]: l for l in s.get(f"{BASE_URL}/api/libraries").json()}
    assert SAMPLE in libs and DEMO in libs
    assert libs[DEMO]["name"] == "Horizon demo (test only)"
    assert libs[DEMO]["counts"] == {"movies": 0, "episodes": 5}
    assert not any("Northern" in d for _, dirs, _ in os.walk(SAMPLE) for d in dirs)


# Northern Survey runtimes read in background (unplayed)
def test_northern_survey_runtimes(s):
    show = _show(s, "Northern Survey")
    assert show
    d = s.get(f"{BASE_URL}/api/shows/{show['id']}").json()
    seasons = {x["season_number"]: x["episodes"] for x in d["seasons"]}
    assert len(seasons[1]) == 3 and len(seasons[2]) == 2
    for ep in seasons[1]:
        assert ep["runtime_status"] == "known" and abs(ep["runtime"] - 40) < 1
    for ep in seasons[2]:
        assert ep["runtime_status"] == "known" and abs(ep["runtime"] - 35) < 1


def test_movies_runtime_status(s):
    movies = s.get(f"{BASE_URL}/api/movies").json()
    titles = {m["title"] for m in movies}
    assert {"Sample Movie", "Big Test Pattern", "Legacy Clip"} <= titles
    for m in movies:
        assert m["runtime_status"] in ("known", "pending", "unknown")


def test_scan_existing_library_fast(s):
    t = time.time()
    r = s.post(f"{BASE_URL}/api/libraries/1/scan")
    assert r.status_code == 200
    assert time.time() - t < 5
    assert r.json()["scan"]["errors"] == []


def test_scan_requires_client_header():
    r = requests.post(f"{BASE_URL}/api/libraries/1/scan")
    assert r.status_code in (400, 401, 403)


# new files in a temporary TEST_ library get their length in the background after scan
def test_background_reader_new_library(s):
    root = f"/tmp/TEST_mc_{uuid.uuid4().hex[:6]}"
    os.makedirs(f"{root}/Movies")
    shutil.copy(f"{SAMPLE}/Movies/Sample Movie (2024).mp4", f"{root}/Movies/TEST Bgread Film (2001).mp4")
    lib_id = None
    try:
        t = time.time()
        r = s.post(f"{BASE_URL}/api/libraries", json={"path": root, "name": "TEST_bg", "scan": True})
        assert r.status_code == 200, r.text
        lib_id = r.json()["id"]
        assert time.time() - t < 5
        deadline = time.time() + 30
        movie = None
        while time.time() < deadline:
            movie = next((m for m in s.get(f"{BASE_URL}/api/movies").json() if m["title"] == "TEST Bgread Film"), None)
            if movie and movie["runtime_status"] == "known":
                break
            time.sleep(1)
        assert movie and movie["runtime_status"] == "known" and abs(movie["runtime"] - 90) < 1
        assert s.get(f"{BASE_URL}/api/metadata/status").json()["pending"] == 0
    finally:
        if lib_id:
            assert s.delete(f"{BASE_URL}/api/libraries/{lib_id}").status_code == 200
        shutil.rmtree(root, ignore_errors=True)
    assert not any(m["title"] == "TEST Bgread Film" for m in s.get(f"{BASE_URL}/api/movies").json())
