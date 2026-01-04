import json
import os
import tempfile
import unittest
from unittest import mock
from io import StringIO
from pathlib import Path

from rich.console import Console

from claude_agent_sdk import HookMatcher

from dogent import __version__
from dogent.config import ConfigManager
from dogent.paths import DogentPaths


class ConfigTests(unittest.TestCase):
    def test_init_files_created(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)
            manager.create_init_files()

            self.assertTrue(paths.doc_preferences.exists())
            # memory and images should not be auto-created now
            self.assertFalse(paths.memory_file.exists())
            self.assertFalse(paths.images_dir.exists())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_doc_template_default_in_config(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)
            manager.create_config_template()
            data = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("llm_profile"), "default")
            self.assertEqual(data.get("doc_template"), "general")
            self.assertEqual(data.get("primary_language"), "Chinese")
            self.assertIsNone(data.get("vision_profile"))
            self.assertEqual(data.get("editor_mode"), "default")
            self.assertNotIn("debug", data)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_warns_on_placeholder_profile(self) -> None:
        original_home = os.environ.get("HOME")
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, color_system=None)
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps(
                    {"llm_profiles": {"deepseek": {"ANTHROPIC_AUTH_TOKEN": "replace-me"}}}
                ),
                encoding="utf-8",
            )

            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(json.dumps({"llm_profile": "deepseek"}), encoding="utf-8")

            manager = ConfigManager(paths, console=console)
            manager.load_settings()

            output = buf.getvalue()
            self.assertIn("placeholder credentials", output)
            self.assertIn("deepseek", output)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_profile_and_project_resolution(self) -> None:
        original_home = os.environ.get("HOME")
        original_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            root = Path(tmp)
            paths = DogentPaths(root)
            manager = ConfigManager(paths)

            profile_dir = Path(home) / ".dogent"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_data = {
                "llm_profiles": {
                    "deepseek": {
                        "ANTHROPIC_BASE_URL": "https://profile.example",
                        "ANTHROPIC_AUTH_TOKEN": "profile-token",
                        "ANTHROPIC_MODEL": "profile-model",
                        "ANTHROPIC_SMALL_FAST_MODEL": "profile-small",
                        "API_TIMEOUT_MS": 100,
                        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": True,
                    }
                }
            }
            (profile_dir / "dogent.json").write_text(
                json.dumps(profile_data), encoding="utf-8"
            )

            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            project_cfg = {
                "llm_profile": "deepseek",
                "anthropic": {
                    "base_url": "https://project.example",
                    "model": "project-model",
                },
            }
            paths.config_file.write_text(
                json.dumps(project_cfg), encoding="utf-8"
            )

            os.environ["ANTHROPIC_AUTH_TOKEN"] = "env-token"

            settings = manager.load_settings()
            self.assertEqual(settings.base_url, "https://project.example")
            self.assertEqual(settings.model, "project-model")
            self.assertEqual(settings.auth_token, "profile-token")
            self.assertEqual(settings.small_model, "profile-small")
            self.assertEqual(settings.api_timeout_ms, 100)
            self.assertTrue(settings.disable_nonessential_traffic)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_editor_mode_normalized(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"editor_mode": "vi"}), encoding="utf-8"
            )
            manager = ConfigManager(paths)
            cfg = manager.load_project_config()
            self.assertEqual(cfg.get("editor_mode"), "vi")
            paths.config_file.write_text(
                json.dumps({"editor_mode": "weird"}), encoding="utf-8"
            )
            cfg = manager.load_project_config()
            self.assertEqual(cfg.get("editor_mode"), "default")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_fallback_model_not_same(self) -> None:
        original_env = {
            "ANTHROPIC_MODEL": os.environ.get("ANTHROPIC_MODEL"),
            "ANTHROPIC_SMALL_FAST_MODEL": os.environ.get("ANTHROPIC_SMALL_FAST_MODEL"),
        }
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            manager = ConfigManager(paths)

            os.environ["ANTHROPIC_MODEL"] = "same-model"
            os.environ["ANTHROPIC_SMALL_FAST_MODEL"] = "same-model"

            options = manager.build_options("sys")
            self.assertIsNone(options.fallback_model)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)
        for key, val in original_env.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def test_profile_md_supported_and_gitignore_not_modified(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            root = Path(tmp)
            gitignore = root / ".gitignore"
            gitignore.write_text("keepme\n", encoding="utf-8")

            profile_dir = Path(home) / ".dogent"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_md = profile_dir / "dogent.json"
            profile_md.write_text(
                json.dumps(
                    {
                        "workspace_defaults": {"llm_profile": "deepseek"},
                        "llm_profiles": {
                            "deepseek": {"ANTHROPIC_AUTH_TOKEN": "md-token"}
                        },
                    }
                ),
                encoding="utf-8",
            )

            paths = DogentPaths(root)
            manager = ConfigManager(paths)
            manager.create_config_template()

            cfg = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(cfg.get("llm_profile"), "deepseek")

            settings = manager.load_settings()
            self.assertEqual(settings.auth_token, "md-token")

            gitignore_content = gitignore.read_text(encoding="utf-8")
            self.assertNotIn(".dogent/dogent.json", gitignore_content)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_home_bootstrap_creates_only_profile_and_web(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            ConfigManager(paths)

            home_dir = Path(tmp_home) / ".dogent"
            self.assertTrue((home_dir / "dogent.json").exists())
            self.assertTrue((home_dir / "dogent.schema.json").exists())
            self.assertFalse((home_dir / "prompts").exists())
            self.assertFalse((home_dir / "templates").exists())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_build_options_registers_dogent_web_tools(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)
            options = manager.build_options("sys")

            self.assertIsNotNone(options.mcp_servers)
            self.assertIn("dogent", options.mcp_servers)
            self.assertIn("WebSearch", options.allowed_tools)
            self.assertIn("WebFetch", options.allowed_tools)
            self.assertNotIn("mcp__dogent__web_search", options.allowed_tools)
            self.assertNotIn("mcp__dogent__web_fetch", options.allowed_tools)
            self.assertIn("mcp__dogent__read_document", options.allowed_tools)
            self.assertIn("mcp__dogent__export_document", options.allowed_tools)
            self.assertIn("mcp__dogent__convert_document", options.allowed_tools)
            self.assertNotIn("mcp__dogent__analyze_media", options.allowed_tools)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_build_options_registers_vision_tools_when_enabled(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"vision_profile": "glm-4.6v"}),
                encoding="utf-8",
            )

            manager = ConfigManager(paths)
            options = manager.build_options("sys")

            self.assertIn("mcp__dogent__analyze_media", options.allowed_tools)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_build_options_uses_default_permission_mode_with_callback(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)

            def can_use_tool(*_args, **_kwargs):
                return None

            options = manager.build_options("sys", can_use_tool=can_use_tool)
            self.assertEqual(options.permission_mode, "default")
            self.assertIs(options.can_use_tool, can_use_tool)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_build_options_registers_hooks(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)

            async def dummy_hook(*_args, **_kwargs):
                return {}

            hooks = {"PreToolUse": [HookMatcher(matcher=None, hooks=[dummy_hook])]}
            options = manager.build_options("sys", hooks=hooks)
            self.assertEqual(options.hooks, hooks)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_build_options_uses_dogent_web_tools_when_profile_set(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            manager = ConfigManager(paths)

            # Configure workspace to use a real web profile
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"llm_profile": "deepseek", "web_profile": "google"}),
                encoding="utf-8",
            )
            # Configure home web profile
            paths.global_dir.mkdir(parents=True, exist_ok=True)
            paths.global_config_file.write_text(
                json.dumps(
                    {"web_profiles": {"google": {"provider": "google_cse", "api_key": "k", "cse_id": "cx"}}}
                ),
                encoding="utf-8",
            )

            options = manager.build_options("sys")
            self.assertIsNotNone(options.mcp_servers)
            self.assertIn("dogent", options.mcp_servers)
            self.assertIn("mcp__dogent__web_search", options.allowed_tools)
            self.assertIn("mcp__dogent__web_fetch", options.allowed_tools)
            self.assertNotIn("WebSearch", options.allowed_tools)
            self.assertNotIn("WebFetch", options.allowed_tools)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_warns_on_missing_web_profile_and_falls_back_native(self) -> None:
        original_home = os.environ.get("HOME")
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, color_system=None)
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps({"web_profile": "does-not-exist"}),
                encoding="utf-8",
            )

            manager = ConfigManager(paths, console=console)
            options = manager.build_options("sys")

            out = buf.getvalue()
            self.assertIn("Web profile 'does-not-exist' not found", out)
            self.assertIsNotNone(options.mcp_servers)
            self.assertIn("WebSearch", options.allowed_tools)
            self.assertIn("WebFetch", options.allowed_tools)
            self.assertIn("mcp__dogent__read_document", options.allowed_tools)
            self.assertIn("mcp__dogent__export_document", options.allowed_tools)
            self.assertIn("mcp__dogent__convert_document", options.allowed_tools)
            self.assertNotIn("mcp__dogent__analyze_media", options.allowed_tools)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_config_template_ignores_home_templates(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_templates = Path(tmp_home) / ".dogent" / "templates"
            home_templates.mkdir(parents=True, exist_ok=True)
            custom_template = '{"llm_profile": "custom"}'
            (home_templates / "dogent_default.json").write_text(
                custom_template, encoding="utf-8"
            )

            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)
            manager.create_config_template()
            content = paths.config_file.read_text(encoding="utf-8")
            self.assertNotIn('"custom"', content)
            self.assertIn('"web_profile"', content)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_load_project_config_merges_global_and_local(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps(
                    {
                        "workspace_defaults": {
                            "llm_profile": "deepseek",
                            "doc_template": "global-doc",
                            "vision_profile": "glm-4.6v",
                            "anthropic": {"base_url": "https://global.example"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(
                json.dumps(
                    {
                        "doc_template": "local-doc",
                        "anthropic": {"model": "local-model"},
                    }
                ),
                encoding="utf-8",
            )

            manager = ConfigManager(paths)
            config = manager.load_project_config()
            self.assertEqual(config.get("llm_profile"), "deepseek")
            self.assertEqual(config.get("doc_template"), "local-doc")
            self.assertEqual(config.get("vision_profile"), "glm-4.6v")
            self.assertEqual(config.get("anthropic", {}).get("base_url"), "https://global.example")
            self.assertEqual(config.get("anthropic", {}).get("model"), "local-model")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_global_config_upgrade_adds_missing_keys(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps({"version": "0.0.1", "workspace_defaults": {}}),
                encoding="utf-8",
            )

            manager = ConfigManager(DogentPaths(root))
            upgraded = json.loads(manager.paths.global_config_file.read_text(encoding="utf-8"))
            self.assertIn("llm_profiles", upgraded)
            self.assertIn("web_profiles", upgraded)
            self.assertIn("vision_profiles", upgraded)
            self.assertEqual(upgraded.get("version"), __version__)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_global_config_warns_on_newer_version(self) -> None:
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, color_system=None)
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home_dir = Path(tmp_home) / ".dogent"
            home_dir.mkdir(parents=True, exist_ok=True)
            (home_dir / "dogent.json").write_text(
                json.dumps({"version": "99.0.0", "workspace_defaults": {}}),
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {"HOME": tmp_home}, clear=False), mock.patch(
                "pathlib.Path.home", return_value=Path(tmp_home)
            ):
                ConfigManager(DogentPaths(root), console=console)
                output = " ".join(buf.getvalue().split())
                self.assertIn("newer than Dogent", output)


if __name__ == "__main__":
    unittest.main()
