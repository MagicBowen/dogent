import os
import tempfile
import unittest
from pathlib import Path

from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.features.document_tools import create_dogent_doc_tools
from dogent.features.ui_tools import create_dogent_ui_tools
from dogent.features.vision_tools import create_dogent_vision_tools
from dogent.features.web_tools import create_dogent_web_tools


class ToolAnnotationsTests(unittest.TestCase):
    def test_document_tools_have_annotations(self) -> None:
        tools = {tool.name: tool for tool in create_dogent_doc_tools(Path("."))}

        self.assertTrue(tools["read_document"].annotations.readOnlyHint)
        self.assertFalse(tools["export_document"].annotations.readOnlyHint)
        self.assertFalse(tools["convert_document"].annotations.openWorldHint)

    def test_ui_and_web_tools_have_annotations(self) -> None:
        ui_tool = create_dogent_ui_tools()[0]
        web_tools = {
            tool.name: tool
            for tool in create_dogent_web_tools(
                root=Path("."),
                web_profile_name="demo",
                web_profile_cfg={"provider": "brave", "api_key": "k"},
            )
        }

        self.assertTrue(ui_tool.annotations.readOnlyHint)
        self.assertTrue(web_tools["web_search"].annotations.openWorldHint)
        self.assertFalse(web_tools["web_fetch"].annotations.readOnlyHint)

    def test_vision_tool_has_annotations(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)

            tool = create_dogent_vision_tools(Path(tmp), manager)[0]

            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.openWorldHint)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
