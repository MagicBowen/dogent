"""Guideline management using .dogent/dogent.md."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .paths import ensure_dogent_dir

GUIDELINES_FILENAME = "dogent.md"

TEMPLATE = """# 文档编写规范

## 文档类型
（示例：技术白皮书/实施指南/项目报告）

## 目标读者
（示例：CTO、架构师、实施工程师、业务负责人）

## 语气与风格
- 语气：正式、专业、可信
- 风格：结构化、循序渐进、强调可操作性

## 语言与输出格式
- 语言：中文
- 默认格式：Markdown
- 需要时可插入代码片段、mermaid 图、表格、要点列表

## 结构与长度
- 章节结构建议（可根据主题调整）：摘要、背景、目标、方法/方案、实现步骤、验证/测试、最佳实践、风险与缓解、总结、参考资料
- 目标长度：根据主题估算，分段分节逐步完成

## 引用与图片
- 所有在线参考资料需在正文标注并在文末列出链接
- 如需插图，请下载到 ./images 并在文中引用相对路径

## 验证与准确性
- 重要事实需验证；标记未验证项并在 todo 中列出验证步骤
- 保持术语一致性，避免前后矛盾

## 其他偏好
- 在写作前先规划 todo 与大纲，逐节完成并最后整体打磨
- 使用清晰小标题，适度使用要点列表帮助阅读
"""


@dataclass
class Guidelines:
    raw: str

    @property
    def summary(self) -> str:
        # Provide a compact summary for prompts.
        lines = [ln.strip() for ln in self.raw.splitlines() if ln.strip()]
        return " ".join(lines[:80])


def ensure_guidelines(cwd: Path) -> Path:
    """Ensure .dogent/dogent.md exists; migrate from legacy .claude.md if present."""
    dogent_dir = ensure_dogent_dir(cwd)
    path = dogent_dir / GUIDELINES_FILENAME
    if not path.exists():
        path.write_text(TEMPLATE, encoding="utf-8")
    return path


def load_guidelines(cwd: Path) -> Guidelines:
    """Load guidelines from .dogent/dogent.md (creating if needed)."""
    path = ensure_guidelines(cwd)
    raw = path.read_text(encoding="utf-8")
    return Guidelines(raw=raw)
