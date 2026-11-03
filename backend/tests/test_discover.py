"""Stage 3: NFO genres/sets, folder collections, Discover filters/sorting/paging, search, Atlas groups."""
import shutil

import pytest

from .conftest import write

NFO = "<?xml version='1.0'?><movie><title>{t}</title><year>{y}</year>{g}{s}</movie>"


def movie(root, rel, title, year, genres=(), set_name=None, nfo=True):
    stem = rel.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    f = write(root / rel)
    if nfo:
        g = "".join(f"<genre>{x}</genre>" for x in genres)
        s = f"<set><name>{set_name}</name></set>" if set_name else ""
        (f.parent / f"{stem}.nfo").write_text(NFO.format(t=title, y=year, g=g, s=s), encoding="utf-8")


@pytest.fixture
def lib(tmp_path, host):
    root = tmp_path / "lib"
    movie(root, "Movies/Alien (1979)/Alien (1979).mkv", "Alien", 1979, ["Horror", "Science Fiction"], "Alien Collection")
    movie(root, "Movies/Aliens (1986)/Aliens (1986).mkv", "Aliens", 1986, ["Science Fiction / Action"], "Alien Collection")
    movie(root, "Movies/Pixar/Up (2009)/Up (2009).mkv", "Up", 2009, ["Animation"])
    movie(root, "Movies/Pixar/Coco (2017)/Coco (2017).mkv", "Coco", 2017, ["Animation", "Family"])
    movie(root, "Movies/Pixar/Brave (2012)/Brave (2012).mkv", "Brave", 2012, ["Animation"], "Explicit Set")
    movie(root, "Movies/Lonely (2001)/Lonely (2001).mkv", "Lonely", 2001, nfo=False)
    movie(root, "Movies/Other (2002).mkv", "Other", 2002, nfo=False)
    movie(root, "Movies/Another (2003).mkv", "Another", 2003, nfo=False)
    write(root / "TV" / "Space Show" / "Season 01" / "Space Show - S01E01 - Launch Day.mkv")
    write(root / "TV" / "Space Show" / "tvshow.nfo", b"<tvshow><title>Space Show</title><genre>Science Fiction</genre></tvshow>")
    res = host.post("/api/libraries", json={"path": str(root)})
    assert res.status_code == 200, res.text
    return root, res.json()


def disc(host, **params):
    r = host.get("/api/discover", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_genres_read_from_nfo_and_split(host, lib):
    items = {i["title"]: i for i in disc(host)["items"]}
    assert items["Alien"]["genres"] == ["Horror", "Science Fiction"]
    assert items["Aliens"]["genres"] == ["Science Fiction", "Action"]
    assert items["Lonely"]["genres"] == []  # no NFO: nothing invented
    assert items["Space Show"]["genres"] == ["Science Fiction"]


def test_collections_nfo_priority_folder_groups_and_generic_folders(host, lib):
    cols = {c["title"]: c for c in disc(host, view="collections")["items"]}
    assert cols["Alien Collection"]["source"] == "nfo" and cols["Alien Collection"]["count"] == 2
    assert cols["Explicit Set"]["source"] == "nfo" and cols["Explicit Set"]["count"] == 1  # NFO set beats the Pixar folder
    assert cols["Pixar"]["source"] == "folder" and cols["Pixar"]["count"] == 2
    assert "Movies" not in cols and "lib" not in cols  # generic / root folders never become collections


def test_folder_groups_can_be_disabled(host, lib):
    r = host.post("/api/settings/library", json={"folder_collections": False})
    assert r.status_code == 200
    titles = {c["title"] for c in disc(host, view="collections")["items"]}
    assert titles == {"Alien Collection", "Explicit Set"}
    host.post(f"/api/libraries/{lib[1]['id']}/scan")  # rescans respect the setting
    assert {c["title"] for c in disc(host, view="collections")["items"]} == titles
    host.post("/api/settings/library", json={"folder_collections": True})
    assert "Pixar" in {c["title"] for c in disc(host, view="collections")["items"]}


def test_collection_ids_stable_and_members(host, lib):
    col = next(c for c in disc(host, view="collections")["items"] if c["title"] == "Alien Collection")
    host.post(f"/api/libraries/{lib[1]['id']}/scan")
    again = next(c for c in disc(host, view="collections")["items"] if c["title"] == "Alien Collection")
    assert again["id"] == col["id"]
    d = disc(host, collection=col["id"])
    assert {i["title"] for i in d["items"]} == {"Alien", "Aliens"} and d["collection"]["title"] == "Alien Collection"


def test_filters_combine_or_within_and_across(host, lib):
    d = disc(host, genre="Animation,Horror")
    assert {i["title"] for i in d["items"]} == {"Up", "Coco", "Brave", "Alien"}
    d = disc(host, genre="Animation,Horror", decade="2010")
    assert {i["title"] for i in d["items"]} == {"Coco", "Brave"}
    d = disc(host, genre="__none__", view="movies")
    assert {i["title"] for i in d["items"]} == {"Lonely", "Other", "Another"}
    assert disc(host, type="show")["total"] == 1
    assert any(g["value"] == "__none__" for g in d["facets"]["genres"])


def test_sorting_and_watch_state(host, lib):
    assert [i["title"] for i in disc(host, view="movies", sort="year")["items"]][:2] == ["Coco", "Brave"]
    assert [i["title"] for i in disc(host, view="movies")["items"]][:2] == ["Alien", "Aliens"]
    coco = next(i for i in disc(host)["items"] if i["title"] == "Coco")
    fid = host.get(f"/api/movies/{coco['id']}").json()["file_id"]
    host.put(f"/api/progress/{fid}", json={"position": 300, "duration": 6000})
    first = disc(host, sort="progress")["items"][0]
    assert first["title"] == "Coco" and first["state"] == "in_progress"
    assert [i["title"] for i in disc(host, state="in_progress")["items"]] == ["Coco"]


def test_paging(host, lib):
    a = disc(host, limit=3)
    b = disc(host, limit=3, offset=3)
    assert a["total"] == 9 and len(a["items"]) == 3 and not {i["key"] for i in a["items"]} & {i["key"] for i in b["items"]}
    assert host.get("/api/discover", params={"sort": "nope"}).status_code == 400


def test_search_titles_shows_episodes(host, lib):
    r = host.get("/api/search", params={"q": "alien"}).json()
    assert [m["title"] for m in r["movies"]] == ["Alien", "Aliens"]  # prefix/whole match first
    r = host.get("/api/search", params={"q": "launch"}).json()
    assert r["totals"]["episodes"] == 1 and r["episodes"][0]["show_title"] == "Space Show"
    r = host.get("/api/search", params={"q": "space"}).json()
    assert r["totals"]["shows"] == 1
    assert host.get("/api/search", params={"q": "zzzz"}).json()["totals"] == {"movies": 0, "shows": 0, "episodes": 0}
    assert host.get("/api/search", params={"q": "  "}).json()["movies"] == []
    assert host.get("/api/search", params={"q": "100%_"}).status_code == 200


def test_atlas_rings(host, lib):
    a = host.get("/api/atlas").json()
    rings = {r["id"]: r["nodes"] for r in a["rings"]}
    assert [n["label"] for n in rings["types"]] == ["Movies", "TV shows"]
    genre = {n["label"]: n["count"] for n in rings["genres"]}
    assert genre["Animation"] == 3 and genre["Science Fiction"] == 3 and genre["Uncategorized"] == 3
    assert list(genre)[-1] == "Uncategorized"
    assert [n["label"] for n in rings["collections"]][:2] == ["Alien Collection", "Explicit Set"]  # NFO sets first


def test_empty_library(host):
    assert disc(host)["total"] == 0
    assert host.get("/api/atlas").json()["total"] == 0
    assert disc(host, view="collections")["items"] == []


def test_unreachable_source_keeps_records(host, lib):
    root, info = lib
    moved = root.parent / "offline"
    shutil.move(str(root), str(moved))  # NAS goes away
    host.post(f"/api/libraries/{info['id']}/scan")
    assert disc(host)["total"] == 9
    assert host.get("/api/atlas").json()["sources"]["unreachable"] == 1
    shutil.move(str(moved), str(root))
