用 `prompt_toolkit + rich` 的组合有两条可行路线可以做到 CLI 中 markdown 编辑和（轻量）渲染 “合二为一、但允许限制渲染”。

**最稳妥、实现成本最低、体验也最好**的是：**单个编辑区仍然是纯文本输入，但在同一屏幕内实时显示“局部/轻量渲染提示”（inline decorations）**——也就是“所见即所得的一部分”，而不是把整段文本替换成渲染后的字符（后者会严重干扰光标位置、撤销/选择、输入法等）。

下面给你一个完整方案（含限制范围、交互与实现方式），并给出一份可运行的代码骨架。

---

## 方案选择：同屏“编辑 + 轻量渲染装饰”（合二为一）

### 核心思路
- **编辑仍然编辑 Markdown 源文本**（光标/选区/撤销行为稳定）
- 同时在同一个 TextArea 上叠加“装饰层”：
  - 用颜色/样式突出：标题、粗体、斜体、行内代码、代码块、引用、任务列表、分隔线
  - 数学：识别 `$...$`/`$$...$$`，但不排版，给背景色/边框感
- 你仍然可以保留一个“全量预览切换”（Ctrl+P），但日常写作靠轻量渲染就够了。

### 为什么不建议“直接把编辑内容替换为渲染后的文本”
- 渲染后字符长度/换行会变化，**光标映射变复杂**（尤其是表格、列表缩进、自动换行）
- 用户编辑的是源 Markdown，但屏幕显示的是另一套字符串，会造成“按一次 Backspace 删的不是看到的东西”的错觉
- 输入法合成、撤销栈、选择范围都会变得脆弱

---

## 轻量渲染的限制范围（推荐支持子集）

为了“合二为一”可控，建议把渲染限制在**不改变文本布局**的范围：只做**syntax highlighting + 少量字符替换（可选）**。

### 建议支持（基本不改布局）
1) 标题：`# ...` 行首高亮
2) 粗体/斜体：`**bold**` / `*italic*`（只对标记符和内容着色，不隐藏星号）
3) 行内代码：`` `code` `` 背景色
4) 代码块：``` fenced ``` 区域整块背景色 + 可选语言标签高亮
5) 引用：`> ` 行首色条感（用颜色模拟）
6) 任务列表：`- [ ]` / `- [x]` 给 `[ ]/[x]` 上色（可选替换成 ☐/☑，但替换会改字符宽度，建议仅上色）
7) 数学：
   - `$...$`：内容背景色（inline code 类似）
   - `$$...$$`：块背景色（类似 code block）
   - 不做 TeX 排版
8) 表格：仅对 `|`、对齐行 `|---|` 做轻量上色（**不做网格化重排**）

### 不建议在“合一模式”做的事
- 把表格渲染成 box table（会改布局）
- 自动折叠/隐藏 markup（会改光标/选择感知）
- 自动重排段落（会改变行列）

---

## prompt_toolkit 中怎么实现“同屏轻量渲染”

用 `TextArea` 的底层 `BufferControl` 支持的 **lexer / processor** 机制（prompt_toolkit 本来就用于语法高亮）：

- **Lexer**：根据当前 Document 返回每一行的样式 spans（最合适做 Markdown 轻量渲染）
- 或 **Processor**：更强大，可以做更复杂的装饰（但更复杂）

推荐：先用 **自定义 Lexer**（简单、性能好），识别你允许的子集语法并上色。

> 关键点：这是“高亮”，不改变文本内容，因此不会破坏编辑体验。

---

## 体验设计（你会得到什么样的“合二为一”）
- 你在编辑区输入 Markdown
- 标题、代码、任务、公式立刻“像预览一样”更醒目（背景色块）
- 表格竖线更清晰，但仍然是文本表格
- 需要整体检查排版时仍可 `Ctrl+P` 进入完整 rich 预览（可选）

---

## 可运行的实现骨架（轻量渲染 + 仍可切换全预览）

下面是一份“最小可用”的示例：  
- `EditingMode.EMACS`（通用）  
- 编辑区 Markdown 轻量高亮（标题/代码块/inline code/任务/数学）  
- `Ctrl+P` 切换到 rich 全预览（可选，你也可以删除这个功能，只保留合一模式）

> 依赖：`pip install prompt_toolkit rich`

```python
#!/usr/bin/env python3
import io
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import DynamicContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import Lexer
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


# ---------- Lightweight Markdown lexer (no layout changes, only styles) ----------
class SimpleMarkdownLexer(Lexer):
    """
    轻量渲染子集：
    - # heading
    - ``` fenced code block
    - `inline code`
    - - [ ] / - [x]
    - $inline math$ and $$block math$$ (no TeX layout, just highlight)
    - > quote
    - table pipes '|' (light)
    """

    RE_INLINE_CODE = re.compile(r"`[^`]+`")
    RE_TASK = re.compile(r"^(\s*[-*]\s+)(\[(?: |x|X)\])(\s+)", re.M)
    RE_HEADING = re.compile(r"^(#{1,6})\s+.*$")
    RE_QUOTE = re.compile(r"^\s*>\s+.*$")
    RE_INLINE_MATH = re.compile(r"(?<!\$)\$[^$\n]+\$(?!\$)")
    # fenced blocks are handled statefully line-by-line

    def lex_document(self, document):
        lines = document.lines

        def get_line(i: int) -> List[Tuple[str, str]]:
            return [("", lines[i])]

        # Precompute per-line styled spans
        styled: List[List[Tuple[str, str]]] = []
        in_fence = False
        in_math_block = False

        for i, line in enumerate(lines):
            spans: List[Tuple[str, str]] = [("class:md.text", line)]

            stripped = line.strip()

            # Fence toggles
            if stripped.startswith("```"):
                in_fence = not in_fence
                spans = [("class:md.fence", line)]
                styled.append(spans)
                continue

            # Math block toggles
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 2:
                # one-line $$...$$ : highlight whole line
                spans = [("class:md.mathblock", line)]
                styled.append(spans)
                continue
            if stripped == "$$":
                in_math_block = not in_math_block
                spans = [("class:md.mathblock", line)]
                styled.append(spans)
                continue

            if in_fence:
                spans = [("class:md.codeblock", line)]
                styled.append(spans)
                continue

            if in_math_block:
                spans = [("class:md.mathblock", line)]
                styled.append(spans)
                continue

            # Heading / Quote (whole line styling)
            if self.RE_HEADING.match(line):
                spans = [("class:md.heading", line)]
                styled.append(spans)
                continue
            if self.RE_QUOTE.match(line):
                spans = [("class:md.quote", line)]
                styled.append(spans)
                continue

            # Inline styling: do a simple scan and apply overlays by splitting
            # Approach: build segments with priorities (simple, good enough for small docs)
            segments = [("class:md.text", line)]

            def apply_regex(segments, regex, style_name):
                out = []
                for st, txt in segments:
                    last = 0
                    for m in regex.finditer(txt):
                        a, b = m.span()
                        if a > last:
                            out.append((st, txt[last:a]))
                        out.append((style_name, txt[a:b]))
                        last = b
                    if last < len(txt):
                        out.append((st, txt[last:]))
                return out

            # Table pipes
            if "|" in line:
                # highlight pipes only (minimal)
                out = []
                for ch in line:
                    if ch == "|":
                        out.append(("class:md.pipe", ch))
                    else:
                        out.append(("class:md.text", ch))
                segments = out
            else:
                segments = [("class:md.text", line)]

            # Task marker: highlight [ ]/[x] at line start
            # (Simple: if matches, rest unchanged)
            m = re.match(r"^(\s*[-*]\s+)(\[(?: |x|X)\])(\s+)(.*)$", line)
            if m:
                prefix, box, space, rest = m.groups()
                segments = [
                    ("class:md.text", prefix),
                    ("class:md.task", box),
                    ("class:md.text", space),
                    ("class:md.text", rest),
                ]
                styled.append(segments)
                continue

            # Inline code, inline math
            segments = apply_regex(segments, self.RE_INLINE_CODE, "class:md.inlinecode")
            segments = apply_regex(segments, self.RE_INLINE_MATH, "class:md.inlinemath")

            styled.append(segments)

        def lex_line(i: int):
            return styled[i] if i < len(styled) else [("class:md.text", "")]

        return lex_line


# ---------- Full preview rendering (optional) ----------
_MATH_BLOCK_RE = re.compile(r"(?s)\$\$(.+?)\$\$")
_MATH_INLINE_RE = re.compile(r"(?s)\$(.+?)\$")


def mark_math_for_preview(md: str) -> str:
    def block_sub(m):
        inner = m.group(1).strip()
        return f"\n\n```math\n{inner}\n```\n\n"

    md = _MATH_BLOCK_RE.sub(block_sub, md)

    parts = re.split(r"(`[^`]*`)", md)
    for i in range(0, len(parts), 2):
        parts[i] = _MATH_INLINE_RE.sub(lambda m: f"`⟦math⟧ {m.group(1).strip()} ⟦/math⟧`", parts[i])
    return "".join(parts)


def render_markdown_to_ansi(md_text: str, width: int) -> str:
    width = max(20, width)
    sio = io.StringIO()
    theme = Theme(
        {
            "markdown.code_block": "bold #d7d7ff on #20243a",
            "markdown.code": "bold #d7d7ff on #20243a",
            "markdown.h1": "bold #ffd75f",
            "markdown.h2": "bold #ffaf5f",
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
    md_text = mark_math_for_preview(md_text)
    console.print(Markdown(md_text, code_theme="monokai", hyperlinks=False))
    return sio.getvalue()


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class EditorApp:
    def __init__(self, filename: Optional[str] = None):
        self.state = State(filename=filename)
        initial = read_file(filename) if filename and os.path.exists(filename) else ""

        self.search_toolbar = SearchToolbar()

        self.editor = TextArea(
            text=initial,
            multiline=True,
            wrap_lines=False,
            scrollbar=True,
            search_field=self.search_toolbar,
            lexer=SimpleMarkdownLexer(),  # 合一：边写边“渲染”的关键
        )

        self.preview_ansi = ""
        self.preview_control = FormattedTextControl(text=lambda: ANSI(self.preview_ansi), focusable=False)
        self.preview_window = Window(content=self.preview_control, wrap_lines=True, scrollbar=True)

        self.editor_frame = Frame(self.editor, title=self._title("EDIT (live markdown)"))
        self.preview_frame = Frame(self.preview_window, title=self._title("PREVIEW (rich)"))

        self.status_bar = Window(height=1, content=FormattedTextControl(self._status))
        self.body = DynamicContainer(lambda: self.preview_frame if self.state.mode == "preview" else self.editor_frame)

        self.root = HSplit([self.body, self.search_toolbar, self.status_bar])

        self.kb = self._bindings()
        self.style = Style.from_dict(
            {
                "frame.border": "ansibrightblack",
                "frame.label": "ansiyellow",
                "status": "reverse",

                # live markdown styles (editor)
                "md.text": "#d0d0d0",
                "md.heading": "bold #ffd75f",
                "md.quote": "italic #87afff",
                "md.pipe": "bold #87afff",
                "md.fence": "bold #5fd7af",
                "md.codeblock": "#d7d7ff on #20243a",
                "md.inlinecode": "bold #d7d7ff on #20243a",
                "md.task": "bold #ffffaf on #303030",
                "md.mathblock": "bold #ffd7ff on #2b2140",
                "md.inlinemath": "bold #ffd7ff on #2b2140",
            }
        )

        self.app = Application(
            layout=Layout(self.root, focused_element=self.editor),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
            style=self.style,
            editing_mode=EditingMode.EMACS,
        )

        self.editor.buffer.on_text_changed += self._on_change

    def _title(self, which: str) -> str:
        name = self.state.filename or "(new)"
        dirty = "*" if self.state.dirty else ""
        return f"{which}  {name}{dirty}"

    def _status(self):
        name = self.state.filename or "(new)"
        dirty = "dirty" if self.state.dirty else "saved"
        row = self.editor.buffer.document.cursor_position_row + 1
        col = self.editor.buffer.document.cursor_position_col + 1
        hints = "Ctrl+P 预览切换 | Ctrl+S 保存 | Ctrl+O 打开 | Ctrl+F 查找 | Ctrl+Q 退出"
        return [("class:status", f" {self.state.mode.upper()} | {name} | {dirty} | Ln {row}, Col {col} | {self.state.status}  {hints} ")]

    def _on_change(self, _):
        self.state.dirty = True
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")

    def _render_preview(self):
        cols = self.app.output.get_size().columns
        self.preview_ansi = render_markdown_to_ansi(self.editor.text, max(20, cols - 4))
        self.state.status = "预览已更新"
        self.app.invalidate()

    async def _save(self):
        path = self.state.filename
        if not path:
            path = await input_dialog(title="Save As", text="输入文件名：").run_async()
            if not path:
                self.state.status = "已取消保存"
                return
            self.state.filename = path

        write_file(path, self.editor.text)
        self.state.dirty = False
        self.state.status = f"已保存到 {path}"
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")
        self.app.invalidate()

    async def _open(self):
        if self.state.dirty:
            ok = await yes_no_dialog(title="Open", text="未保存，仍要打开其他文件吗？").run_async()
            if not ok:
                self.state.status = "已取消打开"
                return

        path = await input_dialog(title="Open", text="输入文件路径：").run_async()
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
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")
        self.app.invalidate()

    def _bindings(self):
        kb = KeyBindings()

        @kb.add("c-p")
        def _(event):
            if self.state.mode == "edit":
                self._render_preview()
                self.state.mode = "preview"
                event.app.layout.focus(self.preview_window)
                self.state.status = "预览模式（Ctrl+P 返回）"
            else:
                self.state.mode = "edit"
                event.app.layout.focus(self.editor)
                self.state.status = "编辑模式"
            self.app.invalidate()

        @kb.add("c-s")
        async def _(event):
            await self._save()

        @kb.add("c-o")
        async def _(event):
            await self._open()

        @kb.add("c-f")
        def _(event):
            event.app.layout.focus(self.search_toolbar)

        @kb.add("c-q")
        async def _(event):
            if self.state.dirty:
                ok = await yes_no_dialog(title="Quit", text="未保存，确定退出吗？").run_async()
                if not ok:
                    self.state.status = "已取消退出"
                    return
            event.app.exit()

        return kb

    def run(self):
        self.app.run()


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    EditorApp(filename).run()


if __name__ == "__main__":
    main()
```

---

## “合二为一”程度，可以再往前走两步（可选）

1) **进一步像“渲染”**：在编辑区把 `- [ ]` 用样式渲染成像 checkbox 一样（现在已上色），但仍不替换字符。  
2) **表格更“预览感”**：在编辑区只高亮 `|---|` 这一行（对齐分隔行）以及每列 `|`，让眼睛更容易读；真正的 box 表格仍建议只在 Ctrl+P 全预览做。
