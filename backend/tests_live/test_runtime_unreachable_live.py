# runtime_status 'unknown' for files the background reader could not reach; 'pending' again after a rescan (live)
# Adds and removes a temporary TEST_ library; run serially: python -m pytest tests_live -n 0
import os
import time
import uuid

import requests

BASE_URL = (os.environ.get("MC_LIVE_URL") or os.environ["REACT_APP_BACKEND_URL"]).rstrip("/")
H = {"X-MC-Client": "web"}
SAMPLE = os.environ.get("MC_LIVE_SAMPLE") or "/app/sample_media"
DEMO = os.environ.get("MC_LIVE_DEMO") or "/app/test_media/horizon_demo"
SRC = f"{DEMO}/TV/Northern Survey (2022)/Season 01/Northern Survey - S01E01 - Arrival.mp4"
N = 150
GONE = [N - 4, N - 3, N - 2, N - 1, N]


def _episodes(s, title):
    show = next((x for x in s.get(f"{BASE_URL}/api/shows").json() if x["title"] == title), None)
    if not show:
        return {}
    d = s.get(f"{BASE_URL}/api/shows/{show['id']}").json()
    return {e["episode_number"]: e for sn in d["seasons"] for e in sn["episodes"]}


def test_unreachable_file_reports_unknown_then_pending_after_rescan():
    s = requests.Session()
    s.headers.update(H)
    tag = uuid.uuid4().hex[:6]
    title = f"TEST Unreach {tag}"
    root = f"/tmp/TEST_mc_unreach_{tag}"
    sdir = f"{root}/TV/{title} (2020)/Season 01"
    os.makedirs(sdir)
    seed = f"{root}/seed.bin"
    import shutil
    shutil.copy(SRC, seed)
    paths = {}
    for i in range(1, N + 1):
        p = f"{sdir}/{title} - S01E{i:03d}.mp4"
        os.link(seed, p)
        paths[i] = p
    lib_id = None
    try:
        r = s.post(f"{BASE_URL}/api/libraries", json={"path": root, "name": f"TEST_unreach_{tag}", "scan": True})
        assert r.status_code == 200, r.text
        lib_id = r.json()["id"]
        for i in GONE:
            os.remove(paths[i])
        deadline = time.time() + 60
        eps = {}
        while time.time() < deadline:
            eps = _episodes(s, title)
            if eps and not any(e["runtime_status"] == "pending" for e in eps.values()):
                break
            time.sleep(1)
        statuses = {i: eps[i]["runtime_status"] for i in GONE}
        print("deleted-file statuses:", statuses)
        assert all(e["runtime_status"] != "pending" for e in eps.values()), "still pending after 60s"
        unknown = [i for i in GONE if statuses[i] == "unknown"]
        assert unknown, f"no deleted file was skipped before being read: {statuses}"
        st = s.get(f"{BASE_URL}/api/metadata/status").json()
        print("metadata status:", st)
        assert st["unreachable"] >= len(unknown)
        # restore files and rescan: skipped set cleared -> pending (or quickly known)
        for i in GONE:
            os.link(seed, paths[i])
        r = s.post(f"{BASE_URL}/api/libraries/{lib_id}/scan")
        assert r.status_code == 200, r.text
        after = _episodes(s, title)
        print("after rescan:", {i: after[i]["runtime_status"] for i in unknown})
        assert all(after[i]["runtime_status"] in ("pending", "known") for i in unknown)
        deadline = time.time() + 30
        while time.time() < deadline:
            after = _episodes(s, title)
            if all(after[i]["runtime_status"] == "known" for i in unknown):
                break
            time.sleep(1)
        assert all(after[i]["runtime_status"] == "known" for i in unknown)
    finally:
        if lib_id:
            assert s.delete(f"{BASE_URL}/api/libraries/{lib_id}").status_code == 200
        for p in paths.values():
            if os.path.exists(p):
                os.remove(p)
        import shutil
        shutil.rmtree(root, ignore_errors=True)
    assert not _episodes(s, title)
