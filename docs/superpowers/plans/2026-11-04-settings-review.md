# Settings review and corrections

**Goal:** Check every existing Settings tab against its actual data, persistence, navigation and screen layout; correct verified defects.

**Scope:** Libraries and scanning, Playback, Collections and folders, Appearance and scaling, Motion and accessibility, Controller and keyboard, Network and devices, System and diagnostics. The paired-device variant is checked in isolated backend tests.

**Constraints:** Home is approved and locked. Preserve the user's media, sources, progress, configuration and network exposure. Exercise mutations and fault injection only in a loopback-only temporary instance with its own database. Do not turn future-feature labels into claimed working features. Hardware and successful media decoding require separate evidence. Do not commit or push this review automatically.

## Checks and corrections

- [x] Read the live settings and all eight tabs without changing their values.
- [x] Reproduce failed-load and failed-save handling in an isolated instance: Playback displays defaults after GET 503 and silently rolls back PUT 503; Collections and Network go blank after GET 503; Collections POST failure is silent; System hides unavailable diagnostics.
- [x] Correct load/retry and save/pending/error feedback. Keep focus stable while saves and retries finish. Verify successful saves persist across reload, errors retain known saved values, and delayed repeated activation cannot create overlapping writes.
- [x] Verify library add/scan/remove flows using disposable folders, including failed scan startup after successful source registration. Preserve removal cancellation and history behavior.
- [x] Check backend preferences concurrency and media-reader diagnostics using focused regression tests. Resolve any unavailable FFprobe dependency only with authorization for that installation.
- [x] Verify local motion/scaling controls on the temporary origin, restore them afterward, and check 1920x1080, 1280x720, 1024x768 and 390x844 plus automatic 4K scaling. Check keyboard category/panel/back navigation.
- [x] Run frontend build/helper checks and relevant backend tests, perform an independent final review, and record a tab-by-tab result with explicit unavailable-feature and hardware limitations.

## Evidence ledger

Baseline checkpoint: `61be756`. The real instance remains on port 8765. The disposable instance is bound only to 127.0.0.1:8767 and uses `data/settings-review-20261104`; fault injection lives only in ignored development data. Baseline UI values: resume Ask, autoplay On, skip 10 seconds, watched 95%, folder collections On, scale Auto, motion Follow system, LAN Off, no paired devices. FFprobe and physical controller were not detected.

Initial backend baseline: 230 passed, 9 skipped, one existing duration-counter assertion failure. The old assertion failure was a Windows test portability problem: it depended on `/bin/false` as a probe executable. Mocked discovery/probing now tests the intended missing-file behavior independently of the operating system.

Final verification: production build passed; 5 frontend helper tests passed; 251 backend tests passed with 9 skipped and one dependency deprecation warning. All 32 final layout cases passed (eight tabs at four viewport sizes). Additional checks exercised every manual scale, automatic 4K scaling, reduced motion, reload persistence, keyboard navigation, failed loads/saves, cancellation, local source outage/recovery and modal focus. Evidence and tab results are recorded in `docs/HOME_INTEGRATION.md` and `docs/verification/settings-review/`.

Independent final review identified pending saves resetting across tab switches, older diagnostic reads overwriting confirmed network updates, and transient FFprobe validation failures being cached. All three were corrected and their triggers rechecked. Concurrent preference writes are serialized. Test mutations and network-policy tests remained in the temporary loopback instance, which has been stopped.

The user authorized FFprobe installation. App-local FFprobe 9.0.1 was installed from the official Gyan GitHub mirror after archive SHA-256 verification. The normal app reported 25 known lengths, zero pending, zero unreadable and zero offline. Existing playback preferences and LAN Off were preserved. Home source/assets have no changes in this review. This work remains local and uncommitted.

Physical controllers/Xbox, physical NAS outages, real PIN pairing, successful media decoding, large-library and long-running scan behavior remain unverified. Disabled future features remain unavailable and are not counted as working controls.
