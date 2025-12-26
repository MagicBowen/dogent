import asyncio
import unittest

from rich.console import Console

from dogent.wait_indicator import LLMWaitIndicator


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


if __name__ == "__main__":
    unittest.main()
