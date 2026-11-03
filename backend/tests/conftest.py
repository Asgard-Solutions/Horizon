import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mediacenter.app import create_app
from mediacenter.config import Config

HOST_HEADERS = {"X-MC-Client": "test"}


class FixedClientIP:
    """ASGI wrapper that makes requests appear to come from a given IP address."""

    def __init__(self, app, ip):
        self.app = app
        self.ip = ip

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            scope = dict(scope, client=(self.ip, 50123))
        await self.app(scope, receive, send)


def write(path: Path, data: bytes = b"\x00" * 2048) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def media_root(tmp_path) -> Path:
    root = tmp_path / "media"
    write(root / "Movies" / "Sample Movie (2024).mp4", os.urandom(50_000))
    write(root / "Movies" / "Sample Movie (2024).nfo",
          b"<?xml version='1.0'?><movie><title>Sample Movie</title><year>2024</year><plot>Plot text</plot></movie>")
    write(root / "Movies" / "Another.Film.2019.1080p.BluRay.x264.mkv")
    write(root / "Movies" / "Old Classic (1984)" / "Old Classic (1984).avi")
    write(root / "Movies" / "Old Classic (1984)" / "poster.jpg", b"\xff\xd8\xff fakejpeg")
    write(root / "Movies" / "notes.txt", b"not a video")
    write(root / "TV" / "Sample Show" / "Season 01" / "Sample Show - S01E01.mkv")
    write(root / "TV" / "Sample Show" / "Season 01" / "Sample Show - S01E02.mkv")
    write(root / "TV" / "Sample Show" / "Season 02" / "Sample Show - S02E01 - The Return.m4v")
    write(root / "TV" / "Sample Show" / "poster.jpg", b"\xff\xd8\xff fakejpeg")
    write(root / "TV" / "Sample Show" / "tvshow.nfo", b"<tvshow><title>Sample Show</title><plot>Show plot</plot></tvshow>")
    write(root / "TV" / "Flat.Show.S03E07.720p.WEB-DL.mp4")
    return root


@pytest.fixture
def app(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    cfg = Config(data_dir=data, frontend_dist=tmp_path / "no-dist", ffprobe_path="/nonexistent/ffprobe")
    application = create_app(cfg)
    return application


@pytest.fixture
def host(app):
    client = TestClient(FixedClientIP(app, "127.0.0.1"), base_url="http://localhost:8765")
    client.headers.update(HOST_HEADERS)
    return client


@pytest.fixture
def lan_client_factory(app):
    def make(ip="192.168.1.50"):
        client = TestClient(FixedClientIP(app, ip), base_url="http://192.168.1.10:8765")
        client.headers.update({"X-MC-Client": "test"})
        return client
    return make


@pytest.fixture
def library(host, media_root):
    res = host.post("/api/libraries", json={"path": str(media_root)})
    assert res.status_code == 200, res.text
    return res.json()
