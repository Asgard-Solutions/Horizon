"""Discover, search and Library Atlas API. Reads the catalog only; every value comes from scanned records."""
import json
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import paths
from .routes_library import _art
from .security import require_viewer

router = APIRouter(prefix="/api", dependencies=[Depends(require_viewer)])
NONE = "__none__"  # facet value for "no genre" / "unknown year"
SORTS = {"title", "added", "year", "progress"}
STATES = ("in_progress", "unwatched", "watched")

MOVIE_ROWS = """
SELECT m.id, m.title, m.sort_title, m.year, m.genres, m.collection_id, m.poster_path, m.fanart_path,
       f.added_at, p.position, p.duration, p.watched, p.updated_at
FROM movies m JOIN media_files f ON f.id = m.file_id LEFT JOIN progress p ON p.path_key = f.path_key
"""
SHOW_ROWS = """
SELECT sh.id, sh.title, sh.sort_title, sh.year, sh.genres, sh.poster_path, sh.fanart_path,
       MAX(f.added_at) AS added_at, COUNT(e.id) AS episodes, SUM(COALESCE(p.watched, 0)) AS watched_eps,
       SUM(CASE WHEN p.watched = 0 AND p.position > 10 THEN 1 ELSE 0 END) AS partial_eps, MAX(p.updated_at) AS updated_at
FROM shows sh JOIN seasons s ON s.show_id = sh.id JOIN episodes e ON e.season_id = s.id
JOIN media_files f ON f.id = e.file_id LEFT JOIN progress p ON p.path_key = f.path_key
GROUP BY sh.id
"""


def _genres(raw) -> list[str]:
    try:
        return [g for g in json.loads(raw) if isinstance(g, str)] if raw else []
    except ValueError:
        return []


def _movie_item(r) -> dict:
    ratio = r["position"] / r["duration"] if r["position"] and r["duration"] else 0
    state = "watched" if r["watched"] else "in_progress" if (r["position"] or 0) > 10 else "unwatched"
    return {"key": f"movie-{r['id']}", "type": "movie", "id": r["id"], "title": r["title"], "sort": r["sort_title"],
            "year": r["year"], "genres": _genres(r["genres"]), "collection_id": r["collection_id"],
            "poster_url": _art("movie-poster", r["id"], r["poster_path"]),
            "fanart_url": _art("movie-fanart", r["id"], r["fanart_path"]), "added_at": r["added_at"],
            "state": state, "progress": round(min(1.0, ratio), 3), "touched": r["updated_at"], "episodes": None}


def _show_item(r) -> dict:
    eps, done, partial = r["episodes"], r["watched_eps"] or 0, r["partial_eps"] or 0
    state = "watched" if eps and done >= eps else "in_progress" if done or partial else "unwatched"
    return {"key": f"show-{r['id']}", "type": "show", "id": r["id"], "title": r["title"], "sort": r["sort_title"],
            "year": r["year"], "genres": _genres(r["genres"]), "collection_id": None,
            "poster_url": _art("show-poster", r["id"], r["poster_path"]),
            "fanart_url": _art("show-fanart", r["id"], r["fanart_path"]), "added_at": r["added_at"],
            "state": state, "progress": round(done / eps, 3) if eps else 0, "touched": r["updated_at"], "episodes": eps}


def load_items(conn, kinds=("movie", "show")) -> list[dict]:
    items = []
    if "movie" in kinds:
        items += [_movie_item(r) for r in conn.execute(MOVIE_ROWS)]
    if "show" in kinds:
        items += [_show_item(r) for r in conn.execute(SHOW_ROWS)]
    return items


def _decade(year) -> str:
    return f"{year // 10 * 10}" if year else NONE


def _split(v: str | None) -> set[str]:
    return {x for x in (v or "").split(",") if x}


def _sort(items: list[dict], sort: str) -> list[dict]:
    items.sort(key=lambda i: (i["sort"], i["type"], i["id"]))
    if sort == "added":
        items.sort(key=lambda i: i["added_at"] or "", reverse=True)
    elif sort == "year":
        items.sort(key=lambda i: (i["year"] is None, -(i["year"] or 0)))
    elif sort == "progress":  # in progress (most recent first), then unwatched, then watched
        items.sort(key=lambda i: i["touched"] or "", reverse=True)
        items.sort(key=lambda i: STATES.index(i["state"]))
    return items


def _facets(items: list[dict]) -> dict:
    genres: dict[str, int] = {}
    decades: dict[str, int] = {}
    states = dict.fromkeys(STATES, 0)
    types = {"movie": 0, "show": 0}
    for i in items:
        for g in i["genres"] or [NONE]:
            genres[g] = genres.get(g, 0) + 1
        d = _decade(i["year"])
        decades[d] = decades.get(d, 0) + 1
        states[i["state"]] += 1
        types[i["type"]] += 1
    return {
        "genres": sorted(({"value": k, "count": v} for k, v in genres.items()), key=lambda x: (x["value"] == NONE, x["value"].casefold())),
        "decades": sorted(({"value": k, "count": v} for k, v in decades.items()), key=lambda x: (x["value"] == NONE, -int(x["value"]) if x["value"] != NONE else 0)),
        "states": [{"value": k, "count": v} for k, v in states.items() if v],
        "types": [{"value": k, "count": v} for k, v in types.items() if v],
    }


def _public(i: dict) -> dict:
    return {k: v for k, v in i.items() if k not in ("sort", "touched")}


def _collections(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT c.id, c.name, c.sort_name, c.source, COUNT(m.id) AS count, MIN(m.year) AS year_from, MAX(m.year) AS year_to,"
        " (SELECT m2.id FROM movies m2 WHERE m2.collection_id = c.id AND m2.poster_path IS NOT NULL ORDER BY m2.year, m2.sort_title LIMIT 1) AS poster_movie"
        " FROM collections c JOIN movies m ON m.collection_id = c.id GROUP BY c.id ORDER BY c.sort_name"
    ).fetchall()
    return [{"key": f"collection-{r['id']}", "type": "collection", "id": r["id"], "title": r["name"], "source": r["source"],
             "count": r["count"], "year_from": r["year_from"], "year_to": r["year_to"],
             "poster_url": f"/api/art/movie-poster/{r['poster_movie']}" if r["poster_movie"] else None} for r in rows]


@router.get("/discover")
def discover(request: Request, view: str = "all", sort: str = "title", genre: str | None = None, decade: str | None = None,
             state: str | None = None, type: str | None = None, collection: int | None = None,
             offset: int = Query(0, ge=0), limit: int = Query(120, ge=1, le=500),
             media_type: Literal["movie", "tv"] | None = None):
    conn = request.state.db
    if sort not in SORTS:
        raise HTTPException(status_code=400, detail="Unknown sort")
    if view == "collections":
        cols = _collections(conn) if media_type != "tv" else []
        return {"view": view, "total": len(cols), "offset": offset, "items": cols[offset:offset + limit], "facets": None}
    kinds = {"movies": ("movie",), "shows": ("show",), "all": ("movie", "show")}.get(view)
    if kinds is None:
        raise HTTPException(status_code=400, detail="Unknown view")
    kinds = tuple(kind for kind in kinds if kind in _scope_kinds(media_type))
    items = load_items(conn, kinds)
    col = None
    if collection is not None:
        items = [i for i in items if i["collection_id"] == collection]
        row = (conn.execute("SELECT id, name, source FROM collections WHERE id = ?", (collection,)).fetchone()
               if media_type != "tv" else None)
        col = {"id": row["id"], "title": row["name"], "source": row["source"]} if row else None
    facets = _facets(items)
    g, d, s, t = _split(genre), _split(decade), _split(state), _split(type)
    # Within one filter values are alternatives (OR); different filters combine (AND).
    items = [i for i in items
             if (not g or (set(i["genres"]) & g) or (NONE in g and not i["genres"]))
             and (not d or _decade(i["year"]) in d)
             and (not s or i["state"] in s)
             and (not t or i["type"] in t)]
    _sort(items, sort)
    return {"view": view, "total": len(items), "offset": offset, "items": [_public(i) for i in items[offset:offset + limit]],
            "facets": facets, "collection": col}


def _like(token: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", token) + "%"


def _scope_kinds(media_type: Literal["movie", "tv"] | None) -> tuple[str, ...]:
    return {"movie": ("movie",), "tv": ("show",)}.get(media_type, ("movie", "show"))


@router.get("/search")
def search(request: Request, q: str = "", limit: int = Query(30, ge=1, le=100),
           media_type: Literal["movie", "tv"] | None = None):
    """Offline title / show / episode search; every word must match (case-insensitive)."""
    conn = request.state.db
    tokens = [t for t in q.strip().split() if t][:6]
    if not tokens:
        return {"query": q, "movies": [], "shows": [], "episodes": [], "totals": {"movies": 0, "shows": 0, "episodes": 0}}
    prefix = re.sub(r"([\\%_])", r"\\\1", q.strip()) + "%"

    def where(cols: list[str]) -> tuple[str, list]:
        parts, args = [], []
        for t in tokens:
            ors = [f"{c} LIKE ? ESCAPE '\\'" for c in cols]
            if re.fullmatch(r"(19|20)\d\d", t):
                ors.append("year = ?")
            parts.append("(" + " OR ".join(ors) + ")")
            args += [_like(t)] * len(cols) + ([int(t)] if re.fullmatch(r"(19|20)\d\d", t) else [])
        return " AND ".join(parts), args

    mw, ma = where(["m.title"])
    if media_type == "tv":
        mw += " AND 0"
    movies = [_public(_movie_item(r)) for r in conn.execute(
        MOVIE_ROWS + f" WHERE {mw} ORDER BY (m.title LIKE ? ESCAPE '\\') DESC, m.sort_title LIMIT ?", (*ma, prefix, limit))]
    m_total = conn.execute(f"SELECT COUNT(*) FROM movies m WHERE {mw}", ma).fetchone()[0]
    sw, sa = where(["sh.title"])
    if media_type == "movie":
        sw += " AND 0"
    show_ids = [r[0] for r in conn.execute(
        f"SELECT sh.id FROM shows sh WHERE {sw} ORDER BY (sh.title LIKE ? ESCAPE '\\') DESC, sh.sort_title LIMIT ?", (*sa, prefix, limit))]
    s_total = conn.execute(f"SELECT COUNT(*) FROM shows sh WHERE {sw}", sa).fetchone()[0]
    by_id = {r["id"]: r for r in conn.execute(SHOW_ROWS.replace("GROUP BY sh.id", f"WHERE sh.id IN ({','.join('?' * len(show_ids))}) GROUP BY sh.id"), show_ids)} if show_ids else {}
    shows = [_public(_show_item(by_id[i])) for i in show_ids if i in by_id]
    ew, ea = where(["e.title", "e.plot", "sh.title"])
    if media_type == "movie":
        ew += " AND 0"
    ep_sql = (" FROM episodes e JOIN seasons s ON s.id = e.season_id JOIN shows sh ON sh.id = s.show_id"
              " JOIN media_files f ON f.id = e.file_id LEFT JOIN progress p ON p.path_key = f.path_key"
              f" WHERE {ew.replace('year = ?', 'sh.year = ?')}")
    episodes = [{"key": f"episode-{r['id']}", "type": "episode", "id": r["id"], "show_id": r["show_id"], "show_title": r["show_title"],
                 "season_number": r["season_number"], "episode_number": r["episode_number"], "title": r["title"],
                 "file_id": r["file_id"], "thumb_url": _art("episode-thumb", r["id"], r["thumb_path"]),
                 "watched": bool(r["watched"])}
                for r in conn.execute("SELECT e.id, e.title, e.episode_number, e.thumb_path, e.file_id, s.season_number, s.show_id,"
                                      " sh.title AS show_title, p.watched" + ep_sql +
                                      " ORDER BY (e.title LIKE ? ESCAPE '\\') DESC, sh.sort_title, s.season_number, e.episode_number LIMIT ?",
                                      (*ea, prefix, limit))]
    e_total = conn.execute("SELECT COUNT(*)" + ep_sql, ea).fetchone()[0]
    return {"query": q, "movies": movies, "shows": shows, "episodes": episodes,
            "totals": {"movies": m_total, "shows": s_total, "episodes": e_total}}


@router.get("/atlas")
def atlas(request: Request, media_type: Literal["movie", "tv"] | None = None):
    """Rings of real groups: media type, genres (+ Uncategorized), collections. Positions are assigned by the client
    from this stable order (count desc, then name), never randomly."""
    conn = request.state.db
    items = load_items(conn, _scope_kinds(media_type))
    sample: dict[str, list[str]] = {}

    def add(node_id: str, item: dict):
        if item["poster_url"] and len(sample.setdefault(node_id, [])) < 3:
            sample[node_id].append(item["poster_url"])

    types = {"movie": 0, "show": 0}
    genres: dict[str, int] = {}
    for i in sorted(items, key=lambda x: (x["sort"], x["id"])):
        types[i["type"]] += 1
        add(f"type:{i['type']}", i)
        for g in i["genres"] or [NONE]:
            genres[g] = genres.get(g, 0) + 1
            add(f"genre:{g}", i)
    type_nodes = [{"id": f"type:{k}", "kind": "type", "value": k, "label": "Movies" if k == "movie" else "TV shows",
                   "count": v, "posters": sample.get(f"type:{k}", [])} for k, v in types.items() if v]
    genre_nodes = [{"id": f"genre:{g}", "kind": "genre", "value": g, "label": "Uncategorized" if g == NONE else g, "count": c,
                    "posters": sample.get(f"genre:{g}", [])}
                   for g, c in sorted(genres.items(), key=lambda x: (x[0] == NONE, -x[1], x[0].casefold()))]
    col_nodes = [{"id": f"collection:{c['id']}", "kind": "collection", "value": c["id"], "label": c["title"], "count": c["count"],
                  "source": c["source"], "posters": [c["poster_url"]] if c["poster_url"] else []}
                 for c in sorted(_collections(conn) if media_type != "tv" else [],
                                 key=lambda c: (c["source"] != "nfo", -c["count"], c["title"].casefold()))]
    libs = conn.execute("SELECT path FROM libraries").fetchall()
    return {"total": len(items), "rings": [
        {"id": "types", "label": "Media", "nodes": type_nodes},
        {"id": "genres", "label": "Genres", "nodes": genre_nodes},
        {"id": "collections", "label": "Collections", "nodes": col_nodes},
    ], "sources": {"total": len(libs), "unreachable": sum(1 for lib in libs if not paths.dir_reachable(lib["path"]))}}
