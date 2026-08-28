# Sonus architecture

Sonus is split into small modules while keeping the existing application behavior.

- `app.py` - minimal entry point.
- `sonus/app.py` - application coordinator and state initialization.
- `sonus/core/models.py` - track data model.
- `sonus/core/player_mixin.py` - pygame playback, pause, seek and volume.
- `sonus/core/queue_mixin.py` - queue operations and playback modes.
- `sonus/core/cache_mixin.py` - background audio caching.
- `sonus/core/runtime_cache.py` - startup cache cleanup.
- `sonus/services/youtube_mixin.py` - yt-dlp processing and search.
- `sonus/ui/ui_mixin.py` - main interface, controls and custom widgets.
- `sonus/ui/settings_mixin.py` - settings and localization UI.
- `sonus/ui/widgets.py` - reusable rounded UI card.
- `sonus/config/common.py` - application constants, translations and themes.
- `sonus/core/platform.py` - Windows icon/application identity helpers.
- `sonus/core/utils.py` - small shared helpers.
