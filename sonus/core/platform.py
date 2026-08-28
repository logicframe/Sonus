import os
import tkinter as tk
from pathlib import Path

_WINDOWS_ICON_HANDLES=[]

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
