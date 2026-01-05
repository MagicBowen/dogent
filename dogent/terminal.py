"""
Cross-platform terminal control module.

Provides terminal control functions for both Unix/Linux/macOS and Windows.
On Unix systems, uses termios/tty.
On Windows, uses msvcrt.
"""

import sys
from typing import Any

if sys.platform == "win32":
    import msvcrt

    class _TerminalSettings:
        """Placeholder for Windows - no settings needed to restore."""

        pass

    def tcgetattr(fd: int) -> _TerminalSettings:
        """Get terminal settings (Windows stub)."""
        return _TerminalSettings()

    def tcsetattr(fd: int, when: int, settings: _TerminalSettings) -> None:
        """Set terminal settings (Windows stub)."""
        pass

    def setcbreak(fd: int) -> None:
        """Set terminal to cbreak mode (Windows stub)."""
        pass

    TCSADRAIN = 0  # Dummy value for Windows compatibility

    def kbhit() -> bool:
        """Check if a keypress is available (Windows)."""
        return msvcrt.kbhit()

    def getch() -> str:
        """Get a single character from stdin (Windows)."""
        return msvcrt.getch().decode("utf-8", errors="ignore")

else:
    import termios
    import tty

    _TerminalSettings = Any  # type: ignore[misc]
    tcgetattr = termios.tcgetattr  # type: ignore[assignment]
    tcsetattr = termios.tcsetattr  # type: ignore[assignment]
    TCSADRAIN = termios.TCSADRAIN
    setcbreak = tty.setcbreak  # type: ignore[assignment]

    import select

    def kbhit() -> bool:
        """Check if a keypress is available (Unix)."""
        return select.select([sys.stdin], [], [], 0)[0] != []

    def getch() -> str:
        """Get a single character from stdin (Unix)."""
        return sys.stdin.read(1)


__all__ = [
    "tcgetattr",
    "tcsetattr",
    "TCSADRAIN",
    "setcbreak",
    "kbhit",
    "getch",
    "_TerminalSettings",
]
