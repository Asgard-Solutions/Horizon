# Movie and TV metadata

**Retired at the user's request on November 4, 2026.** Online scraping, downloads and sidecar export were removed. Other applications supply metadata and artwork. The current scope is documented in `2026-11-04-local-nfo-editor.md`; no token or provider integration remains necessary.

Use TMDB's supported API for both types, including season/episode details. Preserve local NFO fields and artwork as overrides; fill missing fields with cached online data. Store token only in Windows Credential Manager (or deployment environment), never the library database or browser storage. No media folders are written. Exact external IDs take priority; automatic filename matches require an exact title and year with one candidate. Other results go to a review list with manual search/selection. Existing playback IDs, progress, scans, sources and approved Home layout remain intact.

Settings → Libraries & scanning gains provider setup, language, optional fetching after manual scans, explicit fetch/refresh/cancel, and a paged review list. Only indexed movies/shows and their indexed episodes are enriched. Offline/error/unknown matches retain current metadata. Artwork is cached under Horizon's data folder and served through the existing authenticated artwork route. Provider attribution appears in Settings/System. A token is required for live provider verification; mocked provider tests and disposable libraries establish local integration without sending the real library anywhere.

- [x] Add bounded authenticated TMDB client and secure token store with tests (parallel worker).
- [x] Add schema, local override snapshots/IDs, metadata merge and scan persistence with regression tests.
- [x] Add background fetching, conservative matching, review/config/status host-only endpoints and cache serving.
- [x] Add Settings setup/review controls and show actual cast/rating/date on existing detail pages.
- [x] Verify isolated end-to-end matching, refresh/rescan/local override, errors/cancel/offline/artwork/focus/layout and run relevant suites.
- [x] Document setup, verified results and remaining live provider dependency; restart the normal local-only preview without changing its real sources/history/credentials.

Live provider authentication/scraping is not verified: the user's token is unavailable. It must be entered directly in Horizon. The normal library was not rescanned or scraped by this work.
