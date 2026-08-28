from pathlib import Path
from tkinter import StringVar, IntVar, BooleanVar
from concurrent.futures import ThreadPoolExecutor
import threading
import tkinter as tk

from .config.common import *
from .core.models import Track
from .core.platform import configure_windows_app_identity, apply_windows_icon
from .core.runtime_cache import clear_runtime_cache
from .core.queue_mixin import QueueMixin
from .core.player_mixin import PlayerMixin
from .core.cache_mixin import CacheMixin
from .services.youtube_mixin import YouTubeMixin
from .ui.ui_mixin import UIMixin
from .ui.settings_mixin import SettingsMixin

class App(SettingsMixin, UIMixin, YouTubeMixin, QueueMixin, CacheMixin, PlayerMixin):
    def __init__(self, root: tk.Tk):
            self.root = root
            root.title(APP_NAME)
            root.geometry("1180x760")
            root.minsize(920, 620)
    
            self.settings = self.load_settings()
            self.language = self.settings.get("language", "en") if self.settings.get("language", "en") in LANGUAGES else "en"
            self.theme_name = "dark"
            self.theme = THEMES[self.theme_name]
            self.search_placeholder_active = False
            self.search_bar_canvas = None
            self.search_icon_window = None
            self.search_placeholder_label = None
            self.search_placeholder_window = None
            self.search_has_focus = False
            self.settings_window = None
            self.legal_window = None
            self._language_widgets = []
            self._settings_widgets = {}
    
            self.queue: list[Track] = []
            self.current_results: list[Track] = []
            self.current_index = -1
            self.current_audio_path: Path | None = None
    
            self.playing = False
            self.paused = False
            self.position_anchor = 0.0
            self.position_anchor_monotonic = 0.0
            self.mixer_pos_anchor_ms = 0
            self.seek_generation = 0
            self._closing = False
            self._resolving = False
            self._process_generation = 0
            self._volume_dragging = False
            self.seeking = False
            self.cache_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="audio-cache")
            self.cache_futures: dict[str, object] = {}
            self.cache_failures: dict[str, Exception] = {}
            self._queue_validation_pending: set[str] = set()
            self.cache_lock = threading.Lock()
            self.play_mode = StringVar(value="normal")
            self.play_mode_display = StringVar(value=self.tr("normal"))
    
            self.search_limit = IntVar(value=self._clamp_int(self.settings.get("search_results", 10), 1, 50))
            self.cache_enabled = BooleanVar(value=bool(self.settings.get("prefetch_enabled", True)))
            cache_mode = self.settings.get("prefetch_mode", "streaming")
            if cache_mode not in {"streaming", "smart", "mixed"}:
                cache_mode = "streaming"
            self.cache_mode = StringVar(value=cache_mode)
    
            self.volume = IntVar(value=80)
            self.thumb_photo = None
            self.status = StringVar(value=self.tr("ready"))
            self.query = StringVar()
            self.repeat = BooleanVar(value=False)
            self.queue_size_var = StringVar(value=self.tr("queue"))
            self.time_label_var = StringVar(value="00:00 / 00:00")
    
            self.build_ui()
            self.update_add_queue_button_state()
            self.bind_events()
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
            self.init_audio()
            self.refresh_buttons()
            self.root.after(50, self.maybe_show_legal_notice)
            self.poll_player()
