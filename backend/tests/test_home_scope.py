"""Media selectors at the real API boundary; all catalog/history data is synthetic."""
import json

import pytest

from mediacenter.db import connect


def add_file(conn, root, kind, number, *, title=None):
    path = str(root / f"{kind}-{number}.mkv")
    file_id = conn.execute(
        "INSERT INTO media_files (library_id,path,path_key,filename,container,size,mtime,kind,added_at)"
        " VALUES (1,?,?,?,?,0,0,?,'2026-01-01')",
        (path, path, f"{kind}-{number}.mkv", "mkv", kind),
    ).lastrowid
    if kind == "movie":
        conn.execute(
            "INSERT INTO movies (file_id,title,sort_title,year,genres,collection_id,poster_path)"
            " VALUES (?,?,?,2001,?,1,?)",
            (file_id, title or f"Film {number}", title or f"Film {number}",
             json.dumps(["Film", "Shared"]), str(root / "movie-poster.jpg")),
        )
    else:
        conn.execute("INSERT INTO episodes (file_id,season_id,episode_number,title) VALUES (?,1,?,?)",
                     (file_id, number, title or f"Episode {number}"))
    return file_id


def history(conn, file_id, position=30, duration=100, watched=0, updated="2026-01-02"):
    conn.execute(
        "INSERT OR REPLACE INTO progress (path_key,position,duration,watched,updated_at)"
        " SELECT path_key,?,?,?,? FROM media_files WHERE id=?",
        (position, duration, watched, updated, file_id),
    )
    conn.commit()


@pytest.fixture
def catalog(app, tmp_path):
    root = tmp_path / "synthetic-library"
    root.mkdir()
    conn = connect(app.state.config.db_path)
    conn.execute("INSERT INTO libraries (id,path,path_key,name,created_at,last_scan_at)"
                 " VALUES (1,?,?,'Test source','2026-01-01','2026-01-01')", (str(root), str(root)))
    conn.execute("INSERT INTO collections (id,key,name,sort_name,source)"
                 " VALUES (1,'test-set','Test Collection','Test Collection','nfo')")
    conn.execute("INSERT INTO shows (id,show_key,title,sort_title,year,genres,poster_path)"
                 " VALUES (1,'signal','Signal Show','Signal Show',2022,?,?)",
                 (json.dumps(["TV", "Shared"]), str(root / "show-poster.jpg")))
    conn.execute("INSERT INTO seasons (id,show_id,season_number) VALUES (1,1,1)")
    movie = add_file(conn, root, "movie", 1, title="Signal Film")
    other_movie = add_file(conn, root, "movie", 2, title="Other Film")
    episode = add_file(conn, root, "episode", 1, title="Signal Pilot")
    other_episode = add_file(conn, root, "episode", 2)
    conn.commit()
    try:
        yield {"conn": conn, "root": root, "movie": movie, "other_movie": other_movie,
               "episode": episode, "other_episode": other_episode}
    finally:
        conn.close()


def get(host, endpoint, **params):
    response = host.get(f"/api/{endpoint}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("endpoint", ["home", "discover", "search", "atlas"])
@pytest.mark.parametrize("value", ["movies", "show", "all", "", "MOVIE"])
def test_rejects_invalid_media_type(host, endpoint, value):
    response = host.get(f"/api/{endpoint}", params={"media_type": value})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "media_type"]


@pytest.mark.parametrize("scope", ["movie", "tv"])
def test_home_scopes_all_catalog_rows_and_counts(host, catalog, scope):
    history(catalog["conn"], catalog["movie"])
    history(catalog["conn"], catalog["episode"])
    data = get(host, "home", media_type=scope)
    if scope == "movie":
        assert [i["file_id"] for i in data["continue_watching"]] == [catalog["movie"]]
        assert len(data["recent_movies"]) == 2
        assert data["recent_episodes"] == data["shows"] == []
        assert data["counts"] == {"movies": 2, "shows": 0, "episodes": 0, "libraries": 1}
    else:
        assert [i["file_id"] for i in data["continue_watching"]] == [catalog["episode"]]
        assert data["continue_watching"][0]["show_poster_url"] == "/api/art/show-poster/1"
        assert data["recent_movies"] == []
        assert len(data["recent_episodes"]) == 2 and len(data["shows"]) == 1
        assert data["counts"] == {"movies": 0, "shows": 1, "episodes": 2, "libraries": 1}


@pytest.mark.parametrize("scope,kind", [("movie", "movie"), ("tv", "show")])
def test_discover_scopes_facets_totals_before_pagination(host, catalog, scope, kind):
    data = get(host, "discover", media_type=scope, limit=1)
    assert data["total"] == (2 if scope == "movie" else 1)
    assert [i["type"] for i in data["items"]] == [kind]
    assert data["facets"]["types"] == [{"value": kind, "count": data["total"]}]
    genres = {g["value"]: g["count"] for g in data["facets"]["genres"]}
    assert genres == ({"Film": 2, "Shared": 2} if scope == "movie" else {"TV": 1, "Shared": 1})
    assert data["facets"]["decades"] == [{"value": "2000" if scope == "movie" else "2020",
                                            "count": data["total"]}]


@pytest.mark.parametrize("scope,filters", [
    ("movie", {"view": "shows"}), ("tv", {"view": "movies"}),
    ("movie", {"type": "show"}), ("tv", {"type": "movie"}),
    ("tv", {"collection": 1}), ("tv", {"view": "collections"}),
])
def test_discover_conflicting_filters_cannot_escape_scope(host, catalog, scope, filters):
    data = get(host, "discover", media_type=scope, **filters)
    assert data["items"] == [] and data["total"] == 0
    assert data.get("collection") is None
    if data["facets"]:
        assert all(t["value"] == ("movie" if scope == "movie" else "show")
                   for t in data["facets"]["types"])


@pytest.mark.parametrize("scope", ["movie", "tv"])
def test_search_scopes_results_and_totals(host, catalog, scope):
    data = get(host, "search", q="Signal", media_type=scope, limit=1)
    assert data["totals"] == ({"movies": 1, "shows": 0, "episodes": 0} if scope == "movie"
                              else {"movies": 0, "shows": 1, "episodes": 2})
    assert [i["title"] for i in data["movies"]] == (["Signal Film"] if scope == "movie" else [])
    assert [i["title"] for i in data["shows"]] == ([] if scope == "movie" else ["Signal Show"])
    assert [i["title"] for i in data["episodes"]] == ([] if scope == "movie" else ["Signal Pilot"])
    assert get(host, "search", q="  ", media_type=scope)["totals"] == {"movies": 0, "shows": 0, "episodes": 0}


@pytest.mark.parametrize("scope", ["movie", "tv"])
def test_atlas_scoped_groups_drill_down_with_the_same_scope(host, catalog, scope):
    data = get(host, "atlas", media_type=scope)
    rings = {r["id"]: r["nodes"] for r in data["rings"]}
    assert data["total"] == (2 if scope == "movie" else 1)
    assert [(n["value"], n["count"]) for n in rings["types"]] == [
        ("movie" if scope == "movie" else "show", data["total"])]
    assert {n["value"] for n in rings["genres"]} == ({"Film", "Shared"} if scope == "movie" else {"TV", "Shared"})
    assert [n["value"] for n in rings["collections"]] == ([1] if scope == "movie" else [])
    assert [c["id"] for c in get(host, "discover", view="collections", media_type=scope)["items"]] == (
        [1] if scope == "movie" else [])
    for ring, param in [("types", "type"), ("genres", "genre"), ("collections", "collection")]:
        for node in rings[ring]:
            results = get(host, "discover", media_type=scope, **{param: node["value"]})
            assert results["total"] == node["count"]
            assert {i["type"] for i in results["items"]} == {"movie" if scope == "movie" else "show"}


@pytest.mark.parametrize("scope,kind", [("movie", "movie"), ("tv", "episode")])
def test_home_filters_resume_eligibility_before_limit(host, catalog, scope, kind):
    conn = catalog["conn"]
    valid = catalog[kind]
    history(conn, valid, position=1)
    # Invalid rows are newer than the valid row and must not consume the limit.
    cases = [(30, None, 0), (30, 0, 0), (30, -1, 0), (30, float("inf"), 0),
             (30, float("-inf"), 0), (30, float("nan"), 0), (30, "unknown", 0),
             (0, 100, 0), (-1, 100, 0), (100, 100, 0), (101, 100, 0),
             (float("inf"), 100, 0), (float("-inf"), 100, 0), (30, 100, 1)]
    for number, (position, duration, watched) in enumerate(cases, 10):
        file_id = add_file(conn, catalog["root"], kind, number)
        history(conn, file_id, position, duration, watched, updated="2026-02-01")
    assert [i["file_id"] for i in get(host, "home", media_type=scope)["continue_watching"]] == [valid]


@pytest.mark.parametrize("scope,kind,other", [("movie", "movie", "episode"), ("tv", "episode", "movie")])
def test_home_type_filter_prevents_limit_starvation_and_orders_ties(host, catalog, scope, kind, other):
    conn = catalog["conn"]
    selected = [catalog[kind], catalog[f"other_{kind}"]]
    for number in range(10, 23):
        selected.append(add_file(conn, catalog["root"], kind, number))
    for file_id in reversed(selected):
        history(conn, file_id, updated="2026-01-02")
    # The newest selected entry wins; equal timestamps then use ascending file ID.
    history(conn, selected[-1], updated="2026-01-03")
    for number in range(30, 43):
        history(conn, add_file(conn, catalog["root"], other, number), updated="2026-02-01")
    items = get(host, "home", media_type=scope)["continue_watching"]
    assert [i["file_id"] for i in items] == [selected[-1], *selected[:11]]
    history(conn, selected[-1], position=0, updated="2026-03-01")
    assert [i["file_id"] for i in get(host, "home", media_type=scope)["continue_watching"]] == selected[:12]


def test_unscoped_requests_preserve_mixed_catalog_and_legacy_resume(host, catalog):
    history(catalog["conn"], catalog["movie"], position=11, duration=None)
    history(catalog["conn"], catalog["episode"], position=10)
    home = get(host, "home")
    assert [i["file_id"] for i in home["continue_watching"]] == [catalog["movie"]]
    assert home["counts"] == {"movies": 2, "shows": 1, "episodes": 2, "libraries": 1}
    assert get(host, "discover")["total"] == get(host, "atlas")["total"] == 3
    assert get(host, "search", q="Signal")["totals"] == {"movies": 1, "shows": 1, "episodes": 2}


@pytest.mark.parametrize("scope", ["movie", "tv"])
def test_no_sources_and_empty_history_have_no_resume_rows(host, scope):
    home = get(host, "home", media_type=scope)
    assert home["continue_watching"] == home["recent_movies"] == home["recent_episodes"] == home["shows"] == []
    assert home["counts"] == {"movies": 0, "shows": 0, "episodes": 0, "libraries": 0}
    assert home["sources"] == {"total": 0, "unreachable": 0, "last_scan_at": None}
    assert get(host, "discover", media_type=scope)["total"] == 0
    assert get(host, "atlas", media_type=scope)["total"] == 0
    assert get(host, "search", media_type=scope, q="Signal")["totals"] == {"movies": 0, "shows": 0, "episodes": 0}


@pytest.mark.parametrize("scope,kind", [("movie", "movie"), ("tv", "episode")])
def test_empty_then_completed_history_and_offline_source_preserve_catalog(host, catalog, scope, kind):
    assert get(host, "home", media_type=scope)["continue_watching"] == []
    file_id = catalog[kind]
    saved = host.put(f"/api/progress/{file_id}", json={"position": 95, "duration": 100})
    assert saved.status_code == 200 and saved.json()["watched"] is True
    assert get(host, "home", media_type=scope)["continue_watching"] == []
    host.put(f"/api/progress/{file_id}", json={"position": 30, "duration": 100})
    before = {endpoint: get(host, endpoint, media_type=scope, **({"q": "Signal"} if endpoint == "search" else {}))
              for endpoint in ("home", "discover", "search", "atlas")}
    catalog["root"].rename(catalog["root"].with_name("offline"))
    scan = host.post("/api/libraries/1/scan")
    assert scan.status_code == 200
    for endpoint, expected in before.items():
        actual = get(host, endpoint, media_type=scope, **({"q": "Signal"} if endpoint == "search" else {}))
        if "sources" in actual:
            assert actual["sources"]["unreachable"] == 1
            expected["sources"]["unreachable"] = 1
            if "last_scan_at" in actual["sources"]:
                assert actual["sources"]["last_scan_at"]
                expected["sources"]["last_scan_at"] = actual["sources"]["last_scan_at"]
        assert actual == expected
