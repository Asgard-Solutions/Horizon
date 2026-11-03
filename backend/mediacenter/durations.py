"""Background media-length reader.

Runs FFprobe (read-only: it opens files for reading and never writes) on files whose metadata is not cached yet,
after scans, so scans stay fast on large NAS libraries. Results are cached in media_files.probe_json; pending work
is simply "probe_json IS NULL", so an interrupted run resumes on the next start. Files the viewer is looking at
are read first.
"""
import json
import logging
import os
import sqlite3
import subprocess
import threading

from .db import connect
from .paths import library_real_path
from .probe import find_ffprobe, probe_file
from .scanner import SCAN_LOCK

log = logging.getLogger("mediacenter.durations")
MAX_PRIORITY = 200
IDLE_POLL_S = 30


class DurationWorker:
    def __init__(self, db_path, ffprobe_path: str | None, workers: int):
        self.db_path = db_path
        self.ffprobe = find_ffprobe(ffprobe_path)
        self.workers = max(0, workers)
        self._cond = threading.Condition()
        self._priority: list[int] = []
        self._claimed: set[int] = set()
        self._skipped: set[int] = set()  # unreadable right now (offline NAS, timeout); retried after a rescan/restart
        self._threads: list[threading.Thread] = []
        self._stop = False

    @property
    def enabled(self) -> bool:
        return bool(self.ffprobe) and self.workers > 0

    def start(self) -> None:
        if not self.enabled or self._threads:
            return
        self._stop = False
        for i in range(self.workers):
            t = threading.Thread(target=self._run, name=f"duration-reader-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        with self._cond:
            self._stop = True
            self._cond.notify_all()
        for t in self._threads:
            t.join(timeout=5)
        self._threads = []

    def wake(self) -> None:
        """Called after a scan: new/changed files have probe_json NULL; previously unreadable files get another try."""
        with self._cond:
            self._skipped.clear()
            self._cond.notify_all()

    def prioritize(self, file_ids) -> None:
        if not self.enabled:
            return
        ids = list(dict.fromkeys(file_ids))
        with self._cond:
            self._priority = (ids + [i for i in self._priority if i not in ids])[:MAX_PRIORITY]
            self._cond.notify_all()

    def status(self, conn) -> dict:
        row = conn.execute(
            "SELECT SUM(probe_json IS NULL) AS pending,"
            " SUM(probe_json IS NOT NULL AND json_extract(probe_json, '$.duration') IS NOT NULL) AS known,"
            " SUM(probe_json IS NOT NULL AND json_extract(probe_json, '$.duration') IS NULL) AS unknown FROM media_files"
        ).fetchone()
        with self._cond:
            active, skipped = len(self._claimed), len(self._skipped)
        return {"available": self.enabled, "workers": self.workers, "pending": row["pending"] or 0,
                "known": row["known"] or 0, "unknown": row["unknown"] or 0, "active": active, "unreachable": skipped}

    def _next(self, conn):
        excluded = self._claimed | self._skipped
        while self._priority:
            fid = self._priority.pop(0)
            if fid in excluded:
                continue
            row = conn.execute("SELECT id, path, size, mtime FROM media_files WHERE id = ? AND probe_json IS NULL",
                               (fid,)).fetchone()
            if row:
                return row
        for row in conn.execute("SELECT id, path, size, mtime FROM media_files WHERE probe_json IS NULL ORDER BY id LIMIT ?",
                                (len(excluded) + 1,)):
            if row["id"] not in excluded:
                return row
        return None

    def _claim(self, conn, block: bool):
        with self._cond:
            while not self._stop:
                if not SCAN_LOCK.locked():  # never compete with a running scan for the disk or the database
                    row = self._next(conn)
                    if row:
                        self._claimed.add(row["id"])
                        return row
                    if not block:
                        return None
                    self._cond.wait(IDLE_POLL_S)
                else:
                    if not block:
                        return None
                    self._cond.wait(2)
            return None

    def _process(self, conn, row) -> None:
        try:
            real = library_real_path(conn, row["path"])
            if not real or not os.path.isfile(real):
                raise FileNotFoundError(row["path"])
            data = probe_file(self.ffprobe, real, background=True)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            log.info("Duration not read yet for %s: %s", row["path"], exc)
            with self._cond:
                self._skipped.add(row["id"])
            return
        # FFprobe errors (damaged/unknown files) are cached too, so they are not retried until the file changes.
        try:
            conn.execute("UPDATE media_files SET probe_json = ? WHERE id = ? AND probe_json IS NULL AND size = ? AND mtime = ?",
                         (json.dumps(data), row["id"], row["size"], row["mtime"]))
            conn.commit()
        except sqlite3.OperationalError as exc:  # database busy: leave it pending, a later pass retries
            log.info("Could not cache duration for %s: %s", row["path"], exc)

    def _release(self, file_id: int) -> None:
        with self._cond:
            self._claimed.discard(file_id)

    def _run(self) -> None:
        conn = connect(self.db_path)
        try:
            while True:
                row = self._claim(conn, block=True)
                if row is None:
                    return
                try:
                    self._process(conn, row)
                finally:
                    self._release(row["id"])
        finally:
            conn.close()

    def run_until_idle(self) -> int:
        """Synchronous single-threaded pass (tests and tools). Returns the number of files handled."""
        if not self.ffprobe:
            return 0
        conn = connect(self.db_path)
        handled = 0
        try:
            while (row := self._claim(conn, block=False)) is not None:
                try:
                    self._process(conn, row)
                    handled += 1
                finally:
                    self._release(row["id"])
        finally:
            conn.close()
        return handled
