# Horizon Stage 2 — Detail pages, Episode Journey, Cinematic Player

Date: 2026-06. Scope: Stage 2 only (Stage 3 not started).

## Delivered
- **Detail pages (Option A, full-screen backdrop)** — `src/detail/DetailShell.tsx`, `detail.css`
  - Real fanart fills the screen; title, chips (year, runtime, resolution, container, audio), plot and actions layered on top.
  - Adaptive scrim: `useArtTone` measures luminance of the artwork's text side and deepens the gradient (`--tone`, exposed as `data-tone`).
  - Fallbacks: poster only → blurred poster + framed poster; no art → procedural Horizon arcs (no fake cover art).
  - Movie: Resume (primary, autofocused) + Start over + progress bar with elapsed / total / remaining; "Play again" + Watched mark when finished.
  - Enter: art settles (fade + scale), copy rises. Leave: 170 ms fade/slide on Back (instant with reduced motion).
- **Show page (Option A, Episode Journey)** — `EpisodeJourney.tsx`, `EpisodeCard.tsx`, `nextUp.ts`
  - Season tabs above a horizontal strip; cards show artwork (or code fallback), code, title, runtime (when known), plot, state.
  - States: watched (desaturated + green badge), partial (amber bar + "N s/min left"), unwatched (aurora dot). `data-state` on each card.
  - Navigation: Left/Right between episodes (edge stop); Up → selected season tab; Down from tab → previously selected episode; Left/Right on tabs switch season; LB/RB (PageUp/PageDown) switch season while staying in the strip; per-season selection is remembered.
  - Continue / Up next / Start / Watch again action derived only from real progress.
  - Returning from the player restores the season and the episode card (or the primary action if playback started there).
- **Player (Option A, auto-hiding OSD)** — `pages/Player.tsx`, `player/Controls.tsx`, `player.css`
  - Modes: `hidden` → `osd` (title + minimal timeline + hints) → `expanded` (buttons). `data-mode` on `player-page`.
  - Surface: A/Enter play/pause, Left/Right −/+10 s, Up expands (focus on Play/Pause), Down reveals OSD.
  - Expanded: arrows only move focus; seeking only when the seek bar itself is focused; volume only when the volume control is focused.
  - B/Esc closes expanded controls first, then leaves the player. Fades after ~4 s idle while playing; stays while paused.
  - Elapsed, remaining, total and "Ends at" clock; centre feedback mark for play/pause/seek (static under reduced motion).
- **Card polish**
  - Root cause of label misalignment: long non-wrapping subtitles widened the selected flex slot (`min-width:auto`), making its art taller. Fixed with `min-width:0`; selected art now scales from its bottom edge without lift.
  - Fallback art shows a monogram + kind; the title appears once (in the label).
  - Home: returning from a Stage action (Resume / Details) restores focus to that action.
- **Backend**: `runtime` field on movies/episodes from cached FFprobe duration or player-reported duration (real data only; absent until known).
- **Sample media**: `scripts/make_sample_media.py` now also creates "Northern Survey" (2 seasons, NFO titles/plots, gradient thumbs/fanart/poster) and a fanart for Sample Movie.

## Test results
- Backend pytest: 161 passed + 6 new (`tests/test_detail_stage2.py`).
- Frontend QA (`/app/test_reports/iteration_6.json`): all requested flows passed — detail pages and fallbacks, next-up modes (resume/next/rewatch/start), journey navigation, focus restoration, player modes/seek/pause/collapse/exit, next episode, simulated Gamepad (stubbed `navigator.getGamepads`), Home regression, reduced motion.
- One bug found and fixed during QA (PageUp/PageDown focused the first episode instead of the selected one).
- Post-QA polish re-verified by script: label alignment, 1080 px fit of the show page, Details focus restore.

## Not done / remaining
- **Physical Xbox / Windows hardware testing was NOT performed.** Controller behaviour was verified with a simulated Gamepad API only.
- Episode runtime shows only after a file has been probed (first playback) or played; the scanner does not probe during scans.
- The 4K TV interface scale has not been checked yet.
