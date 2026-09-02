# Changelog

All notable changes to Sonus are documented in this file.

## [1.2.0] - 2026-09-02

### Added

- Playback-time handling of unavailable tracks: skipped with a status message, playback advances automatically; pre-queue availability checks removed, playlists with 100+ tracks are added instantly.
- Skip reasons in the status line with the track title (unavailable / network error / timeout).
- Automatic retry of tracks failed with network errors: on queue repeat, on shuffle fallback, and on manual selection.
- Volume level persisted in settings.json; default volume is 50%.
- README notes (RU/EN) about VPN/proxy requirement in regions with restricted YouTube access.

### Changed

- Runtime cache cleanup now runs at application startup.
- yt-dlp network hardening: socket timeout, limited retries, bounded track preparation wait.

### Fixed

- Application freeze on HTTP 403/404/5xx, SSL handshake timeout and offline network conditions.
- Crash (NameError) in the playback error callback caused by late binding of the exception variable in a deferred callback.
- Repeat-queue mode restarting from the first track instead of advancing after a skip.
- Repeat-current mode stopping playback instead of advancing past an unavailable track.
- Corrupted or truncated cached thumbnails not being re-downloaded.

## [1.1.0] - 2026-08-28

### Added

- Keyboard shortcuts for the main application window:
  - `Up` / `Down` — increase or decrease volume by 5%.
  - `Right` / `Left` — switch to the next or previous track.
  - `Enter` — play/pause.
- Keyboard shortcuts are limited to the active Sonus window and do not operate while the application is minimized or another Sonus dialog has focus.

### Changed

- Refactored the application from a single large source file into focused modules without intentionally changing the existing playback and queue architecture.
- Separated application coordination, playback, queue management, caching, YouTube services, UI, settings, configuration and Windows platform helpers into dedicated modules.
- Kept the existing global-release workflow and Windows launcher while moving the implementation behind the minimal `app.py` entry point.

### Fixed

- Arrow-key shortcuts no longer move the queue selection like normal Listbox navigation when they are used as Sonus playback shortcuts.
- Keyboard shortcuts continue to work independently of the active Russian/English keyboard layout where applicable.

## [1.0.0] - 2026-08-27

### Added

- Direct YouTube video processing.
- YouTube playlist processing.
- Text search for music-oriented YouTube results.
- Search result previews and titles.
- Combined queue for playlists and individual tracks.
- Play, pause, previous and next track controls.
- Manual seek and ±10 second seeking.
- Independent playback volume control.
- Background audio caching.
- Streaming, Smart and Mixed caching modes.
- Sequential, repeat-queue and random playback modes.
- Configurable search results from 1 to 50.
- Dark Sonus interface with rounded panels.
- English and Russian interface languages.
- Application icon and console-free GUI launch.
- Automatic cache cleanup at application startup.
- Automatic Windows setup through `run_windows.bat`.

### Fixed

- Multiple simultaneous playback processes.
- Pause/resume timing drift caused by restarting network playback.
- Inaccurate seek behavior.
- Queue replacement when adding additional videos/playlists.
- Keyboard shortcuts under Russian keyboard layout.
- Queue item selection and deletion.
- Settings window scrolling and application shutdown behavior.

### Legal / Release policy

- Added a one-time first-run legal notice and acknowledgement.
- Streaming is the default cache mode.
- Standardized release guidance to source-only releases without bundled third-party binaries.
- Added legal and DMCA guidance to project documentation.
- Standardized the launcher branding to Sonus.

[1.2.0]: https://github.com/LogicFrame/Sonus/releases/tag/v1.2.0
[1.1.0]: https://github.com/LogicFrame/Sonus/releases/tag/v1.1.0
[1.0.0]: https://github.com/LogicFrame/Sonus/releases/tag/v1.0.0
