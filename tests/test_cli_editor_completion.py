import unittest

try:
    from prompt_toolkit.buffer import Buffer, CompletionState
    from prompt_toolkit.completion import Completion
except Exception:  # pragma: no cover - optional dependency
    Buffer = None  # type: ignore
    CompletionState = None  # type: ignore
    Completion = None  # type: ignore

from dogent.cli.input import (
    apply_completion_or_insert_newline,
    move_completion_selection,
)


@unittest.skipIf(Buffer is None, "prompt_toolkit is not available")
class EditorCompletionTests(unittest.TestCase):
    def test_enter_accepts_completion(self) -> None:
        buffer = Buffer()
        buffer.text = "a"
        buffer.cursor_position = 1
        state = CompletionState(
            buffer.document,
            [Completion("alpha", start_position=-1)],
            complete_index=0,
        )
        buffer.complete_state = state

        applied = apply_completion_or_insert_newline(buffer)

        self.assertTrue(applied)
        self.assertEqual("alpha", buffer.text)

    def test_enter_inserts_newline_without_completion(self) -> None:
        buffer = Buffer()
        buffer.text = "hello"
        buffer.cursor_position = len(buffer.text)

        applied = apply_completion_or_insert_newline(buffer)

        self.assertFalse(applied)
        self.assertEqual("hello\n", buffer.text)

    def test_move_completion_selection_handles_up_down(self) -> None:
        buffer = Buffer()
        buffer.text = "a"
        buffer.cursor_position = 1
        state = CompletionState(
            buffer.document,
            [Completion("alpha", start_position=-1), Completion("beta", start_position=-1)],
            complete_index=0,
        )
        buffer.complete_state = state

        moved = move_completion_selection(buffer, "down")

        self.assertTrue(moved)
        self.assertEqual(1, buffer.complete_state.complete_index)

        moved = move_completion_selection(buffer, "up")

        self.assertTrue(moved)
        self.assertEqual(0, buffer.complete_state.complete_index)

    def test_move_completion_selection_no_state(self) -> None:
        buffer = Buffer()
        buffer.text = "hello"
        buffer.cursor_position = len(buffer.text)

        moved = move_completion_selection(buffer, "down")

        self.assertFalse(moved)


if __name__ == "__main__":
    unittest.main()
