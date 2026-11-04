# Horizon Home integration plan

Goal: implement the approved Home v1.2 two-stage flow using the repository's actual local library/progress services and the supplied branding.

Architecture: retain React 19/TypeScript/Vite, React Router, the existing spatial input manager, FastAPI and SQLite. Add a Home selector and per-type hub, and thread explicit movie/tv scope through existing Atlas, Discover and Search. Reuse LibraryManager and playback services; do not replace scanner, database or player implementation.

Spec: the project handoff in `../horizon-emergent-update-v1.1/horizon-home-v1.2/design-spec.md` and the original user requirements. Current logo asset is the clean `../branding/horizon-media-center-logo-v2.svg`.

## Constraints

- No invented product data/artwork, no content hero/feed on Home, no remote services.
- Preserve media file bytes, source/index operations, existing progress completion policy and player behavior.
- Sources/Settings stay globally reachable; selected type survives navigation/Back; row hidden when empty.
- Use the existing input manager; preserve focus by stable IDs and per-type state, including row/item removal and compact screens.
- Work stays local in the fresh dedicated clone. No new branch, commit, push, merge or deployment is authorized by a repository URL alone.

## Baseline evidence

- Repository HEAD: `a11c73f`.
- `yarn build` passes after installing with `yarn install --pure-lockfile`. The existing frozen-lockfile install fails; keep that baseline dependency issue separate and do not rewrite its lockfile without need.
- `python -m pytest tests -n 0 -q --tb=short`: 187 passed, 9 skipped, 1 failed (`test_durations.py::test_missing_file_is_skipped_not_cached`, unreachable counter 0). Initial restricted runs also hit temporary-directory permissions; results above are from an approved unrestricted isolated test run.

## Work

1. Backend selectors, owned separately: add optional `media_type=movie|tv` to Home, Discover, Search and Atlas while keeping unscoped compatibility. Test filtering at the API boundary, eligibility before row limits, empty/completed/invalid progress, type-specific facets/groups and offline-index retention. No schema/scanner/player changes.
2. Frontend context/data helpers: define explicit media context, scoped paths, stable per-type Home memory and resume eligibility/focus recovery. Add native Node tests before implementation; avoid a new test dependency.
3. Home and shared chrome: replace launch hero with Movies/TV Shows, add `/home/:mediaType` hub, real resume row/dialog, source status/setup/Retry and global Sources/Settings. Reuse existing source and availability/player calls. Add supplied background and new logo; retain old browsing components.
4. Existing destinations/input: enforce context in request/cache/query identities and drill-downs, keep Atlas state separate per type, prevent shortcuts or view tabs from escaping selected type, discard late responses. Add Home focus map using existing directional-target attributes and ensure A/B hold behavior is preserved.
5. Verify: build/typecheck; meaningful helper and API tests; full backend suite with baseline failures separate; run actual app against an isolated empty/test library in a hidden browser. Exercise keyboard and simulated Gamepad API events, Back/Settings/Sources/focus, empty history/library, broken art, source loss and responsive/zoom cases. Physical controller/NAS and playback remain unverified unless actual evidence is available.

## Review focus

Late responses crossing movie/tv context; scoped Atlas collection/genre drill-downs; sources/Settings restore origin focus; removing the focused/last resume item; compact stacking and 4K root zoom. Keep native Search text editing and player input intact. Review the final diff and report exact commands, observed passes/failures and unavailable hardware/media dependencies.

## Execution ledger

- Backend scoped API implementation and 43 new tests complete; no schema/scanner/player-service changes.
- Frontend context/resume/focus helper tests observed red then green (5 passed). Selector, hub, branding, Sources entry and destination scoping complete.
- Code review identified pending Retry focus, reordered offscreen resume focus, removed modal-opener focus and Search input gamepad escape; all corrected and exercised by browser checks. Re-review found no important remaining issue in that scope.
- Actual source-loss test showed metadata was not availability evidence. Ruling: use existing authorized stream HEAD as the preflight, preserving playback metadata/service semantics.
- Accessibility check showed manual scaling was being cancelled by proportional TV sizing. Ruling: use scale-aware compact flow and live resize focus maps, while retaining auto 4K layout.
- Final browser run: 15 flow groups passed, including 24 viewport/screen combinations and manual scaling. Backend: 230 passed, 9 skipped, same 1 baseline failure. Frontend build and 5 helper tests pass. Detailed limitations and reproduction instructions are in `docs/HOME_INTEGRATION.md`.
