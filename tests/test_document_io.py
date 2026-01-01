import tempfile
import unittest
from unittest import mock
from pathlib import Path

from dogent import document_io
from dogent.document_io import read_document


class DocumentIOTests(unittest.TestCase):
    def test_read_pdf_text(self) -> None:
        try:
            import fitz  # type: ignore
        except Exception:
            self.skipTest("PyMuPDF not installed")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "text.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello PDF")
            doc.save(str(path))
            doc.close()

            result = read_document(path)
            self.assertIsNone(result.error)
            self.assertIn("Hello PDF", result.content)
            self.assertEqual(result.format, "pdf")

    def test_read_pdf_no_text(self) -> None:
        try:
            import fitz  # type: ignore
        except Exception:
            self.skipTest("PyMuPDF not installed")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.pdf"
            doc = fitz.open()
            doc.new_page()
            doc.save(str(path))
            doc.close()

            result = read_document(path)
            self.assertIsNotNone(result.error)
            self.assertIn("no extractable text", result.error or "")

    def test_read_xlsx_default_and_named_sheet(self) -> None:
        try:
            import openpyxl  # type: ignore
        except Exception:
            self.skipTest("openpyxl not installed")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.xlsx"
            wb = openpyxl.Workbook()
            ws1 = wb.active
            ws1.title = "Sheet1"
            ws1.append(["Name", "Value"])
            ws1.append(["Alpha", 1])
            ws2 = wb.create_sheet("Sheet2")
            ws2.append(["Note"])
            ws2.append(["Second"])
            wb.save(path)

            default_result = read_document(path)
            self.assertEqual(default_result.metadata.get("sheet"), "Sheet1")
            self.assertIn("Alpha", default_result.content)

            sheet2_result = read_document(path, sheet="Sheet2")
            self.assertEqual(sheet2_result.metadata.get("sheet"), "Sheet2")
            self.assertIn("Second", sheet2_result.content)

    def test_read_docx_with_pandoc(self) -> None:
        try:
            import pypandoc  # type: ignore
        except Exception:
            self.skipTest("pypandoc not installed")

        try:
            pypandoc.get_pandoc_version()
        except Exception:
            self.skipTest("pandoc not available")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.docx"
            md = "# Title\n\nHello docx"
            pypandoc.convert_text(md, to="docx", format="md", outputfile=str(path))

            result = read_document(path)
            self.assertIsNone(result.error)
            self.assertIn("Hello docx", result.content)

    def test_resolve_pdf_style_prefers_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace_root = tmp_path / "workspace"
            (workspace_root / ".dogent").mkdir(parents=True)
            workspace_style = workspace_root / ".dogent" / document_io.PDF_STYLE_FILENAME
            workspace_style.write_text("workspace-style", encoding="utf-8")

            global_root = tmp_path / "global"
            global_root.mkdir()
            global_style = global_root / document_io.PDF_STYLE_FILENAME
            global_style.write_text("global-style", encoding="utf-8")

            css, warnings = document_io._resolve_pdf_style(
                workspace_root, global_root=global_root
            )
            self.assertEqual(css, "workspace-style")
            self.assertEqual(warnings, [])

    def test_resolve_pdf_style_falls_back_to_global(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace_root = tmp_path / "workspace"
            workspace_root.mkdir()

            global_root = tmp_path / "global"
            global_root.mkdir()
            global_style = global_root / document_io.PDF_STYLE_FILENAME
            global_style.write_text("global-style", encoding="utf-8")

            css, warnings = document_io._resolve_pdf_style(
                workspace_root, global_root=global_root
            )
            self.assertEqual(css, "global-style")
            self.assertEqual(warnings, [])

    def test_resolve_pdf_style_warns_on_unreadable_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workspace_root = tmp_path / "workspace"
            (workspace_root / ".dogent").mkdir(parents=True)
            workspace_style = workspace_root / ".dogent" / document_io.PDF_STYLE_FILENAME
            workspace_style.write_text("workspace-style", encoding="utf-8")

            global_root = tmp_path / "global"
            global_root.mkdir()
            global_style = global_root / document_io.PDF_STYLE_FILENAME
            global_style.write_text("global-style", encoding="utf-8")

            original_read_text = Path.read_text

            def fake_read_text(self, *args, **kwargs):  # type: ignore[no-untyped-def]
                if self == workspace_style:
                    raise OSError("nope")
                return original_read_text(self, *args, **kwargs)

            with mock.patch.object(Path, "read_text", new=fake_read_text):
                css, warnings = document_io._resolve_pdf_style(
                    workspace_root, global_root=global_root
                )

            self.assertEqual(css, "global-style")
            self.assertTrue(warnings)
            self.assertIn("Could not read PDF style file", warnings[0])

    # def test_build_pdf_header_footer_includes_page_numbers(self) -> None:
    #     header, footer = document_io._build_pdf_header_footer("body { color: #111; }")
    #     self.assertIsNone(header)
    #     self.assertIn("pdf-footer", footer)
    #     self.assertIn("pageNumber", footer)
    #     self.assertIn("totalPages", footer)

    def test_markdown_to_html_adds_pygments_tokens(self) -> None:
        try:
            import pygments  # type: ignore  # noqa: F401
        except Exception:
            self.skipTest("pygments not installed")
        md = "```python\nfor i in range(1):\n    pass\n```"
        html = document_io._markdown_to_html(md, title="Test")
        self.assertIn("class=\"k\"", html)

    def test_markdown_to_html_includes_base_href(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            md = "![alt](image.png)"
            html = document_io._markdown_to_html(
                md,
                title="Test",
                base_path=base_path,
            )
            base_href = base_path.resolve().as_uri()
            if not base_href.endswith("/"):
                base_href = f"{base_href}/"
            self.assertIn(f"<base href=\"{base_href}\" />", html)

    def test_markdown_to_html_inlines_local_images(self) -> None:
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01"
            b"\x01\x01\x00\x18\xdd\x8d\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            img_path = base_dir / "img.png"
            img_path.write_bytes(png_bytes)
            md = "![alt](img.png)"
            html = document_io._markdown_to_html(
                md,
                title="Images",
                base_path=base_dir,
                workspace_root=base_dir,
            )
            self.assertIn("data:image/png;base64", html)


class DocumentIOAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_playwright_install_runs_in_thread(self) -> None:
        with mock.patch(
            "dogent.document_io.asyncio.to_thread", new=mock.AsyncMock()
        ) as to_thread:
            await document_io._ensure_playwright_chromium_installed_async()
            to_thread.assert_awaited_once_with(
                document_io._ensure_playwright_chromium_installed
            )

    async def test_markdown_to_pdf_uses_file_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md_path = tmp_path / "note.md"
            md_path.write_text("![alt](image.png)", encoding="utf-8")
            output_path = tmp_path / "note.pdf"
            with mock.patch(
                "dogent.document_io._resolve_pdf_style",
                return_value=("body { color: #111; }", []),
            ):
                with mock.patch(
                    "dogent.document_io._html_to_pdf", new=mock.AsyncMock()
                ) as html_to_pdf:
                    await document_io._markdown_to_pdf(
                        md_path,
                        output_path=output_path,
                        title="Note",
                        workspace_root=tmp_path,
                    )
            _, kwargs = html_to_pdf.await_args
            self.assertTrue(kwargs["source_url"].startswith("file://"))


class DocumentConversionTests(unittest.IsolatedAsyncioTestCase):
    async def test_convert_docx_to_markdown_with_extract_media(self) -> None:
        try:
            import pypandoc  # type: ignore
        except Exception:
            self.skipTest("pypandoc not installed")

        try:
            pypandoc.get_pandoc_version()
        except Exception:
            self.skipTest("pandoc not available")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            md_path = tmp_path / "source.md"
            md_path.write_text("# Title\n\nHello docx", encoding="utf-8")
            docx_path = tmp_path / "source.docx"
            pypandoc.convert_file(
                str(md_path),
                to="docx",
                format="md",
                outputfile=str(docx_path),
            )

            output_md = tmp_path / "output.md"
            extract_dir = tmp_path / "images"
            result = await document_io.convert_document_async(
                docx_path,
                output_path=output_md,
                extract_media_dir=extract_dir,
            )

            self.assertTrue(output_md.exists())
            self.assertIn("Hello docx", output_md.read_text(encoding="utf-8"))
            self.assertTrue(extract_dir.exists())
            self.assertEqual(result.output_format, "md")

    async def test_convert_pdf_to_markdown(self) -> None:
        try:
            import fitz  # type: ignore
        except Exception:
            self.skipTest("PyMuPDF not installed")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "source.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello PDF")
            doc.save(str(pdf_path))
            doc.close()

            output_md = tmp_path / "output.md"
            result = await document_io.convert_document_async(
                pdf_path, output_path=output_md
            )

            self.assertTrue(output_md.exists())
            self.assertIn("Hello PDF", output_md.read_text(encoding="utf-8"))
            self.assertEqual(result.output_format, "md")
            self.assertTrue(result.notes)


if __name__ == "__main__":
    unittest.main()
