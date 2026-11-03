# Watch progress survives a title being removed and restored at the same path, and a library being removed and re-added.
# Uses its own temporary TEST_ folder (copied media); run serially: python -m pytest tests_live -n 0
import os
import shutil
import uuid

import requests

BASE_URL = (os.environ.get("MC_LIVE_URL") or os.environ["REACT_APP_BACKEND_URL"]).rstrip("/")
SAMPLE = os.environ.get("MC_LIVE_SAMPLE") or "/app/sample_media"
H = {"X-MC-Client": "pytest"}


def _movie(s, lib_title):
    return next((m for m in s.get(f"{BASE_URL}/api/movies").json() if m["title"] == lib_title), None)


def test_progress_survives_remove_and_restore():
    s = requests.Session()
    s.headers.update(H)
    tag = uuid.uuid4().hex[:8]
    root = f"/tmp/TEST_mc_readd_{tag}"
    title = f"TEST Readd {tag}"
    os.makedirs(f"{root}/Movies")
    src = f"{SAMPLE}/Movies/Sample Movie (2024).mp4"
    dst = f"{root}/Movies/{title} (2001).mp4"
    shutil.copy(src, dst)
    lib = s.post(f"{BASE_URL}/api/libraries", json={"path": root, "name": f"TEST_readd_{tag}", "scan": True}).json()
    try:
        m = _movie(s, title)
        assert m
        fid = s.get(f"{BASE_URL}/api/movies/{m['id']}").json()["file_id"]
        assert s.put(f"{BASE_URL}/api/progress/{fid}", json={"position": 42.5, "duration": 90.0}).status_code == 200

        # 1) the file disappears and the title is removed by a rescan
        os.rename(dst, f"{root}/hidden.bin")
        s.post(f"{BASE_URL}/api/libraries/{lib['id']}/scan")
        assert _movie(s, title) is None
        # ...then it comes back at the same path: same progress (the title row itself is recreated)
        os.rename(f"{root}/hidden.bin", dst)
        s.post(f"{BASE_URL}/api/libraries/{lib['id']}/scan")
        m2 = _movie(s, title)
        assert m2
        p = s.get(f"{BASE_URL}/api/movies/{m2['id']}").json()["progress"]
        assert p and abs(p["position"] - 42.5) < 0.01 and not p["watched"]

        # 2) the whole library is removed and added again
        assert s.delete(f"{BASE_URL}/api/libraries/{lib['id']}").status_code == 200
        assert _movie(s, title) is None
        lib = s.post(f"{BASE_URL}/api/libraries", json={"path": root, "name": f"TEST_readd_{tag}", "scan": True}).json()
        m3 = _movie(s, title)
        p = s.get(f"{BASE_URL}/api/movies/{m3['id']}").json()["progress"]
        assert p and abs(p["position"] - 42.5) < 0.01
    finally:
        fid = s.get(f"{BASE_URL}/api/movies/{_movie(s, title)['id']}").json()["file_id"] if _movie(s, title) else None
        if fid:
            s.delete(f"{BASE_URL}/api/progress/{fid}")
        s.delete(f"{BASE_URL}/api/libraries/{lib['id']}")
        shutil.rmtree(root, ignore_errors=True)
