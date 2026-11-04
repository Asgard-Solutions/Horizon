"""SQLite storage (Python standard library, public-domain SQLite engine)."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_scan_at TEXT,
    last_scan_summary TEXT
);

CREATE TABLE IF NOT EXISTS media_files (
    id INTEGER PRIMARY KEY,
    library_id INTEGER NOT NULL REFERENCES libraries(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    container TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    kind TEXT NOT NULL,
    probe_json TEXT,
    added_at TEXT NOT NULL,
    seen_scan TEXT
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL UNIQUE REFERENCES media_files(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    sort_title TEXT NOT NULL,
    year INTEGER,
    plot TEXT,
    poster_path TEXT,
    fanart_path TEXT
);

CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY,
    show_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    sort_title TEXT NOT NULL,
    year INTEGER,
    plot TEXT,
    folder_path TEXT,
    poster_path TEXT,
    fanart_path TEXT
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY,
    show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    season_number INTEGER NOT NULL,
    poster_path TEXT,
    UNIQUE (show_id, season_number)
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL UNIQUE REFERENCES media_files(id) ON DELETE CASCADE,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    episode_number INTEGER NOT NULL,
    episode_end INTEGER,
    title TEXT,
    plot TEXT,
    thumb_path TEXT
);

-- Keyed by normalized file path so watch progress survives removing/re-adding a library folder.
CREATE TABLE IF NOT EXISTS progress (
    path_key TEXT PRIMARY KEY,
    position REAL NOT NULL,
    duration REAL,
    watched INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

-- Groups of movies: explicit NFO <set> (source 'nfo') or a folder holding several movies (source 'folder').
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    sort_name TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_seen_at TEXT,
    last_ip TEXT,
    revoked INTEGER NOT NULL DEFAULT 0
);
"""

# Stage 3 metadata columns, added in place to existing databases (genres are JSON arrays of NFO <genre> values).
ADDED_COLUMNS = {
    "movies": {"genres": "TEXT", "nfo_set": "TEXT", "group_path": "TEXT", "collection_id": "INTEGER"},
    "shows": {"genres": "TEXT"},
    "libraries": {"last_success_at": "TEXT"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Path) -> None:
    conn = connect(db_path)
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(progress)")]
        if "file_id" in cols:  # pre-release schema: progress keyed by file id
            conn.execute("DROP TABLE progress")
        conn.executescript(SCHEMA)
        for table, columns in ADDED_COLUMNS.items():
            have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, decl in columns.items():
                if name not in have:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
                    if (table, name) == ("libraries", "last_success_at"):  # older scans: success unless the folder was unreachable
                        conn.execute("UPDATE libraries SET last_success_at = last_scan_at WHERE last_scan_at IS NOT NULL"
                                     " AND COALESCE(last_scan_summary, '') NOT LIKE '%not reachable%'")
        conn.commit()
    finally:
        conn.close()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
