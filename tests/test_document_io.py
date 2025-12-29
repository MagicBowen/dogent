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


class DocumentIOAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_playwright_install_runs_in_thread(self) -> None:
        with mock.patch(
            "dogent.document_io.asyncio.to_thread", new=mock.AsyncMock()
        ) as to_thread:
            await document_io._ensure_playwright_chromium_installed_async()
            to_thread.assert_awaited_once_with(
                document_io._ensure_playwright_chromium_installed
            )


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
