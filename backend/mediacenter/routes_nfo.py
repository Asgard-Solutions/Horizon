"""Host-only editing of existing local NFO sidecars."""
import hashlib
import hmac
import json
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from . import local_metadata
from .parser import sort_key, split_ext, parse_movie
from .scanner import SCAN_LOCK, DirIndex, _read_nfo, _metadata_snapshot, _save_movie, _rel_dirs, assign_collections, folder_collections_enabled
from .security import require_host

router = APIRouter(prefix="/api/nfo", dependencies=[Depends(require_host)])
Kind = Literal["movie", "tv", "episode"]
ROOTS = {"movie": "movie", "tv": "tvshow", "episode": "episodedetails"}


@router.get("/items")
def items(request: Request, kind: Kind = "movie", show_id: int | None = None, query: str = "", offset: int = 0):
    if not 0 <= offset <= 1000000 or len(query) > 300 or (kind == "episode" and (show_id is None or show_id < 1)):
        raise HTTPException(422, "Choose a show and a valid search page.")
    if kind == "episode":
        sql = "SELECT e.id,COALESCE(e.title,f.filename) AS title,NULL AS year,s.season_number,e.episode_number FROM episodes e JOIN seasons s ON s.id=e.season_id JOIN media_files f ON f.id=e.file_id WHERE s.show_id=?"
        params = [show_id]
        sql += " AND (COALESCE(e.title,'') LIKE ? OR f.filename LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]
        order = " ORDER BY s.season_number,e.episode_number,e.id"
    else:
        sql = f"SELECT id,title,year FROM {local_metadata.TABLES[kind]} WHERE title LIKE ?"
        params = [f"%{query}%"]
        order = " ORDER BY title,id"
    conn = request.state.db
    total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
    return {"total": total, "items": [{**dict(row), "kind": kind} for row in conn.execute(sql + order + " LIMIT 20 OFFSET ?", (*params, offset))]}


def resolve(request, kind, row_id):
    conn = request.state.db
    roots = [row[0] for row in conn.execute("SELECT path FROM libraries")]
    if kind == "tv":
        row = conn.execute("SELECT * FROM shows WHERE id=?", (row_id,)).fetchone()
        if not row:
            raise HTTPException(404, "This show is no longer in the library.")
        directory = row["folder_path"]
        if not directory:
            raise HTTPException(404, "This show has no dedicated folder containing tvshow.nfo.")
        candidates = ["tvshow"]
        identity = row["show_key"]
    else:
        row = conn.execute(f"SELECT m.*,f.path AS media_path,f.path_key,f.filename,f.library_id FROM {local_metadata.TABLES[kind]} m JOIN media_files f ON f.id=m.file_id WHERE m.id=?", (row_id,)).fetchone()
        if not row:
            raise HTTPException(404, "This title is no longer in the library.")
        directory = os.path.dirname(row["media_path"])
        stem, _ = split_ext(row["filename"])
        idx = DirIndex()
        candidates = [stem] + (["movie"] if kind == "movie" and idx.video_count(directory) == 1 else [])
        identity = row["path_key"]
    path = DirIndex().find(directory, candidates, (".nfo",))
    if not path:
        raise HTTPException(404, "No existing local NFO file was found. Create it with your metadata application, then reload. For TV shows use tvshow.nfo; movie/episode NFOs should match the video filename.")
    key = hashlib.sha256(json.dumps([kind, row_id, identity, os.path.normcase(os.path.abspath(path)), request.app.state.instance_id]).encode()).hexdigest()
    return row, path, roots, key


def document(request, kind, row_id):
    from .nfo_document import read_document, inspect_document, NfoError
    row, path, roots, key = resolve(request, kind, row_id)
    try:
        return {**read_document(path, roots, ROOTS[kind]), "path": path, "document_key": key, "kind": kind, "id": row_id, "title": row["title"]}
    except NfoError as exc:
        if exc.status == 422:
            try:
                info = inspect_document(path, roots)
            except NfoError as failure:
                raise HTTPException(failure.status, str(failure)) from None
            return {**info, "fields": None, "read_error": str(exc), "path": path, "document_key": key,
                    "kind": kind, "id": row_id, "title": row["title"]}
        raise HTTPException(exc.status, str(exc)) from None


@router.get("/document/{kind}/{row_id}")
def get_document(kind: Kind, row_id: int, request: Request):
    return document(request, kind, row_id)


class RevisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    document_key: str = Field(pattern=r"^[0-9a-f]{64}$")


class EditIn(RevisionIn):
    fields: dict


def refresh_catalog(conn, kind, row_id, row, path):
    nfo = _read_nfo(path)
    if kind == "movie":
        library = conn.execute("SELECT path FROM libraries WHERE id=?", (row["library_id"],)).fetchone()
        directory = os.path.dirname(row["media_path"])
        _save_movie(conn, row["file_id"], directory, row["filename"], _rel_dirs(library[0], directory), DirIndex())
        assign_collections(conn, folder_collections_enabled(conn))
        return
    title, plot = nfo.get("title") or row["title"], nfo.get("plot")
    if kind == "tv":
        year = nfo.get("year") or parse_movie(os.path.basename(row["folder_path"]), [])["year"]
        genres = json.dumps(nfo["genres"]) if nfo.get("genres") else None
        conn.execute("UPDATE shows SET title=?,sort_title=?,year=?,plot=?,genres=? WHERE id=?", (title, sort_key(nfo.get("sort_title") or title), year, plot, genres, row_id))
        _metadata_snapshot(conn, kind, row_id, nfo, title=title, year=year, plot=plot, genres=genres, poster_path=row["poster_path"], fanart_path=row["fanart_path"])
    else:
        conn.execute("UPDATE episodes SET title=?,plot=? WHERE id=?", (title, plot, row_id))
        _metadata_snapshot(conn, kind, row_id, nfo, title=title, plot=plot, thumb_path=row["thumb_path"])


@router.post("/document/{kind}/{row_id}")
async def save_document(kind: Kind, row_id: int, request: Request):
    from starlette.concurrency import run_in_threadpool
    raw = await request.body()
    if len(raw) > 200000:
        raise HTTPException(413, "NFO edits are too large.")
    try:
        value = EditIn.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError):
        raise HTTPException(422, "Check the NFO fields and reload the file if needed.") from None
    def save():
        from .nfo_document import save_document as write_document, NfoError
        if not SCAN_LOCK.acquire(timeout=.2):
            raise HTTPException(409, "A library scan is running. Finish or cancel it before editing an NFO.")
        try:
            row, path, roots, key = resolve(request, kind, row_id)
            if not hmac.compare_digest(key, value.document_key):
                raise HTTPException(409, "The selected library entry or NFO changed. Reload it before saving.")
            result = write_document(path, roots, value.revision, value.fields, ROOTS[kind])
            try:
                with request.state.db:
                    refresh_catalog(request.state.db, kind, row_id, row, path)
            except Exception:
                return {**result, "path": path, "document_key": key, "kind": kind, "id": row_id, "title": row["title"],
                        "warning": "The NFO was saved and backed up, but the catalog refresh failed. Rescan this source to display the changes."}
            return {**result, "path": path, "document_key": key, "kind": kind, "id": row_id, "title": value.fields.get("title", row["title"])}
        except NfoError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        finally:
            SCAN_LOCK.release()
    return await run_in_threadpool(save)


@router.post("/document/{kind}/{row_id}/delete")
async def delete_document(kind: Kind, row_id: int, request: Request):
    from starlette.concurrency import run_in_threadpool
    raw = await request.body()
    if len(raw) > 2000:
        raise HTTPException(413, "NFO removal request is too large.")
    try:
        value = RevisionIn.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError):
        raise HTTPException(422, "Reload the NFO before removing it.") from None

    def remove():
        from .nfo_document import remove_document, NfoError
        if not SCAN_LOCK.acquire(timeout=.2):
            raise HTTPException(409, "A library scan is running. Finish or cancel it before removing an NFO.")
        try:
            _, path, roots, key = resolve(request, kind, row_id)
            if not hmac.compare_digest(key, value.document_key):
                raise HTTPException(409, "The selected library entry or NFO changed. Reload it before removing it.")
            return {**remove_document(path, roots, value.revision), "path": path,
                    "message": "NFO removed. Rescan this source to refresh its cached metadata. Media files and library titles are kept."}
        except NfoError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        finally:
            SCAN_LOCK.release()
    return await run_in_threadpool(remove)
