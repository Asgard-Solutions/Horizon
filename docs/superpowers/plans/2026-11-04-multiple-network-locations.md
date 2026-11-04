# Multiple network locations

Keep every distinct NAS/share/full folder path as its own location. Reconnecting a path updates that entry without duplicating it. Existing share-only IDs are normalized lazily from their recorded paths, without altering actual sources or credentials. Sign-in storage remains shared per NAS/share.

- [x] Reproduce same-share folder replacement with regression tests; cover multiple NAS servers/shares, legacy rows, duplicate path normalization, shared credential state and capacity retention.
- [x] Key location metadata by canonical Windows full path and add an explicit Add another location action that clears only the form, including account/password/Remember, then restores server focus.
- [x] Verify adding several locations, persistence, selecting an earlier entry, reset/focus and compact layout in an isolated mock-NAS instance; build and run applicable tests.
- [x] Record results, restore the local app without connecting to real NAS devices or changing existing sources/credentials, and leave changes uncommitted.
