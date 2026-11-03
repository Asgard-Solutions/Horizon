# Xbox Series X|S — technical feasibility report (Phase 0)

**Bottom line:** No Xbox hardware was available or used. **Nothing in this report has been tested on an Xbox.**
The Windows server and its API are designed to be reused by an Xbox client, and the web UI was built so it *can* be tried in
the Xbox's Microsoft Edge browser over the LAN. A native Xbox app is feasible on paper but requires Microsoft developer tooling
and a Microsoft developer account, which are **not authorized** for this project yet → **blocker recorded below**.

Legend: **[DOC]** = stated in official Microsoft documentation (links below, read 2026-06). **[TESTED-DEV]** = verified by
running code in the development environment (Linux container, Chromium). **[ASSUMPTION]** = not verified; needs real hardware.

## 1. What Phase 0 delivers toward Xbox

| Item | Status |
|---|---|
| Server reachable from another device on the private LAN, off by default, PIN pairing | **[TESTED-DEV]** — server bound to `0.0.0.0` only after enabling LAN; a request from a non-loopback interface (10.x address) got 401 until paired, wrong PIN was rejected with attempts counter, correct PIN returned a device token, catalog + `206` range streaming worked with the token, host-only admin endpoints returned 403. Automated tests also cover lockout, revoke, PIN change, public-IP refusal. |
| Catalog / streaming API reusable by a native client | **[TESTED-DEV]** — JSON API, numeric IDs, `Authorization: Bearer` token supported (test `test_bearer_token_for_native_clients`). See `docs/API.md`. |
| 10-foot UI: large focus targets, arrow/Enter/Escape navigation | **[TESTED-DEV]** with keyboard in Chromium. |
| Gamepad (W3C Gamepad API, standard mapping: D-pad 12–15, A=0, B=1, left stick) | Implemented. **[ASSUMPTION]** — not tested with any controller. |
| H.264/AAC MP4 playback in a Chromium browser incl. seek & resume | **[TESTED-DEV]** in headless Chromium. On Xbox Edge: **[ASSUMPTION]**. |

## 2. Xbox Edge browser as an initial LAN playback test (not proof of native compatibility)

* Edge on Xbox Series X|S is Chromium-based. Microsoft's consumer guide describes controller/cursor use in Edge on Xbox. **[DOC]** (consumer page, not a developer spec)
* Edge on Xbox has a *browsing controls* vs *game controls* mode toggle (hold Menu). In browsing mode the controller drives a mouse-like cursor;
  pages receive Gamepad API input when the mode lets them. **[ASSUMPTION]** — reported by third parties, not by an official developer document I could find.
  The UI therefore works with **both** a cursor (large click targets) and Gamepad API polling.
* Which video codecs Edge on Xbox decodes in `<video>` is **not documented officially** for the browser. The UWP media table (section 3) is for apps, not for Edge.
  Expected (unverified): H.264/AAC MP4 plays; HEVC may play; MKV is uncertain; AVI will not.
* Plain HTTP on the LAN: Edge may show "Not secure" but should load a private-IP site. Some browser features (e.g. fullscreen) work on HTTP; **[ASSUMPTION]**.

**Hardware test plan for the Edge browser** (requires a Series X|S on the same LAN):
1. Host PC: set PIN, enable LAN, restart `start.bat`, allow python.exe on *Private* networks in Windows Firewall.
2. Xbox: open Edge → `http://<host-ip>:8765` → pairing keypad with the controller → library appears.
3. Record: D-pad focus movement (game-controls mode vs browsing mode), A/B behaviour, `Sample Movie (2024).mp4` play/pause/seek/resume, fullscreen,
   the MKV sample, the AVI sample showing the "can't be played here" panel, 1080p and 4K HEVC files from the user's library, AC-3/E-AC-3/DTS audio.
4. Record whether the screen saver/auto-dim interrupts playback (there is no wake-lock in Phase 0).

## 3. Native Xbox app — requirements from official documentation

| Topic | Finding | Source |
|---|---|---|
| App model | Non-game apps on Xbox are UWP apps. Recommended media-app architectures: (a) thin C# UWP app hosting a website in a full-screen **WebView** (WebView1/EdgeHTML-based), or (b) native UWP (XAML + C#/C++/WinRT) using **MediaPlayer / MediaPlayerElement**. **WebView2 is not supported on Xbox.** | [DOC] application-architecture |
| Codecs (UWP apps) | H.264 up to 1080p60 (High profile); HEVC up to 2160p60 Main/Main10 (all consoles except original Xbox One); VP9 up to 2160p60 (One X, Series X|S); VC-1/MPEG-2/MPEG-4 up to 1080p60. Streaming: MPEG-DASH (recommended), HLS, Smooth; MSE via WebView. DRM: PlayReady only. | [DOC] supported-technologies |
| HEVC | Requires declaring the `hevcPlayback` capability (restricted) in the app manifest. | [DOC] hevc-xbox |
| Audio passthrough | AC-3 / E-AC-3 / DTS support depends on decoders and the audio endpoint; query support at runtime. | [DOC] supported play type strings |
| File system | `broadFileSystemAccess` **not supported**; `FolderPicker` not supported; removable storage not supported (per the limitations list). A native app therefore can't simply browse a NAS like on PC → **streaming from the Windows server (this project's design) is the realistic path.** | [DOC] uwp-limitations-on-xbox |
| Network discovery | `KnownFolders.MediaServerDevices` (DLNA) exists; known issue: query returns empty until `ContentsChanged` fires. Not used in Phase 0. | [DOC] known-issues |
| Resources | Apps (not games) get a limited share: ~1 GB foreground memory, shared CPU cores, ~45% GPU (limits not enforced while debugging). | [DOC] system resource allocation (read via a GitHub mirror of the Microsoft docs; re-check the current page) |
| Input | Gamepad via `Windows.Gaming.Input` or XAML focus navigation (XY focus); apps must be fully usable with a controller, "mouse mode" is opt-in. | **[ASSUMPTION]** from prior knowledge of Microsoft's Xbox UWP design guidance — page not re-read for this report |
| Dev tooling | Windows PC + Visual Studio with UWP workload, console switched to **Developer Mode** via the *Xbox Dev Mode* app, activated against a **Partner Center developer account**; max 3 consoles per account. Apps must target x64. | [DOC] getting-started, Dev Mode activation agreement |
| Account cost | Microsoft states individual Store developer registration is currently free (company accounts are paid); identity verification required. Xbox Dev Mode needs that account. | [DOC] open-a-developer-account |
| Publishing | Store publication of apps requires Partner Center certification; UWP **games** are no longer accepted (not relevant: this is an app). | [DOC] FAQ / architecture |

## 4. Blocker (recorded, not bypassed)

Building, packaging, sideloading or debugging a native Xbox app needs **Visual Studio + Windows SDK (proprietary Microsoft tools), a Microsoft
Partner Center account, and a console in Developer Mode**. These were *not* introduced, per project rule 9. No Xbox package, manifest or
"Xbox-styled" mockup was produced. Phase 0 makes no claim of Xbox compatibility.

Licensing note for later: the UWP SDK and Visual Studio Community are free-of-charge but proprietary; an Xbox client would necessarily depend on
them (the app itself can still be MIT). The MIT server remains independent of Microsoft tooling.

## 5. What needs real hardware vs. what can be done without it

| Can be done without Xbox hardware | Needs a physical Series X|S |
|---|---|
| Server, API, streaming, auth (done, tested) | Edge-on-Xbox: page load, pairing, focus/controller behaviour |
| UI keyboard navigation (done, tested) | Actual codec/container support of Edge-on-Xbox `<video>` |
| Gamepad API on a Windows PC with an Xbox controller in Edge/Chrome (not yet done — easy next step) | Fullscreen, TV overscan/safe area, HDR, 4K output |
| UWP prototype on Windows desktop (UWP runs on PC) — only once Microsoft tools are authorized | Native UWP app in Dev Mode: memory limits, `hevcPlayback`, audio passthrough to AVR |
| Codec matrix checks with `MediaPlayer` on Windows (approximation only) | Performance of large libraries, sleep/screensaver behaviour, network throughput over Wi-Fi |

## 6. Recommendation

1. Phase 1 quick win: test this LAN web UI in Edge on a real Series X|S (plan in section 2). Cost: none; tools: none.
2. If Edge playback is adequate for H.264/HEVC MP4, a native app can start as the documented **thin UWP WebView shell** around the same UI,
   then move playback to `MediaPlayerElement` for codec/audio coverage (MKV, AC-3/DTS passthrough) the browser lacks.
3. Get explicit authorization for Visual Studio + Windows SDK + a Partner Center account before any native work.

## Sources (official Microsoft documentation)

* Xbox app architecture — https://learn.microsoft.com/en-us/windows/uwp/apps-for-xbox/application-architecture
* Supported technologies (codecs, streaming, DRM) — https://learn.microsoft.com/en-us/windows/uwp/apps-for-xbox/supported-technologies
* HEVC on Xbox — https://learn.microsoft.com/en-us/windows/uwp/audio-video-camera/hevc-xbox
* UWP features not supported on Xbox — https://learn.microsoft.com/en-us/uwp/extension-sdks/uwp-limitations-on-xbox
* Known issues (UWP on Xbox) — https://learn.microsoft.com/en-us/windows/uwp/xbox-apps/known-issues
* Getting started / Dev Mode — https://learn.microsoft.com/en-us/windows/uwp/xbox-apps/getting-started
* Xbox Dev Mode activation agreement — https://learn.microsoft.com/en-us/legal/windows/agreements/xbox-one-developer-mode-activation
* Open a developer account — https://learn.microsoft.com/en-us/windows/apps/publish/partner-center/open-a-developer-account
* Supported play-type strings / audio endpoint queries — https://learn.microsoft.com/en-us/windows/uwp/audio-video-camera/supported-play-type-strings
* Consumer guide: Edge on Xbox — https://www.microsoft.com/en-us/edge/learning-center/how-to-use-microsoft-edge-on-xbox
