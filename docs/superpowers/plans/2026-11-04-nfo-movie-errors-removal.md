# Movie NFO errors and recoverable removal

The user reports movie NFO errors while TV editing works, and requests deleting unwanted or duplicate NFO files. Reproduce the movie failure without writing to their library. Existing movie/show/episode editors and approved Home layout remain in place.

Removal applies only to the existing catalog-selected NFO shown on screen. A confirmation names that file and explains that unsaved edits will be discarded. Rename the file to a unique recovery `.bak` beside it, preserving its original bytes/security and leaving media, artwork and indexed titles in place. Require current revision, catalog identity, host/CSRF authorization and the scan lock. Do not overwrite an earlier recovery file. Display the recovery location and explain that a manual rescan refreshes cached catalog metadata. Unsupported XML may still be removed once its safe path/revision can be inspected. No real user file is saved or removed during verification.

- [x] Read actual errors, compare movie/show selection and validation, reproduce the failure on disposable data, then fix its cause.
- [x] Add guarded NFO inspection/removal with backup, stale-file, path, authorization and failure tests.
- [x] Add Delete NFO confirmation and success/error/focus handling for movies, shows and episodes.
- [x] Verify disposable UI workflows, run relevant tests/build, record limitations and restore the normal preview.

The user confirmed movie editing was working again; no additional movie parsing fix was required. Review-driven removal changes pin the verified Windows file through a handle rename, use Linux atomic no-replace rename, and handle long recovery paths. Actual deletion testing used owned disposable files only.
