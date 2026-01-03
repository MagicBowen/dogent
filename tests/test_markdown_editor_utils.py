import unittest
from pathlib import Path

from prompt_toolkit.document import Document

from dogent.cli import SimpleMarkdownLexer, mark_math_for_preview, resolve_save_path


class MarkdownEditorUtilsTests(unittest.TestCase):
    def test_mark_math_for_preview_inline(self) -> None:
        text = "Value $x$ here."
        rendered = mark_math_for_preview(text)
        self.assertIn("`[math] x [/math]`", rendered)

    def test_mark_math_for_preview_block(self) -> None:
        text = "Equation:\n$$\na+b\n$$"
        rendered = mark_math_for_preview(text)
        self.assertIn("```math", rendered)
        self.assertIn("a+b", rendered)

    def test_resolve_save_path_relative_and_absolute(self) -> None:
        root = Path("/tmp/root")
        rel = resolve_save_path(root, "notes.md")
        self.assertEqual(rel, root / "notes.md")
        abs_path = resolve_save_path(root, "/tmp/abs.md")
        self.assertEqual(abs_path, Path("/tmp/abs.md"))

    def test_simple_markdown_lexer_heading(self) -> None:
        lexer = SimpleMarkdownLexer()
        doc = Document(text="# Title")
        line = lexer.lex_document(doc)(0)
        self.assertEqual(line[0][0], "class:md.heading")

    def test_simple_markdown_lexer_inline_code(self) -> None:
        lexer = SimpleMarkdownLexer()
        doc = Document(text="Use `code` here.")
        line = lexer.lex_document(doc)(0)
        styles = {style for style, _ in line}
        self.assertIn("class:md.inlinecode", styles)


if __name__ == "__main__":
    unittest.main()
