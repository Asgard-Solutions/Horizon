"""Host-only SMB setup. Connection metadata is separate from the media library and OS credential vault."""
import hashlib
import http.client
import json
import ntpath
import socket
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from starlette.concurrency import run_in_threadpool

from . import network_shares as smb
from .db import get_setting, set_setting
from .routes_admin import lan_addresses
from .security import require_host

router = APIRouter(prefix="/api/network", dependencies=[Depends(require_host)])
LOCATION_FIELDS = ("id", "server", "share", "folder", "share_path", "path", "username")


class ConnectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    server: str = Field(min_length=1, max_length=253)
    share: str = Field(min_length=1, max_length=80)
    folder: str = Field(default="", max_length=1024)
    account: Literal["windows", "custom", "saved"] = "windows"
    username: str | None = Field(default=None, max_length=256)
    password: SecretStr | None = Field(default=None, max_length=512)
    remember: bool = False


class ShareIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    server: str = Field(min_length=1, max_length=253)
    share: str = Field(min_length=1, max_length=80)


async def _body(request, model):
    raw = await request.body()
    if len(raw) > 8192:
        raise HTTPException(413, "Connection details are too long.")
    try:
        return model.model_validate(json.loads(raw))
    except (ValueError, TypeError, ValidationError):
        # FastAPI's default validation details may echo input. Never echo credential input.
        raise HTTPException(422, "Check the server, share, account and connection details.") from None


def _location_id(path):
    return hashlib.sha256(ntpath.normcase(ntpath.normpath(path)).encode("utf-8")).hexdigest()


def _locations(conn):
    try:
        values = json.loads(get_setting(conn, "network_locations", "[]"))
        unique = {}
        for row in values[:64]:
            if not isinstance(row, dict) or not all(isinstance(row.get(k), str) for k in ("server", "share", "path")):
                continue
            clean = {k: row.get(k) for k in LOCATION_FIELDS}
            clean["id"] = _location_id(clean["path"])
            unique.setdefault(clean["id"], clean)
        return list(unique.values())
    except (TypeError, ValueError):
        return []


def _save_location(conn, result):
    clean = {key: result.get(key) for key in LOCATION_FIELDS if key != "id"}
    clean["id"] = _location_id(result["path"])
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        current = [row for row in _locations(conn) if row["id"] != clean["id"]]
        if len(current) >= 64:
            raise HTTPException(409, "The connection succeeded, but the saved location list is full (64). Existing locations were kept.")
        set_setting(conn, "network_locations", json.dumps([clean] + current))
    return clean


def _addresses():
    return lan_addresses()[:16]


def _can_reach(address, port, instance_id):
    connection = http.client.HTTPConnection(address, port, timeout=.4)
    try:
        connection.request("GET", "/api/health", headers={"X-Horizon-Instance": instance_id})
        response = connection.getresponse()
        content = response.read(2049)
        data = json.loads(content) if response.status == 200 and len(content) <= 2048 else None
        return isinstance(data, dict) and data.get("ok") is True and data.get("instance_matches") is True
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


@router.get("")
def network_status(request: Request):
    cfg = request.app.state.config
    port = cfg.port or request.url.port or 80
    local_only = cfg.bind_host in ("127.0.0.1", "localhost", "::1", "[::1]")
    addresses = [{"url": f"http://{address}:{port}", "reachable": not local_only and _can_reach(address, port, request.app.state.instance_id)} for address in _addresses()]
    locations = _locations(request.state.db)
    signins = {}
    for row in locations:
        target = (row["server"].casefold(), row["share"].casefold())
        if target not in signins:
            try:
                signins[target] = smb.credential_saved(row["server"], row["share"])
            except smb.ShareError:
                signins[target] = False
        row["credential_saved"] = signins[target]
    return {"hostname": socket.gethostname(), "capabilities": smb.capabilities(), "connections": locations,
            "listener": {"bind_host": cfg.bind_host, "port": port, "lan_reachable": any(a["reachable"] for a in addresses)},
            "addresses": addresses}


@router.post("/shares/connect")
async def connect_share(request: Request):
    body = await _body(request, ConnectionIn)
    if body.account == "custom":
        if not body.username or not body.username.strip() or body.password is None:
            raise HTTPException(422, "Enter the share username and password, or choose Windows sign-in.")
    elif body.username is not None or body.password is not None or body.remember:
        raise HTTPException(422, "Only a new share sign-in can include credentials or Remember sign-in.")
    secret = body.password.get_secret_value() if body.password is not None else None
    try:
        result = await run_in_threadpool(smb.connect_share, server=body.server, share=body.share, folder=body.folder,
                                        username=body.username.strip() if body.username else None, password=secret,
                                        remember=body.remember, use_saved=body.account == "saved")
        location = await run_in_threadpool(_save_location, request.state.db, result)
        return {**location, "credential_saved": result["credential_saved"], "accessible": result["accessible"]}
    except smb.ShareError as exc:
        detail = str(exc)
        if secret:
            detail = detail.replace(secret, "[redacted]")
        raise HTTPException(exc.status_code, detail) from None
    except OSError:
        raise HTTPException(503, "The share connection could not complete. Check the server and permissions, then retry.") from None


@router.post("/shares/forget")
async def forget_share(request: Request):
    body = await _body(request, ShareIn)
    try:
        await run_in_threadpool(smb.forget_credentials, body.server, body.share)
    except smb.ShareError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    return {"ok": True, "message": "Saved sign-in forgotten. Existing Windows connections and library sources are unchanged."}
