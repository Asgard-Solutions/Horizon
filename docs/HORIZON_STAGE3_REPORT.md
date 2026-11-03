# Horizon Stage 3 — Completion report (Discover, Search, Library Atlas)

Status: **final closeout complete — awaiting your final approval**. Stage 4 has not been started.
Date: 2026-06. QA reports: `/app/test_reports/iteration_9.json` (first full pass, 7 bugs), `iteration_10.json` (96%), `iteration_11.json` (closeout pass 1: 126/129), `iteration_12.json` (**final regression: 130/132 automated checks = 98.5%**).

## 0. Final closeout (this round)
| Item | Result |
|---|---|
| Search entry from the top menu (Enter, click, `/` or Y) | Focus lands on the **last-used keyboard key** (A the first time), so typing on a physical keyboard works immediately and the on-screen keyboard stays visible. Up from any top-row key goes to the search box, and Up again to the top menu. The key is remembered across visits. The query and selected result are restored on Back. Automated: 12/12 Up checks, 19/20 Search checks. The one failure (focus lost after "Clear search") was fixed afterwards; see below. |
| Empty-library screens, tested in the browser | Ran on a **separate temporary server with its own empty data folder** (port 8766). Covered: Home first-run, Discover "Your library is empty" with an Add media folder button and no filter bar, Atlas "Your Atlas is waiting", and Search with no results. 12/13 automated; the 1 failure was the same Clear-search bug. |
| Removing a title while its details are open, then pressing Back | Ran on a **separate temporary server with copied test media** (port 8767). The files were deleted mid-test and rescanned. Discover (a middle and the last index), Search, Atlas orbit, Atlas grid and a nested "More genres" group all recovered to the nearest remaining item. A cluster that disappears zooms out one level. Focus never fell to an empty page. 24/24 automated. |
| Your preview libraries | Not detached, rescanned or modified. One side effect: QA played a 1-second test clip (Test Title 0011) to the end, which marked it watched; I cleared that progress again. The temporary servers, data folders, copied media and helper script were all deleted afterwards. |
| 4K | The test browser stops at **3840×1920**, so a true 3840×2160 render was **not** verified. Layouts at 3840×1920 passed 4/4. |

**Fixes made in this round:**
- Search entry focus.
- Up from the keyboard's top row now always goes to the search box.
- Atlas rebuilds "More …" groups from fresh data, so removed genres disappear. The saved state now holds only ids, not group contents.
- Atlas restores focus by node id when counts re-sort the rings.
- "Clear search" can be reached with the D-pad, and focus returns to the last-used key after pressing it (fixed after iteration 12, checked by a scripted browser run).
- X deletes a character while a result is focused.
- Grid tiles show "1 title" rather than "1 titles".
- The focused title label on the inner ring no longer covers the cluster name in the centre.
- The selected node is slightly smaller in the overview so neighbouring labels stay readable.
- There is a dedicated Discover empty-library state.

**Automated pass rate (iteration 12, final full regression):** **130 / 132 = 98.5%**. Manual observations are not counted, and 4 invalid checks were excluded: a wrong premise, a wrong selector, a by-design two-step B in the player, and the 4K height cap.
| Area | Passed |
|---|---|
| OSK Up from the top row | 12/12 |
| Search (preview) | 19/20 |
| Isolated removed-title | 24/24 |
| Isolated empty library | 12/13 |
| Discover (preview) | 25/25 |
| Atlas (preview) | 17/17 |
| Home / detail / player / Settings / reduced motion | 17/17 |
| 4K at 3840×1920 | 4/4 |

Both failures were the same Clear-search focus bug. It has been fixed, and the fix was verified by one scripted browser check. **The fix has not been rerun through the full automated suite.**

> **All controller testing was SIMULATED** in a desktop Chromium browser. Arrow keys stood in for the D-pad, Enter for A, Escape for B,
> PageUp/PageDown for LB/RB, and synthetic `PadX`/`PadY` key events for X/Y.
> **Nothing was tested on a physical Xbox, an Xbox controller, Xbox Edge, a Windows PC, or a real 4K TV.**

## 1. What Stage 3 delivers
- **Discover** (`/discover`): views for All media, Movies, TV shows and Collections. It has a virtualised poster wall (only the visible rows are in the page, and data loads in pages of 120), a Sort sheet, combinable filters (Genre, Year, Watched, Type) shown as removable chips, Reset filters, and pages for individual collections (from NFO files or folder groups).
- **Search** (`/search`): searches titles, series and episodes on this PC, offline. The D-pad on-screen keyboard has letters, digits, a punctuation row (`' - . : & !`), Space, Backspace and Clear. X deletes and Y types a space.
- **Library Atlas** (`/atlas`): an orbit map. The inner ring is media type, the middle ring genres, the outer ring collections, and overflow folds into a "More …" node. A zooms into a cluster whose titles sit on 3 orbits (8, 12 and 16 per page), with LB/RB to page. B zooms out. A Grid view toggle is remembered.

## 2. Your acceptance choices and how they were met
### 2A — Back restores the exact tile
| Where | Behaviour | Verified |
|---|---|---|
| Discover | Each result set (view + sort + filters + collection) has its own remembered position: tile index plus exact scroll. It is applied only on Back, so Collections → collection → movie → Back → Back lands on the correct tile at each level. | Index 146/154/162 (beyond the first 120-item data page), scrollY restored exactly; collection index 10 restored after a nested Back |
| Discover controls | Changing a tab, sort or filter never moves focus off the control you used. The filter sheet stays open and focused while you toggle options. Removing a chip moves focus to the next chip (or to Sort if none are left), and Reset moves focus to Sort. | Yes; focus never fell to an empty page |
| Search | The query is kept in the URL (`?q=`). The same result is refocused and the scroll restored. Restore happens only on Back; a fresh visit starts on the keyboard. | Yes, including episode results |
| Atlas | The zoom level, cluster, page and focused title are restored in both orbit and grid mode, with no zoom animation on return. | Yes (Crime → page 2 → title → Back) |
| Removed titles | Discover and Search fall back to the item now at the same position (or the last one). Atlas clamps to the nearest valid node or page, or zooms out if the cluster no longer exists. | Code path reviewed; not exercised against a real deletion in the browser |

### 3A — Physical keyboard with the OSK visible
- Typing on a physical keyboard goes into the query while focus stays where it is, whether on an OSK key or a result. Nothing is typed twice: fast bursts like "northern" were checked.
- Backspace on a result deletes one character and does not navigate back. Escape still goes back.
- Typing inside the input field is native: the cursor, selection and Ctrl+A all behave normally. Ctrl, Alt and Meta shortcuts are never captured.
- Typed letters keep their case ("NoR" stays "NoR"). The focused OSK key is shown as a light key with an accent ring, scaled 1.06×.
- Right from the last key of any OSK row moves to the first result, or to the result you were on before.

### 1A — Edge cases
| Case | Result |
|---|---|
| Empty library | Tested in the browser on an isolated empty server (see section 0). The backend `test_empty_library` also passes. |
| Missing metadata | Monogram and arc fallback art, an "Uncategorized" genre and "Year unknown" were exercised by the synthetic library. |
| Large collections | A synthetic library of 3,900 files (3,003 movies, 153 shows, 908 episodes, 30+ collections) was used throughout. |
| Reduced motion | Emulated `prefers-reduced-motion: reduce` showed no smooth scrolling and no zoom or entrance animations, and navigation still worked. |
| 1080p / 4K | Tested at 1920×1080 and at 3840×1920 (the test browser's maximum height). The Atlas orbit view now fits one screen without scrolling at both sizes. |

## 3. Bugs found by QA and fixed
1. Discover kept a single memory slot, so nested Back steps and sort or tab changes focused the wrong tile. It now has a memory per result set, applied only on Back.
2. The filter sheet re-mounted on every toggle, so focus reset to Done. Removing a chip or pressing Reset dropped focus entirely. The previous facets are now kept while the new result loads, and focus moves to a stable neighbour.
3. The OSK had no D-pad path to the results. An explicit Right-edge exit was added.
4. Atlas grid mode returned focus to the toolbar after Back. It now returns to the title.
5. Up from Discover's first row jumped to the top nav. It now goes to Sort, or to the selected tab in the Collections list.
6. Sheets opened on Done. They now open on the selected option, or the first option if none is selected.
7. Discover focused "All media" even when another view was selected. It now focuses the selected tab.
- Design fixes: the Atlas orbit view fits within 100 vh, and the inner ring (Movies / TV shows) moved to 9 and 3 o'clock so it no longer covers the genre labels. The grid InfoPanel stays visible while scrolling. The hint text now matches each mode. The top nav is solid on scrolling screens, and the Type filter is hidden inside a collection.

## 4. Test results
| Suite | Result |
|---|---|
| Backend unit (`pytest tests`) | **185 passed** |
| Live API (`MC_LIVE_URL=… pytest tests_live -n 0`) | **30 passed**, run against the standard sample libraries. The large synthetic library was detached for this run because the live tests check exact sample counts, then re-attached. The backend has not changed since, and it was not rerun in the final round because your preview libraries were not to be modified. |
| Browser QA, iteration 9 | About 78% passed; 7 bugs found |
| Browser QA, iteration 10 | 96% passed. The one remaining item, sheet focus when nothing is selected, was then fixed and checked by hand. |
| Browser QA, iteration 11 | 126/129 automated; 4 issues found and fixed |
| Browser QA, iteration 12 (final) | **130/132 automated (98.5%)**; the 1 bug behind both failures was fixed and checked by a scripted browser run |
| Regression (Phase 0, Stages 1–2) | Home filmstrip, movie and show detail, Episode Journey, the player (play, and B to exit) and Settings all passed |

## 5. Performance (preview container, synthetic 3,900-file library)
| Measure | Value |
|---|---|
| Full scan of 3,900 files (no probing) | ~0.4 s |
| `GET /api/discover` (first 120, title sort) | 25 ms, 31 KB |
| `GET /api/discover` (genre filter + added sort) | 35 ms |
| `GET /api/search?q=test` | 8 ms |
| `GET /api/atlas` | 80 ms, 43 KB |
| Discover first grid render, cold, through the preview URL | ~1.6 s |
| Grid DOM size | About 6 rows × 8 cards, plus overscan, at any scroll depth |

## 6. Screenshots
`/app/docs/screenshots/stage3/` (refreshed in iteration 12):
- Discover with movies and filters: `discover_movies_filters_1080p`, `discover_all_1080p`, `discover_all_4k`
- Search with the keyboard and results: `search_osk_results_1080p`, `search_results_4k`
- Atlas overview: `atlas_overview_1080p`, `atlas_overview_4k`, `atlas_grid_overview_1080p`
- Atlas zoomed into a genre: `atlas_cluster_genre_1080p`, `atlas_grid_cluster_1080p`
- Atlas with a selected title: `atlas_selected_title_1080p`
- Empty library: `empty_home_1080p`, `empty_discover_1080p`, `empty_atlas_1080p`, `empty_search_1080p`
- Removed-title recovery: `removed_title_recovery_1080p`
- Other: discover_all_1080p, discover_all_4k, discover_collections_1080p, discover_collection_detail_1080p, discover_nothing_matches_1080p, search_results_1080p, search_results_4k, atlas_overview_1080p, atlas_overview_4k, atlas_cluster_1080p, atlas_grid_overview_1080p, atlas_grid_cluster_1080p.

## 7. Outstanding issues and notes
- The last small CSS tweaks (inner-ring label placement, selected-node scale, "1 title" wording) were made after the screenshots were taken. They are checked in one later scripted screenshot, but the files in the folder do not show them.
- In "More genres" and other sparse orbit levels, unfocused nodes show only initials, so two genres can look alike (Music / Mystery). Only the focused node shows its full name. This is cosmetic.
- At 1080p the focus ring of a large overview node can touch the label above it. It stays readable.
- Re-adding removed files gives them new title ids, so their watch progress is not carried over. This is existing scanner behaviour.
- In the player, the first B press hides the controls and the second exits. This is the intended Stage 2 behaviour.
- Typing while focus is on the top nav (rather than inside the Search page) does not edit the query.

## 8. Tests that could not be performed
- A physical Xbox Series X|S, an Xbox controller over the Gamepad API, and Xbox Edge.
- Native Windows 10/11 runs and browsers on Windows.
- A real 4K TV at viewing distance, and HDR.
- Real NAS or UNC libraries, and the behaviour when a source goes offline mid-session (covered only by a backend unit test).
- A true 3840×2160 viewport. The test browser maxes out at 3840×1920, so full 4K is **not** claimed.

All results above come from browser simulation in a Linux container. No testing was done on actual Windows PCs, Xbox consoles, physical controllers, NAS devices or 4K televisions.
