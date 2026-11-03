# Third-party dependency inventory

Generated from the actual lockfiles on 2026-06 (Python: fresh venv from `backend/requirements-dev.txt` + `pip-licenses`;
Node: `yarn licenses list`). Full machine-generated lists: `docs/licenses/python-packages.md`,
`docs/licenses/node-packages-runtime.txt`, `docs/licenses/node-packages-full.txt`.

No dependency is GPL. No dependency calls a paid or online service. Nothing is downloaded at runtime (fonts are bundled).

## Shipped at runtime — Python server

| Package | Version | License | Obligation when redistributing |
|---|---|---|---|
| fastapi | 0.110.1 | MIT | keep copyright + license text |
| starlette | 0.37.2 | BSD-3-Clause | keep notice; no endorsement use of names |
| uvicorn | 0.25.0 | BSD-3-Clause | keep notice |
| pydantic / pydantic-core | 2.14.1 / 2.50.1 | MIT | keep notice |
| anyio | 4.16.0 | MIT | keep notice |
| click | 8.5.0 | BSD-3-Clause | keep notice |
| h11 | 0.16.0 | MIT | keep notice |
| idna | 3.20 | BSD-3-Clause | keep notice |
| annotated-types | 0.8.0 | MIT | keep notice |
| typing-extensions | 4.16.0 | PSF-2.0 | keep notice |
| typing-inspection | 0.4.4 | MIT | keep notice |
| Python 3.11+ | — | PSF-2.0 | keep notice if bundling the interpreter |
| SQLite (via Python `sqlite3`) | bundled with Python | Public domain | none |

## Shipped at runtime — web UI (compiled into `frontend/dist`)

| Package | Version | License | Obligation |
|---|---|---|---|
| react, react-dom, scheduler | 19.3.1 / 0.28.0 | MIT | keep notice (bundled code keeps license comments) |
| react-router, react-router-dom | 7.18.5 | MIT | keep notice |
| cookie, set-cookie-parser (react-router deps) | 1.1.1 / 2.7.3 | MIT | keep notice |
| lucide-react (icons) | 1.66.0 | ISC | keep notice |
| @fontsource-variable/lexend (Lexend font) | 5.3.0 | SIL OFL 1.1 | fonts may be bundled/redistributed; include OFL text; can't sell the font by itself; reserved font names |
| @fontsource-variable/bricolage-grotesque | 5.3.0 | SIL OFL 1.1 | same as above |

## Build / test only (not shipped)

| Package | Version | License | Note |
|---|---|---|---|
| vite | 8.3.5 | MIT | bundler |
| @vitejs/plugin-react | 6.2.1 | MIT | |
| typescript | 5.9.x | Apache-2.0 | |
| @types/react, @types/react-dom | 19.3.0 | MIT | |
| lightningcss (vite dep, platform binary) | 1.33.0 | **MPL-2.0** | file-level copyleft; only matters if you modify and distribute lightningcss itself. Not shipped. |
| detect-libc | 2.1.2 | Apache-2.0 | |
| source-map-js | 1.2.2 | BSD-3-Clause | |
| pytest, pytest-xdist, execnet, pluggy, iniconfig | 9.2.0 / 3.8.0 / … | MIT | tests |
| httpx, httpcore | 0.28.1 / 1.0.9 | BSD-3-Clause | used by FastAPI TestClient |
| certifi | 2026.10.23 | **MPL-2.0** | pulled in by httpx for tests only; not shipped |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | |
| Pygments | 2.21.0 | BSD-2-Clause | pytest output |
| pip-licenses | latest | MIT | used once to generate this inventory |

## Optional external tool (not part of this repository)

| Tool | License | Notes |
|---|---|---|
| FFprobe (FFmpeg project) | LGPL-2.1+ by default; **GPL-2+/3** if built with `--enable-gpl` (e.g. x264/x265) | Invoked as a separate process; never linked. If you ship `ffprobe.exe` with the product: use an LGPL build, ship its license text and source offer / link to the exact source, and don't restrict reverse engineering of it. Most popular Windows "full" builds are GPL — pick an LGPL "shared"/"lgpl" build for redistribution. Not required for Phase 0 operation. |
| FFmpeg (only `scripts/make_sample_media.py` and one optional test) | as above | Development/test only. Sample media generated from lavfi test patterns contains no third-party content. |

## Development environment (not part of the product)

The Phase 0 code was written inside Emergent's container, which also runs supervisor and a MongoDB service used by the
platform template. **The application does not import, call or require any Emergent package, MongoDB, or Emergent service.**
`backend/.env` in the dev container contains preview-only settings and is excluded from exports.
