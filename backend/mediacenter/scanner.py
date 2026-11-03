"""Read-only library scanner.

Only os.walk / os.scandir / os.stat and read-mode opens are used on media folders.
Nothing in a library folder is ever created, renamed, modified or deleted.
"""
import os
import threading
import uuid
import xml.etree.ElementTree as ET
from sqlite3 import Connection

from .db import now_iso
from .parser import IMAGE_EXTENSIONS, is_video, parse_episode, parse_movie, season_from_dir, sort_key, split_ext

SKIP_DIRS = {"$recycle.bin", "system volume information", "@eadir", "#recycle", ".trash", "extrafanart", "featurettes"}
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
    conn.execute("DELETE FROM episodes WHERE file_id = ?", (file_id,))
    conn.execute(
        "INSERT INTO movies (file_id, title, sort_title, year, plot, poster_path, fanart_path) VALUES (?,?,?,?,?,?,?)"
        " ON CONFLICT(file_id) DO UPDATE SET title=excluded.title, sort_title=excluded.sort_title, year=excluded.year,"
        " plot=excluded.plot, poster_path=excluded.poster_path, fanart_path=excluded.fanart_path",
        (file_id, title, sort_key(title), year, nfo.get("plot"), poster, fanart),
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
            "INSERT INTO shows (show_key, title, sort_title, year, plot, folder_path, poster_path, fanart_path)"
            " VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(show_key) DO UPDATE SET title=excluded.title,"
            " sort_title=excluded.sort_title, year=excluded.year, plot=COALESCE(excluded.plot, shows.plot),"
            " folder_path=COALESCE(excluded.folder_path, shows.folder_path),"
            " poster_path=COALESCE(excluded.poster_path, shows.poster_path),"
            " fanart_path=COALESCE(excluded.fanart_path, shows.fanart_path)",
            (key, title, sort_key(title), year, show_nfo.get("plot"), show_dir, poster, fanart),
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


def scan_library(conn: Connection, library: dict) -> dict:
    root = library["path"]
    summary = {"files_found": 0, "added": 0, "updated": 0, "unchanged": 0, "removed": 0,
               "movies": 0, "episodes": 0, "errors": [], "started_at": now_iso()}
    if not os.path.isdir(root):
        summary["errors"].append(f"Folder is not reachable: {root}. Nothing was removed from the catalog.")
        summary["finished_at"] = now_iso()
        return summary

    scan_id = uuid.uuid4().hex
    idx = DirIndex()
    show_cache: dict = {}
    walk_errors: list[str] = []

    with SCAN_LOCK:
        for directory, dirnames, filenames in os.walk(root, onerror=lambda e: walk_errors.append(str(e))):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d.lower() not in SKIP_DIRS)
            rel_dirs = _rel_dirs(root, directory)
            for name in sorted(filenames):
                if not is_video(name) or name.startswith("._"):
                    continue
                full = os.path.join(directory, name)
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

        if walk_errors:
            summary["errors"].extend(walk_errors[:50])
            summary["errors"].append("Some folders could not be read, so missing files were NOT removed this scan.")
        else:
            cur = conn.execute(
                "DELETE FROM media_files WHERE library_id = ? AND (seen_scan IS NULL OR seen_scan != ?)",
                (library["id"], scan_id),
            )
            summary["removed"] = cur.rowcount
        cleanup_orphans(conn)
        summary["finished_at"] = now_iso()
        conn.commit()
    return summary
