# Testing on a real Windows 10/11 PC

Nothing in this guide has been executed on Windows by the developer — it is the procedure for **you** to run.
Record results in `docs/WINDOWS_ACCEPTANCE_CHECKLIST.md`.

## 1. Prerequisites

| Item | Needed? | Notes |
|---|---|---|
| Windows 10 22H2 or Windows 11, 64-bit (x64) | yes | ARM64 Windows: bundled wheels are x64 only → run `Setup.bat -Online` |
| Python 3.11, 3.12 or 3.13 (64-bit) from python.org | yes | Tick **"Add python.exe to PATH"**. 3.14 wheels are bundled but untested. The Microsoft-Store alias `python` may open the Store: disable it in *Settings → Apps → Advanced app settings → App execution aliases* or install from python.org. |
| Internet | **no** | The release zip contains all Python wheels (`vendor/wheels`) and the built UI (`frontend/dist`). |
| Node.js 20.19+ | only to rebuild the UI | `Setup.bat -BuildUI` (needs internet for `yarn install`) |
| FFprobe | optional | codec inspection. Put `ffprobe.exe` in `tools\` or on PATH, or set `MC_FFPROBE`. Prefer an LGPL build. |
| Admin rights | no | Only for creating a firewall rule (section 6). **Don't run the server "as administrator"** — mapped drives become invisible. |

## 2. Install

1. Extract the zip to a folder you own, e.g. `C:\OpenMediaCenter` (avoid `C:\Program Files` — not writable).
   If Windows marks files as "downloaded from the internet": right-click the zip → Properties → **Unblock** before extracting.
2. Double-click **`Setup.bat`**. It: finds Python 3.11+, creates `backend\.venv`, installs the bundled wheels **offline**,
   and runs the startup checks (`run.py --check`). Expected last line: `Setup complete.`
3. To prove offline installation: disconnect the network (airplane mode) **before** step 2.

## 3. Start

Double-click **`Start.bat`**. It runs the checks (Python, packages, data folder writable, SQLite initialised + integrity check,
UI build present, FFprobe, port free, LAN state), then starts the server and opens `http://127.0.0.1:8765/`.
Stop with Ctrl+C or by closing the window. Change the port: `set MC_PORT=8800` before `Start.bat`, or create `backend\.env` from `backend\.env.example`.

Data lives in `data\mediacenter.sqlite3` (catalog, settings, PIN hash, paired devices, progress). Delete the `data` folder to reset.

## 4. Automated tests

Double-click **`RunTests.bat`** (or `cd backend` → `.venv\Scripts\python -m pytest -v -n 0`). Expected: all tests pass, a few are
**skipped on Windows by design** (symlink tests need admin/Developer Mode; live-server tests need `MC_LIVE_URL`).
Results are also written to `test-results-windows.xml`. Please send this file back with the checklist.

Optional live check against the running server (needs `pip install requests` in the venv, and the sample library added):
`set MC_LIVE_URL=http://127.0.0.1:8765` → `.venv\Scripts\python -m pytest tests_live -n 0`.

Create a synthetic test library (needs `ffmpeg.exe` on PATH): `backend\.venv\Scripts\python scripts\make_sample_media.py D:\OMCTest`.

## 5. NAS, UNC paths and mapped drives

* UNC: type `\\NAS\Media` (or `\\192.168.1.5\Media`) in Settings → Library folders → **Add & scan**. Must open in File Explorer first
  for the same Windows user; Windows handles the SMB credentials (Credential Manager).
* Mapped drive: the folder browser lists `Network drive Z:\ -> \\NAS\Media`. Mapped letters exist per user session and are **not visible
  to elevated (Run as administrator) processes or services** — use the UNC path in those cases.
* The catalog stores the resolved path; a library added as `Z:\` and one added as `\\NAS\Media` are recognised as the same folder (overlap rejected).
* If the NAS is offline during a rescan, the scan reports an error and **removes nothing**.

## 6. LAN access and Windows Firewall troubleshooting

1. Settings → Network access: set PIN → **Turn on LAN access** → close and re-open `Start.bat` (the check line must say `LAN access ON (binds 0.0.0.0)`).
2. Windows Firewall shows a prompt for **python.exe** the first time: allow **Private networks** only, **not** Public.
3. On another device on the same network open the address shown in Settings (e.g. `http://192.168.1.20:8765`).

If the other device can't connect:

| Check | How |
|---|---|
| Server really listening on all interfaces | `netstat -ano | findstr :8765` → must show `0.0.0.0:8765`, not `127.0.0.1:8765` (restart after enabling LAN) |
| Network profile is **Private** | PowerShell: `Get-NetConnectionProfile` → if `Public`: *Settings → Network → (your network) → Private network* or `Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private` (admin) |
| Firewall rule exists | `Get-NetFirewallApplicationFilter -Program *python*` or Windows Security → Firewall → *Allow an app*. Because a venv launches the base interpreter, the prompt/rule may name `...\Python312\python.exe`. |
| Use a port rule instead (admin PowerShell) | `New-NetFirewallRule -DisplayName "Open Media Center (Private)" -Direction Inbound -Protocol TCP -LocalPort 8765 -Profile Private -Action Allow` — remove later with `Remove-NetFirewallRule -DisplayName "Open Media Center (Private)"` |
| Reachability from another Windows PC | `Test-NetConnection 192.168.1.20 -Port 8765` → `TcpTestSucceeded : True` |
| Third-party antivirus firewall | Allow the same port/program there |
| Router "AP/client isolation", guest Wi-Fi, VPN on either device | Disable for the test / use the main network |
| Server says "outside the private local network" | Client IP isn't RFC1918/link-local (e.g. VPN/CGNAT `100.x`) — by design |
| Wrong PIN lockout | 5 wrong PINs = 15 min lock per device; restart the server to clear |

Never forward port 8765 on your router. The app doesn't do it and must not be exposed to the internet.

## 7. Browser notes

Supported: current **Edge** and **Chrome** on Windows (primary), Firefox (MKV/HEVC generally won't play).
The UI build targets "widely available" browser baseline (roughly Chromium 107+, Firefox 104+, Safari 16+).
MP4 H.264/AAC should play everywhere; HEVC needs the Windows HEVC extension + Edge; MKV depends on the browser; AVI never plays (explained in the UI).

## 8. Collecting diagnostics for a bug report

* The `Start.bat` window output (copy all), `test-results-windows.xml`, `python --version`, Windows version (`winver`),
* Settings → System section (version, FFprobe, data folder), and for playback issues the "technical details" shown by the player.
