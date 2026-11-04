"""Independent collection preferences regroup disposable catalogs without touching media."""
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from mediacenter import routes_admin, scanner
from mediacenter.db import connect, set_setting

from .test_discover import movie
from .test_scanner import snapshot


@pytest.fixture
def collection_library(host, tmp_path):
    root = tmp_path / "collections"
    movie(root, "Movies/Saga/Alpha (2001)/Alpha (2001).mkv", "Alpha", 2001, ["Drama"], "Series")
    movie(root, "Movies/Saga/Beta (2002)/Beta (2002).mkv", "Beta", 2002, ["Drama"], "Series")
    movie(root, "Movies/Studio/Gamma (2003)/Gamma (2003).mkv", "Gamma", 2003)
    movie(root, "Movies/Studio/Delta (2004)/Delta (2004).mkv", "Delta", 2004)
    movie(root, "Movies/Solo (2005)/Solo (2005).mkv", "Solo", 2005, set_name="Solo Set")
    movie(root, "Movies/Loose (2006).mkv", "Loose", 2006)
    movie(root, "Movies/Other (2007).mkv", "Other", 2007)
    response = host.post("/api/libraries", json={"path": str(root)})
    assert response.status_code == 200, response.text
    return root, response.json()


def collections(host):
    response = host.get("/api/discover", params={"view": "collections"})
    assert response.status_code == 200, response.text
    return {item["title"]: (item["source"], item["count"]) for item in response.json()["items"]}


def test_collection_defaults_are_additive_without_writing_settings(host, app):
    assert host.get("/api/settings/library").json() == {
        "nfo_collections": True, "folder_collections": True,
    }
    conn = connect(app.state.config.db_path)
    try:
        assert list(conn.execute("SELECT * FROM settings")) == []
    finally:
        conn.close()


@pytest.mark.parametrize("legacy_folder", [False, True])
def test_existing_folder_preference_keeps_nfo_enabled(host, legacy_folder):
    response = host.post("/api/settings/library", json={"folder_collections": legacy_folder})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "nfo_collections": True, "folder_collections": legacy_folder, "collections": 0,
    }
    assert host.get("/api/settings/library").json() == {
        "nfo_collections": True, "folder_collections": legacy_folder,
    }


@pytest.mark.parametrize("nfo,folder,want", [
    (True, True, {"Series": ("nfo", 2), "Solo Set": ("nfo", 1), "Studio": ("folder", 2)}),
    (True, False, {"Series": ("nfo", 2), "Solo Set": ("nfo", 1)}),
    (False, True, {"Saga": ("folder", 2), "Studio": ("folder", 2)}),
    (False, False, {}),
])
def test_collection_combinations_and_nfo_priority(host, collection_library, nfo, folder, want):
    response = host.post("/api/settings/library", json={"nfo_collections": nfo, "folder_collections": folder})
    assert response.status_code == 200, response.text
    assert collections(host) == want
    assert response.json() == {
        "nfo_collections": nfo, "folder_collections": folder, "collections": len(want),
    }


def test_partial_saves_preserve_the_other_preference(host, collection_library):
    for patch, want in [
        ({"nfo_collections": False}, {"nfo_collections": False, "folder_collections": True}),
        ({"folder_collections": False}, {"nfo_collections": False, "folder_collections": False}),
        ({"nfo_collections": True}, {"nfo_collections": True, "folder_collections": False}),
        ({}, {"nfo_collections": True, "folder_collections": False}),
        ({"folder_collections": True}, {"nfo_collections": True, "folder_collections": True}),
    ]:
        response = host.post("/api/settings/library", json=patch)
        assert response.status_code == 200, response.text
        assert {key: response.json()[key] for key in want} == want
        assert host.get("/api/settings/library").json() == want


@pytest.mark.parametrize("field", ["nfo_collections", "folder_collections"])
def test_null_preferences_are_rejected_without_changing_catalog(host, collection_library, field):
    before = collections(host)
    assert host.post("/api/settings/library", json={field: None}).status_code == 422
    assert collections(host) == before


@pytest.mark.parametrize("folder,want", [
    (True, {"Saga": ("folder", 2), "Studio": ("folder", 2)}),
    (False, {}),
])
def test_rescan_and_library_removal_honor_disabled_nfo(host, collection_library, tmp_path, folder, want):
    _, library = collection_library
    response = host.post("/api/settings/library", json={"nfo_collections": False, "folder_collections": folder})
    assert response.status_code == 200, response.text
    response = host.post(f"/api/libraries/{library['id']}/scan")
    assert response.status_code == 200, response.text
    assert collections(host) == want
    other = tmp_path / "other"
    movie(other, "Other.mkv", "Other library", 2000)
    added = host.post("/api/libraries", json={"path": str(other)})
    assert added.status_code == 200, added.text
    assert host.delete(f"/api/libraries/{added.json()['id']}").status_code == 200
    assert collections(host) == want


def test_assign_collections_reads_stored_nfo_preference(app, host, collection_library):
    conn = connect(app.state.config.db_path)
    try:
        set_setting(conn, "nfo_collections", "0")
        scanner.assign_collections(conn, True)
        conn.commit()
    finally:
        conn.close()
    assert collections(host) == {"Saga": ("folder", 2), "Studio": ("folder", 2)}


def test_regroup_preserves_metadata_history_and_files_without_rescan(app, host, collection_library, monkeypatch):
    root, _ = collection_library
    first = host.get("/api/movies").json()[0]
    assert host.put(f"/api/progress/{first['file_id']}", json={"position": 42, "duration": 200}).status_code == 200
    files_before = snapshot(root)
    conn = connect(app.state.config.db_path)
    try:
        def catalog():
            return {
                table: [{key: row[key] for key in row.keys() if key != "collection_id"}
                        for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
                for table in ("libraries", "media_files", "movies", "progress")
            }

        before = catalog()

        def no_scan(*args, **kwargs):
            raise AssertionError("Preference changes must use stored metadata, without scanning")

        with monkeypatch.context() as scoped:
            scoped.setattr(routes_admin, "scan_library", no_scan)
            scoped.setattr(scanner.os, "walk", no_scan)
            for enabled, count in ((False, 0), (True, 3)):
                response = host.post("/api/settings/library", json={"nfo_collections": enabled, "folder_collections": enabled})
                assert response.status_code == 200, response.text
                assert response.json()["collections"] == count
                assert catalog() == before
        assert conn.execute("SELECT nfo_set FROM movies WHERE title='Alpha'").fetchone()[0] == "Series"
    finally:
        conn.close()
    assert snapshot(root) == files_before
    assert host.get(f"/api/files/{first['file_id']}/playback").json()["progress"]["position"] == 42


def test_settings_merge_and_regroup_run_in_transaction_under_scan_lock(app):
    conn = connect(app.state.config.db_path)
    observations = []

    def trace(sql):
        if "settings" in sql.lower() or "collections" in sql.lower():
            observations.append((sql, scanner.SCAN_LOCK.locked(), conn.in_transaction))

    conn.set_trace_callback(trace)
    try:
        request = SimpleNamespace(state=SimpleNamespace(db=conn))
        routes_admin.set_library_prefs(routes_admin.LibraryPrefsIn(folder_collections=False), request)
        assert observations
        assert all(locked and transaction for _, locked, transaction in observations), observations
        assert not conn.in_transaction
        assert not scanner.SCAN_LOCK.locked()
    finally:
        conn.close()


def test_partial_save_waits_for_scan_before_reading_other_preference(app, monkeypatch):
    waiting = threading.Event()
    real_lock = scanner.SCAN_LOCK

    class ObservedLock:
        def acquire(self, **kwargs):
            waiting.set()
            return real_lock.acquire(**kwargs)

        def release(self):
            real_lock.release()

    monkeypatch.setattr(routes_admin, "SCAN_LOCK", ObservedLock())

    def save_folder():
        conn = connect(app.state.config.db_path)
        try:
            request = SimpleNamespace(state=SimpleNamespace(db=conn))
            return routes_admin.set_library_prefs(routes_admin.LibraryPrefsIn(folder_collections=False), request)
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        real_lock.acquire()
        try:
            pending = pool.submit(save_folder)
            assert waiting.wait(2), "Preference save did not acquire the scan lock"
            assert not pending.done()
            conn = connect(app.state.config.db_path)
            try:
                set_setting(conn, "nfo_collections", "0")
                conn.commit()
            finally:
                conn.close()
        finally:
            real_lock.release()
        assert pending.result(timeout=3) == {
            "nfo_collections": False, "folder_collections": False, "collections": 0,
        }


def test_failed_regroup_rolls_back_preferences_and_memberships(app, host, collection_library, monkeypatch):
    before = collections(host)

    def fail_regroup(conn, *args, **kwargs):
        conn.execute("UPDATE movies SET collection_id=NULL")
        conn.execute("DELETE FROM collections")
        raise RuntimeError("Regroup failed")

    monkeypatch.setattr(routes_admin, "assign_collections", fail_regroup)
    conn = connect(app.state.config.db_path)
    try:
        request = SimpleNamespace(state=SimpleNamespace(db=conn))
        with pytest.raises(RuntimeError, match="Regroup failed"):
            routes_admin.set_library_prefs(routes_admin.LibraryPrefsIn(folder_collections=False), request)
        # Rollback must happen in the handler, rather than relying on connection closure.
        assert not conn.in_transaction
        assert conn.execute("SELECT value FROM settings WHERE key='folder_collections'").fetchone() is None
        assert not scanner.SCAN_LOCK.locked()
        assert collections(host) == before
    finally:
        conn.close()
