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

    def test_manual_instructions_include_download_path_on_install(self) -> None:
        with mock.patch.object(dm, "_os_name", return_value="linux"):
            message = dm.manual_instructions(
                [dm.DEP_PLAYWRIGHT_CHROMIUM],
                download_path="/tmp/cache",
                install_phase="install",
            )
        self.assertIn("Downloaded files location: /tmp/cache", message)
        self.assertIn("playwright install --with-deps chromium", message)

    def test_manual_instructions_omit_download_path_on_download(self) -> None:
        with mock.patch.object(dm, "_os_name", return_value="linux"):
            message = dm.manual_instructions(
                [dm.DEP_PLAYWRIGHT_CHROMIUM],
                download_path="/tmp/cache",
                install_phase="download",
            )
        self.assertNotIn("Downloaded files location: /tmp/cache", message)


if __name__ == "__main__":
    unittest.main()
