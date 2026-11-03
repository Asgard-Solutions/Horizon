"""Catalog, playback and streaming API (used by the web UI and reusable by a future native client)."""
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .db import now_iso
from .parser import IMAGE_EXTENSIONS
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


def authorize_media_path(conn, path: str) -> str:
    """Only files located inside a configured library folder may be served."""
    real = os.path.realpath(path)
    key = os.path.normcase(real)
    for lib in conn.execute("SELECT path FROM libraries"):
        root = os.path.normcase(os.path.realpath(lib["path"]))
        try:
            if os.path.commonpath([root, key]) == root:
                return real
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail="File is outside the configured library folders.")


MOVIE_SQL = """
SELECT m.*, f.filename, f.container, f.size, f.added_at, p.position, p.duration, p.watched
FROM movies m JOIN media_files f ON f.id = m.file_id LEFT JOIN progress p ON p.file_id = m.file_id
"""
EPISODE_SQL = """
SELECT e.*, s.season_number, s.show_id, sh.title AS show_title, f.filename, f.container, f.size, f.added_at,
       p.position, p.duration, p.watched
FROM episodes e JOIN seasons s ON s.id = e.season_id JOIN shows sh ON sh.id = s.show_id
JOIN media_files f ON f.id = e.file_id LEFT JOIN progress p ON p.file_id = e.file_id
"""


def _movie(row) -> dict:
    return {
        "id": row["id"], "file_id": row["file_id"], "title": row["title"], "year": row["year"], "plot": row["plot"],
        "filename": row["filename"], "container": row["container"], "size": row["size"], "added_at": row["added_at"],
        "poster_url": _art("movie-poster", row["id"], row["poster_path"]),
        "fanart_url": _art("movie-fanart", row["id"], row["fanart_path"]),
        "progress": _progress(row),
    }


def _episode(row) -> dict:
    return {
        "id": row["id"], "file_id": row["file_id"], "show_id": row["show_id"], "show_title": row["show_title"],
        "season_number": row["season_number"], "episode_number": row["episode_number"],
        "episode_end": row["episode_end"], "title": row["title"], "plot": row["plot"], "filename": row["filename"],
        "container": row["container"], "size": row["size"], "added_at": row["added_at"],
        "thumb_url": _art("episode-thumb", row["id"], row["thumb_path"]), "progress": _progress(row),
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


@router.get("/home")
def home(request: Request):
    conn = request.state.db
    cont = []
    for p in conn.execute(
        "SELECT p.file_id, f.kind FROM progress p JOIN media_files f ON f.id = p.file_id"
        " WHERE p.watched = 0 AND p.position > 10 ORDER BY p.updated_at DESC LIMIT 12"
    ):
        if p["kind"] == "movie":
            row = conn.execute(MOVIE_SQL + " WHERE m.file_id = ?", (p["file_id"],)).fetchone()
            if row:
                cont.append({"type": "movie", **_movie(row)})
        else:
            row = conn.execute(EPISODE_SQL + " WHERE e.file_id = ?", (p["file_id"],)).fetchone()
            if row:
                cont.append({"type": "episode", **_episode(row)})
    movies = [_movie(r) for r in conn.execute(MOVIE_SQL + " ORDER BY f.added_at DESC, m.sort_title LIMIT 16")]
    episodes = [_episode(r) for r in conn.execute(EPISODE_SQL + " ORDER BY f.added_at DESC LIMIT 16")]
    shows = [_show_summary(conn, r) for r in conn.execute("SELECT * FROM shows ORDER BY sort_title LIMIT 16")]
    counts = {
        "movies": conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
        "shows": conn.execute("SELECT COUNT(*) FROM shows").fetchone()[0],
        "episodes": conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
        "libraries": conn.execute("SELECT COUNT(*) FROM libraries").fetchone()[0],
    }
    return {"continue_watching": cont, "recent_movies": movies, "recent_episodes": episodes,
            "shows": shows, "counts": counts}


@router.get("/movies")
def list_movies(request: Request):
    return [_movie(r) for r in request.state.db.execute(MOVIE_SQL + " ORDER BY m.sort_title, m.year")]


@router.get("/movies/{movie_id}")
def get_movie(movie_id: int, request: Request):
    row = request.state.db.execute(MOVIE_SQL + " WHERE m.id = ?", (movie_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _movie(row)


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
    seasons = []
    for s in conn.execute("SELECT * FROM seasons WHERE show_id = ? ORDER BY season_number", (show_id,)):
        eps = [_episode(e) for e in conn.execute(
            EPISODE_SQL + " WHERE e.season_id = ? ORDER BY e.episode_number", (s["id"],))]
        seasons.append({"id": s["id"], "season_number": s["season_number"],
                        "poster_url": _art("season-poster", s["id"], s["poster_path"]), "episodes": eps})
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
    prog = conn.execute("SELECT position, duration, watched FROM progress WHERE file_id = ?", (file_id,)).fetchone()
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
    _file_row(conn, file_id)
    watched = int(bool(body.duration) and body.position / body.duration >= WATCHED_RATIO)
    conn.execute(
        "INSERT INTO progress (file_id, position, duration, watched, updated_at) VALUES (?,?,?,?,?)"
        " ON CONFLICT(file_id) DO UPDATE SET position=excluded.position, duration=excluded.duration,"
        " watched=excluded.watched, updated_at=excluded.updated_at",
        (file_id, body.position, body.duration, watched, now_iso()),
    )
    conn.commit()
    return {"file_id": file_id, "position": body.position, "duration": body.duration, "watched": bool(watched)}


@router.delete("/progress/{file_id}")
def clear_progress(file_id: int, request: Request):
    request.state.db.execute("DELETE FROM progress WHERE file_id = ?", (file_id,))
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
