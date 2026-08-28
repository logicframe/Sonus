from pathlib import Path
import shutil
from ..config.common import CACHE_DIR, AUDIO_CACHE_DIR

def clear_runtime_cache() -> None:
    """Remove runtime cache from the previous session and recreate it."""
    try:
        if CACHE_DIR.exists():
            for child in CACHE_DIR.iterdir():
                try:
                    if child.is_dir(): shutil.rmtree(child)
                    else: child.unlink()
                except OSError: pass
    finally:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
