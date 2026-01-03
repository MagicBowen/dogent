## 完整实现方案（CLI 弹出式 Markdown 编辑器：VS Code/通用体验 + 按键切换预览）

下面是一套**可落地、依赖轻、界面美观、交互接近 VS Code/通用**的实现方案：使用 **prompt_toolkit** 做编辑器与界面框架，使用 **rich** 做 Markdown 预览渲染与代码高亮；预览通过**按键切换**触发一次渲染；数学公式在预览中**不排版**，而是以**等宽块**呈现并用**颜色/背景**突出。

---

## 1. 目标与边界

### 目标
- 在 CLI 中弹出全屏编辑器（TUI）
- 编辑体验偏“VS Code/通用”
- 支持**按键切换**到 Markdown 预览（进入预览时渲染一次）
- 预览支持：
  - 表格（尽力支持；见下文增强方案）
  - 任务列表（- [ ] / - [x]）
  - 代码块高亮
  - 数学公式：
    - `$$...$$`：显示为等宽“公式块”，背景/颜色突出
    - `$...$`：显示为等宽 inline“公式片段”，高亮即可
- UI 美观：Frame、状态栏、提示键位、统一配色

### 明确边界（务实）
- **数学公式不做 TeX 排版**（你指定的要求），只做“识别 + 等宽 + 高亮/背景”
- 表格渲染：rich 对 GFM pipe table 的支持在不同版本有差异  
  - 默认方案：rich Markdown 尽力渲染  
  - 需要“更稳表格”时：加一个可选增强（见 §6）

---

## 2. 技术选型

### 核心库
- **prompt_toolkit**
  - TextArea 作为编辑器
  - DynamicContainer 在“编辑/预览”两种布局间切换
  - SearchToolbar 提供 Ctrl+F 搜索条
  - KeyBindings 定制快捷键（VS Code/通用风格）
- **rich**
  - `rich.markdown.Markdown` 负责渲染预览
  - `Console(..., color_system="truecolor")` 输出 ANSI 文本给 preview 窗口
  - 主题 Theme 用于 code/code_block 的背景色（实现“公式块突出”）

---

## 3. UI/交互设计（VS Code/通用风格）

### 布局
- 主区域：单面板切换
  - **EDIT**：TextArea（可滚动）
  - **PREVIEW**：Window 显示渲染后的 ANSI（可滚动）
- 底部：
  - SearchToolbar（Ctrl+F 激活）
  - StatusBar（显示文件名、保存状态、光标位置、快捷键提示）

### 默认快捷键（通用且可控）
- `Ctrl+S` 保存
- `Ctrl+O` 打开
- `Ctrl+Q` 退出（若 dirty 则确认）
- `Ctrl+F` 搜索
- `Ctrl+P` 切换预览（进入预览时渲染一次）
- `Ctrl+Z / Ctrl+Y` 撤销/重做
- 选择（跨终端更稳定的备用方案）：
  - `Ctrl+W` 选中当前单词
  - `Ctrl+L` 选中当前行

> 注：Shift+方向键、Ctrl+方向键在不同终端兼容性不一，所以建议保留 `Ctrl+W/Ctrl+L` 作为“通用可靠”的选择手段。

---

## 4. 预览渲染策略

### 触发方式（按键切换）
- 用户按 `Ctrl+P`：
  - 若在编辑模式：执行一次 `render_preview()` → 切换到预览
  - 若在预览模式：直接回到编辑（不强制重渲染）

### 渲染内容与规则
1) **原始 Markdown**：来自编辑区文本
2) **数学预处理（核心）**
   - `$$...$$` → 转为 fenced code block：  
     ````
     ```math
     ...
     ```
     ````
     这样 rich 会用 code block 渲染成等宽块
   - `$...$` → 转成 inline code：`` `⟦math⟧ ... ⟦/math⟧` ``  
     让它保持等宽，并自然高亮
3) **rich Markdown 渲染**
   - `Markdown(md_text, code_theme="monokai")`
4) **主题高亮（实现“公式块突出”）**
   - 给 `markdown.code_block` / `markdown.code` 设置前景色 + 背景色（例如深蓝底）

---

## 5. 完整可运行实现（单文件）

> 运行：
> ```bash
> pip install prompt_toolkit rich
> python md_editor.py your.md
> ```
> （不传文件名则打开新文件，Ctrl+S 会提示 Save As）

```python
#!/usr/bin/env python3
import io
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import DynamicContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.selection import SelectionType
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, SearchToolbar, TextArea
from prompt_toolkit.shortcuts.dialogs import yes_no_dialog, input_dialog

from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme


@dataclass
class State:
    filename: Optional[str] = None
    dirty: bool = False
    mode: str = "edit"  # edit | preview
    status: str = ""


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---- Math handling: CLI pragmatic (no TeX layout), just monospace + highlight blocks
_MATH_BLOCK_RE = re.compile(r"(?s)\$\$(.+?)\$\$")
_MATH_INLINE_RE = re.compile(r"(?s)\$(.+?)\$")


def mark_math(md: str) -> str:
    """
    - $$...$$ => fenced code block ```math ... ``` (monospace block)
    - $...$   => inline code with marker (monospace inline)
    Heuristic: keep content inside backticks intact.
    """
    def block_sub(m):
        inner = m.group(1).strip()
        return f"\n\n```math\n{inner}\n```\n\n"

    md = _MATH_BLOCK_RE.sub(block_sub, md)

    parts = re.split(r"(`[^`]*`)", md)  # keep inline code spans intact
    for i in range(0, len(parts), 2):
        parts[i] = _MATH_INLINE_RE.sub(
            lambda m: f"`⟦math⟧ {m.group(1).strip()} ⟦/math⟧`",
            parts[i],
        )
    return "".join(parts)


def render_markdown_to_ansi(md_text: str, width: int) -> str:
    width = max(20, width)
    sio = io.StringIO()

    # Elegant-ish theme; code blocks get background = "formula block highlight"
    theme = Theme(
        {
            "markdown.h1": "bold #ffd75f",
            "markdown.h2": "bold #ffaf5f",
            "markdown.h3": "bold #ff875f",
            "markdown.code_block": "bold #d7d7ff on #20243a",
            "markdown.code": "bold #d7d7ff on #20243a",
        }
    )

    console = Console(
        file=sio,
        force_terminal=True,
        color_system="truecolor",
        width=width,
        highlight=True,
        theme=theme,
        legacy_windows=False,
    )

    md_text = mark_math(md_text)
    console.print(Markdown(md_text, code_theme="monokai", hyperlinks=False))
    return sio.getvalue()


class MarkdownCliEditor:
    def __init__(self, filename: Optional[str] = None):
        self.state = State(filename=filename)
        initial = ""
        if filename and os.path.exists(filename):
            initial = read_file(filename)

        self.search_toolbar = SearchToolbar()

        self.editor = TextArea(
            text=initial,
            multiline=True,
            wrap_lines=False,
            scrollbar=True,
            search_field=self.search_toolbar,
        )

        self.preview_ansi = ""
        self.preview_control = FormattedTextControl(
            text=lambda: ANSI(self.preview_ansi),
            focusable=False,
            show_cursor=False,
        )
        self.preview_window = Window(content=self.preview_control, wrap_lines=True, scrollbar=True)

        self.editor_frame = Frame(self.editor, title=self._title("EDIT"))
        self.preview_frame = Frame(self.preview_window, title=self._title("PREVIEW"))

        self.status_bar = Window(height=1, content=FormattedTextControl(self._status_text))
        self.body = DynamicContainer(self._body)
        self.root = HSplit([self.body, self.search_toolbar, self.status_bar])

        self.kb = self._bindings()
        self.style = Style.from_dict(
            {
                "frame.border": "ansibrightblack",
                "frame.label": "ansiyellow",
                "status": "reverse",
            }
        )

        # VS Code/通用体验：默认 Emacs 编辑键位（Ctrl+A/E 等）+ 我们自定义 Ctrl+S/O/P/F
        self.app = Application(
            layout=Layout(self.root, focused_element=self.editor),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
            style=self.style,
            editing_mode=EditingMode.EMACS,
        )

        self.editor.buffer.on_text_changed += self._on_changed

    def _title(self, which: str) -> str:
        name = self.state.filename or "(new)"
        dirty = "*" if self.state.dirty else ""
        return f"{which}  {name}{dirty}"

    def _refresh_titles(self):
        self.editor_frame.title = self._title("EDIT")
        self.preview_frame.title = self._title("PREVIEW")

    def _body(self):
        return self.preview_frame if self.state.mode == "preview" else self.editor_frame

    def _status_text(self):
        mode = self.state.mode.upper()
        name = self.state.filename or "(new)"
        pos = self.editor.buffer.document.cursor_position_row + 1
        col = self.editor.buffer.document.cursor_position_col + 1
        dirty = "dirty" if self.state.dirty else "saved"
        hints = (
            "Ctrl+P 预览/返回 | Ctrl+S 保存 | Ctrl+O 打开 | Ctrl+F 查找 | "
            "Ctrl+Q 退出 | Ctrl+W 选词 | Ctrl+L 选行"
        )
        msg = self.state.status
        return [("class:status", f" {mode} | {name} | {dirty} | Ln {pos}, Col {col} | {msg}  {hints} ")]

    def _on_changed(self, _buf):
        self.state.dirty = True
        self._refresh_titles()

    def _render_preview(self):
        cols = self.app.output.get_size().columns
        width = max(20, cols - 4)
        self.preview_ansi = render_markdown_to_ansi(self.editor.text, width)
        self.state.status = "预览已更新"
        self._refresh_titles()
        self.app.invalidate()

    async def _save(self):
        path = self.state.filename
        if not path:
            result = await input_dialog(title="Save As", text="输入文件名（例如 notes.md）：").run_async()
            if not result:
                self.state.status = "已取消保存"
                return
            path = result
            self.state.filename = path

        write_file(path, self.editor.text)
        self.state.dirty = False
        self.state.status = f"已保存到 {path}"
        self._refresh_titles()
        self.app.invalidate()

    async def _open(self):
        if self.state.dirty:
            ok = await yes_no_dialog(title="Open", text="当前内容未保存，仍要打开其他文件吗？").run_async()
            if not ok:
                self.state.status = "已取消打开"
                return

        path = await input_dialog(title="Open", text="输入要打开的文件路径：").run_async()
        if not path:
            self.state.status = "已取消打开"
            return
        if not os.path.exists(path):
            self.state.status = "文件不存在"
            return

        self.editor.text = read_file(path)
        self.state.filename = path
        self.state.dirty = False
        self.state.status = f"已打开 {path}"
        self._refresh_titles()
        self.app.invalidate()

    def _select_word(self):
        buf = self.editor.buffer
        text = buf.text
        pos = buf.cursor_position
        if not text:
            return

        def is_word(ch: str) -> bool:
            return re.match(r"\w", ch) is not None

        start = pos
        while start > 0 and is_word(text[start - 1]):
            start -= 1
        end = pos
        while end < len(text) and is_word(text[end]):
            end += 1
        if start == end:
            return

        buf.cursor_position = start
        buf.start_selection(selection_type=SelectionType.CHARACTERS)
        buf.cursor_position = end

    def _select_line(self):
        buf = self.editor.buffer
        doc = buf.document
        start = buf.cursor_position + doc.get_start_of_line_position()
        end = buf.cursor_position + doc.get_end_of_line_position()
        buf.cursor_position = start
        buf.start_selection(selection_type=SelectionType.LINES)
        buf.cursor_position = end

    def _bindings(self):
        kb = KeyBindings()

        @kb.add("c-s")
        async def _(event):
            await self._save()

        @kb.add("c-o")
        async def _(event):
            await self._open()

        @kb.add("c-q")
        async def _(event):
            if self.state.dirty:
                ok = await yes_no_dialog(title="Quit", text="文件未保存，确定退出吗？").run_async()
                if not ok:
                    self.state.status = "已取消退出"
                    return
            event.app.exit()

        @kb.add("c-p")
        def _(event):
            if self.state.mode == "edit":
                self._render_preview()
                self.state.mode = "preview"
                self.state.status = "预览模式（再按 Ctrl+P 返回编辑）"
                event.app.layout.focus(self.preview_window)
            else:
                self.state.mode = "edit"
                self.state.status = "编辑模式"
                event.app.layout.focus(self.editor)

            self._refresh_titles()
            event.app.invalidate()

        @kb.add("c-f")
        def _(event):
            event.app.layout.focus(self.search_toolbar)

        @kb.add("c-z")
        def _(event):
            event.app.current_buffer.undo()

        @kb.add("c-y")
        def _(event):
            event.app.current_buffer.redo()

        @kb.add("c-w")
        def _(event):
            self._select_word()

        @kb.add("c-l")
        def _(event):
            self._select_line()

        return kb

    def run(self):
        self._refresh_titles()
        self.app.run()


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    MarkdownCliEditor(filename).run()


if __name__ == "__main__":
    main()
```

---

## 6. 可选增强（按需，不增加复杂度也能用）

你说“不需要复杂长文撰写”，所以上面已经够用；但如果你希望预览更接近 VS Code（尤其是表格/任务列表），建议按需加下面其中一项：

### A) 任务列表更像“checkbox”
在 `render_markdown_to_ansi()` 前加一个预处理：
- `- [ ]` → `- ☐`
- `- [x]` → `- ☑`

这不会改变源文件，只影响预览显示。

### B) 表格更稳（GFM 表格）
如果你发现 rich 对 pipe table 不够理想，推荐增加依赖：
- `markdown-it-py`
- `mdit-py-plugins`（gfm-like table/tasklist）

然后用解析树把 table 渲染为 `rich.table.Table`，其余仍然走 rich Markdown。  
这一步会让表格体验显著提升，但实现代码会多一些（我可以在你确认“需要表格完全稳定”时再给升级版代码）。

---

## 7. 交付结果与用法

- 交付：单文件 `md_editor.py`
- 用法：
  - `python md_editor.py`：新文件
  - `python md_editor.py note.md`：打开已有文件
- 日常流程：
  - 写 markdown（编辑区）
  - `Ctrl+P` 看预览（表格/任务/代码高亮/公式块突出）
  - `Ctrl+P` 返回继续写
  - `Ctrl+S` 保存
