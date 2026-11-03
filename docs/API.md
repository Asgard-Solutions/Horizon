# HTTP API (Phase 0)

Base: `http://<host>:8765`. JSON everywhere. Interactive schema: `/api/docs` (OpenAPI at `/api/openapi.json`).
Designed so a future native client (UWP/WinUI on Xbox) can reuse it unchanged.

## Authentication model

| Caller | How it is recognised | Access |
|---|---|---|
| Host PC | client IP is loopback **and** `Host` is `localhost`/`127.0.0.1`/`[::1]` | everything |
| LAN device | private IP, LAN enabled, valid device token | catalog, playback, progress, streaming |
| Anyone else | — | `/api/health`, `/api/auth/status`, `/api/auth/pair` only |

Device token: returned by `POST /api/auth/pair` and set as HttpOnly cookie `mc_device`. Native clients send `Authorization: Bearer <token>`.
All `POST/PUT/PATCH/DELETE` require header `X-MC-Client: <any>` (CSRF defence).

## Endpoints

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/api/health` | any | liveness |
| GET | `/api/auth/status` | any | `{role, lan_enabled, pin_configured, locked_seconds, message}` |
| POST | `/api/auth/pair` | LAN | `{pin, device_name}` → `{token}`; 401 wrong PIN, 429 locked, 403 LAN off |
| POST | `/api/auth/logout` | LAN | revoke own token |
| GET | `/api/home` | viewer | continue watching, recent movies/episodes, shows, counts |
| GET | `/api/movies`, `/api/movies/{id}` | viewer | movies (title, year, plot, filename, poster_url, fanart_url, progress) |
| GET | `/api/shows`, `/api/shows/{id}` | viewer | shows; detail includes seasons → episodes |
| GET | `/api/files/{file_id}/playback` | viewer | stream_url, compatibility verdict, probe summary, saved progress, context (title, next episode) |
| PUT | `/api/progress/{file_id}` | viewer | `{position, duration}` → watched when ≥ 92 % |
| DELETE | `/api/progress/{file_id}` | viewer | clear progress |
| GET/HEAD | `/api/stream/{file_id}` | viewer | file bytes; supports `Range: bytes=a-b`, `bytes=a-`, `bytes=-n`, `If-Range`; 206/416 |
| GET | `/api/art/{kind}/{id}` | viewer | local artwork; kind = movie-poster, movie-fanart, show-poster, show-fanart, season-poster, episode-thumb |
| GET/POST | `/api/libraries` | host | list / add `{path, name?, scan=true}` (validates, rejects overlaps) |
| DELETE | `/api/libraries/{id}` | host | remove from catalog (files untouched) |
| POST | `/api/libraries/{id}/scan` | host | rescan → summary `{files_found, added, updated, unchanged, removed, movies, episodes, errors}` |
| GET | `/api/fs/roots`, `/api/fs/list?path=` | host | folder browser (directories only + video count) |
| GET | `/api/system` | host | version, ffprobe, data dir, LAN state, addresses |
| POST | `/api/settings/pin` | host | `{pin, revoke_devices=true}` |
| POST | `/api/settings/lan` | host | `{enabled}` (requires PIN) |
| GET/DELETE | `/api/devices`, `/api/devices/{id}` | host | list / revoke paired devices |

Media paths are never accepted from clients for streaming: a client asks for a numeric `file_id`; the server resolves the stored path,
re-resolves symlinks and verifies it is still inside a configured library folder before opening it read-only.
