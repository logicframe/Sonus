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
SEARCH_PLACEHOLDER = "Введите название трека, исполнителя, плейлист или ссылку YouTube…"

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
        self.theme_name = "dark"
        self.theme = THEMES[self.theme_name]
        self.search_placeholder_active = False
        self.search_bar_canvas = None
        self.search_icon_window = None
        self.settings_window = None

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
        self.play_mode_display = StringVar(value="Обычный")

        self.search_limit = IntVar(value=self._clamp_int(self.settings.get("search_results", 10), 1, 50))
        self.cache_enabled = BooleanVar(value=bool(self.settings.get("prefetch_enabled", True)))
        cache_mode = self.settings.get("prefetch_mode", "streaming")
        if cache_mode not in {"streaming", "smart", "mixed"}:
            cache_mode = "streaming"
        self.cache_mode = StringVar(value=cache_mode)

        self.volume = IntVar(value=80)
        self.thumb_photo = None
        self.status = StringVar(value="Готово")
        self.query = StringVar()
        self.repeat = BooleanVar(value=False)
        self.queue_size_var = StringVar(value="Очередь")
        self.time_label_var = StringVar(value="00:00 / 00:00")

        self.build_ui()
        self.update_add_queue_button_state()
        self.bind_events()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.init_audio()
        self.refresh_buttons()
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
        ttk.Label(header, text="YouTube audio player", style="Subtle.TLabel").pack(side=LEFT, padx=(10, 0), pady=(7, 0))

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

        self.process_button = ttk.Button(search_row, text="Обработать", style="Accent.TButton", command=self.process_input)
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
        tk.Label(result_content, text="Результаты поиска", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(11, 8))
        self.results_listbox = tk.Listbox(result_content, activestyle="none", font=("Segoe UI", 10), selectmode=tk.BROWSE, relief="flat", bd=0, highlightthickness=0)
        self.results_listbox.grid(row=1, column=0, sticky="nsew", padx=(14, 0))
        rsb = ttk.Scrollbar(result_content, orient="vertical", style="Vertical.TScrollbar", command=self.results_listbox.yview)
        rsb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 2))
        self.results_listbox.configure(yscrollcommand=rsb.set)
        self.results_hint = ttk.Label(result_content, text="Введите запрос или ссылку.", style="Subtle.TLabel")
        self.results_hint.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 11))

        self.queue_frame = RoundedCard(left, self.theme, radius=16, padding=1)
        self.queue_frame.grid(row=2, column=0, sticky="nsew")
        queue_content = self.queue_frame.content
        queue_content.columnconfigure(0, weight=1)
        queue_content.rowconfigure(1, weight=1)
        tk.Label(queue_content, text="Очередь", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(11, 8))
        self.queue_listbox = tk.Listbox(queue_content, activestyle="none", font=("Segoe UI", 10), selectmode=tk.EXTENDED, relief="flat", bd=0, highlightthickness=0)
        self.queue_listbox.grid(row=1, column=0, sticky="nsew", padx=(14, 0))
        qsb = ttk.Scrollbar(queue_content, orient="vertical", style="Vertical.TScrollbar", command=self.queue_listbox.yview)
        qsb.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 2))
        self.queue_listbox.configure(yscrollcommand=qsb.set)
        ttk.Label(queue_content, text="Двойной клик — воспроизвести. Ctrl+A — выбрать все. Delete/Backspace — удалить.", style="Subtle.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 11))

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
        tk.Label(preview_content, text="Сейчас играет", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(11, 8))
        self.preview = tk.Label(preview_content, text="Превью", anchor="center", bg=self.theme["surface_alt"], fg=self.theme["muted"], bd=0, highlightthickness=0)
        self.preview.grid(row=1, column=0, sticky="nsew", padx=14)
        self.now_title = tk.Label(preview_content, text="Ничего не выбрано", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 13, "bold"), anchor="w", justify="left", wraplength=390)
        self.now_title.grid(row=2, column=0, sticky="w", padx=14, pady=(12, 4))
        self.now_channel = tk.Label(preview_content, text="", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), anchor="w")
        self.now_channel.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

        playback_card = RoundedCard(right, self.theme, radius=16, padding=1)
        playback_card.grid(row=1, column=0, sticky="nsew")
        playback_content = playback_card.content
        playback_content.columnconfigure(0, weight=1)
        playback_content.rowconfigure(2, weight=1)
        ttk.Label(playback_content, text="Управление воспроизведением", style="TLabel").grid(row=0, column=0, sticky="w", padx=14, pady=(11, 2))
        ttk.Label(playback_content, textvariable=self.time_label_var, style="Subtle.TLabel").grid(row=1, column=0, sticky="w", padx=14, pady=(0, 2))
        self.slider = ttk.Scale(playback_content, from_=0, to=100, orient="horizontal", style="Horizontal.TScale")
        self.slider.grid(row=2, column=0, sticky="ew", padx=14, pady=(2, 10))

        controls = ttk.Frame(playback_content, style="TFrame")
        controls.grid(row=3, column=0, sticky="ew", padx=12)
        for i in range(5):
            controls.columnconfigure(i, weight=1)
        self.prev_btn = ttk.Button(controls, text="⏮", command=self.previous_track)
        self.prev_btn.grid(row=0, column=0, padx=2, sticky="ew")
        self.back_btn = ttk.Button(controls, text="−10с", command=lambda: self.seek_relative(-10))
        self.back_btn.grid(row=0, column=1, padx=2, sticky="ew")
        self.play_btn = ttk.Button(controls, text="▶", style="Accent.TButton", command=self.toggle_play)
        self.play_btn.grid(row=0, column=2, padx=2, sticky="ew")
        self.fwd_btn = ttk.Button(controls, text="+10с", command=lambda: self.seek_relative(10))
        self.fwd_btn.grid(row=0, column=3, padx=2, sticky="ew")
        self.next_btn = ttk.Button(controls, text="⏭", command=self.next_track)
        self.next_btn.grid(row=0, column=4, padx=2, sticky="ew")

        bottom = ttk.Frame(playback_content, style="TFrame")
        bottom.grid(row=4, column=0, sticky="ew", padx=12, pady=(10, 11))
        ttk.Label(bottom, text="Режим").pack(side=LEFT)
        self.mode_combo = ttk.Combobox(bottom, textvariable=self.play_mode_display, values=("Обычный", "Повтор текущего", "Повтор очереди", "Случайный"), state="readonly", width=17)
        self.mode_combo.pack(side=LEFT, padx=(6, 12))
        self.mode_combo.bind("<<ComboboxSelected>>", self._mode_selected)
        self.mode_labels = {"Обычный": "normal", "Повтор текущего": "repeat_current", "Повтор очереди": "repeat_queue", "Случайный": "shuffle"}
        self.mode_combo.set("Обычный")
        ttk.Label(bottom, text="Громкость").pack(side=LEFT, padx=(10, 4))
        self.volume_scale = ttk.Scale(bottom, from_=0, to=100, orient="horizontal", variable=self.volume, length=125, style="Horizontal.TScale")
        self.volume_scale.pack(side=LEFT)
        self.volume_scale.bind("<Button-1>", self.volume_mouse_down)
        self.volume_scale.bind("<B1-Motion>", self.volume_mouse_drag)
        self.volume_scale.bind("<ButtonRelease-1>", self.volume_mouse_up)
        self.volume_value = ttk.Label(bottom, text="80%", width=5)
        self.volume_value.pack(side=LEFT, padx=(4, 0))
        self.add_queue_btn = ttk.Button(bottom, text="В очередь →", command=self.add_selected_result)
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
                "search_results": self._clamp_int(self.search_limit.get(), 1, 50),
                "prefetch_enabled": bool(self.cache_enabled.get()),
                "prefetch_mode": self.cache_mode.get(),
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
                "streaming": "Потоковая",
                "smart": "Умная",
                "mixed": "Смешанная",
            }
            if self.cache_enabled.get():
                self.status.set(f"Настройки сохранены · {mode_names.get(self.cache_mode.get(), 'Потоковая')} загрузка")
            else:
                self.status.set("Настройки сохранены · фоновое кэширование отключено")
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
        c.itemconfigure(self.search_entry_window, width=max(80, width - 72), height=max(24, h - 8))

    def set_search_placeholder(self):
        if self.query.get().strip():
            self.search_placeholder_active = False
            return
        self.search_placeholder_active = True
        self.query.set(SEARCH_PLACEHOLDER)
        self.input_entry.configure(fg=self.theme["placeholder"], insertbackground=self.theme["text"])

    def clear_search_placeholder(self, _event=None):
        if self.search_placeholder_active:
            self.search_placeholder_active = False
            self.query.set("")
        self.input_entry.configure(fg=self.theme["text"], insertbackground=self.theme["text"])

    def restore_search_placeholder(self, _event=None):
        if not self.query.get().strip():
            self.set_search_placeholder()

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
        window.title(f"Настройки — {APP_NAME}")
        window.geometry("520x560")
        window.minsize(480, 520)
        window.transient(self.root)
        window.grab_set()
        window.configure(bg=self.theme["bg"])
        window.protocol("WM_DELETE_WINDOW", lambda: self._close_settings(window))

        card = RoundedCard(window, self.theme, radius=18, padding=1)
        card.pack(fill=BOTH, expand=True, padx=14, pady=14)
        content = card.content
        content.columnconfigure(0, weight=1)

        tk.Label(content, text="Настройки", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

        tk.Label(content, text="Результаты поиска", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w", padx=20, pady=(16, 2))
        tk.Label(content, text="Количество результатов при каждом новом поиске. Можно выбрать от 1 до 50.", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left").grid(row=2, column=0, sticky="w", padx=20, pady=(0, 8))

        search_card = RoundedCard(content, self.theme, radius=12, padding=1)
        search_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        search_inner = search_card.content
        tk.Label(search_inner, text="Результатов:", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 10)).pack(side=LEFT, padx=(12, 8), pady=10)
        validate_cmd = (self.root.register(self._validate_search_limit), "%P")
        search_spin = ttk.Spinbox(
            search_inner,
            from_=1,
            to=50,
            textvariable=self.search_limit,
            width=3,
            justify="center",
            command=self._settings_changed,
            style="Sonus.TSpinbox",
            validate="key",
            validatecommand=validate_cmd,
        )
        search_spin.pack(side=LEFT, pady=10)
        search_spin.bind("<FocusOut>", self._normalize_search_limit)
        search_spin.bind("<Return>", self._normalize_search_limit)

        tk.Label(content, text="Загрузка треков в кэш", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=4, column=0, sticky="w", padx=20, pady=(4, 2))
        tk.Label(content, text="Фоновая загрузка не влияет на воспроизведение. При отключении текущий трек всё равно будет загружен при запуске.", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left").grid(row=5, column=0, sticky="w", padx=20, pady=(0, 8))

        cache_card = RoundedCard(content, self.theme, radius=12, padding=1)
        cache_card.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 8))
        cache_inner = cache_card.content
        ttk.Checkbutton(cache_inner, text="Загружать треки в кэш в фоне", variable=self.cache_enabled, command=self._settings_changed).pack(anchor="w", padx=12, pady=(10, 7))

        tk.Label(cache_inner, text="Режим загрузки", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(0, 4))
        mode_frame = tk.Frame(cache_inner, bg=self.theme["surface"])
        mode_frame.pack(fill=X, padx=12, pady=(0, 10))
        mode_options = (
            ("streaming", "Потоковая", "Все треки скачиваются по порядку: от первого в очереди до последнего."),
            ("smart", "Умная", "Сначала текущий выбранный трек, затем все остальные по порядку очереди."),
            ("mixed", "Смешанная", "Сначала текущий трек, затем два предыдущих и два следующих; далее — остальные по порядку."),
        )
        for value, label, _description in mode_options:
            tk.Radiobutton(mode_frame, text=label, value=value, variable=self.cache_mode, command=self._settings_changed, bg=self.theme["surface"], fg=self.theme["text"], selectcolor=self.theme["surface_alt"], activebackground=self.theme["surface"], activeforeground=self.theme["text"], bd=0, highlightthickness=0, font=("Segoe UI", 9)).pack(anchor="w", pady=1)
            tk.Label(mode_frame, text=_description, bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 8), wraplength=400, justify="left").pack(anchor="w", padx=(24, 0), pady=(0, 4))

        tk.Label(content, text="Внешний вид", bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold")).grid(row=7, column=0, sticky="w", padx=20, pady=(6, 2))
        tk.Label(content, text="Тёмная тема используется всегда.", bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9)).grid(row=8, column=0, sticky="w", padx=20, pady=(0, 12))

        ttk.Button(content, text="Закрыть", command=lambda: self._close_settings(window)).grid(row=9, column=0, sticky="e", padx=20, pady=(0, 18))

    def _close_settings(self, window):
        try:
            window.grab_release()
        except tk.TclError:
            pass
        try:
            window.destroy()
        except tk.TclError:
            pass
        self.settings_window = None


    def bind_events(self):
        self.input_entry.bind("<Return>", lambda _e: self.process_input())
        self.input_entry.bind("<FocusIn>", self.clear_search_placeholder)
        self.input_entry.bind("<FocusOut>", self.restore_search_placeholder)
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
            raise RuntimeError("Не установлен yt-dlp. Выполните run_windows.bat или pip install -r requirements.txt")
        if pygame is None:
            raise RuntimeError("Не установлен pygame. Выполните run_windows.bat или pip install -r requirements.txt")
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("Не найден ffmpeg. Он нужен для подготовки аудио-кэша OGG.")

    def process_input(self):
        text = "" if self.search_placeholder_active else self.query.get().strip()
        if not text or self._resolving:
            return
        try:
            self.ensure_tools()
        except Exception as e:
            messagebox.showerror("Зависимость не найдена", str(e))
            return

        self._resolving = True
        self.status.set("Обрабатываю…")
        self.results_hint.configure(text="Получение данных с YouTube…")
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
        self.status.set("Ошибка обработки")
        messagebox.showerror("Ошибка", error)

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
                title=e.get("title") or "Без названия",
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
                title=e.get("title") or "Без названия",
                url=e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                thumbnail=e.get("thumbnail") or (f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""),
                duration=float(e.get("duration") or 0),
                channel=e.get("channel") or e.get("uploader") or "",
            ))
        return tracks

    def _show_processed(self, tracks, mode):
        self._resolving = False
        if not tracks:
            self.status.set("Ничего не найдено")
            self.results_hint.configure(text="Ничего не найдено.")
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
            self.results_hint.configure(text="Двойной клик — добавить и запустить. «В очередь →» — добавить без остановки текущего трека.")
            self.status.set(f"Найдено: {len(tracks)}")
            self.update_add_queue_button_state()
            return

        # A URL always adds its contents; it never replaces an existing queue.
        was_empty = not self.queue
        old_len = len(self.queue)
        self.queue.extend(tracks)
        priority_index = 0 if was_empty else self.current_index
        self.prefetch_tracks(tracks, priority_index=priority_index)
        self.refresh_queue_view()
        self.status.set(f"Добавлено в очередь: {len(tracks)}")
        self.results_hint.configure(text=f"Ссылка добавила {len(tracks)} трек(ов) в очередь.")
        if was_empty and self.queue:
            self.start_track(0)
        elif old_len > 0:
            self.queue_listbox.selection_set(old_len)
            self.queue_listbox.see(old_len)

    def add_selected_result(self):
        if not self.current_results:
            self.status.set("Сначала выполните поиск")
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
        self.status.set("Трек добавлен в очередь")
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
        self.queue_size_var.set("Очередь")
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
            self.now_title.configure(text="Ничего не выбрано")
            self.now_channel.configure(text="")
            self.time_label_var.set("00:00 / 00:00")
            self.slider.configure(to=100)
            self.slider.set(0)
            self.set_thumbnail(None)
            self.status.set("Очередь пуста")
            self.refresh_queue_view()
            self.refresh_buttons()
            return

        if current_was_removed:
            self.stop_audio()
            next_index = min(max(old_current - sum(i < old_current for i in indices), 0), len(self.queue) - 1)
            self.current_index = -1
            self.refresh_queue_view()
            self.status.set("Трек удалён. Переключение…")
            self.start_track(next_index)
            return

        self.refresh_queue_view()
        self.status.set(f"Удалено из очереди: {len(indices)}")

    def clear_queue(self):
        self.stop_audio()
        self.queue.clear()
        self.current_index = -1
        self.current_audio_path = None
        self.current_results = []
        self.results_listbox.delete(0, END)
        self.queue_listbox.delete(0, END)
        self.queue_size_var.set("Очередь")
        self.now_title.configure(text="Ничего не выбрано")
        self.now_channel.configure(text="")
        self.time_label_var.set("00:00 / 00:00")
        self.slider.configure(to=100)
        self.slider.set(0)
        self.status.set("Очередь очищена")
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
        self.status.set("Готовлю аудио…")
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
            self.status.set(f"В очереди: {len(self.queue)} · Кэширование запущено")

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
            raise RuntimeError("Не удалось подготовить OGG-аудио. Проверьте наличие ffmpeg.")
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
        self.status.set("Ошибка воспроизведения")
        self.refresh_buttons()
        messagebox.showerror("Воспроизведение", error)

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
            self.status.set("Воспроизведение")
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
                self.status.set("Пауза")
            except Exception as e:
                self.status.set(f"Ошибка паузы: {e}")
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
                self.status.set("Воспроизведение")
            except Exception as e:
                self.status.set(f"Ошибка продолжения: {e}")
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
            self.status.set(f"Перемотка: {e}")
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
            self.status.set("Очередь закончена")
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
            self.preview.configure(image="", text="Превью")
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
                self.root.after(0, lambda: self.preview.configure(image="", text="Превью недоступно"))
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
    root = tk.Tk()
    icon_path = APP_DIR / "sonus.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except tk.TclError:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        try:
            messagebox.showerror("YouTube Music Desktop", f"Произошла непредвиденная ошибка:\n\n{exc}")
        except Exception:
            pass
        raise
