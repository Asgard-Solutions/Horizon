# Phase 0.5 status — Windows compatibility, portability and deployment

**No test in this phase was executed on Windows or Xbox.** All execution happened in the Linux development container.
Items marked *verified* below were verified there; Windows behaviour is either *simulated* (Windows path semantics via `ntpath`,
mocked Win32 stat data) or *unverified*.

## Delivered

| Item | Where |
|---|---|
| Complete release ZIP (source, prebuilt UI, offline Python wheels, scripts, docs, tests; no secrets/caches/DB) | `export/open-media-center-phase0.5-*.zip` (+ `.sha256.txt`), built by `python scripts/export_project.py` |
| One-click Windows install/start/test | `Setup.bat`, `Start.bat`, `RunTests.bat` (wrappers for `scripts/windows/*`) |
| Startup checks + SQLite initialisation | `python backend/run.py --check` (Python version, pinned packages, data folder writable, DB init + `PRAGMA quick_check`, UI build, FFprobe, port free, LAN mode, dev-only env warning) |
| Offline installation | `vendor/wheels` — all 26 wheels for CPython 3.11–3.14 win_amd64; `requirements*.txt` now pin every transitive package |
| Windows testing guide + firewall troubleshooting | `docs/WINDOWS_TESTING.md` |
| Windows acceptance checklist | `docs/WINDOWS_ACCEPTANCE_CHECKLIST.md` |
| Security review | `docs/SECURITY_REVIEW.md` |
| License verification incl. transitive deps | `scripts/license_inventory.py` → `docs/licenses/INVENTORY.md` (0 problems in shipped deps) |
| Test results | `docs/TEST_RESULTS.md` |

## Windows compatibility changes made in this phase

1. **Path input** (`paths.py`): accepts `D:`, `D:/x`, quoted paths, `\\server\share\...`, `\\?\` long paths; rejects relative, drive-relative (`C:x`),
   root-relative (`\x`) and server-only (`\\NAS`) paths with clear messages. Folder-browser "up" stops at drive and share roots.
2. **Containment checks** are case-insensitive and drive/UNC-aware; a UNC share root no longer fails comparison (bug found by the new tests and fixed).
3. **Drive list via Win32** (`winfs.py`, ctypes): drive letters with type (fixed/removable/network/optical) and mapped-drive targets (`Z:\ -> \\NAS\Media`); falls back to `os.listdrives`/letter probing.
4. **Junctions/symlinks**: the scanner no longer descends into symlinked folders or NTFS junctions (Python 3.11's `os.walk` would follow junctions on Windows); file links pointing outside the library are skipped and reported. OneDrive/cloud placeholders are *not* treated as links.
5. **MIME types pinned**: Windows' registry often maps `.js` to `text/plain`, which (with `nosniff`) would make the UI blank on some PCs.
6. **Exclusive port binding** on Windows (`SO_EXCLUSIVEADDRUSE`) and a clear "port in use" message.
7. **Clear errors** for unreachable shares/mapped drives (elevation/service caveat) and "Access denied" for ACL problems.
8. **FFprobe** launched without console windows, UTF-8 output decoding, no stdin.
9. **IPv4-mapped IPv6** client addresses judged by their IPv4 address.
10. Scripts are ASCII + CRLF; `.gitattributes` keeps them CRLF.

## Verification status

| Area | Status |
|---|---|
| Backend suite (158 tests) on Linux; fresh venv from pinned requirements; from extracted ZIP | **Verified (Linux)** |
| Windows path rules, UNC/drive containment, reparse-point classification | **Simulated** (`ntpath`, mocked `lstat`) — not a Windows run |
| Offline runtime (no outbound connections) | **Verified (Linux)** with a socket/DNS guard; no network-namespace test possible |
| Offline wheel resolution for win_amd64 (3.11–3.14) | **Verified** with `pip --dry-run --platform win_amd64` (resolution only, not installation) |
| UI regression incl. folder browser, confirm dialog, resume after remove/re-add, ZIP download | **Verified (Linux, Chromium)** by QA agent — iteration 2: 100% |
| `Setup.bat` / `Start.bat` / `RunTests.bat` / `setup.ps1` execution | **Unverified** |
| Win32 drive enumeration, mapped-drive targets, UNC/SMB, ACL denial, junction pruning on NTFS, long paths | **Unverified** |
| Windows Firewall prompt/rules, LAN pairing from another device to a Windows host | **Unverified** |
| Edge/Chrome/Firefox on Windows, HEVC extension, controller input | **Unverified** |
| Xbox (browser or native) | **Not attempted** (out of scope for 0.5) |

## License findings

No GPL/LGPL/unknown license in anything shipped (Python runtime wheels, UI bundle, fonts). Weak-copyleft MPL-2.0 appears only in
build/test tools that are not shipped (`lightningcss`, `certifi`). Python itself (PSF) is installed by the user, not bundled.
FFprobe is optional and not bundled; if you bundle it later use an LGPL build and follow `docs/THIRD_PARTY_LICENSES.md`.

## Before authorising Phase 1

1. Run `docs/WINDOWS_ACCEPTANCE_CHECKLIST.md` on at least one Windows 11 and one Windows 10 PC, including a NAS share and a mapped drive.
2. Send back `test-results-windows.xml` and the `Start.bat` output; any Windows-only failure gets fixed before Phase 1.
3. Decide whether the plain-HTTP LAN risk is acceptable for your home network (see security review, residual risk 1).
