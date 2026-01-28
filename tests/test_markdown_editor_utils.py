import unittest
from pathlib import Path

from prompt_toolkit.document import Document

from dogent.cli import (
    SimpleMarkdownLexer,
    format_save_error_message,
    get_lexer_by_name,
    pygments_token_to_classname,
    mark_math_for_preview,
    resolve_save_path,
    wrap_markdown_code_block,
    indent_block,
)


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

    def test_format_save_error_message_with_absolute_hint(self) -> None:
        root = Path("/tmp/root")
        exc = OSError(30, "Read-only file system")
        message = format_save_error_message(
            Path("/draft/doc.md"), exc, path_text="/draft/doc.md", root=root
        )
        self.assertIn("Could not save to /draft/doc.md", message)
        self.assertIn("Paths starting with '/' are absolute.", message)

    def test_format_save_error_message_relative_path(self) -> None:
        root = Path("/tmp/root")
        exc = OSError(13, "Permission denied")
        message = format_save_error_message(
            Path("/tmp/root/draft/doc.md"), exc, path_text="draft/doc.md", root=root
        )
        self.assertIn("Could not save to draft/doc.md", message)
        self.assertIn("Check that the directory exists and is writable.", message)
        self.assertNotIn("Paths starting with '/'", message)

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

    def test_simple_markdown_lexer_code_block_language(self) -> None:
        lexer = SimpleMarkdownLexer()
        doc = Document(text="```python\nprint('hi')\n```")
        line = lexer.lex_document(doc)(1)
        styles = {style for style, _ in line}
        if pygments_token_to_classname is None or get_lexer_by_name is None:
            self.assertIn("class:md.codeblock", styles)
        else:
            has_pygments = any("class:pygments." in style for style in styles)
            self.assertTrue(has_pygments)

    def test_simple_markdown_lexer_code_block_no_language(self) -> None:
        lexer = SimpleMarkdownLexer()
        doc = Document(text="```\nplain\n```")
        line = lexer.lex_document(doc)(1)
        styles = {style for style, _ in line}
        self.assertIn("class:md.codeblock", styles)

    def test_wrap_markdown_code_block_extends_fence(self) -> None:
        text = "```\nexample\n```"
        block = wrap_markdown_code_block(text, language="markdown")
        self.assertTrue(block.startswith("````markdown"))
        self.assertIn("example", block)

    def test_indent_block_prefixes_lines(self) -> None:
        text = "line1\nline2"
        indented = indent_block(text, "  ")
        self.assertEqual(indented, "  line1\n  line2")


if __name__ == "__main__":
    unittest.main()
