# Settings completion: collections, appearance, accessibility and networking

The user requests: an NFO collection option instead of a fixed Always on row; working Light theme; working High Contrast and screen-reader announcements; Kodi-style NAS/SMB and Horizon-device networking. The user explicitly selected NAS/SMB plus Horizon devices, without an internet proxy.

Preserve existing scanning, database, playback, subtitles, sources and history. Preserve the approved Dark Home layout/assets; explicit Light/High Contrast preferences may change its palette and logo without redesigning it. No automatic commits/pushes. Tests that mutate catalog/preferences/network behavior must use disposable data and loopback listeners. Never connect to real shares, save real credentials or widen actual LAN exposure during verification.

## Collections

Add persisted `nfo_collections` alongside `folder_collections`, default On for compatibility. Both switches regroup indexed movie records without rescanning or modifying NFO/media. When enabled, NFO sets retain priority; otherwise enabled folder grouping may apply. Keep parsed metadata even when grouping is off. Partial preference writes preserve the other field and acquire the scan lock before regrouping. Explicit load/save/retry feedback and stable focus remain.

## Appearance and accessibility

Add device-local Dark / Light theme (default Dark) and a High Contrast toggle (default Off), composed with existing scaling/reduced motion. Apply synchronously on startup and persist through reload; settings changes preserve focus. Theme variants cover actual Home, browsing, details, Settings, dialogs and player controls. Use supplied dark-letter logo on light surfaces and white-letter logo on dark/art/player surfaces. Retain default Dark presentation. Ensure readable artwork labels and states, visible borders/focus and useful forced-colors behavior. Check color contrast and actual light/high-contrast screens at TV and compact sizes.

Add device-local screen-reader announcements. Use native accessibility labels and live regions, not synthesized speech. Expose page/navigation context and meaningful action/status updates without duplicate per-focus announcements or polling chatter. Respect the toggle, support a real announcement test, keep focus untouched, and label the control honestly. Verify DOM/accessibility outputs; do not claim actual Narrator/NVDA speech without testing it.

## Network

Separate two real functions: connecting the host to a NAS SMB share, and letting paired devices open Horizon. OS Wi-Fi/Ethernet setup stays with Windows; no non-working proxy/Wi-Fi controls. Show actual host connection addresses/listener and pairing/restart status, refresh controls and clear troubleshooting.

Provide host-only SMB connection form: server, share, optional subfolder, Windows/current account or supplied username/password, Test/Connect, optional Remember credentials. Use native Windows SMB APIs with no drive mapping, no SMB1 enablement, no shell/command-line credentials and no automatic disconnection of pre-existing sessions. Store remembered secrets only in Windows Credential Manager under a Horizon-specific target; never in SQLite, response bodies, logs or plaintext settings. Default no remember. Validate UNC components and private-LAN target. Explicitly report unsupported OS/native API, authentication failure, conflicting Windows sessions and unreachable share. Show connection result/path and browse/add through the existing Libraries & scanning flow; sources remain managed in one place. Native connection setup is session-scoped; credentials/account exposure must be clear.

Existing authenticated paired-device streaming stays intact. A host/port display and live listener/restart readiness must distinguish saved LAN On from a listener that is still loopback-only. Keep PIN/revoke protections. Verification may exercise mocked Windows APIs and disposable fixtures; real NAS credentials/hardware are not available and must be identified as unverified.
