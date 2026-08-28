from dataclasses import dataclass
from pathlib import Path

@dataclass
class Track:
    id: str
    title: str
    url: str
    thumbnail: str = ""
    duration: float = 0.0
    channel: str = ""

    @property
    def label(self):
        return f"{self.title} — {self.channel}" if self.channel else self.title
