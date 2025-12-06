import tempfile
from pathlib import Path

from dogent.config import Settings
from dogent.runtime import build_options


def test_build_options_skips_equal_fallback():
    settings = Settings(
        anthropic_model="deepseek-reasoner",
        anthropic_small_fast_model="deepseek-reasoner",
    )
    opts = build_options(settings, Path("."), "sys")
    assert opts.model == "deepseek-reasoner"
    assert opts.fallback_model is None


def test_build_options_keeps_distinct_fallback():
    settings = Settings(
        anthropic_model="deepseek-reasoner",
        anthropic_small_fast_model="deepseek-chat",
    )
    opts = build_options(settings, Path("."), "sys")
    assert opts.fallback_model == "deepseek-chat"
