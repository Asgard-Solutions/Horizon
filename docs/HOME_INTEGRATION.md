# Horizon Home v1.2 integration

Updated November 3, 2026. Repository baseline: `a11c73faa7aa621e59ec2548e43ab14907317983`. Work is local and uncommitted; no GitHub branch, commit, push, merge or deployment was created.

## Implemented flow

Home now opens with Movies and TV Shows, using the supplied atmospheric background and the user's monitor-emblem Horizon Media Center logo. Choosing a type opens `/home/movie` or `/home/tv`, with Atlas, Discover and Search as the three main choices. Continue Watching appears below only when the actual selected-type API returns valid unfinished movies or playable episodes. There is no initial hero, Filmstrip, Recently Added, recommendation feed or generated library content.

Settings is the only shared header utility. Library sources are managed under Settings → Libraries & scanning using the existing host LibraryManager. The former Sources page is removed; `/sources` redirects to the same Settings section while preserving the media filter. Paired devices retain the existing host-only management restriction. Existing scanning, SQLite schema, file authorization, streaming and player services remain in place. The old Stage/Filmstrip components are retained as existing browsing components but are not mounted on Home.

Destinations and detail/playback links carry `media=movie|tv`. The API accepts optional `media_type=movie|tv` on Home, Discover, Search and Atlas, applying it before pagination, limits, facets, groups and counts. Unscoped callers remain compatible. Scoped Home counts refer to that scope; the initial Home obtains global counts through the unscoped request. The current application has no user profiles, so no profile UI or fictitious profile filtering was added.

Continue Watching uses the existing unique progress-by-path record and completion flag. Scoped rows require finite duration and position, with `0 < position < duration`, and exclude watched records. Ordering is actual progress update time descending with file-ID tie-breaker. Offline entries stay indexed. The UI rechecks the existing stream service with HEAD before offering Resume/Start Over; playback metadata alone is not treated as evidence that a file is reachable. No progress is cleared by Home or opening a dialog.

## Focus and presentation

The existing spatial input manager drives keyboard and Gamepad API navigation. A/B use press edges; held keyboard activation does not cascade through two screens. Physical text-editing arrows stay native, while gamepad directions can exit the Search input. Home focus and horizontal row position are remembered independently for each media type; route utilities restore their opener, dialogs trap focus, and completed/removed items recover to a valid survivor or navigation card. Reordered resume items are scrolled fully into view after return.

The 1920x1080 layout uses the measured Home geometry and inset focus ring. Home-specific tokens are added without replacing global browse/player token values. Auto 4K scaling remains supported. Compact and manual text-scale layouts use flowing content, preserve stable focus across resize, and allow vertical scrolling. The background is 1672x941, not native 4K. The logos are the two exact user-supplied 2172x724 transparent PNGs, with no font dependency. Both are stored locally under `frontend/src/assets/`.

The white-lettered `horizon-media-center-logo-on-dark.png` is used in the shared Home/browse header. The dark-lettered `horizon-media-center-logo-on-light.png` is retained for light backgrounds. CSS crops the supplied transparent vertical padding inside the existing header box; it does not alter the PNGs, distort the artwork, or change the header's focus geometry. Their SHA-256 hashes match the supplied files `exec-8e6d7372-f1d6-4d79-99bd-ea4c59216e94.png` and `exec-13a0e64a-d3fc-4765-8f46-9b89e20db833.png` respectively. The earlier substitute SVG was removed.

After this branding correction, the production build passed again. Browser inspection verified the supplied PNG on Home at 1920x1080, on the Movies hub at 1280x720, and in the compact 390x844 header, with focus preserved across resizing. Current screenshots are `docs/verification/home-v1.2/home-correct-logo-1920x1080.jpg` and `movies-correct-logo.jpg`; the earlier PNG screenshots predate the logo correction.

## Cinematic controls styling update

The user selected cinematic panels, then supplied annotated simplification. Home selectors now contain vertically centered Movies / TV Shows labels and live library counts at the bottom-left of their distinct original backgrounds, with no eyebrow text, descriptions, icon badges or gold markers. Atlas/Discover/Search retain their corresponding navigation icons; shared Settings, Back and Home action buttons use matching surfaces. Remaining icons use the existing lucide-react dependency.

The production build and all five existing helper tests passed after the styling change. Direct browser checks covered 1920x1080 and 1280x720 presentation, 800x600 compact destination cards, 390x844 Home labels/utilities, keyboard TV Search scope and Back restoration, and 200% app text scaling with Reduced motion. Computed transitions were 0s under Reduced motion; the original Auto/Follow system preferences were restored. A review found a compact Discover/icon collision, which was reproduced and fixed; all three destination labels then measured clear of their icons. Forced-colors styling was reviewed statically, without browser emulation. Current actual-app captures are in `docs/verification/cinematic-controls/`. No additional backend or physical controller/playback verification is implied by this visual update.

## Main file map

Card-count placement follow-up: movie totals and TV-series totals now appear only in their corresponding selector cards; the Home footer keeps the library icon and source status. Counts come directly from the existing unscoped `/api/home` response, remain absent until data exists, retain real zero values, and use singular/plural labels. The production build passed. The actual API and UI both reported 2 movies, 2 TV shows and 2 sources during verification. At 1920x1080 and 390x844, both count labels fit inside their cards without overlapping the titles; compact keyboard navigation still focused TV Shows. Current capture: `docs/verification/cinematic-controls/home-card-counts.jpg`.

Annotated Home cleanup: the large library-status panel was removed, and its small library icon moved beside the existing footer counts. Status appears once. The production build passed, and the updated tokens parse as valid JSON. Actual browser checks at 1920x1080 confirmed only the two media names in the selector cards, zero removed decorations, one live status and one footer icon. Keyboard selection opened the TV hub; Back restored TV Shows focus. At 390x844 both titles fit and are vertically centered, and the single footer count/icon scrolls into view. Captures: `docs/verification/cinematic-controls/home-clean-cards.jpg` and `home-clean-cards-compact.jpg`.

Latest visual refinement: Movies and TV Shows now have separate original card backgrounds generated with the built-in image tool. Movies uses warm cinema-projector/film-reel artwork; TV Shows uses cool television-studio screens. Both PNG assets are bundled in `frontend/src/assets/`, with their actual dimensions and complete generation prompts recorded in `docs/branding/card-backgrounds-v1.md`. Home retains its existing atmospheric background. The selector cards use dark copy overlays and right-aligned cropping; their extra drawn arc and the circular arrow badges remain removed. A fresh production build passed. Actual app checks at 1280x720, 1920x1080 and 390x844 verified the distinct assets, readable labels, focus retention of the selected background and compact icon/label separation. Current captures are `docs/verification/cinematic-controls/home-original-card-backgrounds-1920x1080.jpg` and `home-original-card-backgrounds-compact.jpg`.

| Responsibility | Actual files |
|---|---|
| Selector/hub and responsive style | `frontend/src/pages/Home.tsx`, `frontend/src/home/HomeScreen.tsx`, `hub.css`, `useHomeLayout.ts` |
| Data/context/focus memory | `frontend/src/home/context.ts`, `useMediaType.ts`, `useHomeLibrary.ts` |
| Availability and resume options | `frontend/src/home/ResumeDialog.tsx`; existing `/api/files/{id}/playback` and `/api/stream/{id}` HEAD |
| Shared chrome, route restoration, library settings entry | `frontend/src/App.tsx`, `components/PrimaryNav.tsx`, existing `pages/Settings.tsx` |
| Scoped existing destinations | `pages/Atlas.tsx`, `Discover.tsx`, `Search.tsx`; detail/player URL changes only |
| Shared input and async race protection | `frontend/src/nav/spatial.ts`, `frontend/src/hooks.ts` |
| Actual scoped queries | `backend/mediacenter/routes_library.py`, `routes_discover.py` |
| Tests | `frontend/tests/home-context.test.ts`, `backend/tests/test_home_scope.py`, `scripts/dev/verify_home_ui.mjs` |

## Verification evidence

Git checkpoint verification, November 4, 2026: the current production build and all 5 frontend helper tests passed. A fresh backend unit run using an isolated disposable test directory reported 230 passed, 9 skipped and the same pre-existing `test_missing_file_is_skipped_not_cached` duration-counter failure described below. The browser harness passed a syntax check; it was not rerun in full for this checkpoint. Local runtime data, media, environment files, dependencies and build output remain excluded from Git. This is a saved development checkpoint, with the hardware and playback checks below still outstanding.

Settings background follow-up: the Settings route now reuses the exact approved Home background image and overlay, fixed behind the scrolling page. Its header keeps the Horizon Home link and Back button and omits the redundant Settings link. Other routes keep their Settings entry. The production build passed; targeted actual-browser checks verified the shared background, header removal, Settings category/panel keyboard navigation, app Back restoring Home's Settings focus after its existing asynchronous restoration, and a 1024x768 layout without horizontal overflow. No media sources, scan state or playback preferences were changed during these checks. Home's component, stylesheet and background file hashes remained unchanged; Home is approved and locked unless the user explicitly requests a change. Screenshot and observations: `docs/verification/cinematic-controls/settings-home-background.jpg` and `settings-home-background-verification.json`. The full integration harness was not rerun for this visual change.

Neutral mouse-return follow-up: Home retains its remembered focus target but now paints both selection cards with their neutral frame in mouse mode. Only the hovered card receives the teal hover frame; moving away restores neutral even if that card still has DOM focus. The original disappearing-border issue was caused by the global mouse-focus suppression rule; scoped neutral/hover shadows preserve the frame without keeping a selection highlight. Keyboard and gamepad focus styles remain separate, the original artwork remains intact, and forced-colors rules preserve system borders. The production build passed. Targeted actual-browser checks verified Movies and TV Shows through mouse selection, app Back, hover and pointer leave at 1920x1080; keyboard Left, Enter and Escape retained visible focus. A 1024x768 compact check verified neutral mouse return, hover and no horizontal overflow. No physical gamepad or forced-colors runtime check was performed for this follow-up. The regression case in `scripts/dev/verify_home_ui.mjs` now checks neutral return, hover and pointer leave, and passed a syntax check; the full harness was not rerun. Current screenshot and observations are `docs/verification/cinematic-controls/home-neutral-return.jpg` and `home-neutral-verification.json`; prior outline-fix artifacts remain as history.

Settings-only navigation follow-up: the duplicate header entry, Sources page, old focus targets and header token were removed. Empty-library, Atlas, Discover and unavailable-file recovery actions now open the existing library Settings section. The build and all 5 helper tests passed. Direct browser checks confirmed zero Sources header buttons, one Settings button, logo/Settings keyboard navigation, restored Settings focus after Back, scoped legacy URL redirection, and actual empty-library setup opening `section=libraries&media=movie` in an isolated empty database. The updated full browser harness passed a syntax check but was not rerun in full for this follow-up. The attached browser did not honor the compact viewport override, so this follow-up does not claim a new compact-layout pass. The temporary preview server was stopped, and the normal application was restored to Home. Current screenshot: `docs/verification/cinematic-controls/home-settings-only.jpg`.

Actual environment: Windows, Python 3.12 virtual environment using the repository's bundled wheels, Node 24, Chrome 156. Tests used an isolated temporary application database, never a production media library.

| Check | Observed result |
|---|---|
| `cd frontend; yarn build` | Passed TypeScript checking and Vite production build |
| `cd frontend; yarn test` | 5 helper tests passed; each was first observed failing against missing helper behavior |
| New scoped API tests | 43 tests; backend unit total increased by 43 with no new unit failures |
| `cd backend; ../.venv/Scripts/python.exe -m pytest tests -n 0 -q --tb=short` | 230 passed, 9 skipped, 1 existing failure |
| `node scripts/dev/verify_home_ui.mjs` against isolated server | 15 actual-app flow groups passed; latest full report timestamp `2026-11-04T04:35:52.991Z` |

Browser coverage includes real empty/setup states, media-scoped indexed/history responses, source/Settings focus restoration, keyboard and simulated held gamepad input, pending Retry focus, missing/broken artwork, row removal during/after a modal, scoped Search/Atlas, delayed-request cancellation, locally simulated source loss/recovery, and failed player startup without erasing saved progress. Resume-row focus was verified after an authoritative progress update reordered the list.

Eight viewports were exercised on all three Home screens: 1920x1080, 1280x720, 3840x2160, 1366x768, 1920x800, 1024x768, 800x600 and 390x844. Additional checks cover live resize without losing focus and 125%/200% app text scaling. The test fixture media files are intentionally invalid and live only in the isolated test data directory; they establish real indexing and failure handling, not successful video decoding.

The JSON ledger and empty-library screenshots are copied into `docs/verification/home-v1.2/`. A fresh scoped review found four important focus/input issues; these were fixed and the browser tests exercise their triggers. The review follow-up found no important remaining issues in that scope.

## Existing failures and remaining checks

The backend failure already present at baseline remains `tests/test_durations.py::test_missing_file_is_skipped_not_cached`: its expected unreachable counter is at least one, but is zero on this environment. Baseline was 187 passed, 9 skipped, 1 failed; current unit results are 230 passed, 9 skipped, the same one failure. This was not changed as part of Home.

The existing frozen Yarn install rejects the committed lockfile. `yarn install --pure-lockfile` was used to establish the working build without rewriting that lockfile. The separate old live-server suites are not counted as passing; four of their modules require `requests`, which the bundled development environment does not include.

Physical gamepad/Xbox runtime, a physical NAS/UNC outage, Windows folder-picker UX, successful decoding/seeking/resume with the user's real media, long-running scans and a large user collection remain unverified. The source-outage browser check renamed only its own disposable local test directory, then restored it. No Xbox compatibility or complete release signoff is claimed.

The normal local startup checks also passed with an empty database and LAN access disabled. FFprobe is not installed in this environment; the launcher identifies it as optional, and codec inspection remains unavailable until it is provided.

## Run and reproduce

For normal local use after building, run `.venv/Scripts/python.exe backend/run.py --port 8765` from the repository root and open `http://127.0.0.1:8765`. Add actual media folders through Settings → Libraries & scanning. No sample library is automatically created.

For browser verification only, start a separate backend on port 8767 with `MC_DATA_DIR` set to the absolute `data/home-integration-check` directory and `MC_PROBE_WORKERS=0`, then run `node scripts/dev/verify_home_ui.mjs`. The script verifies that exact database location before changing its test index, creates disposable fixtures there, restores its simulated outage, and removes its test libraries from the index afterward. Do not use that test database for the normal application.

These implementation notes supersede the old Home/Stage composition and optional-Atlas-entry language in the historical v1 design documents. The advanced Atlas map and the existing browse views remain available; every new Home entry is backed by the inspected app services.
