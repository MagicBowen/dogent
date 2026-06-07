import asyncio
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from prompt_toolkit.document import Document
from rich.console import Console

from dogent.cli import DogentCLI, DogentCompleter


class ContextCompleterTests(unittest.TestCase):
    def test_context_command_shows_reset_option(self) -> None:
        completer = DogentCompleter(Path("."), ["/context"])
        comps = list(completer.get_completions(Document("/context "), None))
        texts = [c.text for c in comps]
        self.assertIn("reset", texts)

    def test_context_partial_reset_matches(self) -> None:
        completer = DogentCompleter(Path("."), ["/context"])
        comps = list(completer.get_completions(Document("/context re"), None))
        texts = [c.text for c in comps]
        self.assertIn("reset", texts)

    def test_context_reset_with_trailing_space_stops_suggestions(self) -> None:
        completer = DogentCompleter(Path("."), ["/context"])
        comps = list(completer.get_completions(Document("/context reset "), None))
        texts = [c.text for c in comps]
        self.assertEqual([], texts)


class ContextCommandTests(unittest.TestCase):
    def _make_cli(self, root: Path, console: Console) -> DogentCLI:
        return DogentCLI(root=root, console=console, interactive_prompts=False)

    def test_context_reset_clears_session(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = self._make_cli(Path(tmp), console)
            mock_agent = mock.AsyncMock()
            cli.agent = mock_agent  # type: ignore[assignment]

            async def run():
                result = await cli._cmd_context("/context reset")
                return result

            should_continue = asyncio.run(run())
            self.assertTrue(should_continue)
            mock_agent.reset.assert_awaited_once()
            output = console.file.getvalue()
            self.assertIn("Context Reset", output)
            self.assertIn("cleared", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_context_info_shows_turn_count(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = self._make_cli(Path(tmp), console)
            mock_agent = mock.MagicMock()
            mock_agent._turn_count = 3
            mock_agent._client = mock.MagicMock()
            cli.agent = mock_agent  # type: ignore[assignment]

            async def run():
                result = await cli._cmd_context("/context")
                return result

            should_continue = asyncio.run(run())
            self.assertTrue(should_continue)
            output = console.file.getvalue()
            self.assertIn("Session Context", output)
            self.assertIn("Turns this session: 3", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_context_unknown_subcommand_shows_error(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
            cli = self._make_cli(Path(tmp), console)

            async def run():
                result = await cli._cmd_context("/context compact")
                return result

            should_continue = asyncio.run(run())
            self.assertTrue(should_continue)
            output = console.file.getvalue()
            self.assertIn("Unknown context subcommand", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
