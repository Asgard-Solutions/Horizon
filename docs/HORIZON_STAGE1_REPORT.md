# HORIZON — Stage 1 handoff (Foundation + Home / "The Stage")

Source of truth: `design/horizon/HORIZON_DESIGN_SYSTEM_v1.md` + `horizon.tokens.json` (copied into the repo unchanged).
Checkpoint before the redesign: git commit `95d25b6` ("Checkpoint before HORIZON Stage 1 redesign").

## Real stack (inspected, unchanged)

* Backend: Python 3.11 · FastAPI 0.110 · Uvicorn · stdlib `sqlite3` (local `data/mediacenter.sqlite3`) · optional FFprobe. Package `backend/mediacenter/`.
* Frontend: React 19 + TypeScript 5.9 + Vite 8 + react-router 7, plain CSS, lucide-react icons. Built UI served by the Python server.
* No new runtime dependencies except two OFL-1.1 font packages (below). No cloud, CDN, telemetry or remote artwork.

## What Stage 1 implements

| Requirement | Implementation |
|---|---|
| Central design tokens | `frontend/src/theme/horizon.tokens.json` (source) + `horizon.theme.css` (CSS variables, reduced-motion durations → 0). All legacy CSS variables now resolve to tokens (`styles.css :root`). A backend test (`tests/test_design_tokens.py`) fails if CSS drifts from the JSON. |
| Typography | Sora (display) + Inter (body), self-hosted variable fonts via `@fontsource-variable/*` (OFL-1.1; license texts in `docs/licenses/OFL-*.txt`). TV sizes ≥ 1600 px, desktop sizes below, via `--fs-*` variables. |
| Responsive shell | Sticky top navigation (`PrimaryNav`): HORIZON wordmark + original orbit mark, Home · Movies · TV · Library (host) / This device (paired device). Active = luminous underline; focus = separate aurora ring. Safe margins `--safe-x: clamp(24px, 5vw, 96px)`. Search is **not shown** until Stage 2 implements it. |
| The Stage | `home/StageHero.tsx`: real title, eyebrow from real context (Continue watching / Recently added / Series), truthful chips only (Movie/Series/Episode, year, S01 E02, seasons/episodes counts, "N min left" only when a saved duration exists), NFO plot only if present, amber progress only for persisted progress. Primary **Resume from m:ss** / **Play** / **Explore series**; secondary **Details**. Real local fanart → else blurred real poster + crisp poster → else procedural. 120 ms selection debounce, 380 ms crossfade; selection never starts playback. |
| Living Filmstrip | `home/LivingFilmstrip.tsx`: real items; focused card rises and scales 1.12; neighbours step back on a gentle curve (≤ 8° rotateY, art only — labels stay on a flat plane); stable centring; Left/Right move one item and **stop at edges** (visible nudge); groups (only when non-empty): Continue watching, Recently added movies, Series — tabs, PageUp/PageDown, controller LB/RB (mapped, untested on hardware). |
| Grid fallback | One-click "Grid view" / "Filmstrip view", remembered in `localStorage` (`horizon.home.view`). |
| Horizon Line | `home/HorizonLine.tsx`: static SVG, 2 px, bends toward the focused card only; aurora anchor + restrained amber trail; snaps under reduced motion. |
| Missing art | `components/TitleArt.tsx`: midnight gradient + thin horizon arcs + real title (also used on Movies/TV cards and detail posters). |
| Library status | `home/LibraryStatus.tsx`: counts from SQLite + new viewer-safe `sources` field on `/api/home` (`total`, `unreachable`, `last_scan_at` — **no paths**). Unavailable folders: "Your library entries are still here." + Inspect source (host). |
| First run | `home/FirstRun.tsx`: abstract CSS/SVG horizon (no fake titles), **Add media folder** (host) → Library; paired devices get an explanation instead of a dead button; folders-but-no-media variant. |
| Focus & input | Highest-value action focused on launch (Resume when available). Focus restored to the same group + card when returning from details/player (sessionStorage). Entering the tab row lands on the selected tab. Player Escape now returns to the screen playback was started from (history back) instead of pushing a new page. Key hints shown only after keyboard/controller input. |
| Reduced motion | Token durations → 0, no 3D/scale in the strip, instant scrolling. |

## Files changed

New: `frontend/src/theme/horizon.tokens.json`, `frontend/src/theme/horizon.theme.css`, `frontend/src/home/{adapter.ts,StageHero.tsx,LivingFilmstrip.tsx,HorizonLine.tsx,FirstRun.tsx,LibraryStatus.tsx,home.css}`,
`frontend/src/components/{PrimaryNav.tsx,HorizonMark.tsx,TitleArt.tsx}`, `backend/tests/test_design_tokens.py`, `design/horizon/*` (supplied specs), `docs/HORIZON_STAGE1_REPORT.md`, `docs/licenses/OFL-sora.txt`, `docs/licenses/OFL-inter.txt`.
Modified: `frontend/src/pages/Home.tsx` (rewritten), `App.tsx` (top nav), `main.tsx` (fonts/tokens), `styles.css` (token mapping, buttons, shell),
`components/PosterCard.tsx` (TitleArt), `pages/MovieDetail.tsx`, `pages/ShowDetail.tsx` (TitleArt fallback), `pages/Player.tsx` (exit history),
`nav/spatial.ts` (rail edge stop, selected-tab entry, LB/RB → PageUp/PageDown, reduced-motion scrolling), `types.ts`,
`backend/mediacenter/routes_library.py` (`/api/home`: `sources`, show art for continue-watching episodes, 24-item caps), `backend/tests/test_scanner.py` (+2 tests),
`frontend/package.json`/`yarn.lock` (Sora/Inter added, Lexend/Bricolage removed), `docs/THIRD_PARTY_LICENSES.md`, `docs/licenses/INVENTORY.md`.
Removed: `components/Sidebar.tsx`.

## Tests (actual runs, Linux dev container only)

* Backend: `python -m pytest -q -n 0` → **161 passed**, 16 live-server checks skipped (includes all Phase 0/0.5 parsing, duplicate, read-only fingerprint, path-authorization, streaming tests + new token-sync and `/api/home` source-status tests).
* `yarn typecheck` and `yarn build`: pass. License inventory: 0 problems.
* Browser QA (Chromium, testing agent iterations 3–4): see the PRD / final status for results.

## Known gaps / honest limits

* Home groups are capped at 24 items server-side, so the strip never renders hundreds of posters; **true virtualization is not built** (needed for the Stage 2 Movies/TV screens).
* Scan-in-progress state is not shown on Home (scans run synchronously on the Library screen in Phase 0).
* 4K: verified only as a 3840×2160 CSS-pixel viewport in Chromium; real 4K TVs usually report 1920 CSS px at 2× DPR. 125 %/200 % zoom not yet audited.
* Contrast: token pairs are high-contrast on solid surfaces; text over real backdrops depends on the scrim and **has not been measured** with real artwork (the sample posters are solid colours).
* Windows: **unverified**. Xbox: **unverified** — no hardware or runtime test; LB/RB/A/B mapping follows the W3C standard gamepad layout and is untested.
