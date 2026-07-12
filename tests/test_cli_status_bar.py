import asyncio
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from prompt_toolkit.application import Application
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from rich.console import Console

from dogent.cli import DogentCLI


class _FakePromptSession:
    def __init__(self, result: str = "answer") -> None:
        self.result = result

    async def prompt_async(self, _prompt: str, **_kwargs):
        return self.result


class _FakeApplication:
    async def run_async(self):
        return "done"


class CLIStatusBarTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_home = os.environ.get("HOME")
        self._home = tempfile.TemporaryDirectory()
        self._root = tempfile.TemporaryDirectory()
        os.environ["HOME"] = self._home.name
        self.console = Console(
            file=io.StringIO(), force_terminal=False, color_system=None
        )
        self.cli = DogentCLI(
            root=Path(self._root.name),
            console=self.console,
            interactive_prompts=False,
        )

    async def asyncTearDown(self) -> None:
        await self.cli._stop_status_capacity_lookup()
        self.cli.status_bar.stop_live()
        if self._original_home is not None:
            os.environ["HOME"] = self._original_home
        else:
            os.environ.pop("HOME", None)
        self._home.cleanup()
        self._root.cleanup()

    async def test_read_input_hands_off_live_status_around_prompt(self) -> None:
        self.cli.session = _FakePromptSession()  # type: ignore[assignment]
        self.cli.status_bar.stop_live = mock.Mock()  # type: ignore[method-assign]
        self.cli.status_bar.start_live = mock.Mock()  # type: ignore[method-assign]
        result = await self.cli._read_input()
        self.assertEqual(result, "answer")
        self.cli.status_bar.stop_live.assert_called_once()
        self.cli.status_bar.start_live.assert_called_once()

    async def test_prompt_toolbar_overrides_default_background(self) -> None:
        self.assertIsNotNone(self.cli.session)
        style = self.cli.session.style
        self.assertIsNotNone(style)
        attrs = style.get_attrs_for_style_str("class:bottom-toolbar")
        self.assertEqual(attrs.bgcolor, "")
        self.assertFalse(attrs.reverse)

    async def test_inline_capability_uses_stable_startup_tty_state(self) -> None:
        self.cli._interactive_prompts = True
        self.cli._interactive_tty = True
        with mock.patch("dogent.cli.app.sys.stdin.isatty", return_value=False), mock.patch(
            "dogent.cli.app.sys.stdout.isatty", return_value=False
        ):
            self.assertTrue(self.cli._can_use_inline_choice())
            self.assertTrue(self.cli._can_use_multiline_editor())

    async def test_dedicated_prompt_attaches_status_and_restores_live(self) -> None:
        app = _FakeApplication()
        self.cli._attach_status_to_application = mock.Mock()  # type: ignore[method-assign]
        self.cli.status_bar.stop_live = mock.Mock()  # type: ignore[method-assign]
        self.cli.status_bar.start_live = mock.Mock()  # type: ignore[method-assign]
        with mock.patch("dogent.cli.app.patch_stdout", None):
            result = await self.cli._run_dedicated_prompt(app)  # type: ignore[arg-type]
        self.assertEqual(result, "done")
        self.cli._attach_status_to_application.assert_called_once_with(app)
        self.cli.status_bar.stop_live.assert_called_once()
        self.cli.status_bar.start_live.assert_called_once()

    async def test_editor_suspends_status_without_attaching_it(self) -> None:
        app = _FakeApplication()
        self.cli.status_bar.stop_live = mock.Mock()  # type: ignore[method-assign]
        self.cli.status_bar.start_live = mock.Mock()  # type: ignore[method-assign]
        self.cli._attach_status_to_application = mock.Mock()  # type: ignore[method-assign]
        result = await self.cli._run_editor_application(app)  # type: ignore[arg-type]
        self.assertEqual(result, "done")
        self.cli._attach_status_to_application.assert_not_called()
        self.cli.status_bar.stop_live.assert_called_once()
        self.cli.status_bar.start_live.assert_called_once()

    async def test_attach_status_adds_one_bottom_window(self) -> None:
        self.cli.status_bar.enabled = True
        app = Application(layout=Layout(Window()))
        self.cli._attach_status_to_application(app)
        self.assertIsInstance(app.layout.container, HSplit)
        self.assertEqual(len(app.layout.container.children), 2)
        self.cli._attach_status_to_application(app)
        self.assertEqual(len(app.layout.container.children), 2)

    async def test_capacity_task_is_scheduled_and_can_be_stopped(self) -> None:
        self.cli.status_state.resolve_capacity = mock.AsyncMock(  # type: ignore[method-assign]
            return_value=256_000
        )
        settings = SimpleNamespace(
            base_url="https://example.test", auth_token="token"
        )
        self.cli._schedule_status_capacity_lookup(settings)
        await self.cli._status_capacity_task
        self.cli.status_state.resolve_capacity.assert_awaited_once()
        await self.cli._stop_status_capacity_lookup()
        self.assertIsNone(self.cli._status_capacity_task)

    async def test_agent_turn_suspends_idle_status_until_completion(self) -> None:
        self.assertIsNone(self.cli.agent._activity_callback)
        self.cli.status_bar.suspend = mock.Mock()  # type: ignore[method-assign]
        self.cli.status_bar.resume = mock.Mock()  # type: ignore[method-assign]

        async def send_message(*_args, **_kwargs) -> None:
            self.assertTrue(self.cli.status_bar.suspend.called)
            self.assertFalse(self.cli.status_bar.resume.called)

        async def wait_for_escape(stop_event) -> bool:
            while not stop_event.is_set():
                await asyncio.sleep(0)
            return False

        self.cli.agent.send_message = mock.AsyncMock(side_effect=send_message)
        self.cli._wait_for_escape = wait_for_escape  # type: ignore[method-assign]

        await self.cli._run_single_with_interrupt("hello", [])

        self.cli.status_bar.suspend.assert_called_once()
        self.cli.status_bar.resume.assert_called_once()


if __name__ == "__main__":
    unittest.main()
