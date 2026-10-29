"""The single home of every ANSI escape in the project.

Palette: neon cyan + hot magenta, glowing on a black background.
Color switches off when NO_COLOR is set (https://no-color.org) or when
the output stream is not a TTY.
"""

from __future__ import annotations

import os
import sys
from typing import TextIO

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
ON_BLACK = "\033[40m"


def color_enabled(stream: TextIO | None = None) -> bool:
    """Return True if ANSI color should be written to ``stream``."""
    if os.environ.get("NO_COLOR", ""):
        return False
    stream = sys.stdout if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    try:
        return bool(isatty and isatty())
    except (ValueError, OSError):
        return False


class Palette:
    """Wraps text in the synthwave palette, or passes it through untouched."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _paint(self, text: str, *codes: str) -> str:
        if not self.enabled:
            return text
        return "".join(codes) + text + RESET

    def cyan(self, text: str) -> str:
        return self._paint(text, CYAN, ON_BLACK)

    def magenta(self, text: str) -> str:
        return self._paint(text, MAGENTA, ON_BLACK)

    def neon(self, text: str) -> str:
        return self._paint(text, BOLD, MAGENTA, ON_BLACK)

    def dim(self, text: str) -> str:
        return self._paint(text, DIM, CYAN, ON_BLACK)


def palette_for(stream: TextIO | None = None) -> Palette:
    return Palette(color_enabled(stream))
