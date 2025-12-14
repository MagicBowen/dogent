import json
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from rich.console import Console

from dogent.config import ConfigManager
from dogent import __version__
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

    def test_home_templates_updated_on_version_change(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_dir = Path(tmp_home) / ".dogent"
            prompts_dir = home_dir / "prompts"
            templates_dir = home_dir / "templates"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            templates_dir.mkdir(parents=True, exist_ok=True)
            system_prompt = prompts_dir / "system.md"
            system_prompt.write_text("old prompt", encoding="utf-8")
            default_cfg = templates_dir / "dogent_default.json"
            default_cfg.write_text('{"profile": "old"}', encoding="utf-8")
            version_file = home_dir / "version"
            version_file.write_text("0.0.0", encoding="utf-8")
            profile_file = home_dir / "claude.json"
            profile_file.write_text(
                json.dumps({"profiles": {"deepseek": {"ANTHROPIC_AUTH_TOKEN": "keep"}}}),
                encoding="utf-8",
            )

            paths = DogentPaths(Path(tmp))
            ConfigManager(paths)

            self.assertNotEqual(system_prompt.read_text(encoding="utf-8"), "old prompt")
            self.assertNotIn('"old"', default_cfg.read_text(encoding="utf-8"))
            self.assertEqual(version_file.read_text(encoding="utf-8"), __version__)
            self.assertIn("keep", profile_file.read_text(encoding="utf-8"))
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
            (home_dir / "claude.json").write_text(
                json.dumps({"profiles": {"deepseek": {"ANTHROPIC_AUTH_TOKEN": "replace-me"}}}),
                encoding="utf-8",
            )

            root = Path(tmp)
            paths = DogentPaths(root)
            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            paths.config_file.write_text(json.dumps({"profile": "deepseek"}), encoding="utf-8")

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
                "profiles": {
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
            (profile_dir / "claude.json").write_text(
                json.dumps(profile_data), encoding="utf-8"
            )

            paths.dogent_dir.mkdir(parents=True, exist_ok=True)
            project_cfg = {
                "profile": "deepseek",
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
        if original_token is not None:
            os.environ["ANTHROPIC_AUTH_TOKEN"] = original_token
        else:
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

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

    def test_images_path_default(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            root = Path(tmp)
            paths = DogentPaths(root)
            manager = ConfigManager(paths)
            manager.create_config_template()
            settings = manager.load_settings()
            self.assertEqual(settings.images_path, "./images")
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_profile_md_supported_and_gitignore_not_modified(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            root = Path(tmp)
            gitignore = root / ".gitignore"
            gitignore.write_text("keepme\n", encoding="utf-8")

            profile_dir = Path(home) / ".dogent"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_md = profile_dir / "claude.json"
            profile_md.write_text(
                json.dumps(
                    {
                        "profiles": {
                            "deepseek": {"ANTHROPIC_AUTH_TOKEN": "md-token"}
                        }
                    }
                ),
                encoding="utf-8",
            )

            paths = DogentPaths(root)
            manager = ConfigManager(paths)
            manager.create_config_template()

            cfg = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(cfg.get("profile"), "deepseek")

            settings = manager.load_settings()
            self.assertEqual(settings.auth_token, "md-token")

            gitignore_content = gitignore.read_text(encoding="utf-8")
            self.assertNotIn(".dogent/dogent.json", gitignore_content)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_home_bootstrap_copies_prompts_and_templates(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            paths = DogentPaths(Path(tmp))
            ConfigManager(paths)

            self.assertTrue(paths.global_prompts_dir.joinpath("system.md").exists())
            self.assertTrue(paths.global_prompts_dir.joinpath("user_prompt.md").exists())
            self.assertTrue(paths.global_templates_dir.joinpath("dogent_default.json").exists())
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_config_template_respects_home_template(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp_home
            home_templates = Path(tmp_home) / ".dogent" / "templates"
            home_templates.mkdir(parents=True, exist_ok=True)
            custom_template = '{"profile": "custom", "images_path": "/data/imgs"}'
            (home_templates / "dogent_default.json").write_text(
                custom_template, encoding="utf-8"
            )

            paths = DogentPaths(Path(tmp))
            manager = ConfigManager(paths)
            manager.create_config_template()
            content = paths.config_file.read_text(encoding="utf-8")
            self.assertIn('"custom"', content)
            self.assertIn('"/data/imgs"', content)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
