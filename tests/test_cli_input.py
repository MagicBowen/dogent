import unittest

try:
    from prompt_toolkit.document import Document
    from prompt_toolkit.data_structures import Point
except ImportError:  # pragma: no cover - optional dependency
    Document = None  # type: ignore
    Point = None  # type: ignore

from dogent.cli import (
    _clear_count_for_alt_backspace,
    _cursor_target_from_render_info,
    _should_move_within_multiline,
)


class RenderInfoStub:
    def __init__(
        self,
        *,
        cursor_x: int,
        cursor_y: int,
        visible_line_to_row_col: dict[int, tuple[int, int]],
        rowcol_to_yx: dict[tuple[int, int], tuple[int, int]],
        x_offset: int = 0,
    ) -> None:
        self.cursor_position = Point(x=cursor_x, y=cursor_y)
        self.visible_line_to_row_col = visible_line_to_row_col
        self._rowcol_to_yx = rowcol_to_yx
        self._x_offset = x_offset


class MultilineNavigationTests(unittest.TestCase):
    def _skip_if_missing(self) -> None:
        if Document is None or Point is None:
            self.skipTest("prompt_toolkit is required for Document tests")

    def test_single_line_does_not_move_within_buffer(self) -> None:
        self._skip_if_missing()
        doc = Document("hello", cursor_position=5)
        self.assertFalse(_should_move_within_multiline(doc, "up"))
        self.assertFalse(_should_move_within_multiline(doc, "down"))

    def test_multiline_middle_line_moves_within_buffer(self) -> None:
        self._skip_if_missing()
        text = "one\ntwo\nthree"
        doc = Document(text, cursor_position=len("one\n"))
        self.assertTrue(_should_move_within_multiline(doc, "up"))
        self.assertTrue(_should_move_within_multiline(doc, "down"))

    def test_multiline_top_line_only_moves_down(self) -> None:
        self._skip_if_missing()
        text = "one\ntwo\nthree"
        doc = Document(text, cursor_position=0)
        self.assertFalse(_should_move_within_multiline(doc, "up"))
        self.assertTrue(_should_move_within_multiline(doc, "down"))

    def test_multiline_last_line_only_moves_up(self) -> None:
        self._skip_if_missing()
        text = "one\ntwo\nthree"
        doc = Document(text, cursor_position=len(text))
        self.assertTrue(_should_move_within_multiline(doc, "up"))
        self.assertFalse(_should_move_within_multiline(doc, "down"))

    def test_render_info_moves_within_wrapped_line_up(self) -> None:
        self._skip_if_missing()
        doc = Document("abcdefghij", cursor_position=6)
        info = RenderInfoStub(
            cursor_x=1,
            cursor_y=1,
            visible_line_to_row_col={0: (0, 0), 1: (0, 5)},
            rowcol_to_yx={(0, 0): (0, 0), (0, 5): (1, 0)},
        )
        target = _cursor_target_from_render_info(doc, info, "up")
        self.assertEqual(target, 1)

    def test_render_info_moves_within_wrapped_line_down(self) -> None:
        self._skip_if_missing()
        doc = Document("abcdefghij", cursor_position=1)
        info = RenderInfoStub(
            cursor_x=1,
            cursor_y=0,
            visible_line_to_row_col={0: (0, 0), 1: (0, 5)},
            rowcol_to_yx={(0, 0): (0, 0), (0, 5): (1, 0)},
        )
        target = _cursor_target_from_render_info(doc, info, "down")
        self.assertEqual(target, 6)

    def test_render_info_moves_within_wrapped_cjk_line_up(self) -> None:
        self._skip_if_missing()
        text = "\u4e2d\u6587\u4e2d\u6587"
        doc = Document(text, cursor_position=3)
        info = RenderInfoStub(
            cursor_x=2,
            cursor_y=1,
            visible_line_to_row_col={0: (0, 0), 1: (0, 4)},
            rowcol_to_yx={(0, 0): (0, 0), (0, 2): (1, 0)},
        )
        target = _cursor_target_from_render_info(doc, info, "up")
        self.assertEqual(target, 1)

    def test_render_info_moves_within_wrapped_cjk_line_down(self) -> None:
        self._skip_if_missing()
        text = "\u4e2d\u6587\u4e2d\u6587"
        doc = Document(text, cursor_position=1)
        info = RenderInfoStub(
            cursor_x=2,
            cursor_y=0,
            visible_line_to_row_col={0: (0, 0), 1: (0, 4)},
            rowcol_to_yx={(0, 0): (0, 0), (0, 2): (1, 0)},
        )
        target = _cursor_target_from_render_info(doc, info, "down")
        self.assertEqual(target, 3)

    def test_render_info_returns_none_at_edge(self) -> None:
        self._skip_if_missing()
        doc = Document("abc", cursor_position=0)
        info = RenderInfoStub(
            cursor_x=0,
            cursor_y=0,
            visible_line_to_row_col={0: (0, 0)},
            rowcol_to_yx={(0, 0): (0, 0)},
        )
        self.assertIsNone(_cursor_target_from_render_info(doc, info, "up"))


class AltBackspaceShortcutTests(unittest.TestCase):
    def test_clear_count_single_line_clears_all_before_cursor(self) -> None:
        if Document is None:
            self.skipTest("prompt_toolkit is required for Document tests")
        doc = Document("hello", cursor_position=3)
        self.assertEqual(_clear_count_for_alt_backspace(doc), 3)

    def test_clear_count_multiline_clears_current_line_before_cursor(self) -> None:
        if Document is None:
            self.skipTest("prompt_toolkit is required for Document tests")
        doc = Document("one\ntwo\nthree", cursor_position=len("one\ntw"))
        self.assertEqual(_clear_count_for_alt_backspace(doc), len("tw"))


if __name__ == "__main__":
    unittest.main()
