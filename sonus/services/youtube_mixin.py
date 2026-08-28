from ..config.common import *
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.utils import fmt_time

class YouTubeMixin:
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
            unavailable_error = None
            if YOUTUBE_URL_RE.match(text):
                tracks = self.extract_url(text)
                mode = "url"
                if len(tracks) == 1:
                    try:
                        self.validate_track_availability(tracks[0])
                    except Exception as exc:
                        unavailable_error = str(exc).strip() or "Unavailable"
            else:
                tracks = self.search(text)
                mode = "search"
            self.root.after(0, lambda: self._show_processed(tracks, mode, unavailable_error))
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda: self._process_failed(error_message))

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


    def validate_track_availability(self, track):
        """Check only one user-selected/direct video without downloading it."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(track.url, download=False)
        if not info:
            raise RuntimeError("No media information returned by yt-dlp")
        availability = str(info.get("availability") or "").lower()
        if availability and availability not in {"public", "unlisted"}:
            raise RuntimeError(f"YouTube availability: {availability}")
        if info.get("is_unavailable"):
            raise RuntimeError("YouTube marked this video as unavailable")
        return info

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

    def _show_processed(self, tracks, mode, unavailable_error=None):
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
    
        if mode == "url" and len(tracks) == 1 and unavailable_error:
            self.status.set(self.tr("track_unavailable_status", title=track.title))
            return

        # A URL adds its contents; it never replaces an existing queue.
        was_empty = not self.queue
        old_len = len(self.queue)
        self.queue.extend(tracks)
        priority_index = 0 if was_empty else self.current_index
        self.prefetch_tracks(tracks, priority_index=priority_index)
        self.refresh_queue_view()
        self.status.set(self.tr("added_queue", n=len(tracks)))
        self.results_hint.configure(text=self.tr("link_added", n=len(tracks)))
        if was_empty and self.queue:
            self.start_track(0, automatic=True)
        elif old_len > 0:
            self.queue_listbox.selection_set(old_len)
            self.queue_listbox.see(old_len)

    def _selected_result_track(self):
        if not self.current_results and self.results_listbox.size() == 0:
            self.status.set(self.tr("search_first"))
            return None, None
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
            return None, None
        return self.current_results[idx_result], idx_result + 1

    def add_selected_result(self):
        track, position = self._selected_result_track()
        if track is None:
            return
        key = str(track.id or track.url)
        if key in getattr(self, "_queue_validation_pending", set()):
            return
        self._queue_validation_pending.add(key)
        self.status.set(self.tr("checking_track"))
        threading.Thread(target=self._validate_then_queue, args=(track, position, False), daemon=True).start()

    def play_selected_result(self):
        track, position = self._selected_result_track()
        if track is None:
            return
        key = str(track.id or track.url)
        if key in getattr(self, "_queue_validation_pending", set()):
            return
        self._queue_validation_pending.add(key)
        self.status.set(self.tr("checking_track"))
        threading.Thread(target=self._validate_then_queue, args=(track, position, True), daemon=True).start()

    def _validate_then_queue(self, track, position, play_after):
        try:
            self.validate_track_availability(track)
            self.root.after(0, lambda: self._finish_validated_queue_add(track, position, play_after))
        except Exception:
            self.root.after(0, lambda: self._finish_validated_queue_failure(track, position))

    def _finish_validated_queue_add(self, track, position, play_after):
        self._queue_validation_pending.discard(str(track.id or track.url))
        if self._closing:
            return
        self.queue.append(track)
        idx = len(self.queue) - 1
        self.prefetch_tracks([track], priority_index=self.current_index if 0 <= self.current_index < len(self.queue) else idx)
        self.refresh_queue_view()
        self.queue_listbox.selection_clear(0, END)
        self.queue_listbox.selection_set(idx)
        self.queue_listbox.see(idx)
        self.status.set(self.tr("track_added"))
        if play_after or self.current_index < 0:
            self.start_track(idx)

    def _finish_validated_queue_failure(self, track, position):
        self._queue_validation_pending.discard(str(track.id or track.url))
        if self._closing:
            return
        self.status.set(self.tr("track_unavailable_status", title=track.title))

