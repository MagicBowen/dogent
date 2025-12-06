import tempfile
from pathlib import Path

from dogent.config import Settings
from dogent.runtime import build_options, _apply_todo_tool_result
from dogent.todo import TodoManager


def test_build_options_respects_fs_tools_flag():
    settings = Settings(
        anthropic_model="deepseek-reasoner",
        allow_fs_tools=True,
        allow_web=False,
    )
    opts = build_options(settings, Path("."), "sys")
    assert set(opts.allowed_tools) == {"Read", "Write", "Edit", "MultiEdit", "TodoWrite"}


def test_build_options_respects_web_tools_flag_and_model():
    settings = Settings(
        anthropic_model="deepseek-reasoner",
        allow_fs_tools=False,
        allow_web=True,
    )
    opts = build_options(settings, Path("."), "sys")
    assert set(opts.allowed_tools) == {"WebSearch", "WebFetch", "TodoWrite"}
    assert opts.model == "deepseek-reasoner"


def test_build_options_uses_fast_model_when_primary_missing():
    settings = Settings(
        anthropic_model=None,
        anthropic_small_fast_model="deepseek-chat",
        allow_fs_tools=True,
        allow_web=True,
    )
    opts = build_options(settings, Path("."), "sys")
    assert opts.model == "deepseek-chat"


def test_apply_todo_tool_result_updates_items():
    todo = TodoManager()
    a = todo.add("draft section")
    _apply_todo_tool_result(
        todo,
        {
            "items": [
                {"id": a.id, "status": "done"},
                {"title": "new task", "status": "pending"},
            ]
        },
    )
    assert any(i for i in todo.list() if i.id == a.id and i.status == "done")
    assert any(i for i in todo.list() if i.title == "new task")
