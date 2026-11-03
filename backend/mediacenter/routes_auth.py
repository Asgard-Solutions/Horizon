"""Device pairing for LAN clients."""
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .db import get_setting, now_iso
from .security import (COOKIE_NAME, PairingLimiter, authenticate, client_ip, deny_reason, hash_token,
                       is_host_request, is_private_client, lan_enabled, verify_pin)

router = APIRouter(prefix="/api/auth")
limiter = PairingLimiter()


@router.get("/status")
def auth_status(request: Request):
    conn = request.state.db
    principal = authenticate(request, conn)
    ip = client_ip(request)
    return {
        "role": principal.role if principal else "none",
        "device_name": principal.device_name if principal else None,
        "lan_enabled": lan_enabled(conn),
        "pin_configured": bool(get_setting(conn, "pin_hash")),
        "locked_seconds": limiter.locked_for(ip),
        "message": None if principal else deny_reason(request, conn),
    }


class PairIn(BaseModel):
    pin: str = Field(max_length=64)
    device_name: str = Field(default="LAN device", max_length=60)


@router.post("/pair")
def pair(body: PairIn, request: Request, response: Response):
    conn = request.state.db
    ip = client_ip(request)
    if is_host_request(request):
        raise HTTPException(status_code=400, detail="The host PC does not need pairing.")
    if not is_private_client(request) or not lan_enabled(conn):
        raise HTTPException(status_code=403, detail=deny_reason(request, conn))
    locked = limiter.locked_for(ip)
    if locked:
        raise HTTPException(status_code=429, detail=f"Too many wrong PINs. Try again in {locked // 60 + 1} min.",
                            headers={"Retry-After": str(locked)})
    if not verify_pin(body.pin.strip(), get_setting(conn, "pin_hash")):
        limiter.fail(ip)
        left = limiter.attempts_left(ip)
        raise HTTPException(status_code=401, detail=f"Wrong PIN. {left} attempt(s) left before a 15 minute lock.")
    limiter.success(ip)
    token = secrets.token_urlsafe(32)
    name = body.device_name.strip() or "LAN device"
    conn.execute("INSERT INTO devices (name, token_hash, created_at, last_seen_at, last_ip) VALUES (?,?,?,?,?)",
                 (name, hash_token(token), now_iso(), now_iso(), ip))
    conn.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=60 * 60 * 24 * 365, httponly=True, samesite="strict")
    # The token is also returned so a future native client can send it as "Authorization: Bearer <token>".
    return {"ok": True, "device_name": name, "token": token}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        request.state.db.execute("UPDATE devices SET revoked = 1 WHERE token_hash = ?", (hash_token(token),))
        request.state.db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
