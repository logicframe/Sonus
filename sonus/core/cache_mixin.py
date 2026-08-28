from ..config.common import *
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.utils import fmt_time

class CacheMixin:
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
            known_error = self.cache_failures.get(key)
            if known_error is not None:
                return self.cache_futures.get(key) or self._failed_future(known_error)

            future = self.cache_futures.get(key)
            if future is not None:
                if not future.done():
                    return future
                try:
                    future.result()
                    return future
                except Exception as exc:
                    if self._is_unavailable_error(exc):
                        self.cache_failures[key] = exc
                    else:
                        self.cache_futures.pop(key, None)
                        return self.ensure_cache_future(track)
                    return future

            future = self.cache_executor.submit(self.get_or_download_ogg, track)
            self.cache_futures[key] = future
            future.add_done_callback(lambda completed, cached_track=track: self._remember_cache_failure(cached_track, completed))
        return future

    @staticmethod
    def _failed_future(error):
        from concurrent.futures import Future
        future = Future()
        future.set_exception(error)
        return future

    @staticmethod
    def _is_unavailable_error(error):
        text = str(error).lower()
        markers = (
            "video unavailable", "content isn't available", "content is not available",
            "not available in your country", "not available in this country",
            "geo-restricted", "geoblocked", "private video", "members-only",
            "video is unavailable", "this video is not available",
        )
        return any(marker in text for marker in markers)

    def _remember_cache_failure(self, track, future):
        try:
            error = future.exception()
        except Exception as exc:
            error = exc
        if error is None or self._closing or not self._is_unavailable_error(error):
            return
        key = str(track.id or track.url)
        with self.cache_lock:
            self.cache_failures[key] = error

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
