import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, X, Y, StringVar, IntVar, BooleanVar
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pygame
except ImportError:
    pygame = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

APP_DIR = Path(__file__).resolve().parent
CACHE_DIR = APP_DIR / "cache"
AUDIO_CACHE_DIR = CACHE_DIR / "audio"
SETTINGS_FILE = APP_DIR / "settings.json"
APP_NAME = "Sonus"

# Windows shell/taskbar identity and icon helpers.  These are intentionally
# kept dependency-free so the Global build does not need pywin32.
_WINDOWS_ICON_HANDLES = []

def configure_windows_app_identity() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LogicFrame.Sonus")
    except Exception:
        pass


def apply_windows_icon(window: tk.Misc, icon_path: Path) -> None:
    """Apply Sonus icon to a Tk window and its Windows taskbar representation."""
    if os.name != "nt" or not icon_path.exists():
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(int(window.winfo_id()))

        # Load the ICO file directly so the taskbar does not fall back to
        # pythonw.exe's icon.
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        icon = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if icon:
            _WINDOWS_ICON_HANDLES.append(icon)
            WM_SETICON = 0x0080
            ICON_BIG = 1
            ICON_SMALL = 0
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon)
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon)

            # Also set the class icon used by the shell for the top-level Tk
            # window.  This complements WM_SETICON on Windows 10.
            GCLP_HICON = -14
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                user32.SetClassLongPtrW(hwnd, GCLP_HICON, icon)
            else:
                user32.SetClassLongW(hwnd, GCLP_HICON, icon)
    except Exception:
        pass

LANGUAGES = {
    "en": {
        "search_placeholder": "Enter a track, artist, playlist or YouTube link…",
        "subtitle": "YouTube audio player",
        "process": "Process",
        "search_results": "Search results",
        "enter_query": "Enter a query or link.",
        "queue": "Queue",
        "queue_empty": "Queue is empty",
        "queue_hint": "Double-click — play. Ctrl+A — select all. Delete/Backspace — remove.",
        "now_playing": "Now playing",
        "preview": "Preview",
        "nothing_selected": "Nothing selected",
        "playback": "Playback",
        "mode": "Mode",
        "volume": "Volume",
        "add_to_queue": "Add to queue →",
        "normal": "Normal",
        "repeat_current": "Repeat current",
        "repeat_queue": "Repeat queue",
        "shuffle": "Shuffle",
        "ready": "Ready",
        "processing": "Processing…",
        "getting_data": "Getting data from YouTube…",
        "processing_error": "Processing error",
        "error": "Error",
        "nothing_found": "Nothing found.",
        "nothing_found_status": "Nothing found",
        "double_click_hint": "Double-click — add and play. “Add to queue →” — add without stopping the current track.",
        "found": "Found: {n}",
        "added_queue": "Added to queue: {n}",
        "link_added": "The link added {n} track(s) to the queue.",
        "search_first": "Search for something first",
        "track_added": "Track added to queue",
        "track_removed_play": "Track removed. Switching…",
        "removed_queue": "Removed from queue: {n}",
        "queue_cleared": "Queue cleared",
        "preparing_audio": "Preparing audio…",
        "queue_status": "In queue: {n} · Caching started",
        "playback_error": "Playback error",
        "playing": "Playing",
        "paused": "Paused",
        "pause_error": "Pause error: {e}",
        "resume_error": "Resume error: {e}",
        "seek_error": "Seek error: {e}",
        "queue_finished": "Queue finished",
        "preview_unavailable": "Preview unavailable",
        "dependency_missing": "Dependency not found",
        "unexpected_error": "An unexpected error occurred:\n\n{e}",
        "settings_title": "Settings",
        "settings_search_results": "Search results",
        "settings_search_desc": "Number of results for each new search. Choose from 1 to 50.",
        "results_label": "Results:",
        "cache_title": "Track caching",
        "cache_desc": "Background caching does not affect playback. When disabled, the current track is still cached when playback starts.",
        "cache_enable": "Cache tracks in the background",
        "download_mode": "Download mode",
        "streaming": "Streaming",
        "streaming_desc": "Download all tracks in order, from the first in the queue to the last.",
        "smart": "Smart",
        "smart_desc": "Download the currently selected track first, then all other tracks in queue order.",
        "mixed": "Mixed",
        "mixed_desc": "Download the current track first, then two previous and two next tracks; continue in queue order afterward.",
        "language": "Language",
        "language_desc": "Choose the language used by the Sonus interface.",
        "english": "English",
        "russian": "Русский",
        "close": "Close",
        "settings_saved_mode": "Settings saved · {mode} caching",
        "settings_saved_off": "Settings saved · background caching disabled",
        "yt_missing": "yt-dlp is not installed. Run run_windows.bat or pip install -r requirements.txt",
        "pygame_missing": "pygame is not installed. Run run_windows.bat or pip install -r requirements.txt",
        "ffmpeg_missing": "ffmpeg was not found. It is required to prepare the OGG audio cache.",
        "no_title": "Untitled",
        "pause_playback": "Pause",
        "play_playback": "Play",
        "status_play": "Playback",
        "status_paused": "Paused",
        "status_resume": "Playback",
        "settings_error_title": "Settings",
        "default_language": "English",
        "legal_title": "Before you start",
        "legal_text": "Sonus is an independent desktop player intended for personal, non-commercial use.\n\nSonus does not host, store, or distribute YouTube media. Content is accessed at your request and may be temporarily cached on your device for playback and time-shifting.\n\nYou are responsible for complying with YouTube's Terms of Service, copyright law, and the rights of content creators. Use Sonus only with content you are permitted to access.",
        "legal_agree": "I agree",
        "legal_exit": "Exit",
    },
    "ru": {
        "search_placeholder": "Введите название трека, исполнителя, плейлист или ссылку YouTube…",
        "subtitle": "Аудиоплеер YouTube",
        "process": "Обработать",
        "search_results": "Результаты поиска",
        "enter_query": "Введите запрос или ссылку.",
        "queue": "Очередь",
        "queue_empty": "Очередь пуста",
        "queue_hint": "Двойной клик — воспроизвести. Ctrl+A — выбрать все. Delete/Backspace — удалить.",
        "now_playing": "Сейчас играет",
        "preview": "Превью",
        "nothing_selected": "Ничего не выбрано",
        "playback": "Управление воспроизведением",
        "mode": "Режим",
        "volume": "Громкость",
        "add_to_queue": "В очередь →",
        "normal": "Обычный",
        "repeat_current": "Повтор текущего",
        "repeat_queue": "Повтор очереди",
        "shuffle": "Случайный",
        "ready": "Готово",
        "processing": "Обрабатываю…",
        "getting_data": "Получение данных с YouTube…",
        "processing_error": "Ошибка обработки",
        "error": "Ошибка",
        "nothing_found": "Ничего не найдено.",
        "nothing_found_status": "Ничего не найдено",
        "double_click_hint": "Двойной клик — добавить и запустить. «В очередь →» — добавить без остановки текущего трека.",
        "found": "Найдено: {n}",
        "added_queue": "Добавлено в очередь: {n}",
        "link_added": "Ссылка добавила {n} трек(ов) в очередь.",
        "search_first": "Сначала выполните поиск",
        "track_added": "Трек добавлен в очередь",
        "track_removed_play": "Трек удалён. Переключение…",
        "removed_queue": "Удалено из очереди: {n}",
        "queue_cleared": "Очередь очищена",
        "preparing_audio": "Готовлю аудио…",
        "queue_status": "В очереди: {n} · Кэширование запущено",
        "playback_error": "Ошибка воспроизведения",
        "playing": "Воспроизведение",
        "paused": "Пауза",
        "pause_error": "Ошибка паузы: {e}",
        "resume_error": "Ошибка продолжения: {e}",
        "seek_error": "Перемотка: {e}",
        "queue_finished": "Очередь закончена",
        "preview_unavailable": "Превью недоступно",
        "dependency_missing": "Зависимость не найдена",
        "unexpected_error": "Произошла непредвиденная ошибка:\n\n{e}",
        "settings_title": "Настройки",
        "settings_search_results": "Результаты поиска",
        "settings_search_desc": "Количество результатов при каждом новом поиске. Можно выбрать от 1 до 50.",
        "results_label": "Результатов:",
        "cache_title": "Загрузка треков в кэш",
        "cache_desc": "Фоновая загрузка не влияет на воспроизведение. При отключении текущий трек всё равно будет загружен при запуске.",
        "cache_enable": "Загружать треки в кэш в фоне",
        "download_mode": "Режим загрузки",
        "streaming": "Потоковая",
        "streaming_desc": "Все треки скачиваются по порядку: от первого в очереди до последнего.",
        "smart": "Умная",
        "smart_desc": "Сначала загружается текущий выбранный трек, затем все остальные по порядку очереди.",
        "mixed": "Смешанная",
        "mixed_desc": "Сначала текущий трек, затем два предыдущих и два следующих; далее — остальные по порядку.",
        "language": "Язык",
        "language_desc": "Выберите язык интерфейса Sonus.",
        "english": "English",
        "russian": "Русский",
        "close": "Закрыть",
        "settings_saved_mode": "Настройки сохранены · {mode} загрузка",
        "settings_saved_off": "Настройки сохранены · фоновое кэширование отключено",
        "yt_missing": "Не установлен yt-dlp. Выполните run_windows.bat или pip install -r requirements.txt",
        "pygame_missing": "Не установлен pygame. Выполните run_windows.bat или pip install -r requirements.txt",
        "ffmpeg_missing": "Не найден ffmpeg. Он нужен для подготовки аудио-кэша OGG.",
        "no_title": "Без названия",
        "pause_playback": "Пауза",
        "play_playback": "Воспроизвести",
        "status_play": "Воспроизведение",
        "status_paused": "Пауза",
        "status_resume": "Воспроизведение",
        "settings_error_title": "Настройки",
        "default_language": "English",
        "legal_title": "Перед началом",
        "legal_text": "Sonus — независимый настольный проигрыватель для личного некоммерческого использования.\n\nSonus не размещает, не хранит и не распространяет медиаконтент YouTube. Контент запрашивается пользователем и может временно кэшироваться на вашем устройстве для воспроизведения и перемотки.\n\nВы несёте ответственность за соблюдение Условий использования YouTube, авторского права и прав создателей контента. Используйте Sonus только с контентом, к которому у вас есть право доступа.",
        "legal_agree": "Я согласен",
        "legal_exit": "Выйти",
    },
}

SEARCH_PLACEHOLDER = LANGUAGES["en"]["search_placeholder"]

THEMES = {
    "dark": {
        "name": "Тёмная",
        "bg": "#0e1118",
        "surface": "#151922",
        "surface_alt": "#1b202b",
        "surface_hover": "#22283a",
        "border": "#2b3140",
        "text": "#f4f5f8",
        "muted": "#8e96a8",
        "accent": "#9b6cff",
        "accent_hover": "#b089ff",
        "accent_text": "#ffffff",
        "select_bg": "#3b2a66",
        "select_text": "#ffffff",
        "placeholder": "#777f91",
        "danger": "#ef6262",
    },
}



def clear_runtime_cache() -> None:
    """Remove all cache left by a previous application session.

    Cleanup is intentionally performed at startup rather than relying on a
    window-close callback, because a process can be terminated in many ways
    on Windows. Any cache needed by the current session is recreated below.
    """
    try:
        if CACHE_DIR.exists():
            for child in CACHE_DIR.iterdir():
                try:
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                except OSError:
                    # A single stale/locked cache file should not prevent the
                    # application from starting. It can be removed next run.
                    pass
    finally:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


clear_runtime_cache()

YOUTUBE_URL_RE = re.compile(r"^(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/", re.I)


@dataclass
class Track:
    id: str
    title: str
    url: str
    thumbnail: str = ""
    duration: float = 0.0
    channel: str = ""

    @property
    def label(self):
        return f"{self.title} — {self.channel}" if self.channel else self.title


class RoundedCard(tk.Frame):
    """A small reusable rounded panel used to keep the UI surfaces visually consistent."""
    def __init__(self, master, theme, radius=16, padding=1, **kwargs):
        self._theme = theme
        self._radius = radius
        self._padding = padding
        super().__init__(master, bg=theme["bg"], bd=0, highlightthickness=0, **kwargs)
        self.canvas = tk.Canvas(self, bg=theme["bg"], bd=0, highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True)
        self.content = tk.Frame(self.canvas, bg=theme["surface"], bd=0, highlightthickness=0)
        self._window = self.canvas.create_window(padding, padding, anchor="nw", window=self.content)
        self.canvas.bind("<Configure>", self._redraw)
        self.after(0, self._redraw)

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        r = min(radius, max(1, (x2 - x1) / 2), max(1, (y2 - y1) / 2))
        points = [
            x1+r, y1, x2-r, y1, x2-r/2, y1, x2, y1+r/2,
            x2, y2-r, x2, y2-r/2, x2-r/2, y2, x1+r, y2,
            x1+r/2, y2, x1, y2-r/2, x1, y1+r, x1, y1+r/2
        ]
        return self.canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

    def _redraw(self, _event=None):
        self.canvas.delete("card-bg")
        w = max(4, self.canvas.winfo_width())
        h = max(4, self.canvas.winfo_height())
        self._rounded_rect(1, 1, w-1, h-1, self._radius, fill=self._theme["surface"], outline=self._theme["border"], width=1, tags="card-bg")
        self.canvas.tag_lower("card-bg")
        self.canvas.coords(self._window, self._padding, self._padding)
        self.canvas.itemconfigure(self._window, width=max(1, w - self._padding*2), height=max(1, h - self._padding*2))

    def apply_theme(self, theme):
        self._theme = theme
        self.configure(bg=theme["bg"])
        self.canvas.configure(bg=theme["bg"])
        self.content.configure(bg=theme["surface"])
        self._redraw()


class App:
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

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=self.theme["bg"])
        style.configure("TLabel", background=self.theme["surface"], foreground=self.theme["text"], font=("Segoe UI", 10))
        style.configure("Subtle.TLabel", background=self.theme["surface"], foreground=self.theme["muted"])
        style.configure("Title.TLabel", background=self.theme["bg"], foreground=self.theme["text"], font=("Segoe UI", 20, "bold"))
        style.configure("Brand.TLabel", background=self.theme["bg"], foreground=self.theme["text"], font=("Segoe UI", 18, "bold"))
        style.configure("TButton", background=self.theme["surface_alt"], foreground=self.theme["text"], borderwidth=0, padding=(12, 8), font=("Segoe UI", 9))
        style.map("TButton", background=[("active", self.theme["surface_hover"]), ("pressed", self.theme["surface_hover"]), ("disabled", self.theme["surface_alt"])], foreground=[("disabled", self.theme["muted"])])
        style.configure("Accent.TButton", background=self.theme["accent"], foreground=self.theme["accent_text"], borderwidth=0, padding=(14, 9), font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", self.theme["accent_hover"]), ("pressed", self.theme["accent_hover"]), ("disabled", self.theme["surface_alt"])], foreground=[("disabled", self.theme["muted"])])
        style.configure("TLabelFrame", background=self.theme["surface"], foreground=self.theme["text"], bordercolor=self.theme["border"], lightcolor=self.theme["border"], darkcolor=self.theme["border"], relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=self.theme["surface"], foreground=self.theme["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TCombobox", fieldbackground=self.theme["surface_alt"], background=self.theme["surface_alt"], foreground=self.theme["text"], arrowcolor=self.theme["muted"], bordercolor=self.theme["border"])
        style.configure("Compact.TCombobox", fieldbackground=self.theme["surface_alt"], background=self.theme["surface_alt"], foreground=self.theme["text"], arrowcolor=self.theme["muted"], bordercolor=self.theme["border"], padding=(4, 2), arrowsize=10, font=("Segoe UI", 9))
        style.configure("Sonus.TSpinbox", fieldbackground=self.theme["surface_alt"], background=self.theme["surface_alt"], foreground=self.theme["text"], arrowcolor=self.theme["accent"], bordercolor=self.theme["border"], padding=(2, 1), arrowsize=9, font=("Segoe UI", 9))
        style.map("Sonus.TSpinbox", fieldbackground=[("focus", self.theme["surface_hover"])], foreground=[("disabled", self.theme["muted"])])
        style.configure("Sonus.TCheckbutton", background=self.theme["surface"], foreground=self.theme["text"], indicatorcolor=self.theme["accent"], focusthickness=0, padding=(0, 1))
        style.map("Sonus.TCheckbutton", foreground=[("disabled", self.theme["muted"])], indicatorcolor=[("selected", self.theme["accent"]), ("active", self.theme["accent_hover"])])
        style.map("TCombobox", fieldbackground=[("readonly", self.theme["surface_alt"])], selectbackground=[("readonly", self.theme["surface_alt"])], selectforeground=[("readonly", self.theme["text"])])
        # Accent-colored controls keep all sliders/scrollbars readable in the dark UI.
        style.configure(
            "Horizontal.TScale",
            background=self.theme["surface"],
            troughcolor=self.theme["surface_alt"],
            borderwidth=0,
            sliderlength=18,
        )
        style.map(
            "Horizontal.TScale",
            background=[("active", self.theme["accent_hover"]), ("pressed", self.theme["accent"])],
            troughcolor=[("active", self.theme["surface_hover"])],
        )
        for sb_style in ("Vertical.TScrollbar", "Horizontal.TScrollbar", "TScrollbar"):
            style.configure(
                sb_style,
                background=self.theme["accent"],
                troughcolor=self.theme["surface_alt"],
                arrowcolor=self.theme["accent"],
                bordercolor=self.theme["surface"],
                lightcolor=self.theme["accent"],
                darkcolor=self.theme["accent"],
            )
            style.map(
                sb_style,
                background=[("active", self.theme["accent_hover"]), ("pressed", self.theme["accent_hover"])],
            )

        outer = ttk.Frame(self.root, padding=(18, 16, 18, 12))
        outer.pack(fill=BOTH, expand=True)
        outer.configure(style="TFrame")

        header = tk.Frame(outer, bg=self.theme["bg"], bd=0, highlightthickness=0)
        header.pack(fill=X, pady=(0, 14))

        self.app_icon_photo = self.load_app_icon(36)
        icon_label = tk.Label(header, image=self.app_icon_photo, bg=self.theme["bg"], bd=0)
        icon_label.pack(side=LEFT, padx=(0, 9))
        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side=LEFT)
        self.subtitle_label = ttk.Label(header, text=self.tr("subtitle"), style="Subtle.TLabel")
        self.subtitle_label.pack(side=LEFT, padx=(10, 0), pady=(7, 0))

        self.settings_button = ttk.Button(header, text="⚙", width=3, command=self.open_settings)
        self.settings_button.pack(side=RIGHT)

        search_row = tk.Frame(outer, bg=self.theme["bg"], bd=0, highlightthickness=0)
        search_row.pack(fill=X)
        search_row.columnconfigure(0, weight=1)

        self.search_bar_canvas = tk.Canvas(search_row, height=48, bg=self.theme["bg"], highlightthickness=0, bd=0)
        self.search_bar_canvas.grid(row=0, column=0, sticky="ew")
        self.search_bar_canvas.bind("<Configure>", self._redraw_search_bar)

        self.search_icon = tk.Label(self.search_bar_canvas, text="⌕", bg=self.theme["surface_alt"], fg=self.theme["muted"], font=("Segoe UI Symbol", 17))
        self.search_icon_window = self.search_bar_canvas.create_window(24, 24, window=self.search_icon, anchor="center")
        self.input_entry = tk.Entry(self.search_bar_canvas, textvariable=self.query, bg=self.theme["surface_alt"], fg=self.theme["text"], insertbackground=self.theme["text"], relief="flat", bd=0, highlightthickness=0, font=("Segoe UI", 11), selectbackground=self.theme["select_bg"], selectforeground=self.theme["select_text"])
        self.search_entry_window = self.search_bar_canvas.create_window(50, 24, window=self.input_entry, anchor="w", width=600)
        self.search_placeholder_label = tk.Label(self.search_bar_canvas, text="", bg=self.theme["surface_alt"], fg=self.theme["placeholder"], font=("Segoe UI", 11), bd=0, highlightthickness=0, anchor="w")
        self.search_placeholder_window = self.search_bar_canvas.create_window(50, 24, window=self.search_placeholder_label, anchor="w", width=600)
        self.search_placeholder_label.bind("<Button-1>", self._focus_search_from_placeholder)

        self.process_button = ttk.Button(search_row, text=self.tr("process"), style="Accent.TButton", command=self.process_input)
        self.process_button.grid(row=0, column=1, padx=(10, 0), ipady=2)

        body = ttk.Frame(outer, style="TFrame")
        body.pack(fill=BOTH, expand=True, pady=(16, 10))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=2)
        left.rowconfigure(2, weight=3)

        result_frame = RoundedCard(left, self.theme, radius=16, padding=1)
        result_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        result_content = result_frame.content
        result_content.columnconfigure(0, weight=1)
        result_content.rowconfigure(1, weight=1)
        self.results_title_label = tk.Label(result_content, text=self.tr("search_results"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        self.results_title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(11, 8))
        self.results_listbox = tk.Listbox(result_content, activestyle="none", font=("Segoe UI", 10), selectmode=tk.BROWSE, relief="flat", bd=0, highlightthickness=0)
        self.results_listbox.grid(row=1, column=0, sticky="nsew", padx=(14, 0))
        rsb = ttk.Scrollbar(result_content, orient="vertical", style="Vertical.TScrollbar", command=self.results_listbox.yview)
        rsb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 2))
        self.results_listbox.configure(yscrollcommand=rsb.set)
        self.results_hint = ttk.Label(result_content, text=self.tr("enter_query"), style="Subtle.TLabel")
        self.results_hint.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 11))

        self.queue_frame = RoundedCard(left, self.theme, radius=16, padding=1)
        self.queue_frame.grid(row=2, column=0, sticky="nsew")
        queue_content = self.queue_frame.content
        queue_content.columnconfigure(0, weight=1)
        queue_content.rowconfigure(1, weight=1)
        self.queue_title_label = tk.Label(queue_content, text=self.tr("queue"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        self.queue_title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(11, 8))
        self.queue_listbox = tk.Listbox(queue_content, activestyle="none", font=("Segoe UI", 10), selectmode=tk.EXTENDED, relief="flat", bd=0, highlightthickness=0)
        self.queue_listbox.grid(row=1, column=0, sticky="nsew", padx=(14, 0))
        qsb = ttk.Scrollbar(queue_content, orient="vertical", style="Vertical.TScrollbar", command=self.queue_listbox.yview)
        qsb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 2))
        self.queue_listbox.configure(yscrollcommand=qsb.set)
        self.queue_hint_label = ttk.Label(queue_content, text=self.tr("queue_hint"), style="Subtle.TLabel")
        self.queue_hint_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 11))

        right = ttk.Frame(body, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(1, weight=2)

        preview_card = RoundedCard(right, self.theme, radius=16, padding=1)
        preview_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        preview_content = preview_card.content
        preview_content.columnconfigure(0, weight=1)
        preview_content.rowconfigure(1, weight=1)
        self.now_playing_label = tk.Label(preview_content, text=self.tr("now_playing"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        self.now_playing_label.grid(row=0, column=0, sticky="w", padx=14, pady=(11, 8))
        self.preview = tk.Label(preview_content, text=self.tr("preview"), anchor="center", bg=self.theme["surface_alt"], fg=self.theme["muted"], bd=0, highlightthickness=0)
        self.preview.grid(row=1, column=0, sticky="nsew", padx=14)
        self.now_title = tk.Label(preview_content, text=self.tr("nothing_selected"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 13, "bold"), anchor="w", justify="left", wraplength=390)
        self.now_title.grid(row=2, column=0, sticky="w", padx=14, pady=(12, 4))
        self.now_channel = tk.Label(preview_content, text="", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), anchor="w")
        self.now_channel.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

        playback_card = RoundedCard(right, self.theme, radius=16, padding=1)
        playback_card.grid(row=1, column=0, sticky="nsew")
        playback_content = playback_card.content
        playback_content.columnconfigure(0, weight=1)
        playback_content.rowconfigure(2, weight=1)
        self.playback_label = ttk.Label(playback_content, text=self.tr("playback"), style="TLabel")
        self.playback_label.grid(row=0, column=0, sticky="w", padx=14, pady=(11, 2))
        ttk.Label(playback_content, textvariable=self.time_label_var, style="Subtle.TLabel").grid(row=1, column=0, sticky="w", padx=14, pady=(0, 2))
        self.slider = ttk.Scale(playback_content, from_=0, to=100, orient="horizontal", style="Horizontal.TScale")
        self.slider.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 10))

        controls = ttk.Frame(playback_content, style="TFrame")
        controls.grid(row=3, column=0, sticky="ew", padx=12)
        for i in range(5):
            controls.columnconfigure(i, weight=1)
        self.prev_btn = ttk.Button(controls, text="⏮", command=self.previous_track)
        self.prev_btn.grid(row=0, column=0, padx=2, sticky="ew")
        self.back_btn = ttk.Button(controls, text="−10s" if self.language == "en" else "−10с", command=lambda: self.seek_relative(-10))
        self.back_btn.grid(row=0, column=1, padx=2, sticky="ew")
        self.play_btn = ttk.Button(controls, text="▶", style="Accent.TButton", command=self.toggle_play)
        self.play_btn.grid(row=0, column=2, padx=2, sticky="ew")
        self.fwd_btn = ttk.Button(controls, text="+10s" if self.language == "en" else "+10с", command=lambda: self.seek_relative(10))
        self.fwd_btn.grid(row=0, column=3, padx=2, sticky="ew")
        self.next_btn = ttk.Button(controls, text="⏭", command=self.next_track)
        self.next_btn.grid(row=0, column=4, padx=2, sticky="ew")

        bottom = ttk.Frame(playback_content, style="TFrame")
        bottom.grid(row=4, column=0, sticky="ew", padx=12, pady=(10, 11))
        self.mode_label = ttk.Label(bottom, text=self.tr("mode"))
        self.mode_label.pack(side=LEFT)
        self.mode_combo = ttk.Combobox(bottom, textvariable=self.play_mode_display, values=tuple(self.tr(k) for k in ("normal", "repeat_current", "repeat_queue", "shuffle")), state="readonly", width=17)
        self.mode_combo.pack(side=LEFT, padx=(6, 12))
        self.mode_combo.bind("<<ComboboxSelected>>", self._mode_selected)
        self.mode_labels = {self.tr(k): k for k in ("normal", "repeat_current", "repeat_queue", "shuffle")}
        self.mode_combo.set(self.tr("normal"))
        self.volume_label = ttk.Label(bottom, text=self.tr("volume"))
        self.volume_label.pack(side=LEFT, padx=(10, 4))
        self.volume_scale = ttk.Scale(bottom, from_=0, to=100, orient="horizontal", variable=self.volume, length=125, style="Horizontal.TScale")
        self.volume_scale.pack(side=LEFT)
        self.volume_scale.bind("<Button-1>", self.volume_mouse_down)
        self.volume_scale.bind("<B1-Motion>", self.volume_mouse_drag)
        self.volume_scale.bind("<ButtonRelease-1>", self.volume_mouse_up)
        self.volume_value = ttk.Label(bottom, text="80%", width=5)
        self.volume_value.pack(side=LEFT, padx=(4, 0))
        self.add_queue_btn = ttk.Button(bottom, text=self.tr("add_to_queue"), command=self.add_selected_result)
        self.add_queue_btn.pack(side=RIGHT)

        self.set_listbox_theme()
        self.set_search_placeholder()
        self.root.after(0, self._redraw_search_bar)

        ttk.Label(outer, textvariable=self.status, style="Subtle.TLabel").pack(anchor="w")

    @staticmethod
    def _clamp_int(value, low, high):
        try:
            return max(low, min(high, int(value)))
        except (TypeError, ValueError):
            return low

    def tr(self, key, **kwargs):
        text = LANGUAGES[self.language].get(key, LANGUAGES["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def _mode_text(self, mode):
        return self.tr(mode)

    def load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def save_settings(self):
        try:
            data = {
                "theme": "dark",
                "language": self.language,
                "search_results": self._clamp_int(self.search_limit.get(), 1, 50),
                "prefetch_enabled": bool(self.cache_enabled.get()),
                "prefetch_mode": self.cache_mode.get() if self.cache_mode.get() in {"streaming", "smart", "mixed"} else "streaming",
                "legal_accepted": bool(self.settings.get("legal_accepted", False)),
            }
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, tk.TclError):
            pass

    def _settings_changed(self, _value=None):
        self.save_settings()
        if self.cache_enabled.get():
            self._cancel_pending_cache_jobs()
        if hasattr(self, "status"):
            mode_names = {
                "streaming": self.tr("streaming"),
                "smart": self.tr("smart"),
                "mixed": self.tr("mixed"),
            }
            if self.cache_enabled.get():
                self.status.set(self.tr("settings_saved_mode", mode=mode_names.get(self.cache_mode.get(), self.tr("streaming"))))
            else:
                self.status.set(self.tr("settings_saved_off"))
        if hasattr(self, "queue") and self.cache_enabled.get():
            self.prefetch_tracks([], force_reschedule=True)

    def _cancel_pending_cache_jobs(self):
        """Cancel queued-but-not-running cache tasks so a changed mode can reorder them."""
        with self.cache_lock:
            for key, future in list(self.cache_futures.items()):
                try:
                    if not future.running() and not future.done():
                        future.cancel()
                        self.cache_futures.pop(key, None)
                except Exception:
                    pass

    def load_app_icon(self, size=36):
        path = APP_DIR / "sonus.ico"
        if Image is None or not path.exists():
            return None
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def set_listbox_theme(self):
        common = {"bg": self.theme["surface_alt"], "fg": self.theme["text"], "selectbackground": self.theme["select_bg"], "selectforeground": self.theme["select_text"], "disabledforeground": self.theme["muted"], "highlightcolor": self.theme["border"], "highlightbackground": self.theme["border"]}
        self.results_listbox.configure(**common)
        self.queue_listbox.configure(**common)

    def _rounded_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1, x2-radius, y1,
            x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2,
            x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius,
            x1, y1+radius, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=20, **kwargs)

    def _redraw_search_bar(self, _event=None):
        if self.search_bar_canvas is None:
            return
        c = self.search_bar_canvas
        c.delete("bar")
        width = max(120, c.winfo_width())
        h = c.winfo_height() or 48
        self._rounded_rect(c, 1, 1, width-1, h-1, 22, fill=self.theme["surface_alt"], outline=self.theme["border"], width=1, tags="bar")
        c.tag_lower("bar")
        c.coords(self.search_icon_window, 24, h / 2)
        entry_width = max(80, width - 72)
        c.itemconfigure(self.search_entry_window, width=entry_width, height=max(24, h - 8))
        c.itemconfigure(self.search_placeholder_window, width=entry_width, height=max(24, h - 8))
        c.tag_raise(self.search_placeholder_window)

    def _show_search_placeholder(self):
        if self.search_placeholder_label is None:
            return
        self.search_placeholder_active = True
        self.search_placeholder_label.configure(text=self.tr("search_placeholder"), fg=self.theme["placeholder"])
        self.search_bar_canvas.itemconfigure(self.search_placeholder_window, state="normal")
        self.search_bar_canvas.tag_raise(self.search_placeholder_window)

    def _hide_search_placeholder(self):
        if self.search_placeholder_label is None:
            return
        self.search_placeholder_active = False
        self.search_bar_canvas.itemconfigure(self.search_placeholder_window, state="hidden")
        self.input_entry.configure(fg=self.theme["text"], insertbackground=self.theme["text"])

    def set_search_placeholder(self):
        if self.query.get().strip():
            self._hide_search_placeholder()
            return
        self._show_search_placeholder()

    def clear_search_placeholder(self, _event=None):
        # Focus alone must NOT convert the placeholder into user text.
        self.input_entry.configure(fg=self.theme["text"], insertbackground=self.theme["text"])

    def restore_search_placeholder(self, _event=None):
        if not self.query.get().strip():
            self._show_search_placeholder()

    def _focus_search_from_placeholder(self, _event=None):
        self.input_entry.focus_set()
        return "break"

    def _search_keypress(self, event):
        if not self.search_placeholder_active:
            return None
        # Keep the placeholder visible for navigation keys and Ctrl shortcuts.
        if getattr(event, "state", 0) & 0x0004:
            return None
        if getattr(event, "char", ""):
            self._hide_search_placeholder()
        return None

    def maybe_show_legal_notice(self):
        """Show a one-time first-run notice before the user starts using Sonus."""
        if self.settings.get("legal_accepted"):
            return
        if self.legal_window is not None:
            try:
                if self.legal_window.winfo_exists():
                    self.legal_window.focus_force()
                    return
            except tk.TclError:
                pass

        window = tk.Toplevel(self.root)
        self.legal_window = window
        window.title(f"{self.tr('legal_title')} - {APP_NAME}")
        window.geometry("560x390")
        window.minsize(500, 340)
        window.resizable(False, False)
        window.transient(self.root)
        window.configure(bg=self.theme["bg"])
        window.protocol("WM_DELETE_WINDOW", self.on_close)
        icon_path = APP_DIR / "sonus.ico"
        try:
            if icon_path.exists():
                window.iconbitmap(str(icon_path))
                apply_windows_icon(window, icon_path)
        except tk.TclError:
            pass

        card = RoundedCard(window, self.theme, radius=18, padding=1)
        card.pack(fill=BOTH, expand=True, padx=14, pady=14)
        content = card.content
        title = tk.Label(content, text=self.tr("legal_title"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w", padx=22, pady=(22, 10))
        body = tk.Label(content, text=self.tr("legal_text"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 10), justify="left", anchor="w", wraplength=480)
        body.pack(fill=X, padx=22, pady=(0, 18))
        btns = tk.Frame(content, bg=self.theme["surface"])
        btns.pack(fill=X, padx=22, pady=(0, 22))

        def agree():
            self.settings["legal_accepted"] = True
            self.save_settings()
            try:
                window.destroy()
            except tk.TclError:
                pass
            self.legal_window = None

        ttk.Button(btns, text=self.tr("legal_agree"), style="Accent.TButton", command=agree).pack(side=RIGHT)
        ttk.Button(btns, text=self.tr("legal_exit"), command=self.on_close).pack(side=RIGHT, padx=(0, 8))
        window.grab_set()
        window.focus_force()

    def open_settings(self):
        if self.settings_window is not None:
            try:
                if self.settings_window.winfo_exists():
                    self.settings_window.focus_force()
                    return
            except tk.TclError:
                pass

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title(f"{self.tr('settings_title')} - {APP_NAME}")
        window.geometry("520x600")
        window.minsize(480, 520)
        window.transient(self.root)
        window.configure(bg=self.theme["bg"])
        window.protocol("WM_DELETE_WINDOW", lambda: self._close_settings(window))
        icon_path = APP_DIR / "sonus.ico"
        try:
            if icon_path.exists():
                window.iconbitmap(str(icon_path))
                apply_windows_icon(window, icon_path)
        except tk.TclError:
            pass

        card = RoundedCard(window, self.theme, radius=18, padding=1)
        card.pack(fill=BOTH, expand=True, padx=14, pady=14)
        canvas = tk.Canvas(card.content, bg=self.theme["surface"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(card.content, orient="vertical", command=canvas.yview, style="Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        inner = tk.Frame(canvas, bg=self.theme["surface"])
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)
        def on_wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.bind_all("<MouseWheel>", on_wheel, add="+")

        self._settings_widgets = {"window": window, "canvas": canvas, "wheel": on_wheel, "inner": inner}
        inner.columnconfigure(0, weight=1)

        title = tk.Label(inner, text=self.tr("settings_title"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

        search_title = tk.Label(inner, text=self.tr("settings_search_results"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        search_title.grid(row=1, column=0, sticky="w", padx=20, pady=(16, 2))
        search_desc = tk.Label(inner, text=self.tr("settings_search_desc"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left")
        search_desc.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 8))

        search_card = RoundedCard(inner, self.theme, radius=12, padding=1)
        search_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        search_inner = search_card.content
        results_label = tk.Label(search_inner, text=self.tr("results_label"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 10))
        results_label.pack(side=LEFT, padx=(12, 8), pady=10)
        validate_cmd = (self.root.register(self._validate_search_limit), "%P")
        search_spin = ttk.Spinbox(search_inner, from_=1, to=50, textvariable=self.search_limit, width=2, justify="center", command=self._settings_changed, style="Sonus.TSpinbox", validate="key", validatecommand=validate_cmd)
        search_spin.pack(side=LEFT, pady=10)
        search_spin.bind("<FocusOut>", self._normalize_search_limit)
        search_spin.bind("<Return>", self._normalize_search_limit)

        cache_title = tk.Label(inner, text=self.tr("cache_title"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        cache_title.grid(row=4, column=0, sticky="w", padx=20, pady=(4, 2))
        cache_desc = tk.Label(inner, text=self.tr("cache_desc"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left")
        cache_desc.grid(row=5, column=0, sticky="w", padx=20, pady=(0, 8))

        cache_card = RoundedCard(inner, self.theme, radius=12, padding=1)
        cache_card.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 8))
        cache_inner = cache_card.content
        cache_check = tk.Checkbutton(
            cache_inner,
            text=self.tr("cache_enable"),
            variable=self.cache_enabled,
            command=self._settings_changed,
            bg=self.theme["surface"],
            fg=self.theme["text"],
            activebackground=self.theme["surface"],
            activeforeground=self.theme["text"],
            selectcolor=self.theme["accent"],
            disabledforeground=self.theme["muted"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            font=("Segoe UI", 9),
        )
        cache_check.pack(anchor="w", padx=12, pady=(10, 7))

        download_mode_label = tk.Label(cache_inner, text=self.tr("download_mode"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9))
        download_mode_label.pack(anchor="w", padx=12, pady=(0, 4))
        mode_frame = tk.Frame(cache_inner, bg=self.theme["surface"])
        mode_frame.pack(fill=X, padx=12, pady=(0, 10))
        self._settings_widgets["cache_check"] = cache_check
        self._settings_widgets["settings_title"] = title
        self._settings_widgets["search_title"] = search_title
        self._settings_widgets["search_desc"] = search_desc
        self._settings_widgets["results_label"] = results_label
        self._settings_widgets["cache_title"] = cache_title
        self._settings_widgets["cache_desc"] = cache_desc
        self._settings_widgets["download_mode_label"] = download_mode_label
        self._settings_widgets["cache_modes"] = []

        for value, label_key, desc_key in (("streaming", "streaming", "streaming_desc"), ("smart", "smart", "smart_desc"), ("mixed", "mixed", "mixed_desc")):
            rb = tk.Radiobutton(mode_frame, text=self.tr(label_key), value=value, variable=self.cache_mode, command=self._settings_changed, bg=self.theme["surface"], fg=self.theme["text"], selectcolor=self.theme["surface_alt"], activebackground=self.theme["surface"], activeforeground=self.theme["text"], bd=0, highlightthickness=0, font=("Segoe UI", 9))
            rb.pack(anchor="w", pady=1)
            desc = tk.Label(mode_frame, text=self.tr(desc_key), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 8), wraplength=400, justify="left")
            desc.pack(anchor="w", padx=(24, 0), pady=(0, 4))
            self._settings_widgets["cache_modes"].append((rb, desc, label_key, desc_key))

        lang_title = tk.Label(inner, text=self.tr("language"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
        lang_title.grid(row=7, column=0, sticky="w", padx=20, pady=(10, 2))
        lang_desc = tk.Label(inner, text=self.tr("language_desc"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left")
        lang_desc.grid(row=8, column=0, sticky="w", padx=20, pady=(0, 8))
        lang_card = RoundedCard(inner, self.theme, radius=12, padding=1)
        lang_card.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 12))
        lang_inner = lang_card.content
        lang_combo = ttk.Combobox(lang_inner, values=(self.tr("english"), self.tr("russian")), state="readonly", width=10, height=4, style="Compact.TCombobox")
        lang_combo.pack(anchor="w", padx=12, pady=10)
        lang_combo.set(self.tr("english") if self.language == "en" else self.tr("russian"))
        lang_combo.bind("<<ComboboxSelected>>", self._language_selected)

        close_btn = ttk.Button(inner, text=self.tr("close"), command=lambda: self._close_settings(window))
        close_btn.grid(row=10, column=0, sticky="e", padx=20, pady=(0, 18))
        self._settings_widgets.update({"language_title": lang_title, "language_desc": lang_desc, "language_combo": lang_combo, "close": close_btn})

    def _language_selected(self, _event=None):
        combo = self._settings_widgets.get("language_combo")
        if combo is None:
            return
        value = combo.get()
        self.language = "ru" if value == self.tr("russian") else "en"
        self.save_settings()
        self.apply_language()

    def apply_language(self):
        self.root.title(APP_NAME)
        self.subtitle_label.configure(text=self.tr("subtitle"))
        self.process_button.configure(text=self.tr("process"))
        self.results_title_label.configure(text=self.tr("search_results"))
        self.queue_title_label.configure(text=self.tr("queue"))
        self.queue_hint_label.configure(text=self.tr("queue_hint"))
        self.results_hint.configure(text=self.tr("enter_query") if not self.current_results else self.tr("double_click_hint"))
        self.now_playing_label.configure(text=self.tr("now_playing"))
        self.preview.configure(text=self.tr("preview") if not self.thumb_photo else "")
        if not self.queue:
            self.now_title.configure(text=self.tr("nothing_selected"))
        self.playback_label.configure(text=self.tr("playback"))
        self.mode_label.configure(text=self.tr("mode"))
        self.volume_label.configure(text=self.tr("volume"))
        self.add_queue_btn.configure(text=self.tr("add_to_queue"))
        self.back_btn.configure(text="−10s" if self.language == "en" else "−10с")
        self.fwd_btn.configure(text="+10s" if self.language == "en" else "+10с")
        self.mode_labels = {self.tr(k): k for k in ("normal", "repeat_current", "repeat_queue", "shuffle")}
        self.mode_combo.configure(values=tuple(self.tr(k) for k in ("normal", "repeat_current", "repeat_queue", "shuffle")))
        self.mode_combo.set(self.tr(self.play_mode.get()))
        self.queue_size_var.set(self.tr("queue"))
        self.status.set(self.tr("paused" if self.paused else "playing" if self.playing else "ready"))
        if self.search_placeholder_active or not self.query.get().strip():
            self.set_search_placeholder()
        self.refresh_buttons()
        self._update_settings_language()

    def _update_settings_language(self):
        w = self._settings_widgets
        if not w:
            return
        w["window"].title(f"{self.tr('settings_title')} - {APP_NAME}")
        w["settings_title"].configure(text=self.tr("settings_title"))
        w["search_title"].configure(text=self.tr("settings_search_results"))
        w["search_desc"].configure(text=self.tr("settings_search_desc"))
        w["results_label"].configure(text=self.tr("results_label"))
        w["cache_title"].configure(text=self.tr("cache_title"))
        w["cache_desc"].configure(text=self.tr("cache_desc"))
        w["cache_check"].configure(text=self.tr("cache_enable"))
        w["download_mode_label"].configure(text=self.tr("download_mode"))
        for rb, desc, label_key, desc_key in w["cache_modes"]:
            rb.configure(text=self.tr(label_key))
            desc.configure(text=self.tr(desc_key))
        w["language_title"].configure(text=self.tr("language"))
        w["language_desc"].configure(text=self.tr("language_desc"))
        w["language_combo"].configure(values=(self.tr("english"), self.tr("russian")))
        w["language_combo"].set(self.tr("english") if self.language == "en" else self.tr("russian"))
        w["close"].configure(text=self.tr("close"))

    def _unexpected_error_text(self, exc):
        return self.tr("unexpected_error", e=exc)

    def _close_settings(self, window):
        try:
            wheel = self._settings_widgets.get("wheel")
            if wheel:
                self._settings_widgets.get("canvas").unbind_all("<MouseWheel>")
        except Exception:
            pass
        try:
            window.destroy()
        except tk.TclError:
            pass
        self._settings_widgets = {}
        self.settings_window = None


    def bind_events(self):
        self.input_entry.bind("<Return>", lambda _e: self.process_input())
        self.input_entry.bind("<FocusIn>", self.clear_search_placeholder)
        self.input_entry.bind("<FocusOut>", self.restore_search_placeholder)
        self.input_entry.bind("<KeyPress>", self._search_keypress)
        self.input_entry.bind("<Control-KeyPress>", self._input_ctrl_keypress)
        self.results_listbox.bind("<Double-Button-1>", lambda _e: self.play_selected_result())
        self.queue_listbox.bind("<Double-Button-1>", lambda _e: self.play_selected_queue())
        self.queue_listbox.bind("<Delete>", lambda _e: self._remove_selected_queue_event())
        self.queue_listbox.bind("<BackSpace>", lambda _e: self._remove_selected_queue_event())
        self.queue_listbox.bind("<Control-KeyPress>", self._queue_ctrl_keypress)
        self.queue_listbox.bind("<Button-1>", self._queue_click_select)
        self.slider.bind("<ButtonRelease-1>", self.slider_released)
        self.slider.bind("<ButtonPress-1>", self.slider_pressed)

    def _input_ctrl_keypress(self, event):
        # Use Windows virtual-key/keycode so shortcuts work in RU and EN layouts.
        keycode = getattr(event, "keycode", None)
        keysym = str(getattr(event, "keysym", "")).lower()
        if keycode == 65 or keysym in {"a", "ф"}:  # physical A key / RU Ф
            return self._select_all_input(event)
        if keycode == 86 or keysym in {"v", "м"}:  # physical V key / RU М
            return self.paste_from_clipboard(event)
        return None

    def _queue_ctrl_keypress(self, event):
        # keycode 65 is the physical A key on Windows, independent of layout.
        keycode = getattr(event, "keycode", None)
        keysym = str(getattr(event, "keysym", "")).lower()
        if keycode == 65 or keysym in {"a", "ф"}:
            return self._select_all_queue(event)
        return None

    def _select_all_input(self, _event=None):
        if self.search_placeholder_active:
            self._hide_search_placeholder()
            self.query.set("")
        self.input_entry.select_range(0, END)
        self.input_entry.icursor(END)
        return "break"

    def _select_all_queue(self, _event=None):
        if self.queue_listbox.size():
            self.queue_listbox.selection_set(0, END)
            self.queue_listbox.activate(0)
        return "break"

    def _mode_selected(self, _event=None):
        self.play_mode.set(self.mode_labels.get(self.mode_combo.get(), "normal"))

    def paste_from_clipboard(self, _event=None):
        try:
            value = self.root.clipboard_get()
            self._hide_search_placeholder()
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, value)
        except tk.TclError:
            pass
        return "break"

    def init_audio(self):
        if pygame is None:
            return
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.init()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume.get() / 100.0)
        except Exception:
            pass

    def ensure_tools(self):
        if yt_dlp is None:
            raise RuntimeError(self.tr("yt_missing"))
        if pygame is None:
            raise RuntimeError(self.tr("pygame_missing"))
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(self.tr("ffmpeg_missing"))

    def process_input(self):
        text = self.query.get().strip()
        if not text or self._resolving:
            return
        try:
            self.ensure_tools()
        except Exception as e:
            messagebox.showerror(self.tr("dependency_missing"), str(e))
            return

        self._resolving = True
        self.status.set(self.tr("processing"))
        self.results_hint.configure(text=self.tr("getting_data"))
        threading.Thread(target=self._process_worker, args=(text,), daemon=True).start()

    def _process_worker(self, text):
        try:
            if YOUTUBE_URL_RE.match(text):
                tracks = self.extract_url(text)
                mode = "url"
            else:
                tracks = self.search(text)
                mode = "search"
            self.root.after(0, lambda: self._show_processed(tracks, mode))
        except Exception as e:
            self.root.after(0, lambda: self._process_failed(str(e)))

    def _process_failed(self, error):
        self._resolving = False
        self.status.set(self.tr("processing_error"))
        messagebox.showerror(self.tr("error"), error)

    def extract_url(self, url):
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "playlistend": 200,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = list(info.get("entries") or []) if info.get("_type") == "playlist" or info.get("entries") else [info]
        tracks = []
        for e in entries:
            if not e:
                continue
            vid = e.get("id")
            webpage = e.get("webpage_url") or e.get("url")
            if not webpage and vid:
                webpage = f"https://www.youtube.com/watch?v={vid}"
            tracks.append(Track(
                id=str(vid or webpage),
                title=e.get("title") or self.tr("no_title"),
                url=webpage,
                thumbnail=e.get("thumbnail") or (f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""),
                duration=float(e.get("duration") or 0),
                channel=e.get("channel") or e.get("uploader") or "",
            ))
        return tracks

    def _validate_search_limit(self, proposed):
        """Allow only integers from 1 to 50 in the results field."""
        if proposed == "":
            return False
        if not proposed.isdigit():
            return False
        value = int(proposed)
        return 1 <= value <= 50

    def _normalize_search_limit(self, _event=None):
        try:
            value = self._clamp_int(self.search_limit.get(), 1, 50)
        except (tk.TclError, ValueError):
            value = 10
        self.search_limit.set(value)
        self._settings_changed()
        return "break"

    def search(self, query):
        limit = self._clamp_int(self.search_limit.get(), 1, 50)
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True, "playlistend": limit}
        tracks = []
        # Prefer YouTube Music search for text queries so artist/title searches
        # prioritize music-oriented results. Fall back to regular YouTube search
        # when the Music search extractor is unavailable or fails.
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(f"ytmsearch{limit}:{query}", download=False)
            except Exception:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        for e in (info.get("entries") or []):
            if not e:
                continue
            vid = e.get("id")
            tracks.append(Track(
                id=str(vid),
                title=e.get("title") or self.tr("no_title"),
                url=e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                thumbnail=e.get("thumbnail") or (f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""),
                duration=float(e.get("duration") or 0),
                channel=e.get("channel") or e.get("uploader") or "",
            ))
        return tracks

    def _show_processed(self, tracks, mode):
        self._resolving = False
        if not tracks:
            self.status.set(self.tr("nothing_found_status"))
            self.results_hint.configure(text=self.tr("nothing_found"))
            return

        self.current_results = tracks if mode == "search" else []
        self.results_listbox.delete(0, END)
        self.update_add_queue_button_state()
        if mode == "search":
            for i, t in enumerate(tracks):
                label = f"{i+1}. {t.label}"
                if t.duration:
                    label += f"  [{fmt_time(t.duration)}]"
                self.results_listbox.insert(END, label)
            self.results_listbox.selection_set(0)
            self.results_listbox.activate(0)
            self.results_hint.configure(text=self.tr("double_click_hint"))
            self.status.set(self.tr("found", n=len(tracks)))
            self.update_add_queue_button_state()
            return

        # A URL always adds its contents; it never replaces an existing queue.
        was_empty = not self.queue
        old_len = len(self.queue)
        self.queue.extend(tracks)
        priority_index = 0 if was_empty else self.current_index
        self.prefetch_tracks(tracks, priority_index=priority_index)
        self.refresh_queue_view()
        self.status.set(self.tr("added_queue", n=len(tracks)))
        self.results_hint.configure(text=self.tr("link_added", n=len(tracks)))
        if was_empty and self.queue:
            self.start_track(0)
        elif old_len > 0:
            self.queue_listbox.selection_set(old_len)
            self.queue_listbox.see(old_len)

    def add_selected_result(self):
        if not self.current_results:
            self.status.set(self.tr("search_first"))
            return
        sel = self.results_listbox.curselection()
        if not sel:
            active = self.results_listbox.index("active") if self.results_listbox.size() else -1
            if active >= 0:
                self.results_listbox.selection_clear(0, END)
                self.results_listbox.selection_set(active)
                sel = (active,)
        if not sel:
            self.results_listbox.selection_set(0)
            self.results_listbox.activate(0)
            sel = (0,)
        idx_result = int(sel[0])
        if idx_result >= len(self.current_results):
            return
        track = self.current_results[idx_result]
        self.queue.append(track)
        idx = len(self.queue) - 1
        self.prefetch_tracks([track], priority_index=self.current_index if 0 <= self.current_index < len(self.queue) else idx)
        self.refresh_queue_view()
        self.queue_listbox.selection_clear(0, END)
        self.queue_listbox.selection_set(idx)
        self.queue_listbox.see(idx)
        self.status.set(self.tr("track_added"))
        if self.current_index < 0:
            self.start_track(idx)

    def update_add_queue_button_state(self):
        if hasattr(self, "add_queue_btn"):
            state = "normal" if self.current_results else "disabled"
            self.add_queue_btn.configure(state=state)

    def play_selected_result(self):
        sel = self.results_listbox.curselection()
        if not sel or not self.current_results:
            return
        track = self.current_results[sel[0]]
        self.queue.append(track)
        self.prefetch_tracks([track])
        idx = len(self.queue) - 1
        self.refresh_queue_view()
        self.start_track(idx)

    def play_selected_queue(self):
        sel = self.queue_listbox.curselection()
        if not sel:
            return
        self.start_track(sel[0])

    def refresh_queue_view(self):
        self.queue_listbox.delete(0, END)
        for i, track in enumerate(self.queue):
            prefix = "▶ " if i == self.current_index else ""
            self.queue_listbox.insert(END, f"{prefix}{i+1}. {track.label}")
        self.queue_size_var.set(self.tr("queue"))
        if 0 <= self.current_index < len(self.queue):
            self.queue_listbox.selection_clear(0, END)
            self.queue_listbox.selection_set(self.current_index)
            self.queue_listbox.see(self.current_index)

    def _queue_click_select(self, event):
        # Keep Tkinter's native Ctrl/Shift multi-selection behavior. For a plain
        # click, explicitly select the row so Delete/Backspace has a stable target.
        idx = self.queue_listbox.nearest(event.y)
        if not (0 <= idx < self.queue_listbox.size()):
            return
        state = int(getattr(event, "state", 0))
        ctrl = bool(state & 0x0004)
        shift = bool(state & 0x0001)
        if not ctrl and not shift:
            self.queue_listbox.selection_clear(0, END)
            self.queue_listbox.selection_set(idx)
        self.queue_listbox.activate(idx)

    def _remove_selected_queue_event(self, _event=None):
        self.remove_selected_queue()
        return "break"

    def remove_selected_queue(self):
        sel = list(self.queue_listbox.curselection())
        if not sel and self.queue_listbox.size():
            active = self.queue_listbox.index("active")
            if active >= 0:
                sel = [active]
        if not sel:
            return

        indices = sorted({int(i) for i in sel if 0 <= int(i) < len(self.queue)}, reverse=True)
        if not indices:
            return

        current_was_removed = self.current_index in indices
        old_current = self.current_index
        for idx in indices:
            self.queue.pop(idx)
            if idx < old_current:
                self.current_index -= 1

        if not self.queue:
            self.stop_audio()
            self.current_index = -1
            self.current_audio_path = None
            self.position_anchor = 0.0
            self.now_title.configure(text=self.tr("nothing_selected"))
            self.now_channel.configure(text="")
            self.time_label_var.set("00:00 / 00:00")
            self.slider.configure(to=100)
            self.slider.set(0)
            self.set_thumbnail(None)
            self.status.set(self.tr("queue"))
            self.refresh_queue_view()
            self.refresh_buttons()
            return

        if current_was_removed:
            self.stop_audio()
            next_index = min(max(old_current - sum(i < old_current for i in indices), 0), len(self.queue) - 1)
            self.current_index = -1
            self.refresh_queue_view()
            self.status.set(self.tr("track_removed_play"))
            self.start_track(next_index)
            return

        self.refresh_queue_view()
        self.status.set(self.tr("removed_queue", n=len(indices)))

    def clear_queue(self):
        self.stop_audio()
        self.queue.clear()
        self.current_index = -1
        self.current_audio_path = None
        self.current_results = []
        self.results_listbox.delete(0, END)
        self.queue_listbox.delete(0, END)
        self.queue_size_var.set(self.tr("queue"))
        self.now_title.configure(text=self.tr("nothing_selected"))
        self.now_channel.configure(text="")
        self.time_label_var.set("00:00 / 00:00")
        self.slider.configure(to=100)
        self.slider.set(0)
        self.status.set(self.tr("queue_cleared"))
        self.set_thumbnail(None)
        self.refresh_buttons()

    def start_track(self, index, start_position=0.0):
        if not (0 <= index < len(self.queue)) or self._closing:
            return
        self.seek_generation += 1
        generation = self.seek_generation
        self.current_index = index
        track = self.queue[index]
        self.stop_audio()
        self.position_anchor = max(0.0, float(start_position))
        self.position_anchor_monotonic = time.monotonic()
        self.mixer_pos_anchor_ms = 0
        self.update_now_playing(track, self.position_anchor)
        self.status.set(self.tr("preparing_audio"))
        self.playing = False
        self.paused = False
        self.refresh_queue_view()
        if self.cache_enabled.get():
            # Starting a track is an explicit priority request. Reorder queued
            # background work so the requested track can begin as soon as possible.
            self._cancel_pending_cache_jobs()
            self.prefetch_tracks([], priority_index=index)
        future = self.ensure_cache_future(track)
        threading.Thread(target=self._prepare_and_play, args=(generation, index, future, self.position_anchor), daemon=True).start()

    def _prepare_and_play(self, generation, index, future, start_position):
        try:
            audio_path = future.result()
            self.root.after(0, lambda: self._play_local_file(generation, index, audio_path, start_position))
        except Exception as e:
            self.root.after(0, lambda: self._play_failed(generation, str(e)))

    def prefetch_tracks(self, tracks, priority_index=None, force_reschedule=False):
        """Schedule background cache work in the configured order."""
        if not self.cache_enabled.get():
            return
        if not self.queue:
            return

        n = len(self.queue)
        if priority_index is None:
            priority_index = self.current_index if 0 <= self.current_index < n else 0
        priority_index = max(0, min(n - 1, int(priority_index)))

        mode = self.cache_mode.get()
        if mode == "smart":
            order = [priority_index] + [i for i in range(n) if i != priority_index]
        elif mode == "mixed":
            preferred = [priority_index]
            for delta in (-2, -1, 1, 2):
                idx = priority_index + delta
                if 0 <= idx < n and idx not in preferred:
                    preferred.append(idx)
            order = preferred + [i for i in range(n) if i not in preferred]
        else:
            order = list(range(n))

        scheduled = 0
        for idx in order:
            track = self.queue[idx]
            try:
                self.ensure_cache_future(track)
                scheduled += 1
            except Exception:
                continue
        if tracks or force_reschedule or order:
            self.status.set(self.tr("queue_status", n=len(self.queue)))

    def ensure_cache_future(self, track):
        key = str(track.id or track.url)
        with self.cache_lock:
            future = self.cache_futures.get(key)
            if future is not None:
                if not future.done():
                    return future
                # A completed failed download should be retried automatically.
                try:
                    future.result()
                    return future
                except Exception:
                    self.cache_futures.pop(key, None)
            future = self.cache_executor.submit(self.get_or_download_ogg, track)
            self.cache_futures[key] = future
        return future

    def get_or_download_ogg(self, track):
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", track.id or "track")
        cached = AUDIO_CACHE_DIR / f"{safe_id}.ogg"
        if cached.exists() and cached.stat().st_size >= 4096:
            return cached

        partial = AUDIO_CACHE_DIR / f"{safe_id}.part"
        outtmpl = str(partial)
        opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "vorbis", "preferredquality": "160"}],
            "postprocessor_args": ["-vn"],
        }
        # yt-dlp names the converted file using the source extension changed to .ogg.
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(track.url, download=True)
        candidates = list(AUDIO_CACHE_DIR.glob(f"{safe_id}.part.*")) + list(AUDIO_CACHE_DIR.glob(f"{safe_id}.ogg"))
        if not candidates:
            # Some yt-dlp/FFmpeg combinations strip the temporary suffix before conversion.
            candidates = [p for p in AUDIO_CACHE_DIR.glob(f"{safe_id}.*") if p.suffix.lower() == ".ogg"]
        if not candidates:
            raise RuntimeError(self.tr("ffmpeg_missing"))
        source = max(candidates, key=lambda p: p.stat().st_mtime)
        if source != cached:
            try:
                if cached.exists():
                    cached.unlink()
                source.replace(cached)
            except OSError:
                shutil.copy2(source, cached)
                try:
                    source.unlink()
                except OSError:
                    pass
        return cached

    def _play_failed(self, generation, error):
        if generation != self.seek_generation or self._closing:
            return
        self.playing = False
        self.paused = False
        self.status.set(self.tr("playback_error"))
        self.refresh_buttons()
        messagebox.showerror(self.tr("playback_error"), error)

    def _play_local_file(self, generation, index, audio_path, start_position):
        if generation != self.seek_generation or index != self.current_index or self._closing:
            return
        try:
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.set_volume(self.volume.get() / 100.0)
            start_position = max(0.0, float(start_position))
            try:
                pygame.mixer.music.play(loops=0, start=start_position)
            except TypeError:
                pygame.mixer.music.play(0, start_position)
            self.current_audio_path = Path(audio_path)
            self.position_anchor = start_position
            self.position_anchor_monotonic = time.monotonic()
            self.mixer_pos_anchor_ms = max(0, int(pygame.mixer.music.get_pos()))
            self.playing = True
            self.paused = False
            self.status.set(self.tr("playing"))
            self.refresh_buttons()
        except Exception as e:
            self._play_failed(generation, str(e))

    def toggle_play(self):
        if not (0 <= self.current_index < len(self.queue)):
            if self.queue:
                self.start_track(0)
            return
        if self._resolving or self.current_audio_path is None:
            return

        if self.playing:
            try:
                # Freeze the position from the same clock that will be used
                # after resume. Do not use wall-clock time for audio position.
                self.position_anchor = self.current_position()
                pygame.mixer.music.pause()
                self.playing = False
                self.paused = True
                self.status.set(self.tr("paused"))
            except Exception as e:
                self.status.set(self.tr("pause_error", e=e))
            self.refresh_buttons()
            return

        if self.paused:
            try:
                # get_pos() does not include the requested start offset. Capture
                # its current value immediately before unpausing, then measure
                # only the delta after resume. This prevents a stale/rolled-back
                # get_pos value from moving the GUI slider backwards.
                try:
                    current_mixer_ms = max(0, int(pygame.mixer.music.get_pos()))
                except Exception:
                    current_mixer_ms = self.mixer_pos_anchor_ms
                self.mixer_pos_anchor_ms = current_mixer_ms
                pygame.mixer.music.unpause()
                self.position_anchor_monotonic = time.monotonic()
                self.playing = True
                self.paused = False
                self.status.set(self.tr("playing"))
            except Exception as e:
                self.status.set(self.tr("resume_error", e=e))
            self.refresh_buttons()
            return

        self._play_local_file(self.seek_generation, self.current_index, self.current_audio_path, self.position_anchor)

    def stop_audio(self):
        self.playing = False
        self.paused = False
        if pygame is not None:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
        self.current_audio_path = None

    def previous_track(self):
        if not self.queue:
            return
        if self.current_index > 0:
            self.start_track(self.current_index - 1)
        elif self.current_index == 0:
            self.start_track(0)

    def next_track(self):
        if not self.queue:
            return
        mode = self.play_mode.get()
        if mode == "shuffle" and self.queue:
            import random
            choices = [i for i in range(len(self.queue)) if i != self.current_index]
            if not choices:
                choices = list(range(len(self.queue)))
            self.start_track(random.choice(choices))
            return
        nxt = self.current_index + 1
        if nxt < len(self.queue):
            self.start_track(nxt)
        elif mode == "repeat_queue":
            self.start_track(0)
        elif mode == "repeat_current" and self.current_index >= 0:
            self.start_track(self.current_index)

    def seek_relative(self, seconds):
        if not (0 <= self.current_index < len(self.queue)) or self.current_audio_path is None:
            return
        target = max(0.0, self.current_position() + float(seconds))
        if self.queue[self.current_index].duration:
            target = min(target, float(self.queue[self.current_index].duration))
        self.seek_to(target)

    def slider_pressed(self, _event=None):
        self.seeking = True

    def slider_released(self, _event=None):
        if not self.seeking or not (0 <= self.current_index < len(self.queue)):
            self.seeking = False
            return
        target = float(self.slider.get())
        self.seeking = False
        self.seek_to(target)

    def seek_to(self, target):
        if self.current_audio_path is None or not (0 <= self.current_index < len(self.queue)):
            return
        target = max(0.0, float(target))
        duration = float(self.queue[self.current_index].duration or 0)
        if duration:
            target = min(target, duration)
        was_playing = self.playing
        was_paused = self.paused
        try:
            # OGG supports absolute positioning in seconds in SDL_mixer.
            pygame.mixer.music.set_pos(target)
            self.position_anchor = target
            self.position_anchor_monotonic = time.monotonic()
            try:
                self.mixer_pos_anchor_ms = max(0, int(pygame.mixer.music.get_pos()))
            except Exception:
                self.mixer_pos_anchor_ms = 0

            if was_paused:
                # set_pos may temporarily wake the decoder; explicitly restore
                # the paused state and keep the target as the displayed position.
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
                self.playing = False
                self.paused = True
            else:
                self.playing = was_playing
                self.paused = False

            self.slider.set(target)
            self.time_label_var.set(f"{fmt_time(target)} / {fmt_time(duration)}")
        except Exception as e:
            self.status.set(self.tr("seek_error", e=e))
        self.refresh_buttons()

    def current_position(self):
        if self.playing and self.current_audio_path is not None and pygame is not None:
            try:
                reported_ms = max(0, int(pygame.mixer.music.get_pos()))
                delta = (reported_ms - self.mixer_pos_anchor_ms) / 1000.0
                # Some SDL_mixer versions reset get_pos after unpause/seek; in
                # that case the negative delta is treated as zero until the
                # counter advances from its new baseline.
                if delta < 0:
                    delta = 0.0
                pos = self.position_anchor + delta
                duration = float(self.queue[self.current_index].duration or 0) if 0 <= self.current_index < len(self.queue) else 0.0
                if duration:
                    pos = min(pos, duration)
                return max(0.0, pos)
            except Exception:
                pass
        return max(0.0, self.position_anchor)

    def poll_player(self):
        if self._closing:
            return
        if 0 <= self.current_index < len(self.queue) and (self.playing or self.paused):
            track = self.queue[self.current_index]
            duration = float(track.duration or 0)
            pos = self.current_position()
            if duration:
                pos = min(pos, duration)
            if not self.seeking:
                self.slider.set(pos)
            self.time_label_var.set(f"{fmt_time(pos)} / {fmt_time(duration)}")

            if self.playing and pygame is not None:
                try:
                    busy = pygame.mixer.music.get_busy()
                except Exception:
                    busy = True
                if not busy:
                    self.playing = False
                    self.paused = False
                    self.position_anchor = duration if duration else self.current_position()
                    self.position_anchor_monotonic = time.monotonic()
                    self.root.after(50, self.handle_track_end)
                    self.refresh_buttons()
        self.root.after(100, self.poll_player)

    def handle_track_end(self):
        if self._closing or not self.queue:
            return
        mode = self.play_mode.get()
        if mode == "repeat_current" and self.current_index >= 0:
            self.start_track(self.current_index)
            return
        if mode == "shuffle" and self.queue:
            import random
            choices = [i for i in range(len(self.queue)) if i != self.current_index]
            if not choices:
                choices = list(range(len(self.queue)))
            self.start_track(random.choice(choices))
            return
        nxt = self.current_index + 1
        if nxt < len(self.queue):
            self.start_track(nxt)
        elif mode == "repeat_queue" and self.queue:
            self.start_track(0)
        else:
            self.status.set(self.tr("queue_finished"))
            self.refresh_buttons()

    def update_now_playing(self, track, position=0.0):
        self.now_title.configure(text=track.title)
        self.now_channel.configure(text=track.channel)
        duration = float(track.duration or 0)
        self.slider.configure(to=max(1, duration or 1))
        self.slider.set(position)
        self.time_label_var.set(f"{fmt_time(position)} / {fmt_time(duration)}")
        self.set_thumbnail(track.thumbnail)

    def set_thumbnail(self, url):
        if not url or Image is None:
            self.preview.configure(image="", text=self.tr("preview"))
            self.thumb_photo = None
            return

        def worker():
            try:
                key = re.sub(r"[^A-Za-z0-9_-]", "_", url)[-80:] + ".jpg"
                path = CACHE_DIR / key
                if not path.exists():
                    urllib.request.urlretrieve(url, path)
                img = Image.open(path).convert("RGB")
                img.thumbnail((440, 248))
                photo = ImageTk.PhotoImage(img)
                self.root.after(0, lambda: self._set_photo(photo))
            except Exception:
                self.root.after(0, lambda: self.preview.configure(image="", text=self.tr("preview_unavailable")))
        threading.Thread(target=worker, daemon=True).start()

    def _set_photo(self, photo):
        if self._closing:
            return
        self.thumb_photo = photo
        self.preview.configure(image=photo, text="")

    def volume_mouse_position(self, event):
        width = max(1, self.volume_scale.winfo_width())
        x = max(0, min(width, int(event.x)))
        level = round((x / width) * 100)
        self.volume.set(level)
        self.volume_value.configure(text=f"{level}%")
        if pygame is not None:
            try:
                pygame.mixer.music.set_volume(level / 100.0)
            except Exception:
                pass

    def volume_mouse_down(self, event):
        self._volume_dragging = True
        self.volume_mouse_position(event)
        return "break"

    def volume_mouse_drag(self, event):
        if self._volume_dragging:
            self.volume_mouse_position(event)
        return "break"

    def volume_mouse_up(self, event=None):
        if event is not None:
            self.volume_mouse_position(event)
        self._volume_dragging = False
        return "break"

    def refresh_buttons(self):
        if self.playing:
            self.play_btn.configure(text="⏸")
        else:
            self.play_btn.configure(text="▶")

    def on_close(self):
        self._closing = True
        for child in (self.legal_window, self.settings_window):
            try:
                if child is not None and child.winfo_exists():
                    child.destroy()
            except tk.TclError:
                pass
        self.legal_window = None
        self.settings_window = None
        self.seek_generation += 1
        try:
            self.stop_audio()
            if pygame is not None:
                pygame.mixer.quit()
                pygame.quit()
        except Exception:
            pass
        try:
            self.cache_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass


def fmt_time(seconds):
    try:
        total = max(0, int(float(seconds)))
    except Exception:
        total = 0
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"


def main():
    configure_windows_app_identity()
    root = tk.Tk()
    icon_path = APP_DIR / "sonus.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
            apply_windows_icon(root, icon_path)
        except tk.TclError:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            messagebox.showerror(APP_NAME, self._unexpected_error_text(exc))
        except Exception:
            pass
        raise
