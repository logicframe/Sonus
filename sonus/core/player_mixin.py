from ..config.common import *
import concurrent.futures
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.utils import fmt_time

class PlayerMixin:
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

    def start_track(self, index, start_position=0.0, automatic=False):
        if not (0 <= index < len(self.queue)) or self._closing:
            return
        self.seek_generation += 1
        generation = self.seek_generation
        self.current_index = index
        track = self.queue[index]
        self._current_start_automatic = bool(automatic)
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
        threading.Thread(target=self._prepare_and_play, args=(generation, index, future, self.position_anchor, automatic), daemon=True).start()

    def _prepare_and_play(self, generation, index, future, start_position, automatic=False):
        try:
            audio_path = future.result(timeout=30)
            self.root.after(0, lambda: self._play_local_file(generation, index, audio_path, start_position))
        except concurrent.futures.TimeoutError:
            error_message = "Timeout: трек не подготовлен за 30 секунд"
            self.root.after(0, lambda: self._play_failed(generation, error_message, automatic=automatic))
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda: self._play_failed(generation, error_message, automatic=automatic))

    def _play_failed(self, generation, error, automatic=False):
        if generation != self.seek_generation or self._closing:
            return
        self.playing = False
        self.paused = False
        is_unavailable = self._is_unavailable_error_text(error)
        is_network = self._is_network_error_text(error)
        is_timeout = "timeout" in str(error).lower()
        if is_unavailable or is_network or is_timeout:
            # Do not immediately overwrite the useful status with the next
            # track's "preparing" message. Keep the information visible briefly
            # and then continue automatically, regardless of how the track was started.
            failed_index = self.current_index
            track_title = self.queue[failed_index].title if 0 <= failed_index < len(self.queue) else self.tr("no_title")
            if is_timeout:
                status_key = "skip_timeout"
            elif is_unavailable:
                status_key = "skip_unavailable"
            else:
                status_key = "skip_network"
            self.status.set(self.tr(status_key, title=track_title))
            self.refresh_buttons()
            self.root.after(450, lambda: self._continue_after_unavailable(generation, failed_index))
            return
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
            self._play_failed(generation, str(e), automatic=getattr(self, "_current_start_automatic", False))

    @staticmethod
    def _is_network_error_text(error_text):
        """Проверить текст ошибки на сетевые проблемы."""
        text = str(error_text).lower()
        network_markers = (
            "http error 403", "http error 404", "http error 500", "http error 502",
            "http error 503", "http error 504", "connection refused", "connection reset",
            "timed out", "timeout", "handshake operation timed out", "no route to host",
            "network is unreachable", "name or service not known", "unable to download",
            "unable to extract", "getaddrinfo failed"
        )
        return any(marker in text for marker in network_markers)

    @staticmethod
    def _is_unavailable_error_text(error):
        text = str(error).lower()
        markers = (
            "video unavailable", "content isn\'t available", "content is not available",
            "not available in your country", "not available in this country",
            "not available in your region", "not available in this region",
            "geo-restricted", "geoblocked", "private video", "members-only",
            "members only", "age-restricted", "age restricted",
            "video is unavailable", "this video is not available",
            "video is not available", "content unavailable",
        )
        return any(marker in text for marker in markers)

    def _retry_network_for_index(self, index):
        if not (0 <= index < len(self.queue)):
            return False
        track = self.queue[index]
        key = str(track.id or track.url)
        with self.cache_lock:
            err = self.cache_failures.get(key)
            if err is not None and self._is_network_error(err) and not self._is_unavailable_error(err):
                del self.cache_failures[key]
                self.cache_futures.pop(key, None)
                return True
        return False

    def _continue_after_unavailable(self, generation, failed_index):
        if self._closing or generation != self.seek_generation or not self.queue:
            return
        if failed_index != self.current_index:
            return
        if not (0 <= failed_index < len(self.queue)):
            return

        mode = self.play_mode.get()
        failed_key = str(self.queue[failed_index].id or self.queue[failed_index].url)
        failed_keys = set(self.cache_failures)

        if mode == "repeat_current":
            # Повтор текущего невозможен — ищем следующий доступный трек.
            nxt = failed_index + 1
            while nxt < len(self.queue):
                track = self.queue[nxt]
                key = str(track.id or track.url)
                if key not in self.cache_failures:
                    self.start_track(nxt, automatic=True)
                    return
                nxt += 1
            self.status.set(self.tr("queue_finished"))
            self.refresh_buttons()
            return

        if mode == "repeat_queue":
            # Сначала идём дальше по очереди, а только после её конца
            # возвращаемся к началу, пропуская известные ошибки.
            nxt = failed_index + 1
            while nxt < len(self.queue):
                track = self.queue[nxt]
                key = str(track.id or track.url)
                if key not in self.cache_failures:
                    self.start_track(nxt, automatic=True)
                    return
                nxt += 1

            self.clear_network_failures()
            nxt = 0
            while nxt <= failed_index:
                track = self.queue[nxt]
                key = str(track.id or track.url)
                if key not in self.cache_failures:
                    self.start_track(nxt, automatic=True)
                    return
                nxt += 1

            self.status.set(self.tr("queue_finished"))
            self.refresh_buttons()
            return

        if mode == "shuffle":
            import random
            available = [
                i for i in range(len(self.queue))
                if i != failed_index
                and str(self.queue[i].id or self.queue[i].url) not in failed_keys
            ]
            if available:
                self.start_track(random.choice(available), automatic=True)
            else:
                self.status.set(self.tr("queue_finished"))
                self.refresh_buttons()
            return

        # Обычный режим: следующий доступный трек.
        nxt = failed_index + 1
        while nxt < len(self.queue):
            track = self.queue[nxt]
            key = str(track.id or track.url)
            if key not in self.cache_failures:
                self.start_track(nxt, automatic=True)
                return
            nxt += 1

        self.status.set(self.tr("queue_finished"))
        self.refresh_buttons()

    def toggle_play(self):
        if not (0 <= self.current_index < len(self.queue)):
            if self.queue:
                self.start_track(0)
            return
        if self._resolving:
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
    
        if self.current_audio_path is None:
            self.start_track(self.current_index)
        else:
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

    def next_track(self, automatic=False):
        if not self.queue:
            return
        mode = self.play_mode.get()
        if mode == "shuffle" and self.queue:
            import random
            choices = [i for i in range(len(self.queue)) if i != self.current_index]
            if not choices:
                choices = list(range(len(self.queue)))
            self.start_track(random.choice(choices), automatic=automatic)
            return
        nxt = self.current_index + 1
        if nxt < len(self.queue):
            self.start_track(nxt, automatic=automatic)
        elif mode == "repeat_queue":
            self.start_track(0, automatic=automatic)
        elif mode == "repeat_current" and self.current_index >= 0:
            self.start_track(self.current_index, automatic=automatic)

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
            current_key = str(self.queue[self.current_index].id or self.queue[self.current_index].url)
            if current_key not in self.cache_failures:
                self.start_track(self.current_index, automatic=True)
                return
            # A track already known to be unavailable must not be retried by
            # Repeat current. Reuse the normal unavailable-track continuation.
            self._continue_after_unavailable(self.seek_generation, self.current_index)
            return
        if mode == "shuffle" and self.queue:
            import random
            choices = [i for i in range(len(self.queue)) if i != self.current_index]
            if not choices:
                choices = list(range(len(self.queue)))
            choices = [i for i in choices if str(self.queue[i].id or self.queue[i].url) not in self.cache_failures]
            if not choices:
                self.clear_network_failures()
                choices = [
                    i for i in range(len(self.queue))
                    if i != self.current_index
                    and str(self.queue[i].id or self.queue[i].url) not in self.cache_failures
                ]
            if not choices:
                self.status.set(self.tr("queue_finished"))
                self.refresh_buttons()
                return
            self.start_track(random.choice(choices), automatic=True)
            return
        nxt = self.current_index + 1
        while nxt < len(self.queue) and str(self.queue[nxt].id or self.queue[nxt].url) in self.cache_failures:
            nxt += 1
        if nxt < len(self.queue):
            self.start_track(nxt, automatic=True)
        elif mode == "repeat_queue" and self.queue:
            self.clear_network_failures()
            candidates = [i for i in range(len(self.queue)) if str(self.queue[i].id or self.queue[i].url) not in self.cache_failures]
            if candidates:
                self.start_track(candidates[0], automatic=True)
            else:
                self.status.set(self.tr("queue_finished"))
                self.refresh_buttons()
        else:
            self.status.set(self.tr("queue_finished"))
            self.refresh_buttons()
