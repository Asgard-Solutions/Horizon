# Security review — Phase 0.5

Scope: PIN authentication, LAN exposure, file-path restrictions, streaming/artwork endpoints, host-only administration.
Method: code review of `backend/mediacenter/*` plus automated tests (cited) that exercise each control. Reviewed in the Linux dev
environment; **Windows-specific behaviour (ACLs, SMB, junctions on NTFS, Windows Firewall) was not executed on Windows.**

## Threat model

* **Host user** (person at the PC) — trusted administrator.
* **LAN device** (Xbox browser, phone) — trusted only after pairing with the PIN; may view and stream catalogued media, nothing else.
* **Other LAN hosts / malware on the LAN** — untrusted; may try to guess the PIN, read arbitrary files, or change settings.
* **Malicious web page opened on the host PC or a paired device** — untrusted (CSRF, DNS rebinding).
* **Internet** — must never reach the service. The app never opens router ports (no UPnP), and refuses public client IPs.

## Findings and controls

| # | Area | Control | Evidence |
|---|---|---|---|
| 1 | Exposure | Server binds `127.0.0.1` unless LAN is enabled in Settings (then `0.0.0.0` after restart). LAN can't be enabled without a PIN. | `run.py`; manual check in `docs/TEST_RESULTS.md`; `test_lan_cannot_be_enabled_without_pin` |
| 2 | Exposure | Requests from non-private addresses are refused even when LAN is on (incl. IPv4-mapped IPv6 like `::ffff:8.8.8.8`). | `test_public_ip_always_refused`, `test_ipv4_mapped_public_address_is_not_private` |
| 3 | Host identity | "Host" = loopback client **and** `Host` header `localhost/127.0.0.1/[::1]`. A LAN client that sends `Host: localhost` is still a LAN client. | `test_host_admin_requires_loopback_even_with_local_host_header`, `test_dns_rebinding_host_header_is_not_trusted` |
| 4 | Admin | Library add/remove/scan, folder browser, settings, PIN, device list are **host-only** (403 for every device). | `test_pairing_flow_and_device_access` (8 admin endpoints) |
| 5 | PIN | 8–32 digits, rejects repeated/sequential; stored as PBKDF2-SHA256 (240k iterations, random salt); constant-time compare. | `test_pin_rules`, `test_pin_is_not_stored_in_plain_text` |
| 6 | Brute force | 5 failures per IP → 15 min lock; ≥ 20 failures from all IPs in 15 min → global pairing lock. 8 digits + global limit ⇒ ~100 M combinations at ≤ 80/h. | `test_wrong_pin_lockout` |
| 7 | Sessions | Random 256-bit device token; only its SHA-256 is stored; HttpOnly + SameSite=Strict cookie or Bearer header; revocable; PIN change revokes all; disabling LAN blocks all. | `test_revoke_and_pin_change_invalidate_devices`, `test_disabling_lan_blocks_paired_devices`, `test_bearer_token_for_native_clients` |
| 8 | CSRF | Every POST/PUT/PATCH/DELETE needs header `X-MC-Client` (cross-site forms/`fetch` without CORS can't add it; no CORS headers are sent). | `test_state_changes_require_client_header` |
| 9 | Path restriction | Clients never send file paths for media. They send numeric IDs; the server re-resolves the stored path with `realpath` and serves it only if inside a configured library root (case-insensitive, drive- and UNC-aware). | `test_stream_outside_library_is_forbidden`, `test_path_traversal_inside_db_is_forbidden`, `test_is_within_windows` (ntpath) |
| 10 | Links | Scanner never descends into symlinked folders or NTFS junctions; file links resolving outside the library are skipped and reported; streaming re-checks `realpath`. | `test_symlink_escape_is_forbidden`, `test_scanner_skips_linked_folders_and_outside_file_links`, `test_windows_reparse_point_classification` (simulated) |
| 11 | Artwork | Same root check; only `.jpg/.jpeg/.png/.webp` served. | `test_artwork_outside_library_is_forbidden`, `test_artwork_must_be_an_image` |
| 12 | Static UI | SPA route resolves inside `frontend/dist` only; traversal variants (`..`, `%2e%2e`, `%2f`, backslash) can't escape. UI files contain no data. | `test_spa_route_cannot_escape_dist` |
| 13 | Streaming | Single-range parser with strict regex; 416 for unsatisfiable; files opened read-only (`rb`); file must still match the catalogued path key. | `tests/test_streaming.py` |
| 14 | Read-only | No write/rename/delete call targets library folders anywhere in the code; verified by hashing fixtures. | `test_scanning_never_modifies_source_files`; `grep` of the code base |
| 15 | MIME/nosniff | `X-Content-Type-Options: nosniff`; MIME types pinned so a broken Windows registry can't break or mislabel content. | `test_static_ui_has_correct_mime_types_even_with_bad_registry` |
| 17 | Port hijacking | `run.py` binds its own socket; on Windows with `SO_EXCLUSIVEADDRUSE` so another local program can't bind the same port and intercept connections. | `run.py` (Windows path not executed here) |
| 16 | Folder browser | Host-only; lists directories only (no file names except a video count); hidden/system folders skipped. | `test_pairing_flow_and_device_access` |

## Residual risks (accepted for Phase 0.5, to revisit)

1. **No TLS.** PIN (during pairing), tokens and video travel as plain HTTP on the LAN. Anyone who can sniff the LAN (e.g. open Wi-Fi) can steal a token. Mitigation: use only on trusted home networks; Phase 1 candidate: local HTTPS.
2. **Pairing limiter is in memory** — it resets when the server restarts (an attacker cannot restart it, but a reboot resets counters).
3. **Host = anything on loopback.** Other local user accounts or malware on the same PC are treated as the administrator.
4. `/api/docs` (OpenAPI description) and the UI shell are readable without pairing — they contain no media or settings data.
5. **CGNAT / VPN ranges** such as `100.64.0.0/10` (Tailscale) are treated as non-private and refused.
6. The UDP "connect" used to discover the PC's LAN address sends no packets but is still a socket call (it is blocked harmlessly in the offline test).
7. Windows ACL edge cases (folders readable by the user but not listable, EFS-encrypted files, OneDrive placeholders that download on access) are **untested**. Note: reading a OneDrive "online-only" file during scan/streaming would make OneDrive download it — the scanner only `stat`s files, and FFprobe/streaming read files only when you play them.
8. Development-only variables `MC_ADMIN_NETWORKS` / `MC_ALLOWED_HOSTS` widen "host" trust. They are empty by default, not in the release zip's config, and must stay empty on a real installation. `run.py --check` prints a WARN when they are set.
