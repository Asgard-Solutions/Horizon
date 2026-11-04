# Local subtitle files

The user requests working local subtitles beside movie and TV episode videos, completing the existing Playback placeholder. This uses the existing FastAPI/React player and browser text tracks; no downloads, extraction, transcoding or new dependencies are needed. Home remains locked. Existing uncommitted Settings work must be preserved.

Discover matching `.srt` and `.vtt` files in the video's own folder when playback opens, without a rescan or database migration. Accept the exact video stem, or that stem plus dot-separated language/variant tags (for example `Movie.en.srt`, `Show.S01E01.en.forced.vtt`). Do not offer another episode's subtitles. Use language/variant labels plus filename to disambiguate. Files remain read-only. Embedded/image/ASS subtitles and recursive subtitle folders are outside this change.

Serve subtitles through authenticated, file-scoped API endpoints. IDs are opaque filename hashes; clients never supply paths. Revalidate media/library confinement and the selected sidecar on each read, reject links escaping the media folder/library, bound reads, handle unreachable folders and malformed tracks honestly. Convert SRT into UTF-8 WebVTT in memory, keeping timing and safe text, never modifying originals.

`GET /api/files/{id}/subtitles` returns `{tracks: [{id, label, language, url}]}`. Missing/unreachable folders return an actionable error; an accessible folder without matches returns an empty list. `GET /api/files/{id}/subtitles/{track_id}` returns `text/vtt` or an error. Both retain existing viewer authentication. Discovery is separate from playback metadata so a sidecar problem cannot prevent the video from starting.

Playback preferences add `subtitles: "off" | "auto"` (default `off`, compatible with existing saved preferences). Playback settings replace the Coming later row with Off/Automatic and clear naming guidance. Manual per-video selection remains available regardless of this default. Auto prefers browser-language matches, then untagged, then the first deterministic track. Runtime selection is per video and resets on next episode.

The player provides a controller/keyboard-accessible Subtitles dialog with Off, real available tracks, loading, empty and Retry states. Browser text tracks render cues and stay synchronized through seeks. Track errors show retryable feedback without stopping the video or clearing progress. Escape/B closes the dialog and restores the opener; controls must not auto-hide while it is open.

Implementation choices above are the builder's defaults within the user's request. The alternatives (only displaying existing metadata, or adding a transcoding/extraction service) would not deliver local SRT/VTT support within the current player. All writes and successful playback tests use an isolated loopback instance with disposable media, never the user's sources or history.
