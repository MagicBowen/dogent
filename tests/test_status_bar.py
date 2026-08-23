import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from rich.cells import cell_len
from rich.console import Console

from dogent.cli.status_bar import (
    DEFAULT_CONTEXT_WINDOW_TOKENS,
    EXTENDED_CONTEXT_WINDOW_TOKENS,
    StatusBarController,
    StatusBarFormatter,
    StatusBarState,
    context_capacity_from_hints,
    lookup_model_capacity,
    usage_input_tokens,
)


class StatusBarValueTests(unittest.TestCase):
    def test_capacity_override_requires_disable_compact(self) -> None:
        env = {
            "DISABLE_COMPACT": "1",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "320000",
        }
        self.assertEqual(context_capacity_from_hints("sonnet", env), 320_000)
        self.assertIsNone(
            context_capacity_from_hints(
                "sonnet", {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "320000"}
            )
        )

    def test_capacity_ignores_invalid_override_and_reads_1m_suffix(self) -> None:
        env = {
            "DISABLE_COMPACT": "true",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "invalid",
        }
        self.assertEqual(
            context_capacity_from_hints("Claude-Opus[1M]", env),
            EXTENDED_CONTEXT_WINDOW_TOKENS,
        )

    def test_usage_input_tokens_includes_cache_but_not_output(self) -> None:
        usage = {
            "input_tokens": 10,
            "cache_creation_input_tokens": 20,
            "cache_read_input_tokens": 30,
            "output_tokens": 999,
        }
        self.assertEqual(usage_input_tokens(usage), 60)

    def test_usage_input_tokens_avoids_gateway_cache_double_counting(self) -> None:
        usage = {
            "input_tokens": 40_000,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 39_000,
        }
        self.assertEqual(usage_input_tokens(usage), 40_000)
        usage["total_input_tokens"] = 41_000
        self.assertEqual(usage_input_tokens(usage), 41_000)

    def test_usage_input_tokens_rejects_malformed_or_negative_values(self) -> None:
        self.assertIsNone(usage_input_tokens(None))
        self.assertIsNone(usage_input_tokens({"input_tokens": "1"}))
        self.assertIsNone(usage_input_tokens({"input_tokens": -1}))


class StatusBarStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_state_starts_unknown_and_updates_latest_usage(self) -> None:
        state = StatusBarState("sonnet", Path.cwd(), environ={})
        self.assertIsNone(state.snapshot().context_percent)
        changed = state.update_from_assistant(
            "claude-sonnet",
            {
                "input_tokens": 128_000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
            0,
        )
        self.assertTrue(changed)
        self.assertEqual(state.snapshot().context_percent, 50)
        self.assertEqual(state.snapshot().model, "claude-sonnet")

    async def test_state_clamps_percent_and_rejects_stale_generation(self) -> None:
        state = StatusBarState("sonnet", Path.cwd(), environ={})
        state.update_from_assistant("sonnet", {"input_tokens": 999_999}, 0)
        self.assertEqual(state.snapshot().context_percent, 100)
        state.reset_context(1)
        self.assertIsNone(state.snapshot().context_percent)
        self.assertFalse(
            state.update_from_assistant("old", {"input_tokens": 10}, 0)
        )
        self.assertIsNone(state.snapshot().context_percent)

    async def test_configured_1m_suffix_is_preserved_over_resolved_model(self) -> None:
        state = StatusBarState("sonnet[1m]", Path.cwd(), environ={})
        state.update_from_assistant(
            "claude-sonnet-4", {"input_tokens": 100_000}, 0
        )
        snapshot = state.snapshot()
        self.assertEqual(snapshot.model, "sonnet[1m]")
        self.assertEqual(snapshot.context_capacity, 1_000_000)
        self.assertEqual(snapshot.context_percent, 10)

    async def test_set_configured_model_resets_usage_and_notifies(self) -> None:
        changed = mock.Mock()
        state = StatusBarState(
            "first", Path.cwd(), environ={}, on_change=changed
        )
        state.update_from_assistant("first", {"input_tokens": 1}, 0)
        state.set_configured_model("second", 2)
        snapshot = state.snapshot()
        self.assertEqual(snapshot.model, "second")
        self.assertIsNone(snapshot.context_tokens)
        self.assertEqual(state.generation, 2)
        self.assertGreaterEqual(changed.call_count, 2)

    async def test_capacity_lookup_success_cache_failure_and_fallback(self) -> None:
        state = StatusBarState("claude-model", Path.cwd(), environ={})
        lookup = mock.AsyncMock(return_value=640_000)
        self.assertEqual(await state.resolve_capacity(lookup), 640_000)
        self.assertEqual(state.snapshot().context_capacity, 640_000)
        self.assertEqual(await state.resolve_capacity(lookup), 640_000)
        lookup.assert_awaited_once_with("claude-model")

        fallback = StatusBarState("gateway-model", Path.cwd(), environ={})
        self.assertEqual(
            await fallback.resolve_capacity(mock.AsyncMock(side_effect=RuntimeError)),
            DEFAULT_CONTEXT_WINDOW_TOKENS,
        )

    async def test_stale_capacity_lookup_cannot_replace_new_model(self) -> None:
        state = StatusBarState("old", Path.cwd(), environ={})
        release = asyncio.Event()

        async def delayed(_model: str) -> int:
            await release.wait()
            return 900_000

        task = asyncio.create_task(state.resolve_capacity(delayed))
        await asyncio.sleep(0)
        state.set_configured_model("new", 1)
        release.set()
        await task
        self.assertEqual(
            state.snapshot().context_capacity, DEFAULT_CONTEXT_WINDOW_TOKENS
        )


class StatusBarFormatterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = StatusBarState("sonnet", Path.cwd(), environ={})
        self.formatter = StatusBarFormatter(self.state)

    def test_formats_wide_medium_and_narrow_without_wrapping(self) -> None:
        for width in (120, 60, 42, 30, 10):
            line = self.formatter.plain(width)
            self.assertNotIn("\n", line)
            self.assertLessEqual(cell_len(line), width)
        self.assertIn("Context", self.formatter.plain(120))
        self.assertIn("Ctx", self.formatter.plain(60))

    def test_sanitizes_model_and_middle_truncates_workspace(self) -> None:
        state = StatusBarState("bad\x1b[31m\nmodel", Path.cwd(), environ={})
        line = StatusBarFormatter(state).plain(42)
        self.assertNotIn("\x1b", line)
        self.assertNotIn("\n", line)
        self.assertIn("…", line)

    def test_status_text_is_highlighted_and_progress_is_green_without_background(self) -> None:
        self.state.update_from_assistant("sonnet", {"input_tokens": 200_000}, 0)
        rich_text = self.formatter.rich(120)
        self.assertIn("█", rich_text.plain)
        self.assertIn("[███████████████░░░░░]", rich_text.plain)
        self.assertTrue(all("on " not in str(span.style) for span in rich_text.spans))
        meter_offset = rich_text.plain.index("[")
        meter_span = next(
            span for span in rich_text.spans
            if span.start <= meter_offset < span.end
        )
        self.assertIn("green", str(meter_span.style))
        self.assertIn("bold", str(meter_span.style))
        fragments = self.formatter.prompt_fragments(120)
        self.assertEqual("".join(fragment[1] for fragment in fragments), self.formatter.plain(120))
        self.assertTrue(all("bg:" not in fragment[0] for fragment in fragments))
        meter_fragment = next(fragment for fragment in fragments if "█" in fragment[1])
        self.assertIn("ansigreen", meter_fragment[0])
        self.assertIn("bold", meter_fragment[0])

    def test_semantic_segments_preserve_plain_line(self) -> None:
        for width in (120, 60, 30):
            line = self.formatter.plain(width)
            segments = self.formatter._segments(line)
            self.assertEqual("".join(text for _role, text in segments), line)
            self.assertIn("model", {role for role, _text in segments})
            self.assertIn("progress", {role for role, _text in segments})

    def test_wait_activity_is_integrated_into_one_status_line(self) -> None:
        wide = self.formatter.plain(140, "Waiting for LLM response")
        medium = self.formatter.plain(70, "Waiting for LLM response")
        narrow = self.formatter.plain(35, "Waiting for LLM response")
        self.assertIn("⏳ Waiting for LLM response", wide)
        self.assertIn("⏳ Waiting", medium)
        self.assertIn("⏳", narrow)
        self.assertIn(Path.cwd().name, self.formatter.plain(80, "Waiting"))
        self.assertNotIn("\n", wide + medium + narrow)

    def test_ascii_fallback_avoids_unicode_symbols(self) -> None:
        formatter = StatusBarFormatter(self.state, use_unicode=False)
        line = formatter.plain(120)
        self.assertTrue(line.startswith("* "))
        self.assertNotIn("✦", line)
        self.assertNotIn("📁", line)
        self.assertIn("--------------------", line)

    def test_meter_matches_requested_twenty_cell_form(self) -> None:
        self.assertEqual(
            self.formatter._meter(45), "█████████░░░░░░░░░░░"
        )


class StatusBarControllerTests(unittest.TestCase):
    def test_disabled_controller_does_not_start_live_or_create_window(self) -> None:
        state = StatusBarState("sonnet", Path.cwd(), environ={})
        controller = StatusBarController(
            state, Console(force_terminal=False), enabled=False
        )
        controller.start_live()
        self.assertFalse(controller.live_active)
        self.assertIsNone(controller.status_window())

    def test_live_lifecycle_suspend_resume_and_refresh(self) -> None:
        state = StatusBarState("sonnet", Path.cwd(), environ={})
        console = Console(force_terminal=True)
        live = mock.MagicMock()
        with mock.patch(
            "dogent.cli.status_bar.Live", return_value=live
        ) as live_factory:
            controller = StatusBarController(state, console, enabled=True)
            controller.start_live()
            self.assertTrue(controller.live_active)
            live.start.assert_called_once_with(refresh=True)
            self.assertFalse(live_factory.call_args.kwargs["auto_refresh"])
            state.update_from_assistant("sonnet", {"input_tokens": 10}, 0)
            live.update.assert_called_once()
            live.update.reset_mock()
            controller.suspend()
            self.assertTrue(controller.suspended)
            self.assertFalse(controller.live_active)
            self.assertEqual(controller.prompt_toolbar(), [])
            self.assertIsNone(controller.status_window())
            live.stop.assert_called_once()
            controller.start_live()
            self.assertFalse(controller.live_active)
            controller.resume()
            self.assertFalse(controller.suspended)
            self.assertTrue(controller.live_active)
            self.assertEqual(live.start.call_count, 2)
            controller.stop_live()
            self.assertEqual(live.stop.call_count, 2)
            self.assertFalse(controller.live_active)
        self.assertIsNotNone(controller.status_window())

    def test_live_renderable_uses_current_render_width(self) -> None:
        state = StatusBarState("sonnet", Path.cwd(), environ={})
        controller = StatusBarController(
            state, Console(force_terminal=True), enabled=True
        )
        controller.formatter.rich = mock.Mock(return_value="bar")  # type: ignore[method-assign]
        options = SimpleNamespace(max_width=47)
        rendered = list(
            controller._live_renderable.__rich_console__(controller.console, options)
        )
        self.assertEqual(rendered, ["bar"])
        controller.formatter.rich.assert_called_once_with(47, None)


class ModelCapacityLookupTests(unittest.IsolatedAsyncioTestCase):
    async def test_lookup_skips_missing_credentials(self) -> None:
        self.assertIsNone(
            await lookup_model_capacity(
                "sonnet", base_url=None, auth_token=None
            )
        )

    async def test_lookup_reads_max_input_tokens_and_closes_client(self) -> None:
        client = mock.MagicMock()
        client.models.retrieve = mock.AsyncMock(
            return_value=SimpleNamespace(max_input_tokens=700_000)
        )
        client.close = mock.AsyncMock()
        factory = mock.Mock(return_value=client)
        anthropic = SimpleNamespace(AsyncAnthropic=factory)
        with mock.patch.dict("sys.modules", {"anthropic": anthropic}):
            result = await lookup_model_capacity(
                "claude-model",
                base_url="https://example.test",
                auth_token="secret",
                timeout=0.5,
            )
        self.assertEqual(result, 700_000)
        factory.assert_called_once()
        client.models.retrieve.assert_awaited_once_with(model_id="claude-model")
        client.close.assert_awaited_once()

    async def test_lookup_failure_is_non_blocking_fallback_signal(self) -> None:
        anthropic = SimpleNamespace(
            AsyncAnthropic=mock.Mock(side_effect=RuntimeError)
        )
        with mock.patch.dict("sys.modules", {"anthropic": anthropic}):
            result = await lookup_model_capacity(
                "claude-model", base_url=None, auth_token="secret"
            )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
