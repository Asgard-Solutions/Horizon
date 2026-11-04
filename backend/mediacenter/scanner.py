"""Read-only library scanner.

Only os.walk / os.scandir / os.stat and read-mode opens are used on media folders.
Nothing in a library folder is ever created, renamed, modified or deleted.
"""
import json
import os
import threading
import uuid
import xml.etree.ElementTree as ET
from sqlite3 import Connection

from .db import get_setting, now_iso
from .paths import is_link_or_junction, is_within
from .parser import IMAGE_EXTENSIONS, is_video, parse_episode, parse_movie, season_from_dir, sort_key, split_ext

SKIP_DIRS = {"$recycle.bin", "system volume information", "@eadir", "#recycle", ".trash", "extrafanart", "featurettes"}
# Folders that organise a library rather than group related movies; never shown as collections.
GENERIC_FOLDERS = {"movies", "movie", "films", "film", "media", "video", "videos", "tv", "tv shows", "tvshows", "shows",
                   "series", "library", "collections", "collection", "4k", "uhd", "hd", "1080p", "720p", "2160p",
                   "downloads", "download", "completed", "new", "unsorted", "misc", "other", "kids", "children"}
MAX_NFO_BYTES = 1_000_000
SCAN_LOCK = threading.Lock()


def path_key(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _read_nfo(path: str | None) -> dict:
    if not path:
        return {}
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_NFO_BYTES)
        end = data.rfind(b">")
        root = ET.fromstring(data[: end + 1]) if end > 0 else None
    except (OSError, ET.ParseError, ValueError):
        return {}
    if root is None:
        return {}
    out = {}
    for tag in ("title", "plot", "year", "season", "episode"):
        el = root.find(tag)
        if el is not None and el.text and el.text.strip():
            out[tag] = el.text.strip()
    genres: list[str] = []
    for el in root.findall("genre"):
        for part in (el.text or "").replace("|", "/").split("/"):
            name = " ".join(part.split())
            if name and name.casefold() not in {g.casefold() for g in genres}:
                genres.append(name[:60])
    if genres:
        out["genres"] = genres[:12]
    s = root.find("set")
    if s is not None:  # Kodi: <set><name>X</name></set> or legacy <set>X</set>
        name = s.findtext("name") if s.find("name") is not None else s.text
        if name and name.strip():
            out["set"] = " ".join(name.split())[:120]
    if "year" in out:
        try:
            out["year"] = int(out["year"][:4])
        except ValueError:
            out.pop("year")
    return out


class DirIndex:
    """Caches lower-cased directory listings so artwork/NFO lookups don't hit the disk repeatedly."""

    def __init__(self):
        self._cache: dict[str, dict[str, str]] = {}

    def listing(self, directory: str) -> dict[str, str]:
        if directory not in self._cache:
            try:
                with os.scandir(directory) as it:
                    self._cache[directory] = {e.name.lower(): e.path for e in it if e.is_file(follow_symlinks=False)}
            except OSError:
                self._cache[directory] = {}
        return self._cache[directory]

    def find(self, directory: str | None, bases: list[str], exts=IMAGE_EXTENSIONS) -> str | None:
        if not directory:
            return None
        files = self.listing(directory)
        for base in bases:
            for ext in exts:
                hit = files.get(f"{base.lower()}{ext}")
                if hit:
                    return hit
        return None

    def video_count(self, directory: str) -> int:
        return sum(1 for name in self.listing(directory) if is_video(name))


def _rel_dirs(root: str, directory: str) -> list[str]:
    rel = os.path.relpath(directory, root)
    return [] if rel in (".", "") else rel.replace("\\", "/").split("/")


def _upsert_file(conn: Connection, library_id: int, path: str, name: str, st, kind: str, scan_id: str) -> tuple[int, str]:
    key = path_key(path)
    _, ext = split_ext(name)
    row = conn.execute("SELECT id, size, mtime FROM media_files WHERE path_key = ?", (key,)).fetchone()
    if row:
        changed = row["size"] != st.st_size or row["mtime"] != st.st_mtime
        conn.execute(
            "UPDATE media_files SET library_id=?, path=?, filename=?, container=?, size=?, mtime=?, kind=?, seen_scan=?"
            + (", probe_json=NULL" if changed else "") + " WHERE id=?",
            (library_id, path, name, ext, st.st_size, st.st_mtime, kind, scan_id, row["id"]),
        )
        return row["id"], "updated" if changed else "unchanged"
    cur = conn.execute(
        "INSERT INTO media_files (library_id, path, path_key, filename, container, size, mtime, kind, added_at, seen_scan)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (library_id, path, key, name, ext, st.st_size, st.st_mtime, kind, now_iso(), scan_id),
    )
    return cur.lastrowid, "added"


def _save_movie(conn, file_id, directory, name, rel_dirs, idx: DirIndex):
    stem, _ = split_ext(name)
    info = parse_movie(name, rel_dirs)
    nfo = _read_nfo(idx.find(directory, [stem, "movie"], (".nfo",)) if idx.video_count(directory) == 1
                    else idx.find(directory, [stem], (".nfo",)))
    title = nfo.get("title") or info["title"]
    year = nfo.get("year") or info["year"]
    dedicated = idx.video_count(directory) == 1 and bool(rel_dirs)
    poster = idx.find(directory, [f"{stem}-poster", stem] + (["poster", "folder", "cover", "movie"] if dedicated else []))
    fanart = idx.find(directory, [f"{stem}-fanart"] + (["fanart", "backdrop"] if dedicated else []))
    # Folder grouping candidate: the folder that holds this movie's own folder, or the folder holding several movies.
    group_dir = os.path.dirname(directory) if dedicated else directory
    group_rel = rel_dirs[:-1] if dedicated else rel_dirs
    group = group_dir if group_rel and group_rel[-1].strip().casefold() not in GENERIC_FOLDERS else None
    genres = nfo.get("genres")
    conn.execute("DELETE FROM episodes WHERE file_id = ?", (file_id,))
    conn.execute(
        "INSERT INTO movies (file_id, title, sort_title, year, plot, poster_path, fanart_path, genres, nfo_set, group_path)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(file_id) DO UPDATE SET title=excluded.title, sort_title=excluded.sort_title, year=excluded.year,"
        " plot=excluded.plot, poster_path=excluded.poster_path, fanart_path=excluded.fanart_path, genres=excluded.genres,"
        " nfo_set=excluded.nfo_set, group_path=excluded.group_path",
        (file_id, title, sort_key(title), year, nfo.get("plot"), poster, fanart,
         json.dumps(genres) if genres else None, nfo.get("set"), group),
    )


def _save_episode(conn, file_id, root, directory, name, rel_dirs, info, idx: DirIndex, show_cache: dict):
    stem, _ = split_ext(name)
    season_dir = directory if rel_dirs and season_from_dir(rel_dirs[-1]) is not None else None
    if info["uses_show_folder"]:
        show_dir = os.path.dirname(directory) if season_dir else directory
    else:
        show_dir = None

    show_nfo = _read_nfo(idx.find(show_dir, ["tvshow"], (".nfo",)))
    title = show_nfo.get("title") or info["show_title"]
    year = info["show_year"] or show_nfo.get("year")
    key = info["show_key"]
    if key not in show_cache:
        poster = idx.find(show_dir, ["poster", "folder", "cover", "show"])
        fanart = idx.find(show_dir, ["fanart", "backdrop"])
        conn.execute(
            "INSERT INTO shows (show_key, title, sort_title, year, plot, folder_path, poster_path, fanart_path, genres)"
            " VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(show_key) DO UPDATE SET title=excluded.title,"
            " sort_title=excluded.sort_title, year=excluded.year, plot=COALESCE(excluded.plot, shows.plot),"
            " folder_path=COALESCE(excluded.folder_path, shows.folder_path),"
            " poster_path=COALESCE(excluded.poster_path, shows.poster_path),"
            " fanart_path=COALESCE(excluded.fanart_path, shows.fanart_path),"
            " genres=CASE WHEN excluded.folder_path IS NOT NULL THEN excluded.genres ELSE shows.genres END",
            (key, title, sort_key(title), year, show_nfo.get("plot"), show_dir, poster, fanart,
             json.dumps(show_nfo["genres"]) if show_nfo.get("genres") else None),
        )
        show_cache[key] = conn.execute("SELECT id FROM shows WHERE show_key = ?", (key,)).fetchone()["id"]
    show_id = show_cache[key]

    season_no = info["season"]
    season_poster = idx.find(show_dir, [f"season{season_no:02d}-poster", f"season{season_no}-poster"]) or \
        idx.find(season_dir, ["poster", "folder", "cover"])
    conn.execute(
        "INSERT INTO seasons (show_id, season_number, poster_path) VALUES (?,?,?) ON CONFLICT(show_id, season_number)"
        " DO UPDATE SET poster_path=COALESCE(excluded.poster_path, seasons.poster_path)",
        (show_id, season_no, season_poster),
    )
    season_id = conn.execute(
        "SELECT id FROM seasons WHERE show_id=? AND season_number=?", (show_id, season_no)
    ).fetchone()["id"]

    ep_nfo = _read_nfo(idx.find(directory, [stem], (".nfo",)))
    thumb = idx.find(directory, [f"{stem}-thumb", stem])
    conn.execute("DELETE FROM movies WHERE file_id = ?", (file_id,))
    conn.execute(
        "INSERT INTO episodes (file_id, season_id, episode_number, episode_end, title, plot, thumb_path)"
        " VALUES (?,?,?,?,?,?,?) ON CONFLICT(file_id) DO UPDATE SET season_id=excluded.season_id,"
        " episode_number=excluded.episode_number, episode_end=excluded.episode_end, title=excluded.title,"
        " plot=excluded.plot, thumb_path=excluded.thumb_path",
        (file_id, season_id, info["episode"], info["episode_end"], ep_nfo.get("title") or info["episode_title"],
         ep_nfo.get("plot"), thumb),
    )


def cleanup_orphans(conn: Connection) -> None:
    conn.execute("DELETE FROM seasons WHERE id NOT IN (SELECT DISTINCT season_id FROM episodes)")
    conn.execute("DELETE FROM shows WHERE id NOT IN (SELECT DISTINCT show_id FROM seasons)")


def folder_collections_enabled(conn: Connection) -> bool:
    return get_setting(conn, "folder_collections", "1") == "1"


def assign_collections(conn: Connection, folder_groups: bool) -> None:
    """Explicit NFO sets win; otherwise (if enabled) a non-generic folder holding 2+ movies becomes a folder collection.
    Collection ids stay stable across rescans (keyed by set name / folder path)."""
    groups: dict[str, list] = {}
    for r in conn.execute("SELECT id, nfo_set, group_path FROM movies"):
        if r["nfo_set"]:
            key, name, source = "nfo:" + r["nfo_set"].casefold(), r["nfo_set"], "nfo"
        elif folder_groups and r["group_path"]:
            key = "folder:" + os.path.normcase(r["group_path"])
            name, source = os.path.basename(r["group_path"].rstrip("\\/")) or r["group_path"], "folder"
        else:
            continue
        groups.setdefault(key, [name, source, []])[2].append(r["id"])
    groups = {k: g for k, g in groups.items() if g[1] == "nfo" or len(g[2]) >= 2}
    conn.execute("UPDATE movies SET collection_id = NULL")
    for key, (name, source, ids) in groups.items():
        conn.execute("INSERT INTO collections (key, name, sort_name, source) VALUES (?,?,?,?) ON CONFLICT(key)"
                     " DO UPDATE SET name=excluded.name, sort_name=excluded.sort_name, source=excluded.source",
                     (key, name, sort_key(name), source))
        cid = conn.execute("SELECT id FROM collections WHERE key = ?", (key,)).fetchone()["id"]
        conn.executemany("UPDATE movies SET collection_id = ? WHERE id = ?", [(cid, i) for i in ids])
    conn.execute("DELETE FROM collections WHERE id NOT IN (SELECT collection_id FROM movies WHERE collection_id IS NOT NULL)")


COMMIT_EVERY = 200  # long NAS scans commit in batches so playback progress and browsing never wait on the scan


def scan_library(conn: Connection, library: dict, progress=None, cancel: threading.Event | None = None) -> dict:
    """status: complete | partial (some folders unreadable) | cancelled | unreachable.
    Titles are only removed after a complete walk; cancelled, interrupted or unreachable scans never remove anything."""
    root = library["path"]
    summary = {"files_found": 0, "added": 0, "updated": 0, "unchanged": 0, "removed": 0,
               "movies": 0, "episodes": 0, "errors": [], "started_at": now_iso(), "status": "complete"}
    if not os.path.isdir(root):
        summary["errors"].append(f"Folder is not reachable: {root}. Nothing was removed from the catalog.")
        summary["status"] = "unreachable"
        summary["finished_at"] = now_iso()
        return summary

    scan_id = uuid.uuid4().hex
    root_key = path_key(root)
    idx = DirIndex()
    show_cache: dict = {}
    walk_errors: list[str] = []

    with SCAN_LOCK:
        for directory, dirnames, filenames in os.walk(root, onerror=lambda e: walk_errors.append(str(e))):
            # Never descend into symlinks/NTFS junctions: they could point outside the library folder.
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d.lower() not in SKIP_DIRS
                                 and not is_link_or_junction(os.path.join(directory, d)))
            if cancel is not None and cancel.is_set():
                break
            rel_dirs = _rel_dirs(root, directory)
            if progress:
                progress(summary["files_found"], "/".join(rel_dirs))
            for name in sorted(filenames):
                if cancel is not None and cancel.is_set():
                    break
                if not is_video(name) or name.startswith("._"):
                    continue
                full = os.path.join(directory, name)
                if is_link_or_junction(full) and not is_within(root_key, path_key(full)):
                    walk_errors.append(f"Skipped link pointing outside the library: {full}")
                    continue
                try:
                    st = os.stat(full)
                except OSError as exc:
                    walk_errors.append(f"{full}: {exc}")
                    continue
                summary["files_found"] += 1
                ep = parse_episode(name, rel_dirs)
                kind = "episode" if ep else "movie"
                file_id, state = _upsert_file(conn, library["id"], full, name, st, kind, scan_id)
                summary[state] += 1
                if ep:
                    _save_episode(conn, file_id, root, directory, name, rel_dirs, ep, idx, show_cache)
                    summary["episodes"] += 1
                else:
                    _save_movie(conn, file_id, directory, name, rel_dirs, idx)
                    summary["movies"] += 1
                if summary["files_found"] % COMMIT_EVERY == 0:
                    conn.commit()
                    if progress:
                        progress(summary["files_found"], "/".join(rel_dirs))

        if cancel is not None and cancel.is_set():
            summary["status"] = "cancelled"
            summary["errors"].append("Scan cancelled. Titles found so far were kept and nothing was removed.")
        elif walk_errors:
            summary["status"] = "partial"
            summary["errors"].extend(walk_errors[:50])
            summary["errors"].append("Some folders could not be read, so missing files were NOT removed this scan.")
        else:
            cur = conn.execute(
                "DELETE FROM media_files WHERE library_id = ? AND (seen_scan IS NULL OR seen_scan != ?)",
                (library["id"], scan_id),
            )
            summary["removed"] = cur.rowcount
        cleanup_orphans(conn)
        assign_collections(conn, folder_collections_enabled(conn))
        summary["finished_at"] = now_iso()
        conn.commit()
    return summary
