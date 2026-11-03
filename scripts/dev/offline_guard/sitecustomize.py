"""Dev-only: make every outbound TCP/UDP connection to a non-loopback address fail and log it.
Usage: PYTHONPATH=scripts/dev/offline_guard python backend/run.py   (simulates 'no internet' for the server process)"""
import ipaddress
import socket
import sys

_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _blocked(addr):
    try:
        return not ipaddress.ip_address(addr[0]).is_loopback
    except (ValueError, TypeError, IndexError):
        return True  # hostnames would need DNS -> treat as outbound


def _guard(self, addr):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _blocked(addr):
        print(f"[offline-guard] BLOCKED outbound connect to {addr} ({'udp' if self.type == socket.SOCK_DGRAM else 'tcp'})",
              file=sys.stderr, flush=True)
        raise OSError(101, "Network is unreachable (offline guard)")
    return _orig_connect(self, addr)


def _guard_ex(self, addr):
    try:
        _guard(self, addr)
        return 0
    except OSError as exc:
        return exc.errno


socket.socket.connect = _guard
socket.socket.connect_ex = _guard_ex
_orig_getaddrinfo = socket.getaddrinfo


def _gai(host, *a, **k):
    if host not in (None, "localhost", "127.0.0.1", "::1", "0.0.0.0", socket.gethostname()):
        print(f"[offline-guard] BLOCKED DNS lookup {host}", file=sys.stderr, flush=True)
        raise socket.gaierror(-3, "offline guard")
    return _orig_getaddrinfo(host, *a, **k)


socket.getaddrinfo = _gai
print("[offline-guard] active: non-loopback network access disabled", file=sys.stderr, flush=True)
