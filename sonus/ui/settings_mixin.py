from ..config.common import *
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.platform import apply_windows_icon

class SettingsMixin:
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
                "volume": self._clamp_int(self.volume.get(), 0, 100),
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

    def maybe_show_legal_notice(self):
        if self.settings.get("legal_accepted") or self._closing:
            return
        if self.legal_window is not None:
            try:
                if self.legal_window.winfo_exists():
                    self.legal_window.deiconify()
                    self.legal_window.lift()
                    self.legal_window.focus_force()
                    self.legal_window.grab_set()
                    return
            except tk.TclError:
                self.legal_window = None

        window = tk.Toplevel(self.root)
        self.legal_window = window
        window.withdraw()
        window.title(f"{self.tr('legal_title')} - {APP_NAME}")
        window.geometry("560x390")
        window.minsize(500, 340)
        window.resizable(False, False)
        window.transient(self.root)
        window.configure(bg=self.theme["bg"])
        icon_path = APP_DIR / "sonus.ico"
        try:
            if icon_path.exists():
                window.iconbitmap(str(icon_path))
                apply_windows_icon(window, icon_path)
        except (tk.TclError, OSError):
            pass

        def close_app():
            self.on_close()

        try:
            outer = tk.Frame(window, bg=self.theme["bg"], bd=0, highlightthickness=0)
            outer.pack(fill=BOTH, expand=True, padx=14, pady=14)
            card = tk.Frame(outer, bg=self.theme["surface"], bd=0, highlightthickness=1, highlightbackground=self.theme["border"])
            card.pack(fill=BOTH, expand=True)
            title = tk.Label(card, text=self.tr("legal_title"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 18, "bold"))
            title.pack(anchor="w", padx=22, pady=(22, 10))
            body = tk.Label(card, text=self.tr("legal_text"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 10), justify="left", anchor="w", wraplength=480)
            body.pack(fill=X, padx=22, pady=(0, 18))
            btns = tk.Frame(card, bg=self.theme["surface"])
            btns.pack(fill=X, padx=22, pady=(0, 22))

            def agree():
                self.settings["legal_accepted"] = True
                self.save_settings()
                try:
                    window.grab_release()
                except tk.TclError:
                    pass
                try:
                    window.destroy()
                except tk.TclError:
                    pass
                self.legal_window = None
                self.root.focus_force()

            ttk.Button(btns, text=self.tr("legal_agree"), style="Accent.TButton", command=agree).pack(side=RIGHT)
            ttk.Button(btns, text=self.tr("legal_exit"), command=close_app).pack(side=RIGHT, padx=(0, 8))
            window.protocol("WM_DELETE_WINDOW", close_app)
            window.update_idletasks()
            window.deiconify()
            window.lift()
            window.grab_set()
            window.focus_force()
        except Exception as exc:
            try:
                window.destroy()
            except tk.TclError:
                pass
            self.legal_window = None
            messagebox.showerror(self.tr("settings_error_title"), self._unexpected_error_text(exc), parent=self.root)
            self.on_close()

    def open_settings(self):
        if self.settings_window is not None:
            try:
                if self.settings_window.winfo_exists():
                    self.settings_window.deiconify()
                    self.settings_window.lift()
                    self.settings_window.focus_force()
                    return
            except tk.TclError:
                self.settings_window = None

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.withdraw()
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
        except (tk.TclError, OSError):
            pass

        try:
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
                bbox = canvas.bbox("all")
                canvas.configure(scrollregion=bbox if bbox else (0, 0, 0, 0))
            def on_canvas_configure(event):
                canvas.itemconfigure(window_id, width=max(1, event.width))
            def on_wheel(event):
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-event.delta / 120), "units")
            inner.bind("<Configure>", on_inner_configure)
            canvas.bind("<Configure>", on_canvas_configure)
            canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_wheel, add="+"))
            canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

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
            search_card.configure(height=52)
            search_card.pack_propagate(False)
            search_inner = search_card.content
            results_label = tk.Label(search_inner, text=self.tr("results_label"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 10))
            results_label.pack(side=LEFT, padx=(12, 8), pady=10)
            validate_cmd = (self.root.register(self._validate_search_limit), "%P")
            search_spin = ttk.Spinbox(search_inner, from_=1, to=50, textvariable=self.search_limit, width=2, justify="center", command=self._settings_changed, style="Sonus.TSpinbox", validate="key", validatecommand=validate_cmd)
            search_spin.pack(side=LEFT, pady=6)
            search_spin.bind("<FocusOut>", self._normalize_search_limit)
            search_spin.bind("<Return>", self._normalize_search_limit)

            cache_title = tk.Label(inner, text=self.tr("cache_title"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 11, "bold"))
            cache_title.grid(row=4, column=0, sticky="w", padx=20, pady=(4, 2))
            cache_desc = tk.Label(inner, text=self.tr("cache_desc"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9), wraplength=430, justify="left")
            cache_desc.grid(row=5, column=0, sticky="w", padx=20, pady=(0, 8))

            cache_card = RoundedCard(inner, self.theme, radius=12, padding=1)
            cache_card.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 8))
            cache_inner = cache_card.content
            cache_check = tk.Checkbutton(cache_inner, text=self.tr("cache_enable"), variable=self.cache_enabled, command=self._settings_changed, bg=self.theme["surface"], fg=self.theme["text"], activebackground=self.theme["surface"], activeforeground=self.theme["text"], selectcolor=self.theme["accent"], disabledforeground=self.theme["muted"], bd=0, highlightthickness=0, relief="flat", font=("Segoe UI", 9))
            cache_check.pack(anchor="w", padx=12, pady=(10, 7))
            download_mode_label = tk.Label(cache_inner, text=self.tr("download_mode"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 9))
            download_mode_label.pack(anchor="w", padx=12, pady=(0, 4))
            mode_frame = tk.Frame(cache_inner, bg=self.theme["surface"])
            mode_frame.pack(fill=X, padx=12, pady=(0, 10))
            self._settings_widgets.update({"cache_check": cache_check, "settings_title": title, "search_title": search_title, "search_desc": search_desc, "results_label": results_label, "cache_title": cache_title, "cache_desc": cache_desc, "download_mode_label": download_mode_label, "cache_modes": []})
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
            lang_card.configure(height=52)
            lang_card.pack_propagate(False)
            lang_inner = lang_card.content
            lang_combo = ttk.Combobox(lang_inner, values=(self.tr("english"), self.tr("russian")), state="readonly", width=7, height=2, style="Compact.TCombobox")
            lang_combo.pack(anchor="w", padx=12, pady=6)
            lang_combo.set(self.tr("english") if self.language == "en" else self.tr("russian"))
            lang_combo.bind("<<ComboboxSelected>>", self._language_selected)
            close_btn = ttk.Button(inner, text=self.tr("close"), command=lambda: self._close_settings(window))
            close_btn.grid(row=10, column=0, sticky="e", padx=20, pady=(0, 18))
            self._settings_widgets.update({"language_title": lang_title, "language_desc": lang_desc, "language_combo": lang_combo, "close": close_btn})

            inner.update_idletasks()
            on_inner_configure()
            window.update_idletasks()
            window.deiconify()
            window.lift()
            window.focus_force()
        except Exception as exc:
            try:
                window.destroy()
            except tk.TclError:
                pass
            self.settings_window = None
            self._settings_widgets = {}
            messagebox.showerror(self.tr("settings_error_title"), self._unexpected_error_text(exc), parent=self.root)

    def _language_selected(self, _event=None):
        combo = self._settings_widgets.get("language_combo")
        if combo is None:
            return
        value = combo.get()
        self.language = "ru" if value in {LANGUAGES["en"]["russian"], LANGUAGES["ru"]["russian"]} else "en"
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
            canvas = self._settings_widgets.get("canvas")
            if canvas is not None:
                canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        try:
            window.destroy()
        except tk.TclError:
            pass
        self._settings_widgets = {}
        self.settings_window = None

    def _mode_selected(self, _event=None):
        self.play_mode.set(self.mode_labels.get(self.mode_combo.get(), "normal"))
