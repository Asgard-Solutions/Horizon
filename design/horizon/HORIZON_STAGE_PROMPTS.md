# Horizon follow-up prompts for Emergent

Use these after the initial Stage 1 prompt and after reviewing each real preview. Complete each stage and inspect test results before moving to the next. The style guide and tokens remain the source of truth.

## Stage 2 - Movies, TV, details, and search

Implement the browse-and-find experiences from `HORIZON_DESIGN_SYSTEM_v1.md`. Build real-data Movies and TV views, Movie Details, Show Details, season/episode selection, a working Search view, and a grid/list alternative to the Living Filmstrip. Preserve selected title and browse position when navigating back. Use only metadata that already exists; hide unsupported filters and information. Show honest empty and unreachable-source states. Test long titles, missing artwork, keyboard navigation, focus restoration, and 200+ real titles (when the library has them). Keep all Phase 0 regressions passing. Show the preview and report what is verified.

## Stage 3 - Episode Journey and player

Implement Episode Journey using actual show, season, and episode records. Then reskin the existing player OSD with Horizon tokens and animation guidance. Do not change the underlying playback/streaming implementation without an identified need. Preserve play/pause, seek, volume, fullscreen, Resume/Start Over, and persisted Continue Watching. Hide OSD when appropriate, keep it visible while paused or focused, and do not obscure subtitles with permanent elements. Do not invent episode thumbnails or unavailable media metadata. Run media read-only integrity tests and report results.

## Stage 4 - Sources, controls, and quality pass

Build/refine Library Sources and Settings using the existing source operations and truthful statuses. Make unavailable NAS sources remain indexed, make folder removal explicitly non-destructive to media files, and handle scanning and error cases. Add keyboard and runtime gamepad support with visible spatial focus and tested back behavior. Audit reduced-motion mode, WCAG 2.2 AA contrast, 1366x768 / 1920x1080 / simulated 3840x2160 layouts, and 125%-200% scaling where applicable. Run the actual test suite and show a verification ledger for Linux, Windows, and Xbox, with untested environments clearly marked.

## Optional Stage 5 - Library Atlas exploration

Only after Stages 1-4 are stable, prototype the optional Library Atlas as a second way to explore the same real library. Cluster only by metadata genuinely present. Provide reachable D-pad/keyboard node navigation and a permanent return-to-grid action. Respect reduced motion and avoid rendering all media art at once. Keep it optional if performance or accessibility degrades. Test with a substantial library and show how every title remains reachable without Atlas.
