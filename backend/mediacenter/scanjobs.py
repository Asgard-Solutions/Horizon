"""Background library scans: one at a time, queued, with live progress and cancel.

Scans only ever read media folders (see scanner.py). A cancelled, interrupted or unreachable scan never removes titles.
"""
import json
import logging
import threading
import uuid
from collections import deque

from .db import connect, now_iso
from .scanner import scan_library

log = logging.getLogger("mediacenter.scans")
SUCCESS = ("complete", "partial")
MAX_RECENT = 20


def record_scan(conn, library_id: int, summary: dict) -> None:
    """last_scan_at = last attempt; last_success_at = last scan that walked the whole folder."""
    conn.execute("UPDATE libraries SET last_scan_at = ?, last_scan_summary = ? WHERE id = ?",
                 (now_iso(), json.dumps(summary), library_id))
    if summary.get("status", "complete") in SUCCESS:
        conn.execute("UPDATE libraries SET last_success_at = ? WHERE id = ?", (summary.get("finished_at") or now_iso(), library_id))
    conn.commit()


class ScanManager:
    def __init__(self, db_path, on_finished=None):
        self.db_path = db_path
        self.on_finished = on_finished
        self._lock = threading.Lock()
        self._queue: deque[dict] = deque()
        self._current: dict | None = None
        self._cancel = threading.Event()
        self._recent: deque[dict] = deque(maxlen=MAX_RECENT)
        self._thread: threading.Thread | None = None
        self._running = False
        self._stop = False

    def _public(self, job: dict) -> dict:
        return {k: v for k, v in job.items() if not k.startswith("_")}

    def status(self) -> dict:
        with self._lock:
            return {"running": self._public(self._current) if self._current else None,
                    "queued": [self._public(j) for j in self._queue],
                    "recent": [self._public(j) for j in reversed(self._recent)]}

    def enqueue(self, libraries: list[dict]) -> dict:
        with self._lock:
            busy = {j["library_id"] for j in self._queue} | ({self._current["library_id"]} if self._current else set())
            for lib in libraries:
                if lib["id"] in busy:
                    continue
                self._queue.append({"id": uuid.uuid4().hex[:12], "library_id": lib["id"], "library_name": lib["name"],
                                    "path": lib["path"], "state": "queued", "files_found": 0, "current": "",
                                    "queued_at": now_iso(), "started_at": None, "finished_at": None, "summary": None})
            if self._queue and not self._running and not self._stop:
                self._running = True
                self._thread = threading.Thread(target=self._run, name="library-scan", daemon=True)
                self._thread.start()
        return self.status()

    def cancel(self, job_id: str | None = None, library_id: int | None = None) -> dict:
        """No arguments: cancel everything (running + queued)."""
        def match(j):
            return (job_id is None and library_id is None) or j["id"] == job_id or j["library_id"] == library_id
        with self._lock:
            for j in [j for j in self._queue if match(j)]:
                self._queue.remove(j)
                self._recent.append({**j, "state": "cancelled", "finished_at": now_iso()})
            if self._current and match(self._current):
                self._cancel.set()
        return self.status()

    def busy_with(self, library_id: int) -> bool:
        with self._lock:
            return bool(self._current and self._current["library_id"] == library_id)

    def stop(self) -> None:
        with self._lock:
            self._stop = True
            self._queue.clear()
            self._cancel.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _progress(self, files: int, current: str) -> None:
        with self._lock:
            if self._current:
                self._current["files_found"], self._current["current"] = files, current

    def _run(self) -> None:
        conn = connect(self.db_path)
        try:
            while True:
                with self._lock:
                    if self._stop or not self._queue:
                        self._current = None
                        self._running = False
                        return
                    job = self._current = self._queue.popleft()
                    job.update(state="running", started_at=now_iso())
                    self._cancel.clear()
                row = conn.execute("SELECT * FROM libraries WHERE id = ?", (job["library_id"],)).fetchone()
                try:
                    if row is None:
                        summary = {"status": "removed", "errors": ["This source was removed before its scan started."]}
                    else:
                        summary = scan_library(conn, dict(row), self._progress, self._cancel)
                        record_scan(conn, row["id"], summary)
                    state = {"complete": "done", "partial": "done"}.get(summary.get("status"), summary.get("status"))
                except Exception as exc:  # report and move on; the rest of the library keeps working
                    log.exception("Scan failed for %s", job["path"])
                    conn.rollback()
                    summary, state = {"status": "failed", "errors": [f"Scan failed: {exc}"]}, "failed"
                with self._lock:
                    job.update(state=state, summary=summary, finished_at=now_iso(),
                               files_found=summary.get("files_found", job["files_found"]))
                    self._recent.append(job)
                    self._current = None
                if self.on_finished:
                    self.on_finished()
        finally:
            conn.close()
            with self._lock:
                self._running = False
