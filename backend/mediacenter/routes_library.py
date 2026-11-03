"""Catalog, playback and streaming API (used by the web UI and reusable by a future native client)."""
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .db import now_iso
from .parser import IMAGE_EXTENSIONS
from .paths import library_real_path
from .probe import MIME, assess_playback, find_ffprobe, probe_file
from .scanner import path_key
from .security import require_viewer
from .streaming import stream_file

router = APIRouter(prefix="/api", dependencies=[Depends(require_viewer)])

ART_SOURCES = {
    "movie-poster": ("movies", "poster_path"),
    "movie-fanart": ("movies", "fanart_path"),
    "show-poster": ("shows", "poster_path"),
    "show-fanart": ("shows", "fanart_path"),
    "season-poster": ("seasons", "poster_path"),
    "episode-thumb": ("episodes", "thumb_path"),
}
WATCHED_RATIO = 0.92


def _art(kind: str, row_id: int, path: str | None) -> str | None:
    return f"/api/art/{kind}/{row_id}" if path else None


def _progress(row) -> dict | None:
    if row["position"] is None:
        return None
    return {"position": row["position"], "duration": row["duration"], "watched": bool(row["watched"])}


def _runtime(row) -> float | None:
    # Real duration only: cached FFprobe result (background reader or playback), else the duration the player reported.
    return row["probe_duration"] or row["duration"]


def _runtime_status(row, reader) -> str:
    """known | pending (background reader will fill it in) | unknown (unreadable, offline, or no reader)."""
    if _runtime(row):
        return "known"
    waiting = reader is not None and reader.enabled and not row["probed"] and not reader.is_unreachable(row["file_id"])
    return "pending" if waiting else "unknown"


def authorize_media_path(conn, path: str) -> str:
    """Only files located inside a configured library folder may be served."""
    real = library_real_path(conn, path)
    if not real:
        raise HTTPException(status_code=403, detail="File is outside the configured library folders.")
    return real


MOVIE_SQL = """
SELECT m.*, f.filename, f.container, f.size, f.added_at, p.position, p.duration, p.watched,
       json_extract(f.probe_json, '$.duration') AS probe_duration, f.probe_json IS NOT NULL AS probed
FROM movies m JOIN media_files f ON f.id = m.file_id LEFT JOIN progress p ON p.path_key = f.path_key
"""
EPISODE_SQL = """
SELECT e.*, s.season_number, s.show_id, sh.title AS show_title, f.filename, f.container, f.size, f.added_at,
       p.position, p.duration, p.watched, json_extract(f.probe_json, '$.duration') AS probe_duration,
       f.probe_json IS NOT NULL AS probed
FROM episodes e JOIN seasons s ON s.id = e.season_id JOIN shows sh ON sh.id = s.show_id
JOIN media_files f ON f.id = e.file_id LEFT JOIN progress p ON p.path_key = f.path_key
"""


def _movie(row, reader=None) -> dict:
    return {
        "id": row["id"], "file_id": row["file_id"], "title": row["title"], "year": row["year"], "plot": row["plot"],
        "filename": row["filename"], "container": row["container"], "size": row["size"], "added_at": row["added_at"],
        "poster_url": _art("movie-poster", row["id"], row["poster_path"]),
        "fanart_url": _art("movie-fanart", row["id"], row["fanart_path"]),
        "progress": _progress(row), "runtime": _runtime(row), "runtime_status": _runtime_status(row, reader),
    }


def _episode(row, reader=None) -> dict:
    return {
        "id": row["id"], "file_id": row["file_id"], "show_id": row["show_id"], "show_title": row["show_title"],
        "season_number": row["season_number"], "episode_number": row["episode_number"],
        "episode_end": row["episode_end"], "title": row["title"], "plot": row["plot"], "filename": row["filename"],
        "container": row["container"], "size": row["size"], "added_at": row["added_at"],
        "thumb_url": _art("episode-thumb", row["id"], row["thumb_path"]), "progress": _progress(row),
        "runtime": _runtime(row), "runtime_status": _runtime_status(row, reader),
    }


def _show_summary(conn, row) -> dict:
    counts = conn.execute(
        "SELECT COUNT(DISTINCT s.id) AS seasons, COUNT(e.id) AS episodes FROM seasons s"
        " LEFT JOIN episodes e ON e.season_id = s.id WHERE s.show_id = ?", (row["id"],)
    ).fetchone()
    return {
        "id": row["id"], "title": row["title"], "year": row["year"], "plot": row["plot"],
        "poster_url": _art("show-poster", row["id"], row["poster_path"]),
        "fanart_url": _art("show-fanart", row["id"], row["fanart_path"]),
        "season_count": counts["seasons"], "episode_count": counts["episodes"],
    }


def _reader(request: Request):
    return request.app.state.durations


def _read_first(request: Request, items: list[dict]) -> None:
    """Items on screen get their lengths read before the rest of the library."""
    _reader(request).prioritize(i["file_id"] for i in items if i.get("runtime_status") == "pending")


@router.get("/metadata/status")
def metadata_status(request: Request):
    return _reader(request).status(request.state.db)


@router.get("/home")
def home(request: Request):
    conn = request.state.db
    rd = _reader(request)
    cont = []
    for p in conn.execute(
        "SELECT f.id AS file_id, f.kind FROM progress p JOIN media_files f ON f.path_key = p.path_key"
        " WHERE p.watched = 0 AND p.position > 10 ORDER BY p.updated_at DESC LIMIT 12"
    ):
        if p["kind"] == "movie":
            row = conn.execute(MOVIE_SQL + " WHERE m.file_id = ?", (p["file_id"],)).fetchone()
            if row:
                cont.append({"type": "movie", **_movie(row, rd)})
        else:
            row = conn.execute(EPISODE_SQL + " WHERE e.file_id = ?", (p["file_id"],)).fetchone()
            if row:
                show = conn.execute("SELECT id, poster_path, fanart_path FROM shows WHERE id = ?", (row["show_id"],)).fetchone()
                cont.append({"type": "episode", **_episode(row, rd),
                             "show_poster_url": _art("show-poster", show["id"], show["poster_path"]),
                             "show_fanart_url": _art("show-fanart", show["id"], show["fanart_path"])})
    movies = [_movie(r, rd) for r in conn.execute(MOVIE_SQL + f" ORDER BY f.added_at DESC, m.sort_title LIMIT {HOME_LIMIT}")]
    episodes = [_episode(r, rd) for r in conn.execute(EPISODE_SQL + f" ORDER BY f.added_at DESC LIMIT {HOME_LIMIT}")]
    _read_first(request, cont + movies + episodes)
    shows = [_show_summary(conn, r) for r in conn.execute(f"SELECT * FROM shows ORDER BY sort_title LIMIT {HOME_LIMIT}")]
    libs = conn.execute("SELECT path, last_scan_at FROM libraries").fetchall()
    # Viewer-safe source status: counts only, never paths (devices must not learn host paths).
    sources = {"total": len(libs), "unreachable": sum(1 for lib in libs if not os.path.isdir(lib["path"])),
               "last_scan_at": max((lib["last_scan_at"] for lib in libs if lib["last_scan_at"]), default=None)}
    counts = {
        "movies": conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
        "shows": conn.execute("SELECT COUNT(*) FROM shows").fetchone()[0],
        "episodes": conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
        "libraries": conn.execute("SELECT COUNT(*) FROM libraries").fetchone()[0],
    }
    return {"continue_watching": cont, "recent_movies": movies, "recent_episodes": episodes,
            "shows": shows, "counts": counts, "sources": sources}


HOME_LIMIT = 24


@router.get("/movies")
def list_movies(request: Request):
    items = [_movie(r, _reader(request)) for r in request.state.db.execute(MOVIE_SQL + " ORDER BY m.sort_title, m.year")]
    _read_first(request, items)
    return items


@router.get("/movies/{movie_id}")
def get_movie(movie_id: int, request: Request):
    row = request.state.db.execute(MOVIE_SQL + " WHERE m.id = ?", (movie_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Movie not found")
    item = _movie(row, _reader(request))
    _read_first(request, [item])
    return item


@router.get("/shows")
def list_shows(request: Request):
    conn = request.state.db
    return [_show_summary(conn, r) for r in conn.execute("SELECT * FROM shows ORDER BY sort_title")]


@router.get("/shows/{show_id}")
def get_show(show_id: int, request: Request):
    conn = request.state.db
    row = conn.execute("SELECT * FROM shows WHERE id = ?", (show_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Show not found")
    seasons, rd = [], _reader(request)
    for s in conn.execute("SELECT * FROM seasons WHERE show_id = ? ORDER BY season_number", (show_id,)):
        eps = [_episode(e, rd) for e in conn.execute(
            EPISODE_SQL + " WHERE e.season_id = ? ORDER BY e.episode_number", (s["id"],))]
        seasons.append({"id": s["id"], "season_number": s["season_number"],
                        "poster_url": _art("season-poster", s["id"], s["poster_path"]), "episodes": eps})
    _read_first(request, [e for s in seasons for e in s["episodes"]])
    return {**_show_summary(conn, row), "seasons": seasons}


def _file_row(conn, file_id: int):
    row = conn.execute("SELECT * FROM media_files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Media file not found")
    return row


def _ensure_probe(request: Request, row) -> dict | None:
    if row["probe_json"]:
        return json.loads(row["probe_json"])
    ffprobe = find_ffprobe(request.app.state.config.ffprobe_path)
    if not ffprobe:
        return None
    try:
        data = probe_file(ffprobe, authorize_media_path(request.state.db, row["path"]))
    except (OSError, ValueError) as exc:
        return {"error": str(exc)}
    except Exception as exc:  # subprocess timeout etc.
        return {"error": f"FFprobe failed: {exc}"}
    request.state.db.execute("UPDATE media_files SET probe_json = ? WHERE id = ?", (json.dumps(data), row["id"]))
    request.state.db.commit()
    return data


@router.get("/files/{file_id}/playback")
def playback_info(file_id: int, request: Request):
    conn = request.state.db
    row = _file_row(conn, file_id)
    probe = _ensure_probe(request, row)
    context: dict = {"kind": row["kind"]}
    if row["kind"] == "movie":
        m = conn.execute(MOVIE_SQL + " WHERE m.file_id = ?", (file_id,)).fetchone()
        if m:
            context.update(title=m["title"], subtitle=str(m["year"] or ""), back=f"/movies/{m['id']}",
                           backdrop_url=_art("movie-fanart", m["id"], m["fanart_path"]))
    else:
        e = conn.execute(EPISODE_SQL + " WHERE e.file_id = ?", (file_id,)).fetchone()
        if e:
            nxt = conn.execute(
                "SELECT e.file_id FROM episodes e JOIN seasons s ON s.id = e.season_id WHERE s.show_id = ?"
                " AND (s.season_number > ? OR (s.season_number = ? AND e.episode_number > ?))"
                " ORDER BY s.season_number, e.episode_number LIMIT 1",
                (e["show_id"], e["season_number"], e["season_number"], e["episode_number"]),
            ).fetchone()
            context.update(
                title=e["show_title"],
                subtitle=f"S{e['season_number']:02d}E{e['episode_number']:02d}" + (f" · {e['title']}" if e["title"] else ""),
                back=f"/shows/{e['show_id']}", next_file_id=nxt["file_id"] if nxt else None,
            )
    prog = conn.execute("SELECT position, duration, watched FROM progress WHERE path_key = ?", (row["path_key"],)).fetchone()
    return {
        "file_id": file_id, "filename": row["filename"], "container": row["container"], "size": row["size"],
        "stream_url": f"/api/stream/{file_id}", "probe": probe,
        "compatibility": assess_playback(row["container"], probe), "progress": dict(prog) if prog else None,
        "context": context,
    }


class ProgressIn(BaseModel):
    position: float = Field(ge=0)
    duration: float | None = Field(default=None, ge=0)


@router.put("/progress/{file_id}")
def save_progress(file_id: int, body: ProgressIn, request: Request):
    conn = request.state.db
    row = _file_row(conn, file_id)
    watched = int(bool(body.duration) and body.position / body.duration >= WATCHED_RATIO)
    conn.execute(
        "INSERT INTO progress (path_key, position, duration, watched, updated_at) VALUES (?,?,?,?,?)"
        " ON CONFLICT(path_key) DO UPDATE SET position=excluded.position, duration=excluded.duration,"
        " watched=excluded.watched, updated_at=excluded.updated_at",
        (row["path_key"], body.position, body.duration, watched, now_iso()),
    )
    conn.commit()
    return {"file_id": file_id, "position": body.position, "duration": body.duration, "watched": bool(watched)}


@router.delete("/progress/{file_id}")
def clear_progress(file_id: int, request: Request):
    row = _file_row(request.state.db, file_id)
    request.state.db.execute("DELETE FROM progress WHERE path_key = ?", (row["path_key"],))
    request.state.db.commit()
    return {"ok": True}


@router.api_route("/stream/{file_id}", methods=["GET", "HEAD"])
def stream(file_id: int, request: Request):
    row = _file_row(request.state.db, file_id)
    real = authorize_media_path(request.state.db, row["path"])
    if path_key(real) != row["path_key"]:
        raise HTTPException(status_code=403, detail="File path changed since the last scan. Rescan the library.")
    return stream_file(request, real, MIME.get(row["container"], "application/octet-stream"))


@router.get("/art/{kind}/{row_id}")
def artwork(kind: str, row_id: int, request: Request):
    if kind not in ART_SOURCES:
        raise HTTPException(status_code=404, detail="Unknown artwork type")
    table, column = ART_SOURCES[kind]
    row = request.state.db.execute(f"SELECT {column} AS p FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if not row or not row["p"] or not row["p"].lower().endswith(IMAGE_EXTENSIONS):
        raise HTTPException(status_code=404, detail="No artwork")
    real = authorize_media_path(request.state.db, row["p"])
    if not os.path.isfile(real):
        raise HTTPException(status_code=404, detail="Artwork file missing")
    return FileResponse(real, headers={"Cache-Control": "private, max-age=3600"})
