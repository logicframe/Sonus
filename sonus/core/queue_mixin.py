from ..config.common import *
from ..core.models import Track
from ..ui.widgets import RoundedCard
from ..core.utils import fmt_time

class QueueMixin:
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
