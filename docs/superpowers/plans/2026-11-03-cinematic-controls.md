# Cinematic controls implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this single styling task; steps use checkbox syntax.

**Goal:** Apply the user's selected cinematic treatment to existing Home cards and shared buttons.

**Architecture:** Add decorative icons inside existing actions and style their surfaces. Keep all event handling, routes, dimensions and library data intact.

**Tech stack:** Existing React, TypeScript, lucide-react and CSS.

**Spec:** `docs/superpowers/specs/2026-11-03-cinematic-controls-design.md`.

## Constraints and review focus

Work in the current dedicated local checkout. No commit or push. Preserve the supplied PNGs, original background, focus IDs and navigation attributes. No new dependencies, media records or artwork. Verify icon/text overlap, visible keyboard focus, compact/manual-scale layouts, reduced motion and utility access. This reversible visual change uses direct browser checks rather than tests that mirror CSS.

## Task 1: Card and button presentation

- [x] Save a task-local baseline of the five changed source/theme files under ignored `data/`.
- [x] Add decorative card/action/utility icons in `frontend/src/home/HomeScreen.tsx` and `frontend/src/components/PrimaryNav.tsx`.
- [x] Add matching Home accent/panel tokens in `frontend/src/theme/horizon.tokens.json` and `horizon.theme.css`.
- [x] Apply static depth, edges, horizon details, distinct focus and responsive icon positions in `frontend/src/home/hub.css`.
- [x] Run `yarn build` and `yarn test`; verify the actual app and save screenshots.
- [x] Review the styling diff, record observed checks in `docs/HOME_INTEGRATION.md`, and show the actual result.

Execution: user selected the cinematic option. A fresh review found Discover text/icon overlap in the compact three-column layout; reproduced at 800x600, then fixed by placing compact destination icons above titles. Read-only browser measurements confirmed all three titles fit and no longer overlap their icons. Keyboard TV Search retained `media=tv`; Escape restored the Search card, then the TV selector. At 390x844, both media labels avoid their icons and both utilities fit. At 200% app scaling, labels avoid icons and utilities remain reachable; with Reduced motion selected, actual computed card transition duration is 0s. Auto scale and Follow system motion were restored afterward. Source/library data was read only. Forced-colors rules received a static review, without browser emulation.

Final verification: `yarn build` passed after the last CSS adjustment; `yarn test` passed all 5 existing helper tests. Actual 1920x1080 Home and Movies captures are saved under `docs/verification/cinematic-controls/`. The temporary viewport override was reset and the agent's test tab closed. The user's existing Sources tab was left in place. No commits or remote writes were made.
