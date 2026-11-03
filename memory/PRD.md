# PRD — Open Media Center (Phase 0)

## Original problem statement (summary)
Phase 0 technical proof of concept of an open-source media center (Movies + TV only) competing with Kodi/Plex; targets Windows PCs and,
later, Xbox Series X|S. Non-negotiables: no Emergent integrations/services/LLM key at runtime, only permissive OSS deps (documented),
no paid/cloud/metadata APIs, fully local/offline, read-only media access, portable, no mock catalogs, Xbox tooling not introduced without authorization.
Goals: local library (folders incl. mapped/UNC, recursive scan, filename parsing, SQLite, rescan w/o duplicates, local artwork),
basic playback + TV-friendly dark UI (keyboard/controller, range streaming, resume, unsupported-format explanation, FFprobe),
LAN access off by default with local protection, Xbox feasibility report. Deliverables: code, Windows setup, README, license inventory,
tests + real results, Xbox report, risks/next steps, export mechanism.

## User choices
Numeric PIN (≥8 digits, attempt limits, revocable devices, auth on all media endpoints over network); React + TypeScript + Vite;
folder browser plus typed path (remote devices can't browse host files).

## Architecture
FastAPI + Uvicorn + stdlib sqlite3 (`backend/mediacenter/`), React 19 + TS + Vite (`frontend/`), built UI served by the Python server.
Host = loopback (+Host header check); LAN devices = PIN pairing → token (cookie/Bearer). `run.py` binds 127.0.0.1 unless LAN enabled.

## Implemented (2026-06)
- Scanner/parser/NFO/artwork, SQLite catalog, dedupe, read-only guarantee test
- Range streaming, FFprobe compatibility verdict, player with resume, unsupported panel
- Spatial keyboard nav + Gamepad API polling, Home/Movies/TV/Detail/Settings/Pair/Player screens
- LAN mode, PIN (PBKDF2), lockout, device list/revoke, CSRF header, public-IP refusal
- Progress keyed by file path (survives remove/re-add)
- Docs: README, API, THIRD_PARTY_LICENSES, XBOX_FEASIBILITY, TEST_RESULTS, PHASE0_STATUS; Windows .bat/.ps1; export script; sample-media generator
- Tests: 105 backend tests pass; 16 live API checks pass; E2E UI pass

## Backlog
- P0: run on real Windows hardware; Xbox Edge LAN test on hardware
- P1: MKV remux / transcoding strategy (LGPL FFmpeg), background scanning, HTTPS on LAN, QR pairing
- P2: native Xbox UWP client (needs authorization), packaging/installer, subtitles & audio-track selection

## Phase 0.5 (2026-06) — Windows compatibility & deployment
- Windows path rules (paths.py), Win32 drive list (winfs.py), junction/symlink pruning, pinned MIME types, exclusive port bind
- run.py --check (deps, data dir, SQLite init/quick_check, UI, FFprobe, port, LAN), Setup.bat/Start.bat/RunTests.bat
- Offline wheels vendor/wheels (cp311–cp314 win_amd64), fully pinned requirements
- Docs: WINDOWS_TESTING, WINDOWS_ACCEPTANCE_CHECKLIST, SECURITY_REVIEW, PHASE0_5_STATUS, licenses/INVENTORY (scripts/license_inventory.py)
- Tests: 158 backend pass (Linux); QA iteration 2 100%; Windows/Xbox NOT executed
- Next: user runs Windows acceptance checklist; then Phase 1 planning

## Horizon Stage 1 (2026-06) — Home redesign
- StageHero, LivingFilmstrip (aurora focus), FirstRun, PrimaryNav, horizon.theme.css
- Spatial nav: tabs->strip ArrowDown lands on selected card; back restores focus; strip edges stop
- QA iteration 5: frontend 100%
- Open cosmetic: selected-card label offset, duplicate title on fallback art, 4K UI scale
- Next: Stage 2 (Movie/Show detail, Player, Settings in Horizon style)

## Horizon Stage 2 (2026-06) — Details, Episode Journey, Player
- Full-screen detail pages (adaptive scrim, art fallbacks, Resume/Start over/progress, enter/leave motion)
- Show page: season tabs + horizontal Episode Journey, watched/partial/unwatched states, next-up from real progress, focus restore
- Player: hidden/osd/expanded modes, A toggles, L/R 10 s, Up expands, B collapses then exits, 4 s fade while playing
- Card polish: slot min-width fix (label alignment), monogram fallback art, Stage action focus restore
- Backend: runtime field (cached ffprobe or progress duration). Sample media: Northern Survey show
- QA iteration 6 pass (1 bug fixed by QA); pytest 167 pass. Report: /app/docs/HORIZON_STAGE2_REPORT.md
- NOT done: physical Xbox/Windows test; 4K scale; scan-time runtime probing
- Next: Stage 3 (await user go-ahead)

## Stage 2 closeout (2026-06)
- Background duration reader (backend/mediacenter/durations.py): read-only FFprobe after scans, cached probe_json, MC_PROBE_WORKERS=2, visible-first, resumes on restart, unreachable->unknown; GET /api/metadata/status; runtime_status known/pending/unknown; UI "Reading length…" + quiet refresh
- Demo series moved to /app/test_media/horizon_demo (library 2 "Horizon demo (test only)"); make_sample_media.py --demo-series; tests/test_demo_isolation.py; live stage2 test moved to tests_live (run with -n 0)
- 4K: src/theme/uiScale.ts zoom when viewport >=1.25x 1080p; CSS viewport units via --vw/--vh
- Fixes: dt-primary focus ring, data-nav-down (actions->season tab), season tabs edge stop, ep fallback arcs (no dup text), unified remaining label, player next -> osd
- Tests: 174 unit, 30 live (-n 0), QA iteration 7+8 100%. Report docs/HORIZON_STAGE2_REPORT.md, screenshots docs/screenshots/stage2/
- Awaiting user approval before Stage 3. No hardware (Xbox/Windows/4K TV) validation done.

## Horizon Stage 3 (2026-06) — Discover, Search, Library Atlas
- Discover: virtualised poster wall, views, sort sheet, combinable filters/chips, collections (NFO/folder); per-result-set focus memory (index+scroll) applied on Back only
- Search: offline search, D-pad OSK (+punctuation row), physical typing without focus steal/duplicates, OSK Right-edge -> results, restore on Back
- Atlas: orbit rings (type/genre/collection, More folding), zoom into clusters, LB/RB paging, grid mode; restores level/cluster/page/title; fits 100vh
- QA iteration 9 (7 bugs) -> all fixed; iteration 10 96% + last item fixed; pytest 185 unit, 30 live pass
- Report docs/HORIZON_STAGE3_REPORT.md, screenshots docs/screenshots/stage3/
- NOT done: physical Xbox/Windows/4K TV testing. Awaiting user approval before Stage 4

## Stage 3 final closeout (2026-06)
- Search entry focuses last-used OSK key (sessionStorage horizon.search.oskKey, A first time); OSK top row Up -> search input -> nav; Clear search refocuses OSK; X deletes on results
- Discover empty-library state; Atlas resolves stack nodes from fresh /api/atlas (ids only stored), key-based focus restore, vanished cluster zooms out
- Isolated temp servers (separate data dirs, copied media) used for empty-library + removed-title tests, then deleted; preview libraries untouched
- QA iteration 11 (126/129) -> fixes; iteration 12 final 130/132 (98.5%), remaining bug fixed + scripted check
- Awaiting final user approval; Stage 4 not started
