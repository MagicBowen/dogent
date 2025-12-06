import os
import tempfile
from pathlib import Path
from dogent.config import load_settings, write_config


def test_config_precedence_file_over_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        os.environ["ANTHROPIC_MODEL"] = "env-model"
        cfg = {"anthropic_model": "file-model", "anthropic_auth_token": "abc"}
        write_config(cwd, cfg)
        settings = load_settings(cwd)
        assert settings.anthropic_model == "file-model"
        assert settings.anthropic_auth_token == "abc"


def test_config_env_used_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        os.environ["ANTHROPIC_MODEL"] = "env-model"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "token"
        settings = load_settings(cwd)
        assert settings.anthropic_model == "env-model"
        assert settings.anthropic_auth_token == "token"
