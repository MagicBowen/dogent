import unittest

from dogent.cli.wizard import InitWizard, WizardResult


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


if __name__ == "__main__":
    unittest.main()
