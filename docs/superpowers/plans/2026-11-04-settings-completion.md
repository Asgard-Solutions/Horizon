# Settings completion implementation plan

**Goal:** Complete the user-requested collection, theme, accessibility and LAN connection controls.
**Spec:** `docs/superpowers/specs/2026-11-04-settings-completion-design.md`.
**Approach:** Reuse current FastAPI/SQLite, React, CSS tokens, spatial focus, Windows APIs and library setup. No new dependencies or Home redesign.

- [x] Collections: regression tests for additive defaults, On/Off combinations, NFO priority, scan persistence, partial updates and file/history preservation; implement scanner/API and two working toggles.
- [x] Appearance/accessibility: test preference validation/startup/persistence and announcement behavior; implement Light, composable High Contrast, appropriate logos, live announcements and genuine test action; keep existing Dark default.
- [x] Network: native SMB/secure credential adapter, strict input validation, host-only API and useful failure mapping; tests with mocked native calls/private networking, no real shares. Build an actual connect/test form, connection status and single library-management entry. Improve LAN listener/device readiness.
- [x] Integrate/review: production build, helper/backend tests, independent review of concurrency/security/accessibility, then actual UI checks with isolated data at 1920x1080, 1280x720 and 390x844 plus scaling/high contrast. Verify existing subtitle/player and default Home presentation remain intact.
- [x] Document observed results and unavailable hardware/credential tests, capture actual screens, stop test listeners, restore normal local preview and leave changes uncommitted.

Final code verification: build passed; 32 frontend tests passed; 471 backend tests passed, 9 skipped, one dependency warning. All 30 final viewport cases passed, plus 200% compact checks and keyboard category recovery. Reviews closed DNS endpoint substitution by pinning authenticated IO/credentials/library paths to private IPv4, moved SQLite waits off the event loop, verified listener identity, fixed disappearing focus, wrapped the compact announcement test and corrected focus/progress contrast. Real NAS/credential persistence, other physical devices, forced colors and spoken screen-reader output remain explicitly unverified. Normal preview retains loopback binding and saved LAN policy. Evidence and limitations are recorded in `docs/HOME_INTEGRATION.md` and `docs/verification/settings-completion/`.
