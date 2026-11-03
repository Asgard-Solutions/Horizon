# Horizon Stage 2 — Final report (closeout)

Status: **ready for approval**. Stage 3 has not been started.
Date: 2026-06. Tests: `/app/test_reports/iteration_6.json` (Stage 2 build), `iteration_7.json` (closeout), `iteration_8.json` (final regression).

## 1. What Stage 2 delivers
- **Detail pages (full-screen backdrop):** real fanart fills the screen, with an adaptive scrim that measures the artwork's brightness. Title, chips, plot, Resume / Start over / Play again and a watch-progress bar sit on top. Enter and leave transitions are included. Fallbacks: blurred poster + framed poster, or procedural Horizon arcs when there is no art.
- **Episode Journey:** season tabs above a horizontal episode strip. Cards show artwork, code, title, length, plot and state (watched / partial / unwatched).
  - Navigation: Left/Right moves between episodes. Up returns to the selected season tab. Down from a tab goes to the previously selected episode. LB/RB (PageUp/PageDown) switch seasons. The tab row stops at its edges.
  - The next-up action (Continue / Up next / Start / Watch again) comes from real progress. Down from it goes to the selected season tab.
- **Player (auto-hiding):** three modes, hidden → OSD → expanded.
  - On the playback surface: A plays/pauses, Left/Right seek 10 s, Up expands.
  - In expanded controls, arrows only move focus. Seeking happens only on the focused seek bar.
  - B closes the controls first, then exits. Controls fade after about 4 s while playing and stay visible while paused.
  - The OSD shows elapsed time, time remaining and the clock time playback ends.
- **Card polish:** labels now align. The cause was long subtitles widening flex slots; fixed with `min-width: 0`. Fallback art shows each title only once: a monogram on posters, decorative arcs on episodes. Stage actions restore focus on Back. Remaining-time wording is the same everywhere ("36 s left").

## 2. Closeout changes

### 2.1 Episode lengths are read in the background
**Why lengths used to appear only after playback:** the scanner never ran FFprobe. Metadata was read only on demand by `/api/files/{id}/playback`, which the player and the movie page call. The show page never called it. Until then, the only other source of a length was the duration the browser reported while playing.

**Now (`backend/mediacenter/durations.py`):**
| Requirement | Implementation |
|---|---|
| Scan stays fast | `scan_library` still never probes. The reader runs after the scan (`wake()`) in separate threads and pauses while any scan holds `SCAN_LOCK`. |
| Read-only | FFprobe only opens files for reading. On Windows it runs at below-normal priority with no console window. A test checks SHA-256 hashes, mtimes and the file list before and after (`test_media_files_are_never_modified`). |
| Cached in SQLite | The result goes in `media_files.probe_json`. It is written only if the file's size and mtime still match what was read. A changed file is reset by the scanner and read again. |
| Limited concurrency | `MC_PROBE_WORKERS` (default 2; `0` turns it off). A test confirms at most 2 files are read at once. |
| Visible items first | `/api/home`, `/api/movies`, `/api/movies/{id}` and `/api/shows/{id}` push their on-screen files to the front of the queue (up to 200). |
| Graceful fallback | Each movie and episode carries a `runtime_status`: `known`, `pending` or `unknown`. A pending episode shows a faint "Reading length…" label, and the show page quietly refreshes every 4 s without moving focus. Unknown means damaged, unreachable or no FFprobe: no length is shown and nothing polls. |
| Resumes after restart | Pending work is simply rows where `probe_json IS NULL`, and the reader starts with the app. A test stops a reader midway and confirms a fresh one finishes the rest. |
| Unreachable files (e.g. NAS offline) | They are skipped for the current session and shown as `unknown`. A rescan or restart retries them. Damaged files are cached as errors and are not retried until they change. |
| Status | `GET /api/metadata/status` returns `{available, workers, pending, known, unknown, active, unreachable}`. |

Measured in preview: scanning the 5-file demo library took about 1.5 ms. The reader then processed 2 files at a time and finished in under 3 s. In a QA library of 240 episodes, every length appeared on screen within about 10 s.

### 2.2 The demo series is isolated
- "Northern Survey" now lives in its own test-only folder, `/app/test_media/horizon_demo`. In preview it is registered as a separate library, "Horizon demo (test only)". It is no longer inside `/app/sample_media`.
- It is created only by an explicit dev command: `python scripts/make_sample_media.py <sample> --demo-series <separate folder>`. The script refuses a demo folder that is the same as, or inside, the sample library.
- The app never creates libraries or demo titles, and production shows only what the scanner finds in the configured folders. `tests/test_demo_isolation.py` checks that:
  - a fresh install has an empty library;
  - no app code (backend or frontend) mentions demo titles or paths;
  - the Windows launch scripts never generate sample media.
- `test_media/` is excluded from git and from the project export.
- The live tests that depend on demo content were kept: `tests_live/test_detail_stage2_live.py` now looks shows and movies up by title, and skips if the demo library is not added.

### 2.3 Large-screen scaling
- **Problem found at simulated 3840×2160:** the layout stayed at its 1080p pixel size, so text was about 19–22 px on a 4K canvas — too small from the couch.
- **Fix:** `src/theme/uiScale.ts` zooms the whole 1080p layout when the browser's CSS viewport is at least 1.25× larger than 1920×1080 (zoom = min(w/1920, h/1080)). Viewport units now go through `--vw`/`--vh` so they stay true to the screen while zoomed.
- At about 1080p CSS (Xbox Edge, or Windows at its default TV scaling) the zoom stays at 1×.

## 3. Test results (latest)
| Suite | Result |
|---|---|
| Backend unit (`python -m pytest tests`) | **174 passed** (adds 9 duration-reader tests and 4 demo-isolation tests) |
| Live API (`python -m pytest tests_live -n 0`) | **30 passed** (Phase 0 live checks, Stage 2 detail, closeout, unreachable-runtime) |
| Frontend QA, iteration 7 | All flows passed; 1 medium bug (focus ring) and minor notes, all fixed |
| Frontend QA, iteration 8 (final regression) | **100%**: all 7 fixes verified, full regression at 1080p and 4K, no console errors |

Flows covered in iterations 7 and 8:
- **Home:** Stage hero; filmstrip (tabs → selected card); focus restore from cards and from Stage actions.
- **Movie page:** Resume / Start over / progress.
- **Show page:** Episode Journey navigation (Left/Right, Up to the selected tab, Down to the previous episode, LB/RB); season switching; watched, partial and unwatched states; real lengths shown without playback; the "Reading length…" state resolving on its own.
- **Player:** hidden/OSD/expanded modes, A/Enter, ±10 s seek, Up to expand, B closes then exits with focus restored, 4 s fade, staying visible while paused, resume, next episode, mouse click on the seek bar.
- **Reduced motion:** transitions off, static feedback mark.
- **Simulated gamepad** (stubbed `navigator.getGamepads`): D-pad, LB/RB, A, B.
- **Other pages:** Library and Settings.

### Screen sizes checked (all simulated in headless Chromium)
| Viewport | UI scale | Result |
|---|---|---|
| 1920×1080 @1x | 1 | Pass: no overflow, focus ring visible, safe margins |
| 1920×1080 @2x (how Xbox Edge reports a 4K output) | 1 | Pass: sharp rendering |
| 2560×1440 @1x | 1.33 | Pass |
| 3840×2160 @1x (via CDP device metrics) | 2 | Pass: no overflow; navigation, Episode Journey centring and seek-bar clicks accurate |

Screenshots are in `docs/screenshots/stage2/`:
- 1080p: `s8_home_1080`, `s8_movie_1080`, `s8_show_1080`, `s8_player_expanded_1080`, `s8_settings_1080`
- 4K: `s8_home_4k`, `s8_movie_4k`, `s8_show_4k`, `s8_player_expanded_4k` (the screenshot tool capped these at 3840×1920, scale 1.78), plus `s8_home_3840x2160_scale2`
- 1080p at 2x density: `show_dpr2`

## 4. Simulated tests vs. real hardware
| Area | Status |
|---|---|
| Keyboard, mouse, reduced motion in Chromium | Tested (automated, headless Chromium 156) |
| Xbox controller | **Simulated only** (Gamepad API stub). Not tested on an Xbox. |
| Xbox Series X/S (Edge) | **Not tested on hardware** |
| Windows PC (Edge/Chrome, launch scripts, NAS/UNC paths) | **Not tested on hardware** in this stage. The Windows scripts and path logic are covered by unit tests only. |
| Physical 4K TV (readability at viewing distance, overscan) | **Not tested.** Only simulated viewports were used. |
| Real NAS load under background reading | **Not measured.** Concurrency is limited by design (default 2), but it hasn't been measured on a real NAS. |

## 5. Outstanding issues and notes
- **Hardware validation is still needed.** Real Xbox Edge, a Windows PC on a 4K TV, and a real NAS: see the checklist in `docs/WINDOWS_ACCEPTANCE_CHECKLIST.md`.
- **CSS `zoom` dependency:** the 4K scaling needs a browser that supports CSS `zoom`. Edge, Chrome and Firefox 126+ do; older browsers simply keep the 1× layout.
- **Rare stale lengths:** when a file has no length from FFprobe, the length the player reported is used instead. If a file was replaced with identical size and mtime, a stale length could remain. This is unlikely, because the scanner re-reads any file whose size or mtime changed.
- **Reader efficiency (code-review note):** the reader runs a short SQLite query while holding its queue lock, and a growing list of unreachable files makes each pick scan more rows. Both are fine for local SQLite; revisit if libraries grow to tens of thousands of offline files.
- **Live test suite must run serially** (`-n 0`), because some live tests add and remove temporary libraries.
