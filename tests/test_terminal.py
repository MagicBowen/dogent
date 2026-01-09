import ctypes
import importlib
import sys
import types
import unittest
from unittest import mock


class TerminalWindowsTests(unittest.TestCase):
    def test_windows_console_modes(self) -> None:
        import dogent.cli.terminal as terminal

        original_platform = sys.platform
        last_mode = {"value": None}

        def fake_get_std_handle(_value):  # type: ignore[no-untyped-def]
            return 123

        def fake_get_console_mode(_handle, mode_ptr):  # type: ignore[no-untyped-def]
            ctypes.cast(mode_ptr, ctypes.POINTER(ctypes.c_ulong)).contents.value = 0xFFFF
            return 1

        def fake_set_console_mode(_handle, mode):  # type: ignore[no-untyped-def]
            last_mode["value"] = mode
            return 1

        kernel32 = types.SimpleNamespace(
            GetStdHandle=fake_get_std_handle,
            GetConsoleMode=fake_get_console_mode,
            SetConsoleMode=fake_set_console_mode,
        )
        stub_msvcrt = types.SimpleNamespace(
            kbhit=mock.Mock(return_value=True),
            getwch=mock.Mock(return_value="A"),
            getch=mock.Mock(return_value=b"A"),
        )

        try:
            with mock.patch.object(sys, "platform", "win32"):
                with mock.patch.dict(sys.modules, {"msvcrt": stub_msvcrt}):
                    with mock.patch.object(
                        ctypes, "WinDLL", return_value=kernel32, create=True
                    ):
                        win_term = importlib.reload(terminal)
                        settings = win_term.tcgetattr(0)
                        self.assertEqual(settings.handle, 123)
                        self.assertEqual(settings.mode, 0xFFFF)
                        win_term.setcbreak(0)
                        self.assertIsNotNone(last_mode["value"])
                        self.assertEqual(
                            last_mode["value"] & win_term.ENABLE_LINE_INPUT, 0
                        )
                        self.assertEqual(
                            last_mode["value"] & win_term.ENABLE_ECHO_INPUT, 0
                        )
                        self.assertEqual(
                            last_mode["value"] & win_term.ENABLE_QUICK_EDIT_MODE, 0
                        )
                        win_term.tcsetattr(0, win_term.TCSADRAIN, settings)
                        self.assertEqual(last_mode["value"], settings.mode)
                        self.assertEqual(win_term.getch(), "A")
        finally:
            with mock.patch.object(sys, "platform", original_platform):
                importlib.reload(terminal)


if __name__ == "__main__":
    unittest.main()
