"""HTTP byte-range streaming (RFC 9110 single-range subset)."""
import os
import re
from email.utils import formatdate

from fastapi import HTTPException, Request
from fastapi.responses import Response, StreamingResponse

CHUNK = 1024 * 1024
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


class RangeNotSatisfiable(Exception):
    pass


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Return inclusive (start, end) or None for a full response. Raises RangeNotSatisfiable."""
    if not header:
        return None
    first = header.split(",")[0].strip()
    m = _RANGE.match(first)
    if not m or (m.group(1) == "" and m.group(2) == ""):
        return None  # malformed Range headers are ignored per RFC 9110
    start_s, end_s = m.groups()
    if size == 0:
        raise RangeNotSatisfiable()
    if start_s == "":
        length = int(end_s)
        if length == 0:
            raise RangeNotSatisfiable()
        return max(0, size - length), size - 1
    start = int(start_s)
    end = int(end_s) if end_s else size - 1
    if start >= size or end < start:
        raise RangeNotSatisfiable()
    return start, min(end, size - 1)


def _iter_file(path: str, start: int, length: int):
    with open(path, "rb") as fh:
        fh.seek(start)
        remaining = length
        while remaining > 0:
            data = fh.read(min(CHUNK, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


def stream_file(request: Request, path: str, media_type: str) -> Response:
    try:
        st = os.stat(path)
    except OSError:
        raise HTTPException(status_code=404, detail="File is no longer available on disk.")
    size = st.st_size
    etag = f'"{st.st_mtime_ns:x}-{size:x}"'
    headers = {
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Last-Modified": formatdate(st.st_mtime, usegmt=True),
        "Cache-Control": "private, max-age=0",
    }
    range_header = request.headers.get("range")
    if_range = request.headers.get("if-range")
    if if_range and if_range != etag:
        range_header = None
    try:
        rng = parse_range(range_header, size)
    except RangeNotSatisfiable:
        return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{size}"})

    if rng is None:
        start, end, status = 0, size - 1, 200
    else:
        start, end = rng
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    length = max(0, end - start + 1)
    headers["Content-Length"] = str(length)
    if request.method == "HEAD":
        return Response(status_code=status, headers=headers, media_type=media_type)
    return StreamingResponse(_iter_file(path, start, length), status_code=status, headers=headers, media_type=media_type)
