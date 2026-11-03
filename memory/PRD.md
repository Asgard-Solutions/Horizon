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
