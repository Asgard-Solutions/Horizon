# Windows acceptance checklist (Phase 0.5)

Tester: ________  Date: ________  Windows version: ________  Python: ________  Browser(s): ________

Status column: **P** pass · **F** fail (describe) · **N/A**. Nothing here has been run on Windows by the developer — all rows start empty.

## A. Installation & startup
| # | Step | Expected | Status / notes |
|---|---|---|---|
| A1 | Extract zip to `C:\OpenMediaCenter`, network **disconnected**, run `Setup.bat` | Completes, no download, ends with "Setup complete" | |
| A2 | Run `Start.bat` | All checks OK (FFprobe may be WARN), browser opens UI | |
| A3 | `data\mediacenter.sqlite3` created | File exists after first start | |
| A4 | Stop (Ctrl+C) and start again | Library and settings still present | |
| A5 | Start a second copy | Check reports port in use and stops (no crash) | |
| A6 | `RunTests.bat` | All tests pass (some skipped), `test-results-windows.xml` written | |
| A7 | Whole session with network disconnected | Everything below works offline | |

## B. Folders & scanning
| # | Step | Expected | Status / notes |
|---|---|---|---|
| B1 | Folder browser shows drive letters with type (fixed/removable/network) | Drives listed; mapped drives show `-> \\server\share` | |
| B2 | Add a local folder via browser (e.g. `D:\Movies`) | Scan summary shows correct counts | |
| B3 | Type path with forward slashes `D:/Movies` or just `D:` | Accepted and normalised | |
| B4 | Type relative path `Movies` / drive-relative `C:Movies` / `\\NAS` | Clear error, nothing added | |
| B5 | Add a UNC share `\\NAS\Media` | Scans; titles appear | |
| B6 | Add the same share via its mapped letter `Z:\` | Rejected as already in library / overlapping | |
| B7 | Run server elevated, try mapped drive | Error message explains mapped drives & suggests UNC | |
| B8 | Folder with no read permission (remove your user's Read ACL on a test folder) | Error "Access denied" or scan error listed; app keeps running | |
| B9 | Movies named `Title (2024).mp4`, `Title.2019.1080p.mkv`, folder-per-movie with `poster.jpg` | Correct title/year/poster | |
| B10 | TV `Show\Season 01\Show - S01E02.mkv`, flat `Show.S02E05.mp4` | Show → seasons → episodes correct | |
| B11 | Rescan 3× | No duplicates; "0 new" | |
| B12 | Delete/rename a file in Explorer, rescan | Removed/updated in catalog | |
| B13 | Disconnect NAS, rescan | Error shown, **nothing removed** | |
| B14 | Folder containing a junction (`mklink /J inside C:\Windows`) | Junction not followed; no Windows files catalogued | |
| B15 | Long paths (> 260 chars) | Either scanned or reported as error (note which; depends on LongPathsEnabled) | |

## C. Read-only guarantee
| # | Step | Expected | Status / notes |
|---|---|---|---|
| C1 | Before scanning: `Get-ChildItem D:\TestMedia -Recurse -File | Get-FileHash | Export-Csv before.csv` | — | |
| C2 | Scan, play, rescan, remove library | — | |
| C3 | Repeat hash → `after.csv`; `Compare-Object (Import-Csv before.csv) (Import-Csv after.csv) -Property Hash,Path` | No differences; no new files (no `.nfo`, thumbnails, `Thumbs.db` created by the app) | |
| C4 | Mark a test folder Read-only/deny Write ACL for your user | Scanning and playback still work | |

## D. Playback & resume (Edge and Chrome)
| # | Step | Expected | Status / notes |
|---|---|---|---|
| D1 | Play `Sample Movie (2024).mp4` | Starts, picture + sound | |
| D2 | Pause/play (Enter, Space, click) | Works | |
| D3 | Seek with ←/→ on seek bar and by clicking | Jumps without restarting download | |
| D4 | Volume ←/→ on volume control, M mute | Works | |
| D5 | Fullscreen (F, button, double-click) | Fullscreen and back | |
| D6 | Exit at ~40 s, reopen | Resume prompt/button at ~40 s; Continue watching row on Home | |
| D7 | Restart server, reopen | Resume position kept | |
| D8 | Play to the end | Marked watched, leaves Continue watching | |
| D9 | AVI file | "Can't be played here" panel with reason; Try anyway → error panel, no fake playback | |
| D10 | MKV (H.264/AAC) in Edge/Chrome/Firefox | Note per browser: plays / explained error | |
| D11 | HEVC MP4 (with/without HEVC extension) | Note behaviour | |
| D12 | 4K or high-bitrate file from NAS over Wi-Fi and Ethernet | Note stutter / seek latency | |

## E. Keyboard navigation (no mouse)
| # | Step | Expected | Status / notes |
|---|---|---|---|
| E1 | Home → Movies → detail → Play → Exit using only arrows/Enter/Esc | Possible; focus ring always visible | |
| E2 | TV show: season tabs, episode list, next episode | Works | |
| E3 | Settings: type path, Browse dialog, Remove confirm dialog | All reachable; Esc closes dialogs | |
| E4 | Xbox/USB controller on the PC in Edge (D-pad, A, B) | Moves focus / activates / back (record) | |

## F. LAN pairing & security
| # | Step | Expected | Status / notes |
|---|---|---|---|
| F1 | Fresh install: from another device open `http://<pc-ip>:8765` | Not reachable (server bound to 127.0.0.1) | |
| F2 | Set PIN `12345678` | Rejected (sequence) | |
| F3 | Set an 8+ digit PIN, enable LAN, restart, allow firewall **Private** | Check line says LAN ON | |
| F4 | Other device: page loads, shows PIN keypad | Yes | |
| F5 | 5 wrong PINs | Locked for 15 min with message | |
| F6 | Correct PIN on another device | Library visible, video plays & seeks | |
| F7 | On the device open Settings | "This device" only; no folders/network settings | |
| F8 | From the device try `http://<pc-ip>:8765/api/fs/roots` and `/api/libraries` | 403 | |
| F9 | Host: revoke the device | Device gets the pairing screen again | |
| F10 | Host: change PIN | All devices must pair again | |
| F11 | Turn LAN off + restart | Other device can't connect at all | |
| F12 | Network profile set to Public | Device can't connect (firewall) — expected | |

## G. Browser compatibility on the host
| Browser / version | UI loads | Keyboard nav | MP4 plays | MKV | Notes |
|---|---|---|---|---|---|
| Edge | | | | | |
| Chrome | | | | | |
| Firefox | | | | | |

Sign-off: all of A, B1–B13, C, D1–D9, E1–E3, F1–F11 pass → Phase 0.5 accepted on Windows.
