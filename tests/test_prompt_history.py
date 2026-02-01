import tempfile
import unittest
from pathlib import Path

from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.cli.input import LimitedInMemoryHistory


class PromptHistoryTests(unittest.TestCase):
    def test_prompt_history_strings_filters_and_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history = HistoryManager(DogentPaths(Path(tmp)))
            history.append(
                summary="User request",
                status="started",
                prompt="expanded",
                user_input="first",
            )
            history.append(
                summary="Command",
                status="command",
                prompt="/show history",
                user_input="/show history",
            )
            history.append(summary="Clarification", status="clarification", prompt=None)
            history.append(summary="Whitespace", status="started", prompt="   ")

            prompts = history.prompt_history_strings(limit=30)
            self.assertEqual(prompts, ["first", "/show history"])

    def test_prompt_history_strings_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history = HistoryManager(DogentPaths(Path(tmp)))
            for idx in range(35):
                history.append(
                    summary="User request",
                    status="started",
                    prompt=f"expanded-{idx}",
                    user_input=f"prompt-{idx}",
                )
            prompts = history.prompt_history_strings(limit=30)
            expected = [f"prompt-{idx}" for idx in range(5, 35)]
            self.assertEqual(prompts, expected)

    def test_limited_in_memory_history_caps_entries(self) -> None:
        if LimitedInMemoryHistory is None:
            self.skipTest("prompt_toolkit is not available")
        history = LimitedInMemoryHistory(max_length=2)
        history.append_string("a")
        history.append_string("b")
        history.append_string("c")
        self.assertEqual(history.get_strings(), ["b", "c"])


if __name__ == "__main__":
    unittest.main()
