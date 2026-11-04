# REELHEIM Media Center

**Home design locked — November 4, 2026.** The approved REELHEIM logo, aurora fjord backdrop, Movies/TV artwork and gold icons, card typography and full gold selection glow are the current visual baseline. Preserve this Home design unless the user explicitly requests a change. See [Home approval](docs/HOME_INTEGRATION.md#approved-reelheim-home-lock--november-4-2026).

The current Home interface uses the two-stage Movies / TV Shows → Atlas / Discover / Search flow, with real selected-type Continue Watching and globally reachable Settings, with source management inside Settings. See [Home integration and verification](docs/HOME_INTEGRATION.md) for the actual changes, test results and remaining runtime checks. The technical Phase 0 notes below describe the existing media host that the interface preserves.

A self-hosted media center for **personal Movies and TV Shows**, runs entirely on your own Windows PC and home network.
Scanning and playback use local media, NFO files and artwork without accounts or online metadata services. Video/artwork files are read-only to the app; explicit NFO editor saves back up and update only the selected NFO.

Phase 0 proves the smallest end-to-end path: pick a folder → scan → browse → play (with seek and resume),
plus optional, PIN-protected LAN access so another device (e.g. the Xbox browser) can be tried.

> Status, what was actually tested and what is still unverified: see [`docs/PHASE0_STATUS.md`](docs/PHASE0_STATUS.md).

## Architecture

```
 Browser UI (React + TypeScript, built by Vite) ── same origin ──►  Python server (FastAPI + Uvicorn)
   Home · Movies · TV Shows · Settings · Player                        ├─ /api/...  catalog, playback info, progress
   keyboard / D-pad / Gamepad API navigation                           ├─ /api/stream/{id}  HTTP byte-range streaming
                                                                       ├─ SQLite catalog (data/mediacenter.sqlite3)
                                                                       └─ read-only scanner (+ optional FFprobe)
```

* `backend/mediacenter/` — server package (`parser.py` filename rules, `scanner.py`, `streaming.py`, `security.py`, `probe.py`, routes).
* `frontend/` — web UI. `yarn build` produces `frontend/dist`, which the Python server serves at `/`.
* The JSON API is client-agnostic (cookie **or** `Authorization: Bearer` token), so a future native Xbox/UWP client can reuse it. See [`docs/API.md`](docs/API.md).

## Windows installation (quick start)

Requirements: Windows 10/11 x64 and **Python 3.11–3.13** from python.org ("Add python.exe to PATH"). Nothing else.
The release zip already contains every Python package as wheels (`vendor/wheels`) and the built UI (`frontend/dist`),
so **installation and use work without internet**. Node.js is only needed to rebuild the UI.

1. Extract the zip to a folder you own (e.g. `C:\OpenMediaCenter`).
2. Double-click **`Setup.bat`** – creates `backend\.venv`, installs the bundled wheels offline, runs the startup checks.
3. Double-click **`Start.bat`** – checks dependencies, initialises/verifies the SQLite database, starts the server, opens `http://127.0.0.1:8765`.
4. Optional: **`RunTests.bat`** – runs the automated test suite and writes `test-results-windows.xml`.

Detailed Windows test procedure, NAS/mapped-drive notes and firewall troubleshooting: [`docs/WINDOWS_TESTING.md`](docs/WINDOWS_TESTING.md).
Acceptance checklist: [`docs/WINDOWS_ACCEPTANCE_CHECKLIST.md`](docs/WINDOWS_ACCEPTANCE_CHECKLIST.md). Security review: [`docs/SECURITY_REVIEW.md`](docs/SECURITY_REVIEW.md).

Manual equivalent (PowerShell):

```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\python -m pip install --no-index --find-links ..\vendor\wheels -r requirements-dev.txt
.venv\Scripts\python run.py --check
.venv\Scripts\python run.py --open-browser
```

Data is stored in `data\` next to the project (change with `MC_DATA_DIR`, see `backend/.env.example`).

### Development mode (hot reload)

```powershell
backend\.venv\Scripts\python backend\run.py --port 8765      # API server
cd frontend; yarn dev                                         # UI on http://localhost:3000, proxies /api to :8765
```

## Adding media folders

Settings → **Library folders**:

* **Browse** — walks the drives/folders of the host PC (host-only; remote devices can never browse host files).
* **Type a path** — e.g. `D:\Movies`, a mapped drive `Z:\Video`, or a UNC share `\\NAS\Media`.
  The server must run under a Windows user that can already open that share in Explorer; credentials are handled by Windows, not by this app.
  Mapped drive letters are per-user — if the server runs as a different user, use the UNC path.
* Folders that overlap an existing library folder are rejected (prevents duplicates).

### Scanning rules

* Recursive scan; video extensions: `mp4 m4v mkv avi mov webm wmv flv mpg mpeg ts m2ts mts vob divx ogv 3gp`.
* **TV episode** if the filename contains `S01E02` (also `s1e2`, `S01E01-E02`, `1x02`). Show name comes from the
  show folder when the file is inside `Season N`/`S01`, otherwise from the filename. `Show (2019)` → year 2019.
* Otherwise a **movie**: `Title (2024).ext`, `Title.2024.1080p...ext`; if the filename has no year, the parent folder is used.
* Local metadata: `movie.nfo` / `<file>.nfo`, `tvshow.nfo`, episode `<file>.nfo` (Kodi-style XML: title/year/plot).
* Local artwork: `<file>-poster.jpg`, `poster.jpg`/`folder.jpg` (only in a folder dedicated to one movie or the show folder),
  `fanart.jpg`, `seasonNN-poster.jpg`, `<file>-thumb.jpg`. jpg/png/webp.
* Rescan = upsert by normalized absolute path: no duplicates, IDs and watch progress are kept, deleted files are removed from the catalog.
  If a folder is unreachable (e.g. NAS offline) **nothing** is removed.
* **Read-only guarantee:** the scanner only lists, stats and opens files for reading. Removing a library folder only removes catalog rows.
  This is covered by an automated test that hashes every fixture file before/after scan, playback-info, streaming and removal.

## Playback

* Files are streamed with HTTP byte-range requests (`206 Partial Content`), so the browser can seek.
* Player: play/pause, seek bar, ±10/30 s, volume, mute, fullscreen, next episode. Position is saved every 10 s, on pause and on exit;
  reopening offers **Resume** or **Start over**. ≥ 92 % watched → marked watched.
* **No transcoding in Phase 0.** Before playing, the server gives a verdict from the container and (if FFprobe is available) the codecs;
  the browser then double-checks with `canPlayType()` and real media events. Playback is only shown as running after the `playing` event.
  Unsupported files (e.g. AVI, MPEG-4 Part 2, 10-bit H.264) show an explanation instead of a fake player. MKV is "may not play" — it depends on the browser.

### Local subtitle files

Put `.srt` or `.vtt` files in the same folder as the matching video. Examples: `Movie.mp4` with `Movie.srt` or `Movie.en.srt`; `Show.S01E01.mkv` with `Show.S01E01.eng.forced.srt`. Filenames are matched case-insensitively; another episode's subtitles are not offered. No rescan is needed.

Settings → Playback → Local subtitle files selects **Off by default** or **Automatic**. Automatic prefers this browser's language. During playback, open the controls (Up on the keyboard/controller) and choose **Subtitles** to select a real track or Off. Escape/B closes the menu. Original files are never changed; SRT is converted to WebVTT in memory.

This supports local text sidecars only, not embedded subtitle extraction, ASS/SSA or image subtitles. Limits and verified behavior are recorded in [HOME_INTEGRATION.md](docs/HOME_INTEGRATION.md#local-subtitles--november-4-2026).

### FFprobe (optional, recommended)

FFprobe is used as an **external program** (never linked or bundled by this repo). Put `ffprobe.exe` on PATH, in `tools\ffprobe.exe`,
or set `MC_FFPROBE`. Video lengths are read in the background after each scan (read-only, cached in SQLite, resumes after a restart);
`MC_PROBE_WORKERS` (default 2, `0` = off) limits how many files are read at once to keep NAS load low. Use an **LGPL** build of FFmpeg if you plan to redistribute it (see `docs/THIRD_PARTY_LICENSES.md`).
Without FFprobe everything still works; codec compatibility is just reported as "not checked".

## Collections, appearance and accessibility

Settings → Collections & folders provides independent **NFO collections** and **Folder groups** switches. Both default On. NFO sets take priority when enabled; switching either option only regroups the catalog, without changing NFO files, media or watch history.

REELHEIM uses its standard cinematic appearance. Settings → Appearance & 4K scaling controls interface size. Motion & accessibility offers reduced motion and opt-in **Additional screen reader announcements**, with a test button. These preferences are saved on the current device. Announcements use the running screen reader through ARIA live regions; REELHEIM does not synthesize speech itself. Existing labels, focus and error/status messages remain available with extra announcements Off. Retired Light/Dark and High Contrast preferences are ignored.

## Keyboard / controller

| Input | Action |
|---|---|
| Arrow keys / D-pad / left stick | Move focus (spatial navigation) |
| Enter / Space / A | Activate |
| Escape / Backspace / B | Back |
| Player: ←/→ on the seek bar (or when controls are hidden) | Seek −10 s / +10 s |
| Player: ←/→ on volume | Volume −/+ 10 % |
| Player: F / M / K or Space | Fullscreen / mute / play-pause |

Gamepad input uses the standard W3C Gamepad API (Xbox mapping). It was tested with keyboard only; see the Xbox report for what is unverified.

## LAN access (off by default)

1. Settings → Network & devices → set a numeric **PIN (8–32 digits**, no repeated/sequential digits; stored as PBKDF2-SHA256).
2. **Turn on LAN access**, then restart `start.bat`. The server binds to `127.0.0.1` when LAN is off and to `0.0.0.0` only when on.
3. On the other device open one of the listed addresses (e.g. `http://192.168.1.20:8765`), enter the PIN on the on-screen keypad.
4. Windows Firewall will ask about `python.exe` — allow **Private networks only**.

The page distinguishes saved device-access policy from an actual REELHEIM listener. **Refresh connection status** checks this REELHEIM instance; a loopback-only preview is not presented as ready for other devices. The check runs from the host and cannot establish that another device's firewall or Wi-Fi isolation permits access.

### NAS / SMB shared folders

On the Windows host, Settings → Network & devices → **Connect to a NAS or shared folder** accepts a server name or private IPv4 address, share name and optional subfolder. Choose the current Windows sign-in, another account, or a sign-in previously saved by REELHEIM, then **Connect & test folder**. No drive letter is mapped and pre-existing Windows sessions are never disconnected automatically.

Remember is optional and defaults Off. Remembered secrets use a REELHEIM-specific Windows Credential Manager entry for the Windows user running the server; passwords are not stored in the SQLite database. **Forget saved sign-in** removes only that saved credential, leaving current Windows sessions and library sources in place. The password field clears after each attempt.

Use **Add another location** to clear the connection form and add another NAS, share or subfolder without replacing earlier locations. Each full folder path has its own saved entry; reconnecting the same path updates that entry. Locations on the same NAS share use the same saved sign-in, so forgetting it affects every location on that share. Up to 64 locations are retained; a full list reports an error instead of discarding existing entries.

A successful connection returns a validated private IPv4 UNC path. **Open in Libraries & scanning** prefills it in the existing source form; Browse opens that folder. Choose the media folder and Add source there. Source addition/removal/scanning remains in one place. Keep the NAS address stable: saved connections and credentials are pinned to its private IP, and an address change requires connection/library reconfiguration. Existing hostname-based sources are not rewritten automatically. IPv6-literal setup is not supported.

Wi-Fi/Ethernet, Windows firewall and SMB protocol policy remain OS settings. An internet proxy is not needed for this local-share workflow. A real NAS login, Windows credential persistence across restarts and another physical device must still be validated; current automated network tests use mocks.

Protection: every library/streaming endpoint requires a paired device token (HttpOnly, SameSite=Strict cookie or Bearer header);
5 wrong PINs per address → 15 min lock, plus a global limit of 20 failures / 15 min; paired devices can be revoked; changing the PIN revokes all devices;
admin endpoints (folders, folder browsing, settings, devices) only answer requests from the host PC itself; requests from public
(non-private) IP addresses are always refused; state-changing requests need an `X-MC-Client` header (CSRF defence) and the Host header is checked for
host requests (DNS-rebinding defence). No router/UPnP configuration is ever performed.
**Limitation:** traffic is plain HTTP on your LAN (no TLS in Phase 0). Opening the host's own LAN IP from the host counts as a LAN device.

## Local NFO metadata and editing

Kodi-style UTF-8 combination NFOs with HTTP(S) links after the XML are supported; the links are preserved and never fetched.

Other applications supply metadata and artwork. REELHEIM reads existing local NFOs and correctly named artwork during scans; it does not scrape online, require a provider token, or download/export artwork.

Use **Settings → Libraries & scanning → Local NFO editor**, or **Edit NFO** on a movie/show detail page. Select Movies or TV Shows; a show's **Episodes** button selects individual episode NFOs. Search and pagination use the real indexed library.

**Delete NFO** removes the selected sidecar after confirmation and keeps the original beside it as `<original>.nfo.horizon-deleted-<unique-id>.bak`. It also works when XML cannot be edited. Media files, artwork and library titles stay in place; run a manual source rescan to refresh cached metadata. If another matching NFO remains in the folder, reopening the editor selects that file and requires a new confirmation before removing it. To recover a removed NFO, rename its backup to the original filename when that name is free; do not replace a new NFO created by another application.

Open an existing NFO, edit the supported fields, and choose **Save NFO & create backup**. Title, sort title, year, release/air date, tagline, plot, genres, cast/roles, rating, local provider IDs and movie collection/set can be corrected. Unknown XML tags/comments and technical/playback information are retained. The NFO is backed up beside the original with a unique `.horizon-<id>.bak` suffix before replacement. The selected catalog entry updates immediately; video files, artwork, episode order and watch progress are preserved. Scanning still only reads files.

The editor is host-only, requires existing NFOs, and refuses stale edits when another application has changed the file. Reload from disk to resolve a conflict. Missing, unsupported, protected or offline NFOs report an error; REELHEIM never invents an NFO or moves/renames the media. Unsaved edits require an explicit discard when closing or reloading. Native filesystem permissions must allow the write/backup. Windows security attributes are checked before replacement; unsupported NAS security operations refuse saving safely. Actual NAS writes remain unverified.

## Tests

```bat
RunTests.bat
```
or `cd backend && .venv\Scripts\python -m pytest -v -n 0`. Covers filename parsing, scan structure, duplicate handling, rescans,
read-only guarantee, media-path authorization (traversal, symlink escape, artwork), LAN/PIN/device auth, and HTTP range streaming.
`python scripts/make_sample_media.py D:\TestMedia [--demo-series D:\TestDemo]` generates a synthetic test library (needs ffmpeg);
`--demo-series` writes the REELHEIM demo series into its own folder, to add as a separate test-only library. The app never creates or adds demo content by itself.
Latest results: [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md).

## Exporting the project

```bat
python scripts\export_project.py
```
Creates `export\open-media-center-phase0-<timestamp>.zip` (+ SHA-256 manifest) with all source, docs, lockfiles and the prebuilt UI,
excluding `.env`, local data, virtualenvs and `node_modules`. No GitHub or Emergent service is involved. `git bundle` also works if you use git.

## Licenses

Project code: MIT (see `LICENSE`). Third-party inventory: [`docs/THIRD_PARTY_LICENSES.md`](docs/THIRD_PARTY_LICENSES.md);
full generated list incl. transitive packages: `python scripts/license_inventory.py` → [`docs/licenses/INVENTORY.md`](docs/licenses/INVENTORY.md).

## Known limitations (Phase 0)

No transcoding, no embedded-subtitle extraction, no audio-track selection, no user profiles,
no HTTPS, scanning runs synchronously in the request (fine for hundreds of files, not yet for very large libraries),
no file-system watcher (use Rescan). Xbox: see [`docs/XBOX_FEASIBILITY.md`](docs/XBOX_FEASIBILITY.md).
