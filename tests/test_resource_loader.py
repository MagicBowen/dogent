import json
import unittest

from dogent.config.resources import (
    iter_dir,
    read_config_text,
    read_prompt_text,
    read_schema_text,
    read_template_text,
    read_text,
    resource_path,
)


class ResourceLoaderTests(unittest.TestCase):
    def test_read_config_and_prompt_text(self) -> None:
        config_text = read_config_text("dogent_default.json")
        self.assertIn('"llm_profile"', config_text)
        self.assertEqual(config_text, read_text("resources", "dogent_default.json"))

        prompt_text = read_prompt_text("system.md")
        self.assertIn("Dogent", prompt_text)
        lesson_prompt = read_prompt_text("lesson_drafter_system.md")
        self.assertIn("engineering lessons", lesson_prompt)
        vision_prompt = read_prompt_text("vision_analyze.md")
        self.assertIn("Return ONLY valid JSON", vision_prompt)

    def test_read_template_text(self) -> None:
        template_text = read_template_text("doc_general.md")
        self.assertIn("General Document Template", template_text)

    def test_read_schema_text(self) -> None:
        schema_text = read_schema_text("global", "dogent.schema.json")
        schema = json.loads(schema_text)
        self.assertIn("workspace_defaults", schema.get("properties", {}))

        clarification_text = read_schema_text(None, "clarification.schema.json")
        clarification = json.loads(clarification_text)
        self.assertEqual("Dogent Clarification Payload", clarification.get("title"))

    def test_iter_dir_lists_templates(self) -> None:
        entries = iter_dir("templates")
        names = {entry.name for entry in entries}
        self.assertIn("doc_general.md", names)

    def test_resource_path(self) -> None:
        resources_root = resource_path("resources")
        self.assertIsNotNone(resources_root)
        self.assertTrue(resources_root.is_dir())


if __name__ == "__main__":
    unittest.main()
