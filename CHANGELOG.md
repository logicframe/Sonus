# Changelog

All notable changes to Sonus are documented in this file.

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

[1.1.0]: https://github.com/LogicFrame/Sonus/releases/tag/v1.1.0
[1.0.0]: https://github.com/LogicFrame/Sonus/releases/tag/v1.0.0
