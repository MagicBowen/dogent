import asyncio
import unittest
from unittest import mock

from rich.console import Console

from dogent.agent.wait import LLMWaitIndicator


class WaitIndicatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_wait_indicator_start_stop(self) -> None:
        console = Console(record=True, force_terminal=False, color_system=None)
        indicator = LLMWaitIndicator(console, label="Testing")
        await indicator.start()
        await asyncio.sleep(0.01)
        await indicator.stop()

    async def test_wait_indicator_formats_status(self) -> None:
        indicator = LLMWaitIndicator(Console(), label="Waiting")
        text = indicator._format_status(1.2)  # type: ignore[attr-defined]
        self.assertIn("Waiting", text)
        self.assertIn("1.2", text)

    async def test_wait_indicator_uses_shared_activity_callback(self) -> None:
        callback = mock.Mock()
        console = Console(record=True, force_terminal=False, color_system=None)
        indicator = LLMWaitIndicator(
            console, label="Shared", activity_callback=callback
        )
        await indicator.start()
        await asyncio.sleep(0.01)
        await indicator.stop()
        self.assertTrue(any("Shared" in str(call.args[0]) for call in callback.call_args_list[:-1]))
        self.assertIsNone(callback.call_args_list[-1].args[0])
        self.assertEqual(console.export_text(), "")


if __name__ == "__main__":
    unittest.main()
