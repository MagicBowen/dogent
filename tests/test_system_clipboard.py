import unittest
from unittest import mock

from dogent import cli


class SystemClipboardTests(unittest.TestCase):
    def test_system_clipboard_supported_darwin(self) -> None:
        with mock.patch.object(cli, "pyperclip", None), mock.patch.object(
            cli, "_darwin_clipboard_cmd", side_effect=["/usr/bin/pbcopy", "/usr/bin/pbpaste"]
        ), mock.patch.object(cli.sys, "platform", "darwin"):
            self.assertTrue(cli._system_clipboard_supported())

    def test_write_system_clipboard_darwin_uses_cmd(self) -> None:
        with mock.patch.object(cli, "pyperclip", None), mock.patch.object(
            cli, "_darwin_clipboard_cmd", return_value="/usr/bin/pbcopy"
        ), mock.patch.object(cli.sys, "platform", "darwin"), mock.patch.object(
            cli.subprocess, "run"
        ) as run_mock:
            ok = cli._write_system_clipboard("hello")
            self.assertTrue(ok)
            run_mock.assert_called_once()

    def test_read_system_clipboard_darwin_uses_cmd(self) -> None:
        fake = mock.Mock()
        fake.stdout = b"clipboard"
        with mock.patch.object(cli, "pyperclip", None), mock.patch.object(
            cli, "_darwin_clipboard_cmd", return_value="/usr/bin/pbpaste"
        ), mock.patch.object(cli.sys, "platform", "darwin"), mock.patch.object(
            cli.subprocess, "run", return_value=fake
        ) as run_mock:
            text = cli._read_system_clipboard()
            self.assertEqual(text, "clipboard")
            run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
