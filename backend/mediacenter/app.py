"""FastAPI application factory."""
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import routes_admin, routes_auth, routes_discover, routes_library
from .config import APP_VERSION, Config, load_config
from .db import connect, init_db
from .durations import DurationWorker

# Windows reads MIME types from the registry, which is often wrong (e.g. .js as text/plain) and breaks the UI
# because responses carry X-Content-Type-Options: nosniff. Pin the types we serve.
for _ext, _type in {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".html": "text/html",
                    ".svg": "image/svg+xml", ".woff2": "font/woff2", ".woff": "font/woff", ".json": "application/json",
                    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.items():
    mimetypes.add_type(_type, _ext)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-mc-client"


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or load_config()
    init_db(cfg.db_path)
    durations = DurationWorker(cfg.db_path, cfg.ffprobe_path, cfg.probe_workers)

    @asynccontextmanager
    async def lifespan(_app):
        durations.start()  # resumes any files left unread by a previous run
        yield
        durations.stop()

    app = FastAPI(title="Open Media Center (Phase 0)", version=APP_VERSION, docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)
    app.state.config = cfg
    app.state.durations = durations

    @app.middleware("http")
    async def db_and_csrf(request: Request, call_next):
        if request.url.path.startswith("/api") and request.method in UNSAFE_METHODS \
                and not request.headers.get(CSRF_HEADER):
            return JSONResponse({"detail": f"Missing {CSRF_HEADER} header."}, status_code=403)
        request.state.db = connect(cfg.db_path)
        try:
            response = await call_next(request)
        finally:
            request.state.db.close()
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": APP_VERSION}

    app.include_router(routes_auth.router)
    app.include_router(routes_admin.router)
    app.include_router(routes_library.router)
    app.include_router(routes_discover.router)
    _mount_frontend(app, cfg.frontend_dist)
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built web UI (frontend/dist) from the same origin when it exists."""
    index = dist / "index.html"
    if not index.is_file():
        return
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)
