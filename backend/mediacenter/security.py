"""Access control.

* Requests from the host machine itself (loopback) are trusted as the administrator.
* LAN access is OFF by default. When on, remote devices must pair with the host PIN and then
  present a device token (cookie or Bearer header) on every library/streaming request.
* Public (non-private) client addresses are always refused.
"""
import hashlib
import hmac
import ipaddress
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from .db import get_setting, now_iso

COOKIE_NAME = "mc_device"
PIN_MIN, PIN_MAX = 8, 32
PBKDF2_ITERATIONS = 240_000
MAX_FAILS_PER_IP = 5
MAX_FAILS_GLOBAL = 20
LOCK_SECONDS = 15 * 60
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "[::1]"}


def hash_pin(pin: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def validate_new_pin(pin: str) -> str | None:
    if not pin.isdigit() or not (PIN_MIN <= len(pin) <= PIN_MAX):
        return f"PIN must be {PIN_MIN}-{PIN_MAX} digits."
    if len(set(pin)) == 1:
        return "PIN cannot be a single repeated digit."
    digits = [int(c) for c in pin]
    steps = {digits[i + 1] - digits[i] for i in range(len(digits) - 1)}
    if steps in ({1}, {-1}):
        return "PIN cannot be a simple ascending or descending sequence."
    return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PairingLimiter:
    """In-memory failed-attempt limiter, per client IP plus a global ceiling against distributed guessing."""

    def __init__(self):
        self._lock = threading.Lock()
        self._fails: dict[str, list[float]] = {}
        self._global: list[float] = []
        self._locked_until: dict[str, float] = {}
        self._global_locked_until = 0.0

    def _prune(self, now: float):
        self._global = [t for t in self._global if now - t < LOCK_SECONDS]
        for ip in list(self._fails):
            self._fails[ip] = [t for t in self._fails[ip] if now - t < LOCK_SECONDS]

    def locked_for(self, ip: str) -> int:
        now = time.time()
        until = max(self._locked_until.get(ip, 0), self._global_locked_until)
        return max(0, int(until - now))

    def fail(self, ip: str):
        now = time.time()
        with self._lock:
            self._prune(now)
            self._fails.setdefault(ip, []).append(now)
            self._global.append(now)
            if len(self._fails[ip]) >= MAX_FAILS_PER_IP:
                self._locked_until[ip] = now + LOCK_SECONDS
            if len(self._global) >= MAX_FAILS_GLOBAL:
                self._global_locked_until = now + LOCK_SECONDS

    def success(self, ip: str):
        with self._lock:
            self._fails.pop(ip, None)

    def attempts_left(self, ip: str) -> int:
        return max(0, MAX_FAILS_PER_IP - len(self._fails.get(ip, [])))


@dataclass
class Principal:
    role: str  # "host" | "device"
    device_id: int | None = None
    device_name: str | None = None


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _ip(addr: str):
    try:
        return ipaddress.ip_address(addr.split("%")[0])
    except ValueError:
        return None


def _request_hostname(request: Request) -> str:
    host = (request.headers.get("host") or "").lower()
    if host.startswith("["):
        return host.split("]")[0] + "]"
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def is_host_request(request: Request) -> bool:
    cfg = request.app.state.config
    ip = _ip(client_ip(request))
    if ip is None:
        return False
    trusted_ip = ip.is_loopback or any(ip in net for net in cfg.admin_networks)
    if not trusted_ip:
        return False
    # Host-header check defeats DNS-rebinding attacks from web pages open on the host PC.
    hostname = _request_hostname(request)
    return hostname in LOCAL_HOSTNAMES or hostname in cfg.allowed_hosts


def is_private_client(request: Request) -> bool:
    ip = _ip(client_ip(request))
    return ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local)


def lan_enabled(conn) -> bool:
    return get_setting(conn, "lan_enabled", "0") == "1"


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def authenticate(request: Request, conn) -> Principal | None:
    if is_host_request(request):
        return Principal(role="host")
    if not is_private_client(request) or not lan_enabled(conn):
        return None
    token = _token_from_request(request)
    if not token:
        return None
    row = conn.execute(
        "SELECT id, name, last_seen_at FROM devices WHERE token_hash = ? AND revoked = 0", (hash_token(token),)
    ).fetchone()
    if not row:
        return None
    conn.execute("UPDATE devices SET last_seen_at = ?, last_ip = ? WHERE id = ?", (now_iso(), client_ip(request), row["id"]))
    conn.commit()
    return Principal(role="device", device_id=row["id"], device_name=row["name"])


def deny_reason(request: Request, conn) -> str:
    if not is_private_client(request):
        return "Access from outside the private local network is not allowed."
    if not lan_enabled(conn):
        return "LAN access is disabled on the host. Enable it in Settings on the host PC."
    return "This device is not paired. Enter the host PIN to pair."


def require_viewer(request: Request) -> Principal:
    conn = request.state.db
    principal = authenticate(request, conn)
    if principal is None:
        raise HTTPException(status_code=401 if lan_enabled(conn) and is_private_client(request) else 403,
                            detail=deny_reason(request, conn))
    return principal


def require_host(request: Request) -> Principal:
    if not is_host_request(request):
        raise HTTPException(status_code=403, detail="This action is only available on the host PC.")
    return Principal(role="host")
