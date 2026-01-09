"""
Cross-platform terminal control module.

Provides terminal control functions for both Unix/Linux/macOS and Windows.
On Unix systems, uses termios/tty.
On Windows, uses msvcrt.
"""

import sys
from dataclasses import dataclass
from typing import Any

if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    STD_INPUT_HANDLE = -10
    ENABLE_PROCESSED_INPUT = 0x0001
    ENABLE_LINE_INPUT = 0x0002
    ENABLE_ECHO_INPUT = 0x0004
    ENABLE_MOUSE_INPUT = 0x0010
    ENABLE_EXTENDED_FLAGS = 0x0080
    ENABLE_QUICK_EDIT_MODE = 0x0040

    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.LPDWORD]
    kernel32.GetConsoleMode.restype = wintypes.BOOL
    kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetConsoleMode.restype = wintypes.BOOL

    @dataclass(frozen=True)
    class _TerminalSettings:
        handle: int
        mode: int

    def _input_handle() -> int:
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        if handle is None or handle == wintypes.HANDLE(-1).value:
            raise OSError("Failed to get Windows console handle")
        return int(handle)

    def tcgetattr(fd: int) -> _TerminalSettings:
        """Get terminal settings (Windows)."""
        handle = _input_handle()
        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            raise OSError("Failed to read Windows console mode")
        return _TerminalSettings(handle=handle, mode=mode.value)

    def tcsetattr(fd: int, when: int, settings: _TerminalSettings) -> None:
        """Set terminal settings (Windows)."""
        if not kernel32.SetConsoleMode(settings.handle, settings.mode):
            raise OSError("Failed to restore Windows console mode")

    def setcbreak(fd: int) -> None:
        """Set terminal to cbreak mode (Windows)."""
        settings = tcgetattr(fd)
        mode = settings.mode
        mode &= ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_QUICK_EDIT_MODE)
        mode |= ENABLE_EXTENDED_FLAGS
        if not kernel32.SetConsoleMode(settings.handle, mode):
            raise OSError("Failed to set Windows console mode")

    TCSADRAIN = 0  # Dummy value for Windows compatibility

    def kbhit() -> bool:
        """Check if a keypress is available (Windows)."""
        return msvcrt.kbhit()

    def getch() -> str:
        """Get a single character from stdin (Windows)."""
        if hasattr(msvcrt, "getwch"):
            return msvcrt.getwch()
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
