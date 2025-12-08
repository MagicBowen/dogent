from __future__ import annotations

import textwrap
from importlib import resources
from pathlib import Path
from typing import Iterable, List

from .file_refs import FileAttachment
from .paths import DogentPaths
from .todo import TodoManager


class PromptBuilder:
    """Builds system and user prompts from templates."""

    def __init__(self, paths: DogentPaths, todo_manager: TodoManager) -> None:
        self.paths = paths
        self.todo_manager = todo_manager
        self._system_template = self._load_template("system.md")
        self._user_template = self._load_template("user_prompt.md")

    def build_system_prompt(self) -> str:
        preferences = "未提供，提醒用户运行 /init 并填写 .dogent/dogent.md。"
        if self.paths.doc_preferences.exists():
            preferences = self.paths.doc_preferences.read_text(
                encoding="utf-8", errors="replace"
            ).strip() or preferences
        return self._system_template.format(
            working_dir=self.paths.root,
            preferences=preferences,
        )

    def build_user_prompt(
        self, user_message: str, attachments: List[FileAttachment]
    ) -> str:
        return self._user_template.format(
            user_message=user_message.strip(),
            todo_block=self.todo_manager.render_plain(),
            attachments=self._format_attachments(attachments),
        )

    def _format_attachments(self, attachments: Iterable[FileAttachment]) -> str:
        attachments = list(attachments)
        if not attachments:
            return "无 @file 内容。"
        blocks = []
        for attachment in attachments:
            notice = " (truncated)" if attachment.truncated else ""
            blocks.append(
                textwrap.dedent(
                    f"""\
                    @file {attachment.path}{notice}
                    ```
                    {attachment.content}
                    ```
                    """
                ).strip()
            )
        return "\n\n".join(blocks)

    def _load_template(self, name: str) -> str:
        base = resources.files("dogent").joinpath("prompts")
        return Path(base.joinpath(name)).read_text(encoding="utf-8")
