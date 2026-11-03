# Automated test results (actual runs)

Environment: Linux dev container (Emergent workspace), Python 3.11.18, fresh venv from `backend/requirements-dev.txt` (no Emergent packages), FFmpeg/FFprobe 5.x from Debian (dev-only). Run date: 2026-06.
Windows execution of the suite has **not** been performed yet (no Windows machine available here).

## Backend unit/integration suite — `cd backend && python -m pytest -v`

**Result: 105 passed, 0 failed** (+16 live-server checks skipped because `MC_LIVE_URL` was not set — they are run separately below).
Also re-run from the exported zip in a clean directory: 105 passed.

```
PASSED tests/test_parser.py::test_clean_name 
PASSED tests/test_parser.py::test_episode_without_show_name_at_root_is_rejected 
PASSED tests/test_parser.py::test_is_video[.mp4-False] 
PASSED tests/test_parser.py::test_is_video[a.MKV-True] 
PASSED tests/test_parser.py::test_is_video[a.avi-True] 
PASSED tests/test_parser.py::test_is_video[a.m4v-True] 
PASSED tests/test_parser.py::test_is_video[a.mov-True] 
PASSED tests/test_parser.py::test_is_video[a.mp4-True] 
PASSED tests/test_parser.py::test_is_video[a.nfo-False] 
PASSED tests/test_parser.py::test_is_video[a.txt-False] 
PASSED tests/test_parser.py::test_is_video[mp4-False] 
PASSED tests/test_parser.py::test_is_video[poster.jpg-False] 
PASSED tests/test_parser.py::test_multi_episode 
PASSED tests/test_parser.py::test_not_episode[1920x1080 demo.mp4] 
PASSED tests/test_parser.py::test_not_episode[Movie.2010.1080p.mkv] 
PASSED tests/test_parser.py::test_not_episode[Sample Movie (2024).mp4] 
PASSED tests/test_parser.py::test_not_episode[Season Finale.mp4] 
PASSED tests/test_parser.py::test_parse_episode[Episode S01E04.mkv-dirs5-Folder Show-1-4-None] 
PASSED tests/test_parser.py::test_parse_episode[Other.Series.S02E05.720p.mp4-dirs7-Other Series-2-5-None] 
PASSED tests/test_parser.py::test_parse_episode[S01E03.mkv-dirs4-Folder Show-1-3-None] 
PASSED tests/test_parser.py::test_parse_episode[Sample Show - S01E02.mkv-dirs0-Sample Show-1-2-None] 
PASSED tests/test_parser.py::test_parse_episode[Sample Show - S02E01 - The Return.m4v-dirs3-Sample Show-2-1-The Return] 
PASSED tests/test_parser.py::test_parse_episode[Sample.Show.S01E02.720p.HDTV.x264.mkv-dirs1-Sample Show-1-2-None] 
PASSED tests/test_parser.py::test_parse_episode[Show 1x05 Title.avi-dirs6-Show-1-5-Title] 
PASSED tests/test_parser.py::test_parse_episode[sample show s10e110.mp4-dirs2-sample show-10-110-None] 
PASSED tests/test_parser.py::test_parse_episode_show_year_from_folder 
PASSED tests/test_parser.py::test_parse_movie[2001 A Space Odyssey (1968).mkv-dirs3-2001 A Space Odyssey-1968] 
PASSED tests/test_parser.py::test_parse_movie[Another_Film_[2019].m4v-dirs2-Another Film-2019] 
PASSED tests/test_parser.py::test_parse_movie[Blade Runner 2049 (2017).mp4-dirs4-Blade Runner 2049-2017] 
PASSED tests/test_parser.py::test_parse_movie[Great Film (1999).mkv-dirs8-Great Film-1999] 
PASSED tests/test_parser.py::test_parse_movie[Sample Movie (2024).mp4-dirs0-Sample Movie-2024] 
PASSED tests/test_parser.py::test_parse_movie[Sample.Movie.2024.1080p.BluRay.x264.mkv-dirs1-Sample Movie-2024] 
PASSED tests/test_parser.py::test_parse_movie[Some.Movie.720p.WEB-DL.mp4-dirs6-Some Movie-None] 
PASSED tests/test_parser.py::test_parse_movie[Untitled Home Video.avi-dirs5-Untitled Home Video-None] 
PASSED tests/test_parser.py::test_parse_movie[movie.mp4-dirs7-Great Film-1999] 
PASSED tests/test_parser.py::test_season_dir[S03-3] 
PASSED tests/test_parser.py::test_season_dir[Season 1-1] 
PASSED tests/test_parser.py::test_season_dir[Specials-None] 
PASSED tests/test_parser.py::test_season_dir[Staffel 4-4] 
PASSED tests/test_parser.py::test_season_dir[season_02-2] 
PASSED tests/test_probe.py::test_10bit_h264_unsupported 
PASSED tests/test_probe.py::test_avi_is_unsupported_without_probe 
PASSED tests/test_probe.py::test_hevc_and_dolby_audio_are_maybe 
PASSED tests/test_probe.py::test_mkv_is_maybe 
PASSED tests/test_probe.py::test_mp4_h264_aac_supported 
PASSED tests/test_probe.py::test_mp4_mpeg4_video_unsupported 
PASSED tests/test_probe.py::test_mp4_without_probe_is_unknown 
PASSED tests/test_probe.py::test_real_ffprobe 
PASSED tests/test_scanner.py::test_adding_same_or_nested_folder_is_rejected 
PASSED tests/test_scanner.py::test_invalid_paths_are_rejected 
PASSED tests/test_scanner.py::test_progress_save_and_restore 
PASSED tests/test_scanner.py::test_progress_survives_library_remove_and_readd 
PASSED tests/test_scanner.py::test_remove_library_clears_catalog_only 
PASSED tests/test_scanner.py::test_rescan_does_not_duplicate 
PASSED tests/test_scanner.py::test_rescan_picks_up_removed_and_new_files 
PASSED tests/test_scanner.py::test_scan_builds_library_structure 
PASSED tests/test_scanner.py::test_scanning_never_modifies_source_files 
PASSED tests/test_scanner.py::test_unreachable_folder_keeps_catalog 
PASSED tests/test_security.py::test_artwork_must_be_an_image 
PASSED tests/test_security.py::test_artwork_outside_library_is_forbidden 
PASSED tests/test_security.py::test_bearer_token_for_native_clients 
PASSED tests/test_security.py::test_disabling_lan_blocks_paired_devices 
PASSED tests/test_security.py::test_dns_rebinding_host_header_is_not_trusted 
PASSED tests/test_security.py::test_host_has_full_access 
PASSED tests/test_security.py::test_lan_cannot_be_enabled_without_pin 
PASSED tests/test_security.py::test_lan_is_disabled_by_default 
PASSED tests/test_security.py::test_pairing_flow_and_device_access 
PASSED tests/test_security.py::test_path_traversal_inside_db_is_forbidden 
PASSED tests/test_security.py::test_pin_is_not_stored_in_plain_text 
PASSED tests/test_security.py::test_pin_rules[11111111-False] 
PASSED tests/test_security.py::test_pin_rules[1234567-False] 
PASSED tests/test_security.py::test_pin_rules[12345678-False] 
PASSED tests/test_security.py::test_pin_rules[48151623-True] 
PASSED tests/test_security.py::test_pin_rules[4815162342-True] 
PASSED tests/test_security.py::test_pin_rules[87654321-False] 
PASSED tests/test_security.py::test_pin_rules[abcdefgh-False] 
PASSED tests/test_security.py::test_public_ip_always_refused 
PASSED tests/test_security.py::test_removed_library_files_are_not_served 
PASSED tests/test_security.py::test_revoke_and_pin_change_invalidate_devices 
PASSED tests/test_security.py::test_state_changes_require_client_header 
PASSED tests/test_security.py::test_stream_outside_library_is_forbidden 
PASSED tests/test_security.py::test_symlink_escape_is_forbidden 
PASSED tests/test_security.py::test_wrong_pin_lockout 
PASSED tests/test_streaming.py::test_full_response 
PASSED tests/test_streaming.py::test_head_request 
PASSED tests/test_streaming.py::test_if_range_mismatch_returns_full_file 
PASSED tests/test_streaming.py::test_missing_file_returns_404 
PASSED tests/test_streaming.py::test_parse_range[None-100-None] 
PASSED tests/test_streaming.py::test_parse_range[bytes=--100-None] 
PASSED tests/test_streaming.py::test_parse_range[bytes=-10-100-expected3] 
PASSED tests/test_streaming.py::test_parse_range[bytes=-500-100-expected4] 
PASSED tests/test_streaming.py::test_parse_range[bytes=0-1, 5-6-100-expected7] 
PASSED tests/test_streaming.py::test_parse_range[bytes=0-9-100-expected1] 
PASSED tests/test_streaming.py::test_parse_range[bytes=10--100-expected2] 
PASSED tests/test_streaming.py::test_parse_range[bytes=5-5-100-expected6] 
PASSED tests/test_streaming.py::test_parse_range[bytes=90-500-100-expected5] 
PASSED tests/test_streaming.py::test_parse_range[bytes=abc-100-None] 
PASSED tests/test_streaming.py::test_parse_range[items=0-9-100-None] 
PASSED tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=-0-100] 
PASSED tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=0--0] 
PASSED tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=100--100] 
PASSED tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=50-10-100] 
PASSED tests/test_streaming.py::test_partial_responses 
PASSED tests/test_streaming.py::test_unknown_file_id 
PASSED tests/test_streaming.py::test_unsatisfiable_range 
```

## Live-server API checks — `MC_LIVE_URL=<preview url> python -m pytest tests_live -n 0`

**Result: 16 passed** against the running dev server with the synthetic sample library.

## Frontend

* `yarn typecheck` (tsc --noEmit): passed. `yarn build`: passed.
* End-to-end browser test (Playwright/Chromium 1920×1080, keyboard only) by the QA agent: all requested flows passed — see `docs/PHASE0_STATUS.md` for the list. Three low-priority UX issues were reported and fixed afterwards (spatial-nav jump to sidebar from last grid row, asymmetric seek when controls hidden, folder-browser initial focus) plus pluralisation, stale error message, library loading state and a controller-friendly confirm dialog.

## Manual LAN check (dev container)

`python run.py` with LAN OFF bound to `127.0.0.1:8765` only (request to the container LAN IP failed to connect). After setting a PIN + enabling LAN + restart it bound to `0.0.0.0:8765`; from the container LAN IP: `/api/movies` → 401, wrong PIN → 401 with attempts left, correct PIN → token, catalog → 200, `Range: bytes=0-1023` → 206 (1024 bytes), `/api/fs/roots` → 403.

## Not tested

* Anything on Windows hardware (paths with drive letters/UNC, Windows Firewall prompt, `setup.bat`/`start.bat`).
* Anything on Xbox (browser or native). * Real Xbox/USB game controller input. * Large real-world libraries.
