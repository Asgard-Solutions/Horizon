# Automated test results (actual runs)

**Approved Git checkpoint, November 4, 2026:** `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider --basetemp data/git-checkpoint-final` passed **590 tests**, skipped 10 and reported three existing dependency deprecation warnings (exit 0). All **25 frontend checks passed**, including gold hover/keyboard/gamepad styling and neutral mouse restoration; the production build/type check passed with the existing bundle-size advisory. This verifies the offline suite for the locked REELHEIM Home and completed Settings/subtitle/NAS/NFO checkpoint. Historical live-suite and physical-device limitations below remain applicable.

**Latest NFO removal, November 4, 2026:** `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider --basetemp data/nfo-removal-release-check` passed **590 tests**, skipped 10 and reported three existing dependency warnings (exit 0). Fourteen removal cases and disposable browser checks cover confirmation/cancel, recovery bytes, malformed NFOs, conflict/identity protection and retained catalog/media. Frontend helpers passed **24/24**; type check/build passed with a bundle-size advisory. Actual NAS reading was checked; no real NFO was saved or removed. [Evidence and limits](HOME_INTEGRATION.md#recoverable-nfo-deletion--november-4-2026) include the unverified physical NAS removal, POSIX branch and new dialog's TV/compact layouts.

**Latest local NFO editor, November 4, 2026:** `.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short -p no:cacheprovider --basetemp data/nfo-complete-final` passed **576 tests**, skipped 10 and reported three existing dependency deprecation warnings (exit 0). Frontend helper tests passed **24/24**; the final type check and production build passed, with a bundle-size advisory. Local Windows movie/show/episode saves, backups, retained unknown XML, external-edit conflict handling, missing NFO errors, keyboard focus, unsaved navigation and TV/compact layouts were checked using disposable files. [Integration evidence and limits](HOME_INTEGRATION.md#local-nfo-editor--november-4-2026) and `verification/local-nfo-editor/checks.json` record the actual scope. No real NFO was edited. Physical NAS writes/controllers and the separate legacy live suites are not verified.

**Historical online metadata checkpoint — retired at the user's request:** `cd backend && ../.venv/Scripts/python.exe -m pytest tests -q --tb=short -p no:cacheprovider --basetemp ../data/metadata-final-episodes` passed **609 tests**, skipped 9 and reported three existing dependency warnings. Frontend tests passed **24/24** and the production build/type check passed. [Integration evidence and limits](HOME_INTEGRATION.md) cover actual browser matching, cached artwork, local overrides and keyboard/layout checks using an isolated simulated provider. That provider implementation has since been removed; no token is required. The bare all-directory backend run had four `tests_live/` collection errors for missing `requests`, named in the integration notes; it is not an all-suite pass.

**Historical platform note:** the older runs below were executed in the Linux development container (Debian 12, Python 3.11.18, SQLite 3.40.1, FFprobe 5.1 dev-only).
**Current Windows evidence:** [HOME_INTEGRATION.md](HOME_INTEGRATION.md) records Home, subtitles and completed Settings options. Final production build passed; 32 frontend tests passed; 471 backend tests passed with 9 skipped and one dependency deprecation warning. The latest Settings matrix passed 30 cases, plus compact 200% and keyboard checks. NAS/credential operations were mocked; physical NAS/device access, OS credential persistence, forced colors and screen-reader speech remain unverified. Earlier subtitle rendering/seeking used actual disposable playable media. These results do not establish Xbox compatibility. The older Linux results below are historical.

## Phase 0.5 backend suite — `cd backend && python -m pytest -v -n 0`

**158 passed, 0 failed, 16 skipped** (the 16 are the live-server checks in `tests_live/`, skipped without `MC_LIVE_URL`; run separately below). Also run in a fresh venv built only from `requirements-dev.txt`: 158 passed.

```
tests/test_parser.py::test_is_video[a.mp4-True] PASSED
tests/test_parser.py::test_is_video[a.MKV-True] PASSED
tests/test_parser.py::test_is_video[a.avi-True] PASSED
tests/test_parser.py::test_is_video[a.m4v-True] PASSED
tests/test_parser.py::test_is_video[a.mov-True] PASSED
tests/test_parser.py::test_is_video[a.txt-False] PASSED
tests/test_parser.py::test_is_video[a.nfo-False] PASSED
tests/test_parser.py::test_is_video[poster.jpg-False] PASSED
tests/test_parser.py::test_is_video[.mp4-False] PASSED
tests/test_parser.py::test_is_video[mp4-False] PASSED
tests/test_parser.py::test_parse_movie[Sample Movie (2024).mp4-dirs0-Sample Movie-2024] PASSED
tests/test_parser.py::test_parse_movie[Sample.Movie.2024.1080p.BluRay.x264.mkv-dirs1-Sample Movie-2024] PASSED
tests/test_parser.py::test_parse_movie[Another_Film_[2019].m4v-dirs2-Another Film-2019] PASSED
tests/test_parser.py::test_parse_movie[2001 A Space Odyssey (1968).mkv-dirs3-2001 A Space Odyssey-1968] PASSED
tests/test_parser.py::test_parse_movie[Blade Runner 2049 (2017).mp4-dirs4-Blade Runner 2049-2017] PASSED
tests/test_parser.py::test_parse_movie[Untitled Home Video.avi-dirs5-Untitled Home Video-None] PASSED
tests/test_parser.py::test_parse_movie[Some.Movie.720p.WEB-DL.mp4-dirs6-Some Movie-None] PASSED
tests/test_parser.py::test_parse_movie[movie.mp4-dirs7-Great Film-1999] PASSED
tests/test_parser.py::test_parse_movie[Great Film (1999).mkv-dirs8-Great Film-1999] PASSED
tests/test_parser.py::test_parse_episode[Sample Show - S01E02.mkv-dirs0-Sample Show-1-2-None] PASSED
tests/test_parser.py::test_parse_episode[Sample.Show.S01E02.720p.HDTV.x264.mkv-dirs1-Sample Show-1-2-None] PASSED
tests/test_parser.py::test_parse_episode[sample show s10e110.mp4-dirs2-sample show-10-110-None] PASSED
tests/test_parser.py::test_parse_episode[Sample Show - S02E01 - The Return.m4v-dirs3-Sample Show-2-1-The Return] PASSED
tests/test_parser.py::test_parse_episode[S01E03.mkv-dirs4-Folder Show-1-3-None] PASSED
tests/test_parser.py::test_parse_episode[Episode S01E04.mkv-dirs5-Folder Show-1-4-None] PASSED
tests/test_parser.py::test_parse_episode[Show 1x05 Title.avi-dirs6-Show-1-5-Title] PASSED
tests/test_parser.py::test_parse_episode[Other.Series.S02E05.720p.mp4-dirs7-Other Series-2-5-None] PASSED
tests/test_parser.py::test_parse_episode_show_year_from_folder PASSED
tests/test_parser.py::test_multi_episode PASSED
tests/test_parser.py::test_not_episode[Sample Movie (2024).mp4] PASSED
tests/test_parser.py::test_not_episode[1920x1080 demo.mp4] PASSED
tests/test_parser.py::test_not_episode[Movie.2010.1080p.mkv] PASSED
tests/test_parser.py::test_not_episode[Season Finale.mp4] PASSED
tests/test_parser.py::test_episode_without_show_name_at_root_is_rejected PASSED
tests/test_parser.py::test_season_dir[Season 1-1] PASSED
tests/test_parser.py::test_season_dir[season_02-2] PASSED
tests/test_parser.py::test_season_dir[S03-3] PASSED
tests/test_parser.py::test_season_dir[Specials-None] PASSED
tests/test_parser.py::test_season_dir[Staffel 4-4] PASSED
tests/test_parser.py::test_clean_name PASSED
tests/test_probe.py::test_avi_is_unsupported_without_probe PASSED
tests/test_probe.py::test_mp4_h264_aac_supported PASSED
tests/test_probe.py::test_mp4_without_probe_is_unknown PASSED
tests/test_probe.py::test_mkv_is_maybe PASSED
tests/test_probe.py::test_mp4_mpeg4_video_unsupported PASSED
tests/test_probe.py::test_hevc_and_dolby_audio_are_maybe PASSED
tests/test_probe.py::test_10bit_h264_unsupported PASSED
tests/test_probe.py::test_real_ffprobe PASSED
tests/test_scanner.py::test_scan_builds_library_structure PASSED
tests/test_scanner.py::test_rescan_does_not_duplicate PASSED
tests/test_scanner.py::test_adding_same_or_nested_folder_is_rejected PASSED
tests/test_scanner.py::test_rescan_picks_up_removed_and_new_files PASSED
tests/test_scanner.py::test_unreachable_folder_keeps_catalog PASSED
tests/test_scanner.py::test_scanning_never_modifies_source_files PASSED
tests/test_scanner.py::test_remove_library_clears_catalog_only PASSED
tests/test_scanner.py::test_invalid_paths_are_rejected PASSED
tests/test_scanner.py::test_progress_save_and_restore PASSED
tests/test_scanner.py::test_progress_survives_library_remove_and_readd PASSED
tests/test_security.py::test_host_has_full_access PASSED
tests/test_security.py::test_lan_is_disabled_by_default PASSED
tests/test_security.py::test_lan_cannot_be_enabled_without_pin PASSED
tests/test_security.py::test_pin_rules[1234567-False] PASSED
tests/test_security.py::test_pin_rules[12345678-False] PASSED
tests/test_security.py::test_pin_rules[87654321-False] PASSED
tests/test_security.py::test_pin_rules[11111111-False] PASSED
tests/test_security.py::test_pin_rules[abcdefgh-False] PASSED
tests/test_security.py::test_pin_rules[4815162342-True] PASSED
tests/test_security.py::test_pin_rules[48151623-True] PASSED
tests/test_security.py::test_pairing_flow_and_device_access PASSED
tests/test_security.py::test_bearer_token_for_native_clients PASSED
tests/test_security.py::test_wrong_pin_lockout PASSED
tests/test_security.py::test_revoke_and_pin_change_invalidate_devices PASSED
tests/test_security.py::test_disabling_lan_blocks_paired_devices PASSED
tests/test_security.py::test_public_ip_always_refused PASSED
tests/test_security.py::test_dns_rebinding_host_header_is_not_trusted PASSED
tests/test_security.py::test_state_changes_require_client_header PASSED
tests/test_security.py::test_pin_is_not_stored_in_plain_text PASSED
tests/test_security.py::test_stream_outside_library_is_forbidden PASSED
tests/test_security.py::test_path_traversal_inside_db_is_forbidden PASSED
tests/test_security.py::test_symlink_escape_is_forbidden PASSED
tests/test_security.py::test_artwork_outside_library_is_forbidden PASSED
tests/test_security.py::test_artwork_must_be_an_image PASSED
tests/test_security.py::test_removed_library_files_are_not_served PASSED
tests/test_streaming.py::test_parse_range[None-100-None] PASSED
tests/test_streaming.py::test_parse_range[bytes=0-9-100-expected1] PASSED
tests/test_streaming.py::test_parse_range[bytes=10--100-expected2] PASSED
tests/test_streaming.py::test_parse_range[bytes=-10-100-expected3] PASSED
tests/test_streaming.py::test_parse_range[bytes=-500-100-expected4] PASSED
tests/test_streaming.py::test_parse_range[bytes=90-500-100-expected5] PASSED
tests/test_streaming.py::test_parse_range[bytes=5-5-100-expected6] PASSED
tests/test_streaming.py::test_parse_range[bytes=0-1, 5-6-100-expected7] PASSED
tests/test_streaming.py::test_parse_range[items=0-9-100-None] PASSED
tests/test_streaming.py::test_parse_range[bytes=abc-100-None] PASSED
tests/test_streaming.py::test_parse_range[bytes=--100-None] PASSED
tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=100--100] PASSED
tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=50-10-100] PASSED
tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=-0-100] PASSED
tests/test_streaming.py::test_parse_range_unsatisfiable[bytes=0--0] PASSED
tests/test_streaming.py::test_full_response PASSED
tests/test_streaming.py::test_partial_responses PASSED
tests/test_streaming.py::test_unsatisfiable_range PASSED
tests/test_streaming.py::test_head_request PASSED
tests/test_streaming.py::test_if_range_mismatch_returns_full_file PASSED
tests/test_streaming.py::test_missing_file_returns_404 PASSED
tests/test_streaming.py::test_unknown_file_id PASSED
tests/test_windows_hardening.py::test_static_ui_has_correct_mime_types_even_with_bad_registry PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/../secret.txt] PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/..%2fsecret.txt] PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/%2e%2e/secret.txt] PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/assets/../../secret.txt] PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/..\\secret.txt] PASSED
tests/test_windows_hardening.py::test_spa_route_cannot_escape_dist[/assets/..%5c..%5csecret.txt] PASSED
tests/test_windows_hardening.py::test_spa_fallback_serves_index_to_unpaired_devices_but_no_data PASSED
tests/test_windows_hardening.py::test_ipv4_mapped_public_address_is_not_private PASSED
tests/test_windows_hardening.py::test_host_admin_requires_loopback_even_with_local_host_header PASSED
tests/test_windows_hardening.py::test_scanner_skips_linked_folders_and_outside_file_links PASSED
tests/test_windows_hardening.py::test_run_py_check_initialises_database PASSED
tests/test_windows_hardening.py::test_add_library_messages PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[D:\\Movies-D:\\Movies] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[D:\\Movies\\\\-D:\\Movies] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[D:/Movies/Kids-D:\\Movies\\Kids] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[D:-D:\\] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[z:\\-z:\\] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths["E:\\TV Shows"-E:\\TV Shows] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[  C:\\Users\\Me\\Videos  -C:\\Users\\Me\\Videos] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[\\\\NAS\\Media-\\\\NAS\\Media] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[\\\\nas.local\\media\\Movies\\..\\TV-\\\\nas.local\\media\\TV] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[//NAS/Media/Movies-\\\\NAS\\Media\\Movies] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[\\\\192.168.1.5\\share-\\\\192.168.1.5\\share] PASSED
tests/test_windows_paths.py::test_accepts_windows_paths[\\\\?\\D:\\Very\\Long\\Path-\\\\?\\D:\\Very\\Long\\Path] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[   ] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[Movies] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[Movies\\Kids] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[C:Movies] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[\\Movies] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[\\\\NAS] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[\\\\NAS\\\\] PASSED
tests/test_windows_paths.py::test_rejects_ambiguous_or_relative_windows_paths[D:\x00evil] PASSED
tests/test_windows_paths.py::test_parent_dir_windows[D:\\-None] PASSED
tests/test_windows_paths.py::test_parent_dir_windows[D:\\Movies-D:\\] PASSED
tests/test_windows_paths.py::test_parent_dir_windows[D:\\Movies\\Kids-D:\\Movies] PASSED
tests/test_windows_paths.py::test_parent_dir_windows[\\\\NAS\\Media-None] PASSED
tests/test_windows_paths.py::test_parent_dir_windows[\\\\NAS\\Media\\TV-\\\\NAS\\Media\\] PASSED
tests/test_windows_paths.py::test_is_within_windows[D:\\Movies-D:\\Movies\\A (2020)\\a.mkv-True] PASSED
tests/test_windows_paths.py::test_is_within_windows[D:\\Movies-d:\\movies\\A.MKV-True] PASSED
tests/test_windows_paths.py::test_is_within_windows[D:\\Movies-D:\\Movies2\\a.mkv-False] PASSED
tests/test_windows_paths.py::test_is_within_windows[D:\\Movies-D:\\Movies\\..\\Secret\\a.mkv-False] PASSED
tests/test_windows_paths.py::test_is_within_windows[D:\\Movies-E:\\Movies\\a.mkv-False] PASSED
tests/test_windows_paths.py::test_is_within_windows[\\\\NAS\\Media-\\\\nas\\media\\TV\\x.mp4-True] PASSED
tests/test_windows_paths.py::test_is_within_windows[\\\\NAS\\Media-\\\\NAS\\Media2\\x.mp4-False] PASSED
tests/test_windows_paths.py::test_is_within_windows[\\\\NAS\\Media-\\\\OTHER\\Media\\x.mp4-False] PASSED
tests/test_windows_paths.py::test_is_within_windows[\\\\NAS\\Media-D:\\x.mp4-False] PASSED
tests/test_windows_paths.py::test_posix_rules_unchanged PASSED
tests/test_windows_paths.py::test_windows_reparse_point_classification[16-0-False] PASSED
tests/test_windows_paths.py::test_windows_reparse_point_classification[1040-2684354563-True] PASSED
tests/test_windows_paths.py::test_windows_reparse_point_classification[1040-2684354572-True] PASSED
tests/test_windows_paths.py::test_windows_reparse_point_classification[1040-2415919130-False] PASSED
```

## Live-server checks — `MC_LIVE_URL=<url> python -m pytest tests_live -n 0`

16 passed (Phase 0 run, against the dev server with the synthetic library).

## Offline runtime check (Phase 0.5)

The server was started with `PYTHONPATH=scripts/dev/offline_guard` (a `sitecustomize` that blocks every non-loopback connect and DNS lookup and logs attempts). Through it: UI index 200, JS bundle 200 `text/javascript`, add+scan library (6 files), playback info with FFprobe codecs, range streaming 206, progress save, system info — all OK. Guard log: one blocked UDP `connect` to 10.255.255.255 (the LAN-address discovery trick; sends no packets and is handled). No other outbound attempt. Built UI contains no fetchable external URLs (only XML namespace strings and documentation links inside React/Router error messages). A true network-namespace test was not possible (container lacks privileges).

## Windows packaging checks performed on Linux

* `pip install --dry-run --no-index --find-links vendor/wheels --platform win_amd64` resolves all 22 packages for CPython 3.11, 3.12, 3.13 and 3.14 (offline). `colorama` (Windows-only marker) is bundled.
* `.bat`/`.ps1` files are ASCII with CRLF line endings. **PowerShell/cmd syntax was not executed** (no Windows/PowerShell available).
* `run.py --check` exercised: OK path, missing UI → FAIL + exit 1, port-in-use → FAIL; `run.py` refuses to start on a used port.

## Frontend

* `yarn typecheck` and `yarn build`: passed. E2E browser tests: see the testing-agent report summary in `docs/PHASE0_5_STATUS.md`.

## Not executed

* Windows: Setup/Start/RunTests scripts, drive enumeration via Win32 API, UNC/mapped drives, ACL denial, NTFS junctions, Windows Firewall, Edge/Chrome on Windows, `SO_EXCLUSIVEADDRUSE` bind.
* Xbox: nothing.
