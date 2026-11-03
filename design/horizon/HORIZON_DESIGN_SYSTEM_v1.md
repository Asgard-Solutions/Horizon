# Horizon UI/UX design system

**Version:** 1.0 | **Status:** proposed design specification | **Product:** Horizon (working name) | **Experience:** The Living Cinema

**Purpose:** A build-ready design and interaction guide for the existing local-first media center. This document defines the desired UI and is not a claim that the features below have all been implemented. The existing Phase 0 functions are described in Section 2; the rest are design requirements and proposed behaviors.

**Priority order if requirements conflict:** (1) media safety and working playback; (2) reachable, predictable navigation; (3) readable content; (4) performance and accessibility; (5) cinematic decoration.

## 1. Product brief

Horizon is a personal media center for movies and TV episodes stored in local or network folders. The user owns the collection. The UI should feel like a high-end personal cinema on a large display while remaining quick and clear on a Windows desktop.

**Primary tasks**

1. Resume a movie or episode with the fewest possible actions.
2. Explore a large personal movie/TV collection using artwork and context.
3. Find a specific title, season, or episode without friction.
4. Start playback, seek, pause, adjust volume, and return exactly where the user expects.
5. Add, rescan, inspect, or remove a media source without touching the media files.

**Designed for:** Windows PC with mouse/keyboard, a TV viewed from approximately 8-12 feet, and controller navigation. Native Xbox support is an unverified future runtime target, not a completed feature.

**Desired personality:** confident, calm, tactile, cinematic, slightly futuristic, never busy. It should look unmistakably like an entertainment application, not a SaaS analytics dashboard.

**Visual metaphor:** A single illuminated "stage" displays the selected title. A curved "filmstrip" is an inviting route through the collection. A navigable "atlas" can offer an optional zoomed-out view once straightforward browsing works well.

## 2. Current system and hard constraints

These are the project facts supplied for Phase 0; the implementation must be inspected before editing.

- Add local or NAS media folders by browsing or entering a path such as `D:\Movies` or `\\NAS\Media`.
- Read filenames to group movies, TV shows, seasons, and episodes.
- Use local information files and poster images when available.
- Store library data in a local SQLite database.
- Rescan without introducing duplicates; do not delete entries when a source is temporarily unreachable.
- Playback provides play/pause, seek, volume, fullscreen, Resume/Start Over, and Continue Watching.
- Source media files remain unchanged; existing integrity tests fingerprint files around scanning, playback, streaming, and source removal.
- The working environment tested so far is Linux. Windows and Xbox are not verified.

**Non-negotiables**

- Do not replace working media operations with mocked records or fake APIs.
- Do not move access to local paths or private media into a remotely hosted service.
- Do not add account creation, ads, subscriptions, internet-only services, telemetrics, remote metadata dependencies, or online artwork fetching without explicit approval.
- Do not invent cast, genre, duration, rating, release year, resolution, availability, or progress when absent from existing data.
- Do not create controls or navigation destinations that do nothing. Disabled controls require a useful explanation or should be hidden.
- A design preview is not proof of filesystem integration, Windows compatibility, or Xbox compatibility.

## 3. Experience principles

### 3.1 Content leads

The interface recedes behind the content. Use the selected title's real poster or backdrop if available. Avoid defaulting to a wall of unrelated stock art.

### 3.2 One clear primary action

Every screen has a visible, unmistakable next action: Resume, Play, Open series, Select season, Search, or Add folder. A user should not have to discover a hidden hover state to proceed.

### 3.3 Spatial navigation with no surprises

Focus moves in a visible, consistent direction. The UI remembers the previously selected title and scroll position when returning from details or playback. Dynamic layout must not teleport focus.

### 3.4 Offline means fully usable

Existing scanned media, artwork, and metadata remain browseable when internet is unavailable. A temporarily offline NAS gets a transparent status message instead of an empty library.

### 3.5 Cinema without distraction

Motion supports orientation. No full-screen random particles, scrolling headline marquees, auto-advancing hero content, autoplay trailers, or constant looping animation.

## 4. Signature interaction model

### 4.1 The Stage

The selected movie or show controls a single hero composition, but selection does not trigger playback. The Stage shows a backdrop, a strong title, truthful metadata chips, one prominent action, and one secondary action. It can take a subtle 300-500 ms crossfade when focus changes. Never animate whole-screen brightness harshly.

For an in-progress item, primary action reads **Resume** (the saved time can be added if actual time data exists). Otherwise it reads **Play** for a movie or **Explore series** for a show. Secondary action is **Details**. More details may appear in an unobtrusive disclosure panel.

### 4.2 The Living Filmstrip

The Filmstrip is a spatial browsing rail with a controlled curve. Its focused card rises and grows slightly; adjacent cards are stepped back with a soft perspective. Its purpose is recognizable navigation, not theatrical distortion.

- Center or near-center focus remains in a stable visual zone while the strip scrolls behind it.
- Unfocused posters remain recognizable, with no rotation beyond approximately +/-8 degrees in a supported 3D rendering mode.
- Focus enlargement target is 1.10x to 1.14x; keep safe spacing to avoid overlap.
- Keep interactive text on a non-rotated plane. No unreadable slanted descriptions.
- Left/right move one real item; shoulder buttons can move to adjacent groups. Edges stop visibly, not an unexplained circular wrap.
- Provide a one-click/controller-accessible **Grid view**. Remember that view preference locally.
- Reduce or remove 3D transform entirely when `prefers-reduced-motion` is active or hardware performance warrants it.
- Virtualize long libraries so hundreds of posters do not render or animate at once.

### 4.3 The Library Atlas (optional, later phase)

The Atlas is a zoomed-out constellation of the user's actual collection. It should feel like a geographic map of movies/shows, but it is an exploration surface rather than the only way to find content.

- Organize by data the library actually has: media type, series, source folder, or other confirmed metadata.
- Do not fabricate semantic relationships or genre clusters when tags are unavailable.
- Each node can be reached by keyboard and controller; a linear index/list remains available.
- Use progressive rendering and clustering; do not draw every title as an animated object for a very large library.
- Atlas must not delay the release of fast conventional Movies and TV views.

### 4.4 Episode Journey

TV navigation is a show page with a clear season selector and an episode timeline. The selected episode has a full title, episode number, saved progress when known, and Play/Resume. This is a straightforward sequence with subtle timeline styling, not a complicated branching story map.

### 4.5 The Horizon Line - a signature navigational motif

A fine, partially interrupted horizontal light line ties the interface together. On Home it travels under the Stage and subtly bends toward the focused Filmstrip card. On a details page it becomes the title underline; in player mode the same visual language appears in the progress rail. This creates continuity when the interface changes modes.

- Use a 2 px base line, muted most of the time, with aurora at the active anchor and occasional restrained amber in the trailing segment.
- It must never compete with text, appear above video, or become the only focus indicator.
- When selected artwork changes, move its anchor with the Filmstrip's 180-280 ms transition. In reduced-motion mode, snap to its new position.
- Do not draw connector lines to every poster. The line belongs to the currently focused item only.
- Use CSS or a lightweight SVG path; no always-running canvas or large particle system.

**Design distinction:** Horizon's recognizable layout is one cinematic Stage, one active Filmstrip, and one connective Horizon Line. The interface should not default to rows of unrelated poster tiles or giant glass navigation panels.

## 5. Identity and brand

### 5.1 Name, voice, and mark

- Working product name: **HORIZON**.
- Optional brand line: **Your Library. Your Universe.** Use sparingly; do not repeat on every screen.
- Wordmark: geometric uppercase lettering with restrained tracking. Display type should be prominent without resembling a futuristic gaming HUD.
- Symbol direction: a simple interrupted circular horizon/orbit with a thin horizontal stroke. Design it as a crisp vector/SVG that works at 24 px and at splash-screen size. Do not copy another product logo.
- Brand surfaces should be mostly flat. Use amber as a small sense of warmth, not as an overwhelming second accent.

### 5.2 Copywriting

Use concise entertainment-language labels: **Continue watching**, **Resume**, **Start over**, **Recently added**, **All movies**, **All series**, **Open details**, **Add media folder**, **Scan again**.

Use sentence case for headings and buttons except for the Horizon wordmark. Use informative messages. For example: "This folder is unavailable. Your library entries are still here." Avoid jargon like "SMB mount failure" on the main screen; place technical details in Library Settings.

## 6. Color system

Colors are defined in `horizon.tokens.json` and must be implemented through shared variables rather than copied literals across components.

| Role | Token | Hex | Usage |
|---|---|---|---|
| Base | `bg.canvas` | `#0A0E15` | Main scene / background |
| Deep surface | `bg.surface` | `#101925` | Secondary panels |
| Raised surface | `bg.raised` | `#172737` | Cards, menus |
| Active surface | `bg.active` | `#1C2B39` | Selected panel under a focus outline |
| Border | `border.default` | `#344656` | Dividers / passive boundaries |
| Strong border | `border.strong` | `#506477` | Active structural lines; do not use as body text |
| Primary text | `text.primary` | `#F4F6F8` | Titles and body |
| Secondary text | `text.secondary` | `#BFCDD8` | Labels and descriptions |
| Tertiary text | `text.tertiary` | `#91A4B5` | Supporting metadata |
| Main accent | `accent.aurora` | `#87E8D0` | Focus outlines, primary actions |
| Pressed accent | `accent.strong` | `#55D9BE` | Pressed/active emphasis |
| Text on accent | `accent.ink` | `#061A18` | Primary-button labels |
| Warm accent | `accent.amber` | `#E7B778` | Small hints and progress emphasis |
| Success | `status.success` | `#88D9AF` | Completed scan |
| Error | `status.error` | `#FF898F` | Unavailable/error notice |

Text foregrounds listed above are intended for the dark surfaces; do not place them over unpredictable bright artwork without a sufficient scrim. Text-on-background contrast must be tested on the final computed composition. Proposed foregrounds have high contrast against the four solid dark backgrounds; gradients, overlays, and screenshots still require verification.

**Gradient recipe**: Stage image should sit behind a dark horizontal scrim, strongest near textual content. Example: `linear-gradient(90deg, rgba(10,14,21,.98) 0%, rgba(10,14,21,.90) 30%, rgba(10,14,21,.44) 68%, rgba(10,14,21,.20) 100%)`. Add a subtle bottom scrim for the Filmstrip and controls. Do not tint every element with heavy gradients.

**Glow recipe**: focused media card may have `0 0 0 3px #87E8D0` plus a soft low-opacity 18-24 px mint glow. Keep actual outline solid and visible if shadows are disabled. No continuous pulsing focus indicator.

**Color use budget**: dark neutral colors should occupy most of the display; aurora highlights actions/focus; amber is a small tertiary signal. Never use color alone to convey state.

## 7. Typography

### 7.1 Font families

- Display: **Sora**, fallback `Inter`, `Segoe UI`, system sans-serif.
- Interface/body: **Inter**, fallback `Segoe UI`, Arial, system sans-serif.
- Self-host fonts only after verifying license and including license notices. The app must not depend on remote font CDNs.
- Variable fonts are acceptable if the host runtime supports them well; avoid font loading shifts and synthesize as few weights as possible.

### 7.2 Type sizes (logical CSS pixels)

| Role | TV / 1080p target | Desktop target | Weight | Notes |
|---|---:|---:|---:|---|
| Hero title | 64-80 | 48-64 | 600 | Up to 2 lines; soft gradient mask only if needed |
| Page heading | 40 | 32 | 600 | Sora |
| Section heading | 28 | 24 | 600 | Sora or Inter |
| Card title (selected) | 24 | 20 | 600 | 2 lines max in card |
| Body / description | 22 | 16-18 | 400 | 1.4-1.55 line height |
| Button / primary nav | 22 | 16-18 | 600 | Clear, stable label |
| Metadata / hint | 18-20 | 14-16 | 500 | Do not shrink key info below this on TV |
| Technical fine print | 16 | 13-14 | 400 | Only on utility screens, never critical actions |

Apply responsive `clamp()` rules and a TV-mode class or media/runtime tuning rather than assuming a specific device-pixel ratio. Validate real viewport behavior at 720p, 1080p, and 4K. Avoid elaborate gradients inside letters, ultra-thin type, and all-caps body copy.

Truncation rules: long movie names can wrap to two lines on Stage, card labels can truncate after two lines with an accessible full title, and titles in details should be allowed more space. Never truncate the focused title without offering its full text nearby.

## 8. Layout, grids, and safe areas

### 8.1 Overall frame

- Reference artboard: 1920x1080, 16:9.
- TV safe area: reserve approximately 5% from each edge for critical actions and text (at 1920x1080, approximately 96 px horizontal and 54 px vertical). Actual host/system insets take precedence.
- Desktop shell: minimum 24 px inset, scaling to 48-64 px on wide windows.
- Use a 12-column underlying grid with 16-24 px gutters on desktop and more breathing room on TV.
- The Home screen should present the main hero and at least one useful browse path without demanding excessive vertical scrolling at 1080p.
- Layout should work as a responsive application, not as one giant fixed-position screenshot.

### 8.2 Regions of the 1080p Home reference

1. Top shell: roughly 72-96 px, with wordmark, Home, Movies, TV, Collections (only if real), Search, and unobtrusive library status.
2. The Stage: approximately 380-480 px depending on content; left-text, right/backdrop emphasis; strong readable action buttons.
3. The Filmstrip: approximately 260-340 px including poster imagery and labels; one selected title clearly framed.
4. Bottom utility: slim guidance and state, not a second large navigation bar.

These dimensions are composition targets, not hardcoded pixel heights; adapt to smaller screens and accessibility settings.

### 8.3 Breakpoints and behavior

- **Large TV/wide (`>=1600 CSS px`)**: full hero, spatial Filmstrip, persistent top navigation, enlarged labels.
- **Laptop/standard (`1100-1599`)**: compressed hero, 3-5 visible cards, simplified curvature, standard cursor and keyboard support.
- **Compact desktop/tablet (`768-1099`)**: smaller or stacked Stage; visible search; Filmstrip can simplify to horizontal cards or grid.
- **Small (`<768`)**: fallback responsive browse layout. The app is not phone-first; keep it functionally usable if window resized.
- **Short-height windows (`<800 CSS px`)**: reduce decorative Stage height before reducing font readability or hiding primary controls.

The breakpoints are design targets; measured content and user scaling can require adjustments.

### 8.4 Spacing and shape

- Base 4 px unit: `4, 8, 12, 16, 24, 32, 48, 64, 80, 96`.
- Button horizontal padding: 24-32 px; vertical padding: 14-20 px.
- Card-to-card gap: 20-28 px in TV mode; 12-20 px compact.
- Corner radii: 8 px fields, 12 px buttons, 16 px cards, 24 px large panels, fully pill-shaped only for status chips.
- Use subtle borders to separate elevated surfaces. Avoid double borders around everything.

## 9. Global navigation and information architecture

**Primary destinations:** Home, Movies, TV, Search, Library. Optional Collections only when the data model supports it. Settings is reachable from Library or an explicit Options menu, never hidden behind a fake profile/avatar.

**Route model (conceptual):** `Home -> Movies -> Movie details -> Player` and `Home -> TV -> Show -> Season/Episode -> Player`. The UI can use routes or local state depending on existing stack; the back stack and focus restore matter more than implementation choice.

**Navigation contract**

- On app open, focus the highest-value action (Resume if available; otherwise a clearly visible first card / Add folder on empty library).
- The top navigation has a consistent place on all browse screens.
- `B`/Escape returns to the previous contextual view; one more step can return Home. Do not lose filter, selection, or browse position.
- Direct play should never require a secondary surprise confirmation unless choosing Resume/Start Over when there is a saved position.
- Modal dialogs trap focus intentionally and restore it on close. Ordinary pages do not trap focus.
- When an async scan changes the library, keep the currently focused title if it still exists; otherwise move to the nearest visible valid item.

## 10. Components and states

### 10.1 Buttons

**Primary:** solid aurora fill, deep-ink label, 12 px radius, medium-semibold type, play/resume icon only if it helps. Clear focus outline outside the filled button, visible on hover/keyboard/gamepad.

**Secondary:** dark surface, 1 px strong border, primary text. **Tertiary:** text and icon with enough contrast and a large hit region.

All buttons have default, hover, focus-visible, pressed, disabled, and loading states where relevant. Hover should not replace focus. Minimum touch/pointer hit target 44x44 px; TV controller target area aim approximately 64x64 px or a similarly forgiving focus rectangle. Do not shrink controls to fit dense layouts.

### 10.2 Poster card

- Default ratio: 2:3. Use actual local poster artwork.
- Baseline reference: around 190x285 px at 1080p, selected 10-14% larger through transform with allotted breathing space.
- Default card does not need text burned into the poster. Title appears below or in a clear separate overlay, with screen-reader label.
- Focus: 3 px aurora outline + subtle halo + optional 4-10 px visual lift.
- Progress line: 3-5 px at bottom when real persisted viewing progress exists; do not render for unwatched titles.
- Missing image: use a gradient/typographic card constructed from the actual title, never fake cover art or an unrelated stock photo.
- Long titles and small sizes: keep accessible label readable and unclipped.

### 10.3 Hero panel

- Wide image crop: use the real local backdrop if available; else poster + neutral atmospheric treatment.
- Left-aligned text region 36-45% of width; scrim over imagery.
- Label based on actual context (e.g., "Continue watching"), title, truthful metadata, 1-3 lines of overview only when provided, CTAs.
- When synopsis is absent, do not fill with a generated story. Reclaim space with sensible typography.
- Stage updates from focus after a brief stable selection (e.g., 100-150 ms debounce) to prevent flickering during repeated D-pad input.

### 10.4 Chips and indicators

Compact chips may show `Movie`, `Series`, `S02 E03`, or `1h 42m` when verified in existing data. Do not show invented `4K`, `Dolby Atmos`, age rating, stars, or network logos.

### 10.5 Navigation bar

Wordmark left; primary destinations centered/near-left; Search visible; right utilities only if they do real work. Active destination uses an underline or short luminous stroke with clear label. Focus has a separate ring; active and focus cannot be visually identical.

### 10.6 Search

Search appears as a spacious overlay or dedicated screen. Immediate text input and a back action. Results update locally with debouncing; support title/show/episode matching only where current data allows. Filtering may include media type, source folder, watched/in progress, year/genre only if stored. Show result count and helpful empty states. Keyboard `/` opens search outside player text fields; Y may open search while browsing.

### 10.7 Dialogs, banners, toasts

- Dialogs: confirmation for destructive changes to the **library index**, with explicit note that media files are not deleted.
- Banners: offline source, scan progress, or actual file-unavailable status. Explain what remains available.
- Toasts: short acknowledgments for rescan queued, folder added, settings saved. Never show a success message before backend confirms it.
- Error messages are actionable and never replace the entire browsing experience when some sources remain available.

### 10.8 Inputs and settings

Use the same design language, but prioritize clean forms over cinematic curvature. Source path entry needs a readable monospace-ish presentation and reliable Windows UNC path rendering; allow paste without formatting or smart quotes. Clear validation feedback, correct loading and error states.

## 11. Screens: detailed specifications

### 11.1 Home / The Stage

**Structure:** top navigation; Stage hero; Continue Watching (when applicable); Living Filmstrip of real Recent/All titles; minimal status. Do not fill empty sections with invented data.

**First-run no-library state:** attractive neutral horizon artwork (abstract CSS/SVG, not fake content), a large **Add media folder** action, and one concise sentence describing supported local/NAS sources. If host cannot browse folders, explain that rather than presenting a dead Browse button.

**With library:** choose a stable initial Stage item based on actual Continue Watching or most recent content. Primary CTA Resume/Play; secondary Details. Show selected Filmstrip poster with obvious focus; top nav remains available. Avoid automatic poster cycling.

**Success condition:** user can resume with no more than two intentional actions from launch when Continue Watching exists and the saved state permits it.

### 11.2 Movies

**Structure:** All movies heading, available sort/filter row, Filmstrip or accessible poster grid, optional details preview pane. Useful sort keys include title and date added when stored; do not promise unsupported fields. Display a count derived from real data. Cards share component and focus behavior with Home. For large collections, render only what is in/near view and preserve scroll position.

### 11.3 TV / Shows

Show cards first; selecting a show reveals season navigation. Episodes can have a compact timeline row with episode number and title, or a readable vertical list when data is sparse. Selecting episode offers Resume/Play and clear details. Watch progress is derived from saved records; do not assume 'watched' based on mere presence of a filename.

### 11.4 Title details

Backdrop + title + metadata + synopsis if present + primary play action. File/storage technical details can be in a secondary information sheet. For TV, show seasons and episodes; for movies, direct play. Users can return to the exact poster/season they came from.

**Saved playback:** if prior position is meaningful and a saved Resume/Start Over choice already exists in the app, preserve its behavior. Do not overwrite a resumed position by opening a details panel. The threshold to offer resume can stay as the existing backend logic.

### 11.5 Player

A low-noise overlay over actual video: compact top title / back affordance, lower progress rail, current time and duration if provided by media engine, play/pause, seek, volume, fullscreen. Preserve current playback engine and streaming/seeking logic; style components, not the media pipeline.

- While playing, auto-hide OSD only after inactivity (proposed 4 seconds); never auto-hide a focused OSD control or while paused/dialog open.
- OSD appears with pointer movement, supported controller/keyboard input, or explicit tap.
- Progress bar clearly distinguishes buffered media if data is available, played, and remaining. Do not invent preview thumbnails.
- Preserve current media file's audio/video presentation; never cover subtitles with permanent controls.
- If media source disappears, show actionable **File unavailable** and retain the library entry as appropriate.
- Keep existing Resume/Start Over semantics and playhead persistence.

### 11.6 Library / Sources

A functional utility screen, not a poster gallery. List configured source paths, scan status, last result when known, and available Add / Scan again / Remove-from-library actions. If a NAS is down, display **Source unavailable** without deleting indexed titles. Removing a source from the library must not delete files and requires clear confirmation. Technical error messages can expand for debugging.

### 11.7 Settings / Preferences

Only include actual preferences. Candidate future items: reduced motion, grid/filmstrip preference, text size, controller mapping information, diagnostics. Mark unimplemented options as future scope in design documents, not as live clickable UI.

### 11.8 Optional Atlas exploration

Only after fast accessible browsing is working. The collection's genuine nodes are clustered spatially; each cluster has an index/list entry reachable via D-pad. Zoom levels must be meaningful, with a persistent **Back to grid** action. Use no fabricated thematic similarities or automatic recommendations.

## 12. Interaction and input matrix

| Action | Mouse/keyboard | Controller target in browse mode | Controller target in player |
|---|---|---|---|
| Move focus | Pointer / arrows | D-pad or left stick | D-pad / left stick over visible OSD |
| Activate | Click / Enter | A | A toggles play/pause when player has focus; OSD controls activate normally |
| Back | Escape / visible Back | B | B hides OSD or returns to previous view, based on context |
| Details/info | Click Details | X where appropriate | X can show actual media info if implemented |
| Search | Click Search / `/` outside fields | Y in browse | Not mapped by default |
| Move group | Accessible section controls | LB / RB | No implicit seek remap unless tested |
| Seek | Progress bar / arrow keys when player active | N/A | Left/right when seek mode or OSD focus is explicitly on timeline |
| Options | Menu / Settings action | Menu when host delivers it | Player options if implemented |
| Fullscreen | Button / F in player | Available player action | Available player action |

This table is an intended mapping, not proof of console keycode support. Actual Xbox browser/native runtime button events require testing. Prevent conflicts (for example: A to press a focused Play/Pause button versus A to toggle globally). Display contextual hints in a small unobtrusive footer: `A Select`, `B Back`, etc. Hide hints on mouse-first sessions or when irrelevant.

**Focus behavior**

- Every selectable item has an actual focus element and a visible focus ring (minimum 3 px solid aurora; maintain approximately 2-4 px offset where possible).
- `focus-visible` is separate from hover, selected, and currently playing states.
- Spatial arrow navigation follows visual proximity; prefer a stable grid when layout is compressed.
- Focus never jumps underneath dialogs or offscreen after asynchronous data refresh.
- Scroll focused cards into view with short motion, or instantly for reduced motion.
- Back from player restores the last details location; Back from details restores the exact browse card if present.
- A focused rail must have reachable exit paths (up/down to other regions; B back); never require a mouse.

## 13. Animation, sound, and feedback

**Default easing:** `cubic-bezier(0.22, 1, 0.36, 1)` for gentle settle, and `cubic-bezier(0.2, 0.8, 0.2, 1)` for focus transitions.

| Interaction | Duration target | Behavior |
|---|---:|---|
| Focus ring / button hover | 90-140 ms | Opacity, outline, minor lift |
| Poster focus change | 160-240 ms | Scale and positional settle |
| Filmstrip scroll | 180-280 ms | Short, smooth, directional |
| Stage artwork swap | 280-450 ms | Crossfade, no blinding flash |
| Details transition | 240-360 ms | Fade/slide with clear spatial anchor |
| Small menu / dialog | 160-240 ms | Scale/fade, immediate focus handoff |
| Player OSD appearance | 140-220 ms | Fade in/out, no excessive movement |

No autoplay video previews. Do not add synthetic UI sound effects by default. If optional audio feedback is added later, it must be off by default or user-configurable and never interfere with video audio.

**Reduced motion:** honor `prefers-reduced-motion` and an optional app preference. Set decorative transitions to instant or minimal fade; turn off parallax, 3D swing, large scale changes, and smooth continuous motion. Preserve focus and state feedback without animation.

**Performance guardrails:** favor transform/opacity animations; avoid expensive real-time backdrop blurs, large canvas particle layers, and dozens of animated poster elements. Limit animated elements to currently visible content. Low-power mode may disable curves or heavy shadows.

## 14. Imagery, artwork, and iconography

- Priority order: actual local backdrop -> actual local poster -> neutral procedural title treatment.
- Backdrops prefer wide landscape art with a protected text scrim; posters keep native crop except `object-fit: cover` in fixed-ratio containers where acceptable.
- Avoid external stock images, fabricated film posters, fake thumbnails, and automatic online scraping.
- Never auto-download remote posters or metadata without explicit opt-in and a separate feature decision.
- Missing art treatment: deep navy/midnight gradient, thin horizon arc, title typography taken from the real record, subtle grain/texture if cheap. No actor images or fake studio logos.
- Default icons: a consistent, simple 2 px stroke family (for example Lucide, if its license is compatible). 24 px desktop / 28-32 px TV where appropriate.
- Custom Horizon logo must remain legible as a monochrome mark. No excessive chromatic aberration, neon outlines, or sci-fi cockpit frames.
- Icons always have text labels for major actions. Never rely on an unlabeled icon for Resume, Play, Add folder, or Remove.

## 15. Content and data contract

**Allowed content source:** the app's real SQLite-backed library/API, local media engine, and locally available metadata/art. The implementation must inspect actual schema before binding fields.

**Likely UI fields, subject to schema inspection:** stable media ID, media type, display title, source path, poster/backdrop URI, show ID, season/episode numbers, duration, watched/resume position, description, date added, source availability. Do not assume all exist just because they would be convenient. Use adapter mapping and conditional display.

**Data rules**

- Build a thin adapter layer between existing backend and visual components; do not rewrite database models just for visuals.
- Do not hallucinate metadata. A blank description is acceptable and should look intentional.
- Media IDs must remain stable for focus restoration and continuation state.
- Continue Watching is sourced from persisted progress. Do not synthesize it from recently viewed navigation.
- Rescan state and source-unavailable state remain separate from missing/deleted file status.
- Never delete content due solely to a temporarily unreachable source.
- Player, scanner, and folder removal remain read-only toward media file bytes.
- If the design is shown without a connected real library, display a clearly labeled "UI preview - no media library connected" state with no fictitious titles. Do not present it as a functional library.

## 16. Empty, loading, and failure states

| State | Required treatment | Primary action |
|---|---|---|
| First run, zero sources | Calm branded empty Stage; explain local folders | Add media folder |
| Scanning | Visible progress/status from actual scanner; no invented percentage | Browse existing library if possible |
| Empty scan result | "No supported media found in this folder" plus source path | Review folder / Scan again |
| NAS/source unreachable | Keep indexed library visible; source-specific warning | Retry scan / Inspect source |
| Missing poster | Typography card from real title; same interaction | Play / Details |
| No search matches | State actual query, offer reset | Clear search |
| File unavailable at play | Error without deleting index entry | Back / Retry |
| SQLite/backend failure | Technical detail in diagnostic area; no fabricated library | Retry / Diagnostics if implemented |
| Long title | Wrap or ellipsis + full accessible label | Normal navigation |
| Large library | Progressive loading/virtualization, count only if known | Browse / Search |

For loading, use skeletons shaped like real components only when data is genuinely loading. Never leave perpetual animated placeholders to conceal failed requests.

## 17. Accessibility and comfort

- Meet **WCAG 2.2 AA** where applicable to a desktop/TV UI. Minimum 4.5:1 for normal text, 3:1 for large text and meaningful UI boundaries, including computed compositing over backdrop imagery.
- Use semantic links, buttons, dialogs, nav, headings, proper label relationships, and descriptive media names. Avoid div-only click surfaces with no keyboard support.
- Visible keyboard/gamepad focus cannot rely exclusively on a small color shift.
- Honor system text scaling; layout must not clip primary actions at 125-200% desktop zoom where feasible.
- Do not use small all-caps labels for essential information in 10-foot mode.
- No flashing, unrequested animation, auto-playing previews, or rapid crossfade loops.
- Screen reader must announce selected titles, Play/Resume labels, progress when actual, loading, and source status.
- Provide accessible alternatives for Atlas and Filmstrip. The spatial version is a visual option, never the sole route to a title.
- Dialog focus traps should restore previous focus; escape routes must be predictable.
- Avoid extremely dark overlay text. Test grayscale and color-blind simulation so state does not depend on hue alone.

## 18. Implementation guidance for Emergent

### 18.1 Before writing UI code

Inspect the imported repository, framework, package manager, routes, tests, media playback interfaces, SQLite access, CSS approach, and local host architecture. Document the real stack. Importing a repo into Emergent may require starting a new job; do not assume a mid-job sync mechanism exists.

Create a branch/checkpoint and run existing tests before major changes. Record baseline failures separately from new failures.

### 18.2 Component architecture (conceptual, not stack mandate)

- `AppShell`, `PrimaryNav`, `LibraryStatus`
- `StageHero`, `HeroActions`, `ArtworkBackdrop`
- `LivingFilmstrip`, `PosterCard`, `PosterGrid`, `ViewToggle`
- `MovieDetails`, `ShowDetails`, `SeasonSelector`, `EpisodeJourney`
- `SearchPanel`, `FilterBar`, `EmptyState`, `StatusBanner`
- `PlayerOSD`, `ProgressControl`, `ResumeChoice`
- `SourceList`, `SourceStatus`, `FolderManager`
- `FocusController` / input adapter, `MediaLibraryAdapter`, design token stylesheet

Component names are suggestions. Match the actual codebase conventions, preserve data contracts, and avoid adding unnecessary dependencies.

### 18.3 Styling approach

Create a central token source (`horizon.tokens.json`) and CSS variables or the equivalent theme object. Separate core semantics from decorative variants; a card should remain usable with all animations disabled. Keep design primitives composable and inspect contrast in real rendered states.

### 18.4 App/runtime boundary

The media host must stay responsible for local filesystem operations, byte-range streaming, and data persistence. A remote browser preview cannot be assumed to access arbitrary Windows disks or NAS shares. If Emergent's preview lacks those host capabilities, present it as a visual preview, not proof of end-to-end local integration. Do not copy private media into Emergent hosting without explicit authorization.

### 18.5 Delivery increments

1. **Foundation / Home:** tokens, shell, controller-aware focus, Stage, Continue Watching, basic real-data Filmstrip, first-run screen.
2. **Browse / Search / Details:** Movies, TV, filtering, accessible grid fallback, actual title metadata.
3. **TV / Player:** Episode Journey and OSD styling while maintaining playback semantics.
4. **Sources / QA:** Library utility UI, unreachable states, keyboard/controller testing, layout/accessibility regression.
5. **Optional Atlas:** add only after the above is stable, without reducing navigation performance.

Every increment should have a usable interactive preview, a test report, and a statement of what could not be verified. Don't silently replace real data with placeholders to satisfy a demo.

## 19. Acceptance tests and review checklist

### 19.1 Functional regression

- [ ] Existing Phase 0 tests run with results documented.
- [ ] A real folder can still be added and rescanned without duplicates.
- [ ] An unreachable NAS preserves indexed records and shows the correct status.
- [ ] Media files have unchanged fingerprints before/after scanning, playback, streaming, and source removal.
- [ ] Real movie plays, pauses, seeks, adjusts volume, enters fullscreen, and can resume/start over.
- [ ] Continue Watching reflects persisted data and survives app restart.
- [ ] No user-visible feature is secretly backed by mock API responses or invented library entries.

### 19.2 Screen and interaction QA

- [ ] Home, Movies, TV, Details, Player, Search, and Library screens work with mouse and keyboard.
- [ ] Directional focus follows visible geometry; active item has an unmistakable ring.
- [ ] Back restores the prior title, season, and browsing position.
- [ ] Contextual controller actions have clear labels and no dead ends.
- [ ] Filmstrip has working grid alternative and respects reduced motion.
- [ ] Long names, no artwork, no synopsis, zero sources, scanning, and unavailable source are coherent.
- [ ] No primary UI is clipped at 1366x768, 1920x1080, and simulated 3840x2160.
- [ ] Tested at 125% and 200% browser/OS zoom as appropriate to actual host.
- [ ] Contrast measured over rendered artwork and focus states.
- [ ] Hundreds of titles remain browseable without rendering every full-resolution image at once.
- [ ] UI remains usable without internet after data has been indexed locally.

### 19.3 Platform verification ledger

- **Linux dev:** re-test against existing app baseline; report actual results.
- **Windows PC:** not verified today; record setup, folder browsing, UNC paths, playback, focus, fullscreen, and scan results when tested.
- **Xbox console:** not verified today; hardware/runtime compatibility must be researched and tested, including controller mapping and local source access. A web gamepad test is not Xbox certification.

### 19.4 Visual review scoring (1-5 each)

Score **focus clarity**, **legibility at 10 feet**, **character without cliché**, **directness of Play/Resume**, **real-data integrity**, **performance**, **reduced-motion quality**, and **error-state honesty**. Any dimension below 4 blocks visual signoff until corrected. This is a proposed internal design review rubric, not a test result.

## 20. Things Horizon must not become

- A Netflix/Plex/Kodi clone with rows copied from their layouts.
- A technical dashboard dominating the Home screen.
- A demo using nonexistent movie titles or fake posters.
- A decorative 3D environment that is slower than an ordinary grid.
- A UI that requires hover or internet access to perform basic actions.
- A UI that deletes library entries because a NAS is temporarily disconnected.
- A feature checklist full of clickable elements that have no implementation.
- A claim of "Xbox ready" based solely on a desktop browser preview.

## 21. Handoff artifacts and definition of done

Deliver source changes to the actual application, updated tokens/theme, responsive UI components, keyboard/focus behavior, real-data bindings, tests, and screenshots at the requested viewport sizes. Include a short written handoff identifying files changed, test commands/results, performance considerations, accessibility gaps, and platform-specific unknowns.

**Design-system acceptance:** a reviewer can point to any visible color, spacing, type style, interactive control, or screen transition and find its rationale here or a documented extension. A beautiful screenshot without working navigation and real library data is not completion.
