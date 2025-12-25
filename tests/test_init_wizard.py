import unittest

from dogent.init_wizard import InitWizard, WizardResult


class InitWizardTests(unittest.TestCase):
    def test_parse_wizard_payload_reads_json(self) -> None:
        payload = (
            '{'
            '"doc_template":"global:resume",'
            '"dogent_md":"# Dogent Writing Configuration (Minimal)\\n\\n## Document Template\\n\\n'
            '**Selected Template**: [Configured] global:resume\\n"'
            '}'
        )
        result = InitWizard._parse_wizard_payload(payload)
        self.assertIsNotNone(result)
        assert isinstance(result, WizardResult)
        self.assertEqual(result.doc_template, "global:resume")
        self.assertIn("# Dogent Writing Configuration", result.dogent_md)

    def test_parse_wizard_payload_handles_preamble(self) -> None:
        payload = (
            "Here is the result:\\n"
            '{"doc_template":"general","dogent_md":"# Dogent Writing Configuration (Minimal)\\n"}'
            "\\nThanks!"
        )
        result = InitWizard._parse_wizard_payload(payload)
        self.assertIsNotNone(result)
        assert isinstance(result, WizardResult)
        self.assertEqual(result.doc_template, "general")

    def test_parse_wizard_payload_missing_markdown(self) -> None:
        payload = '{"doc_template":"general"}'
        self.assertIsNone(InitWizard._parse_wizard_payload(payload))


if __name__ == "__main__":
    unittest.main()
