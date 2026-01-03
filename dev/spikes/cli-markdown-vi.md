## 完整实现方案：在不改变其它需求的前提下切换到 Vi 模式（`vi_mode=True`）

你的原目标是“边写边简单 Markdown 渲染、渲染与编写合二为一、允许限制渲染”。这套方案不变，只需要把 `prompt_toolkit` 的编辑模式切到 **Vi**，并补齐 Vi 下常见的交互/状态提示（如 Normal/Insert）。

### 总体设计（保持不变）
- **单一编辑区**：用户编辑的是 Markdown 源文本
- **轻量渲染**：通过 `Lexer` 给编辑区做语法/块高亮（不改变文本内容、不隐藏标记、不重排）
- **可选全预览**：用 `rich` 渲染完整预览（`Ctrl+P` 切换）
- **限制渲染范围**：标题、引用、任务列表、行内代码、代码块、行内/块公式（仅高亮，不做 TeX 排版）

### Vi 模式落地要点
- `Application(editing_mode=EditingMode.VI)`（等价于你说的 `vi_mode=True` 目标效果）
- 状态栏显示：`VI: NORMAL/INSERT/REPLACE/VISUAL`（靠 `app.vi_state` 判断）
- 快捷键策略：
  - 保留跨模式稳定可用的控制键：`Ctrl+S` 保存、`Ctrl+O` 打开、`Ctrl+P` 预览切换、`Ctrl+Q` 退出、`Ctrl+F` 查找
  - 同时支持 **Vi 原生**：`/` 搜索（prompt_toolkit 内置），`Esc` 回 Normal 等
- 预览模式下默认不可编辑：焦点切到 preview window；`Ctrl+P` 回来继续编辑

---

## 完整可运行代码（Vi 模式 + 轻量渲染 + 可切换 rich 预览）

> 依赖：`pip install prompt_toolkit rich`  
> 运行：`python md_vi_editor.py [optional.md]`

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


# -------------------- State --------------------
@dataclass
class State:
    filename: Optional[str] = None
    dirty: bool = False
    mode: str = "edit"  # edit | preview
    status: str = ""


# -------------------- Lightweight Markdown lexer (no layout changes) --------------------
class SimpleMarkdownLexer(Lexer):
    """
    轻量渲染子集（只上色，不改变字符/布局）：
    - # heading
    - > quote
    - ``` fenced code block
    - `inline code`
    - - [ ] / - [x] task list
    - $inline math$ and $$block math$$ (no TeX layout)
    - table pipes '|': highlight pipes only
    """

    RE_HEADING = re.compile(r"^(#{1,6})\s+.*$")
    RE_QUOTE = re.compile(r"^\s*>\s+.*$")
    RE_INLINE_CODE = re.compile(r"`[^`]+`")
    RE_INLINE_MATH = re.compile(r"(?<!\$)\$[^$\n]+\$(?!\$)")

    def lex_document(self, document):
        lines = document.lines
        styled: List[List[Tuple[str, str]]] = []

        in_fence = False
        in_math_block = False

        for line in lines:
            stripped = line.strip()

            # fenced code toggle
            if stripped.startswith("```"):
                in_fence = not in_fence
                styled.append([("class:md.fence", line)])
                continue

            # math block toggle ($$ on its own line) + one-liner $$...$$
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 2:
                styled.append([("class:md.mathblock", line)])
                continue
            if stripped == "$$":
                in_math_block = not in_math_block
                styled.append([("class:md.mathblock", line)])
                continue

            if in_fence:
                styled.append([("class:md.codeblock", line)])
                continue
            if in_math_block:
                styled.append([("class:md.mathblock", line)])
                continue

            # full-line styles
            if self.RE_HEADING.match(line):
                styled.append([("class:md.heading", line)])
                continue
            if self.RE_QUOTE.match(line):
                styled.append([("class:md.quote", line)])
                continue

            # task list (simple line-start form)
            m = re.match(r"^(\s*[-*]\s+)(\[(?: |x|X)\])(\s+)(.*)$", line)
            if m:
                prefix, box, space, rest = m.groups()
                styled.append(
                    [
                        ("class:md.text", prefix),
                        ("class:md.task", box),
                        ("class:md.text", space),
                        ("class:md.text", rest),
                    ]
                )
                continue

            # base segments: optionally highlight table pipes
            if "|" in line:
                segments: List[Tuple[str, str]] = []
                for ch in line:
                    if ch == "|":
                        segments.append(("class:md.pipe", ch))
                    else:
                        segments.append(("class:md.text", ch))
            else:
                segments = [("class:md.text", line)]

            def apply_regex(segs, regex, style_name):
                out: List[Tuple[str, str]] = []
                for st, txt in segs:
                    last = 0
                    for mm in regex.finditer(txt):
                        a, b = mm.span()
                        if a > last:
                            out.append((st, txt[last:a]))
                        out.append((style_name, txt[a:b]))
                        last = b
                    if last < len(txt):
                        out.append((st, txt[last:]))
                return out

            segments = apply_regex(segments, self.RE_INLINE_CODE, "class:md.inlinecode")
            segments = apply_regex(segments, self.RE_INLINE_MATH, "class:md.inlinemath")
            styled.append(segments)

        def lex_line(i: int):
            return styled[i] if i < len(styled) else [("class:md.text", "")]

        return lex_line


# -------------------- Full preview rendering (optional) --------------------
_MATH_BLOCK_RE = re.compile(r"(?s)\$\$(.+?)\$\$")
_MATH_INLINE_RE = re.compile(r"(?s)\$(.+?)\$")


def mark_math_for_preview(md: str) -> str:
    """
    Rich Markdown 不负责 TeX 排版，这里把数学用“代码块/行内代码”标出来，便于阅读。
    不追求完整 LaTeX 解析，只做轻量替换。
    """
    def block_sub(m):
        inner = m.group(1).strip()
        return f"\n\n```math\n{inner}\n```\n\n"

    md = _MATH_BLOCK_RE.sub(block_sub, md)

    # avoid touching inline code segments
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


# -------------------- App --------------------
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
            lexer=SimpleMarkdownLexer(),  # 合一：边写边“渲染”
        )

        # Preview area (rich-rendered ANSI)
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

                # live markdown styles
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

        # --- Vi mode enabled here ---
        self.app = Application(
            layout=Layout(self.root, focused_element=self.editor),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
            style=self.style,
            editing_mode=EditingMode.VI,  # <= vi_mode=True 的等价实现
        )

        # Mark dirty on edits
        self.editor.buffer.on_text_changed += self._on_change

    def _vi_submode(self) -> str:
        """
        prompt_toolkit Vi 状态：尽量给出用户熟悉的 NORMAL/INSERT/VISUAL/REPLACE。
        不同版本属性可能略有差异，这里做防御式读取。
        """
        try:
            vs = self.app.vi_state
        except Exception:
            return "VI"

        # Common attributes in prompt_toolkit:
        # vs.input_mode: InputMode (INSERT/NAVIGATION/REPLACE/...)
        # vs.waiting_for_digraph / recording_register / etc.
        mode = getattr(vs, "input_mode", None)
        s = str(mode).upper() if mode is not None else "VI"

        # Normalize wording a bit
        if "INSERT" in s:
            return "VI: INSERT"
        if "REPLACE" in s:
            return "VI: REPLACE"
        if "NAVIGATION" in s or "NORMAL" in s:
            return "VI: NORMAL"
        if "VISUAL" in s:
            return "VI: VISUAL"
        return f"VI: {s}"

    def _title(self, which: str) -> str:
        name = self.state.filename or "(new)"
        dirty = "*" if self.state.dirty else ""
        return f"{which}  {name}{dirty}"

    def _status(self):
        name = self.state.filename or "(new)"
        dirty = "dirty" if self.state.dirty else "saved"
        row = self.editor.buffer.document.cursor_position_row + 1
        col = self.editor.buffer.document.cursor_position_col + 1
        vimode = self._vi_submode() if self.state.mode == "edit" else "VIEW"
        hints = "Ctrl+P 预览切换 | Ctrl+S 保存 | Ctrl+O 打开 | Ctrl+F 查找 | Ctrl+Q 退出"
        return [
            (
                "class:status",
                f" {vimode} | {self.state.mode.upper()} | {name} | {dirty} | Ln {row}, Col {col} | {self.state.status}  {hints} ",
            )
        ]

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

        # Keep control-key shortcuts consistent across vi modes.
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

        # Convenience: in preview, press 'q' to go back (like many pagers).
        @kb.add("q")
        def _(event):
            if self.state.mode == "preview":
                self.state.mode = "edit"
                event.app.layout.focus(self.editor)
                self.state.status = "编辑模式"
                self.app.invalidate()

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

## 方案说明（你能得到的效果）

- **编辑区即“合一模式”**：标题/代码/公式/任务列表会即时以不同背景色或高亮显示，阅读更接近预览，但**仍是可靠的文本编辑**。
- **Vi 模式**：进入后默认 Normal，`i/a/o` 插入，`Esc` 返回；状态栏会显示当前 Vi 子模式。
- **需要更完整预览时**：`Ctrl+P` 切到 rich 预览，`Ctrl+P` 或 `q` 返回编辑。

---

## 可选增强（不改变核心方案）
如果你确实希望更“所见即所得”，但又不想破坏光标/撤销，我建议下一步做：
1. **把 `*`、`#`、反引号等标记符也上更淡的颜色**（弱化“源码感”）
2. **当前行/当前块高亮**（更像现代编辑器）
3. **在 Normal 模式支持 `:w` `:q` `:wq`**（可用 prompt_toolkit 的 Vi bindings 或自己做一个命令行小窗口）

---

## 需求确认后的目标

你给的偏好：

1. **不支持多文件 buffer**：始终只有一个当前缓冲区；`:e file` 会直接替换当前内容。  
2. **纯提示拒绝**：dirty 时 `:q` / `:e` 直接拒绝并在状态栏提示（不弹确认框），只有 `!` 强制才执行。  
3. **不需要 `:%s`**：Ex 命令不做范围与替换语言，保持轻量。

在这个范围内，“行为接近 Vim”的关键就是把 **Ex 命令行**、**dirty 规则**、**常用命令集合** 做得像 Vim，并与 `prompt_toolkit` 的 Vi 模式无缝协作。

---

## 完整方案描述（设计与行为）

### 1) 编辑核心：prompt_toolkit Vi 模式
- `Application(editing_mode=EditingMode.VI)`  
- 主编辑区 `TextArea`：你继续写 Markdown 源码
- 轻量 Markdown “渲染”（高亮）继续用 `Lexer`，不改变布局和文本

> 这样获得：Normal/Insert/Visual 等基本 vi 操作体验（prompt_toolkit 自带），你不需要自己实现 motions、寄存器、撤销等。

### 2) Ex 命令行（`:`）实现方式
- 在底部放一个**单行输入框**（命令行），默认隐藏
- Normal 模式按 `:`：显示命令行并聚焦，prompt 为 `:`
- 在命令行里：
  - `Enter` 执行命令并返回编辑区
  - `Esc` 取消并返回编辑区
- 执行结果与错误统一写入 **status bar**（像 Vim 的命令回显区域）

### 3) dirty 与强制 `!` 规则（像 Vim）
- `:q`：若 dirty → 拒绝，提示 `No write since last change (add ! to override)`
- `:q!`：强制退出
- `:e file`：若 dirty → 拒绝，除非 `:e! file`
- `:e!`（无参数）：放弃修改并重新加载当前文件
- `:w`：写入当前文件；若没有文件名，提示 `No file name`（更像 Vim），你也可以再加 `:w {file}` 保存为
- `:wq`：先写再退出；若写失败/无文件名且没给参数 → 拒绝并提示

> 你要求“纯提示拒绝”，所以不弹对话框。

### 4) 支持的 Ex 命令集合（够用且像 Vim）
- `:w [file]` / `:w! [file]`（这里 `!` 可先不做覆盖保护，因为 Vim 默认覆盖；保留 `!` 以兼容习惯）
- `:q` / `:q!`
- `:wq [file]`
- `:x [file]`（类似 `:wq`；在 Vim 中仅 dirty 才写，这里也按这个语义）
- `:e {file}` / `:e! {file}` / `:e!`（重载）
- `:noh`（清除搜索高亮/搜索串，做轻量近似）
- `:set wrap/nowrap`（映射 `TextArea.wrap_lines`）
- `:help`

并且支持常见缩写：`w`, `q`, `e`, `noh`, `set` 等。

---

## 完整可运行实现（单文件）

> 依赖：`pip install prompt_toolkit rich`  
> 运行：`python vim_md_editor.py [file.md]`

```python
#!/usr/bin/env python3
import io
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict

from prompt_toolkit import Application
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import ConditionalContainer, DynamicContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, SearchToolbar, TextArea

from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme


# -------------------- State --------------------
@dataclass
class State:
    filename: Optional[str] = None
    dirty: bool = False
    mode: str = "edit"  # edit | preview
    status: str = ""


# -------------------- Lightweight Markdown lexer (no layout changes) --------------------
class SimpleMarkdownLexer(Lexer):
    RE_HEADING = re.compile(r"^(#{1,6})\s+.*$")
    RE_QUOTE = re.compile(r"^\s*>\s+.*$")
    RE_INLINE_CODE = re.compile(r"`[^`]+`")
    RE_INLINE_MATH = re.compile(r"(?<!\$)\$[^$\n]+\$(?!\$)")

    def lex_document(self, document):
        lines = document.lines
        styled: List[List[Tuple[str, str]]] = []

        in_fence = False
        in_math_block = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                in_fence = not in_fence
                styled.append([("class:md.fence", line)])
                continue

            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 2:
                styled.append([("class:md.mathblock", line)])
                continue
            if stripped == "$$":
                in_math_block = not in_math_block
                styled.append([("class:md.mathblock", line)])
                continue

            if in_fence:
                styled.append([("class:md.codeblock", line)])
                continue
            if in_math_block:
                styled.append([("class:md.mathblock", line)])
                continue

            if self.RE_HEADING.match(line):
                styled.append([("class:md.heading", line)])
                continue
            if self.RE_QUOTE.match(line):
                styled.append([("class:md.quote", line)])
                continue

            # task list: - [ ] / - [x]
            m = re.match(r"^(\s*[-*]\s+)([(?: |x|X)])(\s+)(.*)$", line)
            if m:
                prefix, box, space, rest = m.groups()
                styled.append(
                    [
                        ("class:md.text", prefix),
                        ("class:md.task", box),
                        ("class:md.text", space),
                        ("class:md.text", rest),
                    ]
                )
                continue

            # base segments: highlight table pipes only
            if "|" in line:
                segments: List[Tuple[str, str]] = [
                    ("class:md.pipe" if ch == "|" else "class:md.text", ch) for ch in line
                ]
            else:
                segments = [("class:md.text", line)]

            def apply_regex(segs, regex, style_name):
                out: List[Tuple[str, str]] = []
                for st, txt in segs:
                    last = 0
                    for mm in regex.finditer(txt):
                        a, b = mm.span()
                        if a > last:
                            out.append((st, txt[last:a]))
                        out.append((style_name, txt[a:b]))
                        last = b
                    if last < len(txt):
                        out.append((st, txt[last:]))
                return out

            segments = apply_regex(segments, self.RE_INLINE_CODE, "class:md.inlinecode")
            segments = apply_regex(segments, self.RE_INLINE_MATH, "class:md.inlinemath")
            styled.append(segments)

        def lex_line(i: int):
            return styled[i] if i < len(styled) else [("class:md.text", "")]

        return lex_line


# -------------------- Rich preview rendering (optional) --------------------
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


# -------------------- Ex command parsing --------------------
@dataclass
class ExCommand:
    canonical: str
    bang: bool
    args: str
    raw: str


class ExResolver:
    """
    Minimal Vim-like abbreviation resolver.
    """
    def __init__(self):
        # canonical -> accepted abbreviations
        self.cmds: Dict[str, List[str]] = {
            "write": ["w", "wr", "wri", "writ", "write"],
            "quit": ["q", "qu", "qui", "quit"],
            "wq": ["wq"],
            "xit": ["x", "xi", "xit"],
            "edit": ["e", "ed", "edi", "edit"],
            "nohlsearch": ["noh", "nohl", "nohls", "nohlsearch"],
            "set": ["se", "set"],
            "help": ["h", "he", "hel", "help"],
        }

    def resolve(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (canonical, error). error in {unknown, ambiguous}
        """
        name = name.lower()
        if name == "":
            return None, "unknown"

        # Exact abbreviation match first
        for canonical, abbrs in self.cmds.items():
            if name in abbrs:
                return canonical, None

        # Prefix match on canonical (vim-like), detect ambiguity
        matches = [c for c in self.cmds.keys() if c.startswith(name)]
        matches = list(dict.fromkeys(matches))
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, "ambiguous"
        return None, "unknown"


def parse_ex(raw: str, resolver: ExResolver) -> ExCommand:
    """
    raw: without leading ':'
    Supports: {cmd}[!][ {args}]
    """
    s = raw.strip()
    if not s:
        return ExCommand(canonical="", bang=False, args="", raw=raw)

    parts = s.split(None, 1)
    token = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    bang = token.endswith("!")
    name = token[:-1] if bang else token

    canonical, err = resolver.resolve(name)
    if err == "ambiguous":
        canonical = "__ambiguous__"
    elif err == "unknown":
        canonical = "__unknown__"

    return ExCommand(canonical=canonical, bang=bang, args=rest.strip(), raw=raw)


# -------------------- Main app --------------------
class VimMarkdownApp:
    def __init__(self, filename: Optional[str] = None):
        self.state = State(filename=filename)
        self.resolver = ExResolver()

        initial = ""
        if filename and os.path.exists(filename):
            initial = self._read_file(filename)

        self.search_toolbar = SearchToolbar()

        self.editor = TextArea(
            text=initial,
            multiline=True,
            wrap_lines=False,
            scrollbar=True,
            search_field=self.search_toolbar,
            lexer=SimpleMarkdownLexer(),
        )

        # Ex command line (hidden unless active)
        self.ex_visible = False
        self.exline = TextArea(
            height=1,
            multiline=False,
            wrap_lines=False,
            prompt=":",
        )

        # Preview window (optional)
        self.preview_ansi = ""
        self.preview_control = FormattedTextControl(text=lambda: ANSI(self.preview_ansi), focusable=False)
        self.preview_window = Window(content=self.preview_control, wrap_lines=True, scrollbar=True)

        self.editor_frame = Frame(self.editor, title=self._title("EDIT (live markdown)"))
        self.preview_frame = Frame(self.preview_window, title=self._title("PREVIEW (rich)"))

        self.body = DynamicContainer(lambda: self.preview_frame if self.state.mode == "preview" else self.editor_frame)

        self.ex_container = ConditionalContainer(
            content=Window(
                height=1,
                content=self.exline.control,
            ),
            filter=Condition(lambda: self.ex_visible),
        )

        self.status_bar = Window(height=1, content=FormattedTextControl(self._status))

        self.root = HSplit([self.body, self.search_toolbar, self.ex_container, self.status_bar])

        self.kb = self._bindings()

        self.style = Style.from_dict(
            {
                "status": "reverse",
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
            editing_mode=EditingMode.VI,
        )

        self.editor.buffer.on_text_changed += self._on_change

    # ---------- utils ----------
    def _read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _write_file(self, path: str, text: str) -> None:
        # keep it simple, vim overwrites by default
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _title(self, which: str) -> str:
        name = self.state.filename or "[No Name]"
        dirty = " [+]" if self.state.dirty else ""
        return f"{which}  {name}{dirty}"

    def _vi_submode(self) -> str:
        try:
            mode = self.app.vi_state.input_mode
            s = str(mode).upper()
        except Exception:
            return "VI"
        if "INSERT" in s:
            return "VI: INSERT"
        if "REPLACE" in s:
            return "VI: REPLACE"
        if "VISUAL" in s:
            return "VI: VISUAL"
        # prompt_toolkit uses NAVIGATION for "normal"
        return "VI: NORMAL"

    def _status(self):
        name = self.state.filename or "[No Name]"
        row = self.editor.buffer.document.cursor_position_row + 1
        col = self.editor.buffer.document.cursor_position_col + 1
        vimode = self._vi_submode() if self.state.mode == "edit" else "VIEW"
        return [
            (
                "class:status",
                f" {vimode} | {name} | Ln {row}, Col {col} | {self.state.status} ",
            )
        ]

    def _on_change(self, _):
        self.state.dirty = True
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")
        # don't spam status; keep last message unless you want to clear it

    def _render_preview(self):
        cols = self.app.output.get_size().columns
        self.preview_ansi = render_markdown_to_ansi(self.editor.text, max(20, cols - 2))
        self.state.status = "Preview updated"
        self.app.invalidate()

    # ---------- Ex commands ----------
    async def _ex_write(self, args: str, bang: bool) -> bool:
        """
        :w [file]
        Return True if wrote successfully.
        """
        path = args.strip() or (self.state.filename or "")
        if not path:
            self.state.status = "No file name"
            return False

        try:
            self._write_file(path, self.editor.text)
        except Exception as e:
            self.state.status = f"Write error: {e}"
            return False

        self.state.filename = path
        self.state.dirty = False
        self.state.status = f"Wrote {path}"
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")
        return True

    async def _ex_edit(self, args: str, bang: bool) -> None:
        """
        :e {file}
        :e! {file}
        :e!   (reload current file)
        """
        target = args.strip() or (self.state.filename or "")
        if not target:
            self.state.status = "No file name"
            return

        if self.state.dirty and not bang:
            self.state.status = "No write since last change (add ! to override)"
            return

        if not os.path.exists(target):
            self.state.status = f"Can't open file: {target}"
            return

        try:
            self.editor.text = self._read_file(target)
        except Exception as e:
            self.state.status = f"Read error: {e}"
            return

        self.state.filename = target
        self.state.dirty = False
        self.state.status = f"Opened {target}"
        self.editor_frame.title = self._title("EDIT (live markdown)")
        self.preview_frame.title = self._title("PREVIEW (rich)")

    async def execute_ex(self, raw: str) -> None:
        ex = parse_ex(raw, self.resolver)

        if ex.canonical == "":
            self.state.status = ""
            return

        if ex.canonical == "__unknown__":
            self.state.status = f"Not an editor command: {raw.strip()}"
            return

        if ex.canonical == "__ambiguous__":
            self.state.status = f"Ambiguous command: {raw.strip()}"
            return

        if ex.canonical == "help":
            self.state.status = "Ex: :w :q :q! :wq :x :e :e! :noh :set wrap/nowrap :help"
            return

        if ex.canonical == "write":
            await self._ex_write(ex.args, ex.bang)
            return

        if ex.canonical == "quit":
            if self.state.dirty and not ex.bang:
                self.state.status = "No write since last change (add ! to override)"
                return
            self.app.exit()
            return

        if ex.canonical == "wq":
            ok = await self._ex_write(ex.args, ex.bang)
            if ok:
                self.app.exit()
            return

        if ex.canonical == "xit":
            # vim: :x writes only if changed
            if self.state.dirty:
                ok = await self._ex_write(ex.args, ex.bang)
                if not ok:
                    return
            self.app.exit()
            return

        if ex.canonical == "edit":
            await self._ex_edit(ex.args, ex.bang)
            return

        if ex.canonical == "nohlsearch":
            try:
                self.search_toolbar.search_buffer.text = ""
            except Exception:
                pass
            self.state.status = "noh"
            return

        if ex.canonical == "set":
            await self._ex_set(ex.args)
            return

        self.state.status = f"Unhandled command: {raw.strip()}"

    async def _ex_set(self, args: str) -> None:
        """
        Minimal :set support:
        - :set wrap / :set nowrap
        - :set?  show current values (minimal)
        """
        s = args.strip()
        if s in ("", "?"):
            self.state.status = f"wrap={'on' if self.editor.wrap_lines else 'off'}"
            return

        tokens = s.split()
        for tok in tokens:
            if tok == "wrap":
                self.editor.wrap_lines = True
                self.state.status = "set wrap"
            elif tok == "nowrap":
                self.editor.wrap_lines = False
                self.state.status = "set nowrap"
            else:
                self.state.status = f"Unknown option: {tok}"
                return

    # ---------- key bindings ----------
    def _bindings(self) -> KeyBindings:
        kb = KeyBindings()

        # Toggle preview (optional)
        @kb.add("c-p")
        def _(event):
            if self.state.mode == "edit":
                self._render_preview()
                self.state.mode = "preview"
                event.app.layout.focus(self.preview_window)
                self.state.status = "Preview (Ctrl+P to return)"
            else:
                self.state.mode = "edit"
                event.app.layout.focus(self.editor)
                self.state.status = ""
            event.app.invalidate()

        # Ex command-line: ':' in VI normal/navigation
        @kb.add(":")
        def _(event):
            if self.state.mode != "edit":
                return

            # Only trigger exline in NORMAL/NAVIGATION, not in INSERT.
            try:
                mode_s = str(self.app.vi_state.input_mode).upper()
            except Exception:
                mode_s = "NAVIGATION"

            if "INSERT" in mode_s or "REPLACE" in mode_s:
                return  # let ':' be typed normally in insert/replace

            self.ex_visible = True
            self.exline.text = ""
            self.state.status = ":"  # mimic vim command prompt feedback
            event.app.layout.focus(self.exline)
            event.app.invalidate()

        # Execute ex command
        @kb.add("enter")
        async def _(event):
            if self.ex_visible and event.app.layout.current_control == self.exline.control:
                raw = self.exline.text
                self.ex_visible = False
                self.exline.text = ""
                event.app.layout.focus(self.editor)
                await self.execute_ex(raw)
                event.app.invalidate()

        # Cancel ex command
        @kb.add("escape")
        def _(event):
            if self.ex_visible and event.app.layout.current_control == self.exline.control:
                self.ex_visible = False
                self.exline.text = ""
                self.state.status = ""
                event.app.layout.focus(self.editor)
                event.app.invalidate()

        # In preview, allow 'q' to return (pager-like)
        @kb.add("q")
        def _(event):
            if self.state.mode == "preview":
                self.state.mode = "edit"
                event.app.layout.focus(self.editor)
                self.state.status = ""
                event.app.invalidate()

        return kb

    def run(self):
        self.app.run()


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    VimMarkdownApp(filename).run()


if __name__ == "__main__":
    main()
```

---

## 这个版本“接近 Vim”的点（与你的三条偏好一致）

- `:` 打开命令行；`Esc` 取消；`Enter` 执行——交互像 Vim  
- dirty 时 `:q` / `:e` **直接拒绝**，只有加 `!` 才强制——像 Vim  
- 单 buffer 模型：`:e file` 直接替换当前内容——符合你的要求  
- 不引入 `:%s`、范围、复杂脚本——保持实现简单、稳定
