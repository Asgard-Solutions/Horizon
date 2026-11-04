# Local Subtitles Implementation Plan

> Execute in the existing checkout, preserving the prior Settings audit. No commit or push unless requested.

**Goal:** Discover, select and render local SRT/WebVTT subtitles beside movies and episodes.
**Architecture:** Separate authenticated sidecar discovery/conversion APIs; persisted automatic-display preference; browser text tracks controlled by the existing player.
**Tech Stack:** Existing Python/FastAPI, React/TypeScript and HTML text tracks. No new dependencies.
**Spec:** `docs/superpowers/specs/2026-11-04-local-subtitles-design.md`.

## Constraints and review focus

- Home remains locked; preserve prior local changes and actual media/history/preferences.
- Track IDs cannot grant arbitrary-file access; reject symlink escapes and stale/missing tracks.
- Episode matching, case differences, language tags, UTF encodings, malformed timing and bounded reads need backend tests.
- Selection must disable old tracks, survive seek and not carry into the next video.
- Loading, empty and failed discovery/track reads require truthful UI recovery.
- Dialog focus, Back, player shortcuts and the controls timeout must coexist.

## Tasks

- [x] Backend: first write failing tests for discovery, conversion, access control, stale/offline data and preference validation/persistence. Add `mediacenter/subtitles.py`, API endpoints and the additive `subtitles` preference in `routes_library.py`; update preference default assertion. Run focused tests then full backend suite.
- [x] Frontend: first test deterministic automatic language selection and text-track mode application. Add subtitle types, a focused player subtitle hook/dialog, controls entry and Settings Off/Automatic row. Keep media playback/progress logic unchanged.
- [x] Integration: build and run helper tests, review the change independently, then verify actual cue rendering with disposable playable media and sidecars in a loopback-only database. Exercise Off/Auto/manual selection, seeking, error/retry, episode isolation, keyboard/Back and compact layout.
- [x] Finish: record actual results and limitations, save an actual UI screenshot, stop the test instance, restore the normal app and leave changes uncommitted.

Final evidence: production build passed; 11 frontend helper tests passed; backend suite 319 passed, 9 skipped, one dependency warning. Both independent reviews have no outstanding important findings after correcting retry focus and end-of-episode focus. Actual SRT/VTT rendering, seeking, default/automatic/manual/Off, malformed-file recovery, discovery retry, per-episode isolation, compact layout and Back focus were checked with disposable playable media. Native track listeners corrected an observed missing React load signal. Subtitle positions clear controls and retain bottom margin. Normal app port 8765 is running with existing Ask/On/10s/95% and additive subtitles Off; test port 8767 is stopped. Home source/assets unchanged; no real source/history/preference mutations. Detailed results and format/hardware limitations are in `docs/HOME_INTEGRATION.md`.
