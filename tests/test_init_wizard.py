import os
import tempfile
import unittest
from pathlib import Path

from dogent.cli.wizard import INIT_WIZARD_OUTPUT_SCHEMA, InitWizard, WizardResult
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.features.doc_templates import DocumentTemplateManager


class InitWizardTests(unittest.TestCase):
    def test_parse_wizard_payload_reads_json(self) -> None:
        payload = (
            '{'
            '"doc_template":"global:resume",'
            '"primary_language":"Chinese",'
            '"dogent_md":"# Dogent Writing Configuration (Minimal)\\n\\n## Document Context\\n\\n'
            '**Document Name**: [Configured] Resume\\n"'
            '}'
        )
        result = InitWizard._parse_wizard_payload(payload)
        self.assertIsNotNone(result)
        assert isinstance(result, WizardResult)
        self.assertEqual(result.doc_template, "global:resume")
        self.assertEqual(result.primary_language, "Chinese")
        self.assertIn("# Dogent Writing Configuration", result.dogent_md)

    def test_parse_wizard_payload_reads_structured_dict(self) -> None:
        result = InitWizard._parse_wizard_payload(
            {
                "doc_template": "general",
                "primary_language": "English",
                "dogent_md": "# Dogent Writing Configuration\n",
            }
        )
        self.assertIsNotNone(result)
        assert isinstance(result, WizardResult)
        self.assertEqual(result.doc_template, "general")
        self.assertEqual(result.primary_language, "English")

    def test_parse_wizard_payload_handles_preamble(self) -> None:
        payload = (
            "Here is the result:\\n"
            '{"doc_template":"general","primary_language":"English","dogent_md":"# Dogent Writing Configuration (Minimal)\\n"}'
            "\\nThanks!"
        )
        result = InitWizard._parse_wizard_payload(payload)
        self.assertIsNotNone(result)
        assert isinstance(result, WizardResult)
        self.assertEqual(result.doc_template, "general")
        self.assertEqual(result.primary_language, "English")

    def test_parse_wizard_payload_missing_markdown(self) -> None:
        payload = '{"doc_template":"general"}'
        self.assertIsNone(InitWizard._parse_wizard_payload(payload))

    def test_build_options_uses_tools_empty_array(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            wizard = InitWizard(
                ConfigManager(paths),
                paths,
                DocumentTemplateManager(paths),
            )

            options = wizard._build_options("sys")
            self.assertEqual(options.tools, [])
            self.assertEqual(options.allowed_tools, [])
            self.assertEqual(
                options.output_format,
                {"type": "json_schema", "schema": INIT_WIZARD_OUTPUT_SCHEMA},
            )
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
