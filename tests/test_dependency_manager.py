import unittest
from unittest import mock

from dogent.features import dependency_manager as dm


class DependencyManagerTests(unittest.TestCase):
    def test_extract_progress_percent_from_percent(self) -> None:
        self.assertEqual(dm.extract_progress_percent("Downloading 10%"), 10)
        self.assertEqual(dm.extract_progress_percent("100% complete"), 100)

    def test_extract_progress_percent_from_fraction(self) -> None:
        self.assertEqual(dm.extract_progress_percent("1.5 MB / 3.0 MB"), 50)

    def test_missing_dependencies_for_export_pdf(self) -> None:
        def module_available(name: str) -> bool:
            return name != "playwright"

        with (
            mock.patch.object(dm, "_module_available", side_effect=module_available),
            mock.patch.object(dm, "_playwright_chromium_available", return_value=False),
        ):
            missing = dm.missing_dependencies_for_tool(
                "mcp__dogent__export_document", {"format": "pdf"}
            )
        self.assertEqual(
            set(missing), {dm.DEP_PLAYWRIGHT, dm.DEP_PLAYWRIGHT_CHROMIUM}
        )

    def test_missing_dependencies_for_read_docx(self) -> None:
        with (
            mock.patch.object(dm, "_module_available", return_value=False),
            mock.patch.object(dm, "_pandoc_available", return_value=False),
        ):
            missing = dm.missing_dependencies_for_tool(
                "mcp__dogent__read_document", {"path": "file.docx"}
            )
        self.assertEqual(set(missing), {dm.DEP_PYPANDOC, dm.DEP_PANDOC})

    def test_build_install_steps_for_pandoc_and_playwright(self) -> None:
        steps = dm.build_install_steps(
            [dm.DEP_PANDOC, dm.DEP_PYPANDOC, dm.DEP_PLAYWRIGHT_CHROMIUM]
        )
        labels = [step.label for step in steps]
        self.assertTrue(any("Pandoc" in label for label in labels))
        self.assertTrue(any("Playwright Chromium" in label for label in labels))


if __name__ == "__main__":
    unittest.main()
