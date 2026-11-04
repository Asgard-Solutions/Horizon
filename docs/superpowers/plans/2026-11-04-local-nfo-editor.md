# Local NFO editing and removal of online metadata

The user cancelled online scraping, downloads and folder-sidecar export: other applications provide NFO/artwork. Keep Horizon's local NFO/artwork scanning, display and FFprobe inspection. Remove TMDB setup, background jobs, network client, credential UI and provider branding. Never fetch metadata online or export artwork.

Add a host-only NFO editor for indexed movies, TV shows and episodes. Read the existing sidecar selected by the scanner's naming rules; never create replacement video/library records. Edit structured title, plot, year/date, genres, cast, rating, external IDs and movie set while retaining unknown XML elements and playback/import fields. Validate size/type, reject unsupported/unsafe XML and symlink/junction/hardlink paths, require a matching content revision before saving, and create a distinct backup before replacing an existing NFO. Derive file paths only from authorized catalog entries. Writes are explicit per-file actions; no automatic edits, downloads, file moves or artwork changes. Update only the selected catalog metadata after save, preserving progress, IDs and technical probe data.

- [x] Remove online implementation and controls; preserve local metadata display.
- [x] Build validated local NFO read/edit/save with backup/conflict/path tests.
- [x] Add paged title selection and movie/show/episode editor with keyboard focus and readable errors.
- [x] Verify on disposable libraries, run applicable tests/build, restore the normal app without editing real NFOs and record limits.
