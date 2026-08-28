import tkinter as tk
from tkinter import ttk, BOTH, LEFT, RIGHT, X, Y

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
