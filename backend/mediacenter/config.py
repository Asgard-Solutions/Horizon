"""Runtime configuration. Everything is local; values come from environment variables or an optional .env file."""
import ipaddress
import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
APP_VERSION = "0.1.0-phase0"


def load_env_file(path: Path) -> None:
    """Minimal KEY=VALUE loader (no third-party dependency). Existing environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Config:
    data_dir: Path
    frontend_dist: Path
    ffprobe_path: str | None = None
    admin_networks: list = field(default_factory=list)
    allowed_hosts: list[str] = field(default_factory=list)
    bind_host: str | None = None
    port: int | None = None
    probe_workers: int = 2

    @property
    def db_path(self) -> Path:
        return self.data_dir / "mediacenter.sqlite3"


def load_config() -> Config:
    load_env_file(BACKEND_DIR / ".env")
    data_dir = Path(os.environ.get("MC_DATA_DIR") or PROJECT_DIR / "data").resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    port = os.environ.get("MC_PORT")
    return Config(
        data_dir=data_dir,
        frontend_dist=Path(os.environ.get("MC_FRONTEND_DIST") or PROJECT_DIR / "frontend" / "dist"),
        ffprobe_path=os.environ.get("MC_FFPROBE") or None,
        # Extra networks treated like the host itself (dev/reverse-proxy only). Empty by default.
        admin_networks=[ipaddress.ip_network(n, strict=False) for n in _split(os.environ.get("MC_ADMIN_NETWORKS", ""))],
        allowed_hosts=[h.lower() for h in _split(os.environ.get("MC_ALLOWED_HOSTS", ""))],
        bind_host=os.environ.get("MC_BIND_HOST") or None,
        port=int(port) if port else None,
        # Concurrent background FFprobe reads (keeps NAS load low). 0 turns background reading off.
        probe_workers=int(os.environ.get("MC_PROBE_WORKERS") or 2),
    )
