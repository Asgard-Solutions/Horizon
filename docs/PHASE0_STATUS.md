# Phase 0 status report

## What works (implemented and exercised)

| Requirement | Status | How it was verified |
|---|---|---|
| Local server, no Emergent/cloud/API keys | Done | Exported zip → clean dir → fresh venv with only `requirements-dev.txt` → 105 tests pass and `run.py` serves UI + API offline-capable (no outbound calls in code; fonts bundled). |
| Add folder (browser + typed path, validation, overlap rejection) | Done | Unit tests + browser E2E. |
| Mapped drives / UNC (`Z:\`, `\\NAS\Media`) | Implemented via standard Windows file APIs | **Not tested on Windows.** |
| Recursive scan, MP4/MKV/AVI/M4V/… | Done | Unit tests on fixture tree + real sample library. |
| Movie / TV filename parsing, Seasons/Episodes, NFO, local artwork | Done | 40+ parser cases, scan-structure test, E2E. |
| SQLite catalog, rescan without duplicates, removal on rescan, unreachable folder safe | Done | Unit tests. |
| Read-only media access | Done | Test hashes all fixture files (content, size, mtime, listing) before/after scan, probe, streaming and library removal. |
| Dark 10-foot UI: Home, Movies, TV Shows, Settings, Player | Done | E2E in Chromium. |
| Keyboard navigation (arrows, Enter, Escape/Backspace) with visible focus | Done | E2E, keyboard only. |
| Gamepad API (Xbox mapping) | Implemented | **Not tested with a controller.** |
| Playback with play/pause/seek/volume/fullscreen | Done | E2E with H.264/AAC MP4 and MKV in Chromium (fullscreen request issued; visual fullscreen not verifiable headless). |
| Save/restore position, Resume / Start over, Continue watching | Done | Unit test + E2E (exit at ~41 s → resumes at ~42 s). Progress survives rescans and folder remove/re-add. |
| HTTP byte-range streaming (206, 416, HEAD, If-Range, suffix) | Done | Unit tests + live checks. |
| Unsupported formats explained, no fake playback | Done | AVI shows reasons; "Try anyway" → real media error panel. FFprobe-based codec checks + browser `canPlayType`. |
| LAN access off by default, PIN ≥ 8 digits, lockout, revoke, auth on all media endpoints | Done | Unit tests + manual LAN test through a non-loopback interface. |
| Native-client-ready API (Bearer token) | Done | Unit test. |
| Export without GitHub | Done | `scripts/export_project.py` (verified zip contents and that it runs). |

## What remains unverified

* **Windows**: the code uses only cross-platform Python APIs and was written for Windows paths, but setup/start scripts, drive-letter/UNC paths,
  Windows Firewall behaviour and `os.listdrives` were **not run on Windows**. This is the first thing to do in Phase 1.
* **Xbox**: no hardware test of any kind. See `docs/XBOX_FEASIBILITY.md` (native app blocked on unauthorized Microsoft tooling/account).
* Controller input (Gamepad API) and real TV viewing distance.
* Browser codec coverage beyond Chromium (Edge on Windows behaves like Chromium but has extra platform decoders, e.g. HEVC with the extension — untested).
* Libraries with thousands of files (scan is synchronous; expect long requests).

## Export from Emergent — limitation disclosure

`python scripts/export_project.py` produces a self-contained zip inside the workspace (`export/`). Getting that file off the Emergent
container requires an Emergent UI feature (code download or GitHub push) that is outside this project and that I cannot invoke or verify from here.
If neither is available to you, that is a platform limitation: the project itself has no dependency on Emergent and the zip is complete.

## Risks

1. **Browser-only playback** covers H.264/AAC MP4 well; MKV, HEVC, AC-3/DTS and AVI are partially or not playable → users with typical
   libraries will hit "can't play here" often until transcoding/remuxing or a native player exists.
2. **Plain HTTP on LAN** — PIN and media travel unencrypted on the home network.
3. **Xbox path** depends on Microsoft-proprietary SDKs and a developer account (free for individuals today, but proprietary and policy-dependent);
   Edge-on-Xbox codec support is undocumented.
4. **FFmpeg licensing** if ever bundled: must use an LGPL build and meet LGPL obligations; GPL builds are common and easy to ship by mistake.
5. Synchronous scanning and no filesystem watcher may not scale to very large NAS libraries; network shares that disconnect mid-scan are
   handled conservatively (nothing removed) but are slow.
6. Windows-specific behaviour (mapped drives under a different user/service account, long paths > 260 chars) untested.

## Recommended next steps for Phase 1

1. Run `setup.bat` / `start.bat` / `run_tests.bat` on a real Windows 10/11 PC with a local folder, a mapped drive and a UNC share; fix findings.
2. Xbox Edge LAN test with a Series X|S (plan in the feasibility report, no tooling needed).
3. Decide the playback strategy: on-the-fly remux (MKV→fMP4, copy codecs) via an LGPL FFmpeg build, and/or a native client with `MediaPlayerElement`.
4. Background scanning with progress, plus a periodic/explicit rescan of changed folders.
5. Optional HTTPS on LAN (self-signed with pinning, or a local CA) and a QR-code pairing flow for TVs.
6. If native Xbox is approved: obtain authorization for Visual Studio + Windows SDK + Partner Center, then prototype a UWP shell reusing `docs/API.md`.
7. Packaging for Windows (embedded Python or a single-folder build) with a license-notice bundle.
