import pytest

from mediacenter.streaming import RangeNotSatisfiable, parse_range


@pytest.mark.parametrize("header,size,expected", [
    (None, 100, None),
    ("bytes=0-9", 100, (0, 9)),
    ("bytes=10-", 100, (10, 99)),
    ("bytes=-10", 100, (90, 99)),
    ("bytes=-500", 100, (0, 99)),
    ("bytes=90-500", 100, (90, 99)),
    ("bytes=5-5", 100, (5, 5)),
    ("bytes=0-1, 5-6", 100, (0, 1)),
    ("items=0-9", 100, None),
    ("bytes=abc", 100, None),
    ("bytes=-", 100, None),
])
def test_parse_range(header, size, expected):
    assert parse_range(header, size) == expected


@pytest.mark.parametrize("header,size", [("bytes=100-", 100), ("bytes=50-10", 100), ("bytes=-0", 100), ("bytes=0-", 0)])
def test_parse_range_unsatisfiable(header, size):
    with pytest.raises(RangeNotSatisfiable):
        parse_range(header, size)


@pytest.fixture
def movie(host, library, media_root):
    m = next(m for m in host.get("/api/movies").json() if m["title"] == "Sample Movie")
    return m, (media_root / "Movies" / "Sample Movie (2024).mp4").read_bytes()


def test_full_response(host, movie):
    m, data = movie
    r = host.get(f"/api/stream/{m['file_id']}")
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert int(r.headers["content-length"]) == len(data)
    assert r.headers["content-type"] == "video/mp4"
    assert r.content == data


def test_partial_responses(host, movie):
    m, data = movie
    url = f"/api/stream/{m['file_id']}"
    r = host.get(url, headers={"Range": "bytes=100-199"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 100-199/{len(data)}"
    assert r.headers["content-length"] == "100"
    assert r.content == data[100:200]

    r = host.get(url, headers={"Range": "bytes=-256"})
    assert r.status_code == 206 and r.content == data[-256:]

    r = host.get(url, headers={"Range": f"bytes={len(data) - 10}-"})
    assert r.status_code == 206 and r.content == data[-10:]

    # Spans multiple 1 MB chunks is not needed for correctness, but a large middle slice must be exact.
    r = host.get(url, headers={"Range": "bytes=1000-40999"})
    assert r.content == data[1000:41000]


def test_unsatisfiable_range(host, movie):
    m, data = movie
    r = host.get(f"/api/stream/{m['file_id']}", headers={"Range": f"bytes={len(data)}-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(data)}"


def test_head_request(host, movie):
    m, data = movie
    r = host.head(f"/api/stream/{m['file_id']}", headers={"Range": "bytes=0-1023"})
    assert r.status_code == 206
    assert r.headers["content-length"] == "1024"
    assert r.content == b""


def test_if_range_mismatch_returns_full_file(host, movie):
    m, data = movie
    url = f"/api/stream/{m['file_id']}"
    etag = host.head(url).headers["etag"]
    assert host.get(url, headers={"Range": "bytes=0-9", "If-Range": etag}).status_code == 206
    r = host.get(url, headers={"Range": "bytes=0-9", "If-Range": '"stale"'})
    assert r.status_code == 200 and len(r.content) == len(data)


def test_missing_file_returns_404(host, movie, media_root):
    m, _ = movie
    (media_root / "Movies" / "Sample Movie (2024).mp4").unlink()
    assert host.get(f"/api/stream/{m['file_id']}").status_code == 404


def test_unknown_file_id(host, library):
    assert host.get("/api/stream/99999").status_code == 404
