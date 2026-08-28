from pathlib import Path
import tkinter as tk
from tkinter import TclError
from .config.common import APP_DIR
from .core.platform import configure_windows_app_identity, apply_windows_icon
from .core.runtime_cache import clear_runtime_cache
from .app import App

def main():
    clear_runtime_cache()
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
