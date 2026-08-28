from ..config.common import *
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.utils import fmt_time
from ..core.platform import apply_windows_icon

class UIMixin:
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
        self.results_listbox.bind("<<ListboxSelect>>", lambda _e: self.update_add_queue_button_state(), add="+")
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
        self._rounded_rect(c, 1, 1, width-1, h-1, 22, fill=self.theme["surface_alt"], outline=(self.theme["accent"] if self.search_has_focus else self.theme["border"]), width=2 if self.search_has_focus else 1, tags="bar")
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
        # Focus alone must NOT convert the placeholder into user text, but the search bar should visibly react.
        self.search_has_focus = True
        self.input_entry.configure(fg=self.theme["text"], insertbackground=self.theme["text"])
        self._redraw_search_bar()

    def restore_search_placeholder(self, _event=None):
        self.search_has_focus = False
        if not self.query.get().strip():
            self._show_search_placeholder()
        self._redraw_search_bar()

    def _focus_search_from_placeholder(self, _event=None):
        self.input_entry.focus_set()
        self.search_has_focus = True
        self._redraw_search_bar()
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

    def bind_events(self):
        # Media hotkeys are scoped to this Tk application, not the whole OS.
        # Tk receives these events only while Sonus is the active window; the
        # explicit state/top-level check also prevents them from firing while
        # the main window is minimized or a modal Sonus dialog is active.
        self.root.bind_all("<KeyPress-Up>", self._hotkey_volume_up, add="+")
        self.root.bind_all("<KeyPress-Down>", self._hotkey_volume_down, add="+")
        self.root.bind_all("<KeyPress-Right>", self._hotkey_next_track, add="+")
        self.root.bind_all("<KeyPress-Left>", self._hotkey_previous_track, add="+")
        self.root.bind_all("<KeyPress-Return>", self._hotkey_play, add="+")

        self.input_entry.bind("<Return>", lambda _e: self.process_input())
        self.input_entry.bind("<FocusIn>", self.clear_search_placeholder)
        self.input_entry.bind("<FocusOut>", self.restore_search_placeholder)
        self.input_entry.bind("<KeyPress>", self._search_keypress)
        self.input_entry.bind("<Control-KeyPress>", self._input_ctrl_keypress)
        self.results_listbox.bind("<Double-Button-1>", lambda _e: self.play_selected_result())
        self.queue_listbox.bind("<Double-Button-1>", lambda _e: self.play_selected_queue())
        self.queue_listbox.bind("<Delete>", lambda _e: self._remove_selected_queue_event())
        self.queue_listbox.bind("<BackSpace>", lambda _e: self._remove_selected_queue_event())
        # The media hotkeys are bound directly to the queue listbox as well as
        # bind_all. Direct bindings run before Tk's Listbox class bindings,
        # so Up/Down/Left/Right cannot move the native listbox cursor/selection.
        self.queue_listbox.bind("<KeyPress-Up>", self._hotkey_volume_up)
        self.queue_listbox.bind("<KeyPress-Down>", self._hotkey_volume_down)
        self.queue_listbox.bind("<KeyPress-Right>", self._hotkey_next_track)
        self.queue_listbox.bind("<KeyPress-Left>", self._hotkey_previous_track)
        self.queue_listbox.bind("<KeyPress-Return>", self._hotkey_play)
        self.queue_listbox.bind("<Control-KeyPress>", self._queue_ctrl_keypress)
        self.queue_listbox.bind("<Button-1>", self._queue_click_select)
        self.slider.bind("<ButtonRelease-1>", self.slider_released)
        self.slider.bind("<ButtonPress-1>", self.slider_pressed)

    def _hotkeys_allowed(self):
        """Return True only when the main Sonus window is active and visible."""
        if self._closing:
            return False
        try:
            if self.root.state() == "iconic":
                return False
            focused = self.root.focus_get()
            if focused is None:
                return False
            return focused.winfo_toplevel() is self.root
        except tk.TclError:
            return False

    def _hotkey_volume_change(self, delta, _event=None):
        if not self._hotkeys_allowed():
            return None
        level = max(0, min(100, int(self.volume.get()) + int(delta)))
        self.volume.set(level)
        self.volume_value.configure(text=f"{level}%")
        if pygame is not None:
            try:
                pygame.mixer.music.set_volume(level / 100.0)
            except Exception:
                pass
        return "break"

    def _hotkey_volume_up(self, event=None):
        return self._hotkey_volume_change(5, event)

    def _hotkey_volume_down(self, event=None):
        return self._hotkey_volume_change(-5, event)

    def _hotkey_next_track(self, event=None):
        if not self._hotkeys_allowed():
            return None
        self.next_track()
        return "break"

    def _hotkey_previous_track(self, event=None):
        if not self._hotkeys_allowed():
            return None
        self.previous_track()
        return "break"

    def _hotkey_play(self, event=None):
        # Enter in the search field keeps its existing meaning: submit the
        # query/link. Everywhere else in the main window it is Play/Pause.
        if not self._hotkeys_allowed():
            return None
        try:
            if self.root.focus_get() is self.input_entry:
                return None
        except tk.TclError:
            return None
        self.toggle_play()
        return "break"

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

    def paste_from_clipboard(self, _event=None):
        try:
            value = self.root.clipboard_get()
            self._hide_search_placeholder()
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, value)
        except tk.TclError:
            pass
        return "break"

    def update_add_queue_button_state(self):
        # Keep the button clickable at all times.  When there are no results,
        # add_selected_result() gives the user a localized status message.
        if hasattr(self, "add_queue_btn"):
            self.add_queue_btn.configure(state="normal")

    def refresh_buttons(self):
        if self.playing:
            self.play_btn.configure(text="⏸")
        else:
            self.play_btn.configure(text="▶")

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
