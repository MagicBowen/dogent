## 完整方案（pip 分发，Win/Linux/macOS + macOS arm64；支持 `.docx`，不支持 `.doc`、支持 PDF，但是不做 OCR；允许首次联网下载 pandoc/Chromium）

### 要实现的能力
1) **读取**：`pdf`、`docx`、`md`  
2) **统一中间格式**：Markdown（给 LLM）  
3) **LLM 输出**：Markdown  
4) **导出**：按需生成 `docx` 或 `pdf`  
5) **用户无需预装 pandoc/TeX/Chromium**：首次用到时可联网自动下载

---

处理 PDF 遵循以下步骤：
1️⃣ 本地预处理
文件读取：直接从本地磁盘读取 PDF 文件内容
格式检测：识别文本型 PDF、扫描图像 PDF 或混合型文档
内容提取：
- 对文本型 PDF：提取文字内容，保留页码、标题、表格结构
- 对扫描 PDF：提示用户暂不支持

---

## 技术选型（为何这样选）

### 输入 → Markdown
- `.md`：直接读取
- `.docx`：`mammoth`（docx→HTML，保语义）+ HTML→Markdown（轻量转换）
- `.pdf`：`PyMuPDF`（fitz）抽取文本（你的假设是“非扫描件”，足够）

### 导出
- Markdown → `.docx`：**pandoc**（通过 `pypandoc` 调用，运行时自动下载 pandoc）
- Markdown → `.pdf`：Markdown→HTML（`markdown-it-py`）→ **Playwright/Chromium 打印 PDF**（运行时自动安装 Chromium）

> 这样就避免了 TeX 依赖，同时 docx 质量也很好。

---

## 依赖与 extras（推荐的 pip 安装体验）

### `pyproject.toml`（核心依赖 + 可选 PDF）
```toml
[project]
name = "yourpkg"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "pymupdf>=1.24.0",
  "mammoth>=1.8.0",
  "beautifulsoup4>=4.12.0",
  "lxml>=5.2.0",
  "markdown-it-py>=3.0.0",
  "pypandoc>=1.13",
]

[project.optional-dependencies]
pdf = ["playwright>=1.46.0"]
```

安装建议：
- 只需要读入+docx 导出：`pip install yourpkg`
- 还需要 PDF 导出：`pip install yourpkg[pdf]`

> 不强制依赖 `pypandoc-binary`，因为你允许联网下载 pandoc；这样对 macOS arm64 / 各 Linux 更一致。

---

## 运行时自动准备依赖（关键：免安装体验）

### 1) 自动确保 pandoc 可用（需要时下载）
用 `pypandoc.download_pandoc()` 做兜底。逻辑：
- 如果系统已有 pandoc：直接用
- 否则：自动下载到本地缓存目录（pypandoc 管理）
- 下载失败：给出清晰提示（网络/权限/代理）

### 2) 自动确保 Chromium 可用（需要导出 PDF 时安装）
Playwright 的浏览器必须安装。策略：
- 第一次导出 PDF 时尝试启动 chromium
- 启动失败则调用 `python -m playwright install chromium`（通过 subprocess）
- 再重试

> 这样用户“第一次导出”会慢一些，但之后就稳定。

---

## 完整参考实现（可直接放进你的包）

下面是一套“最小但工程化”的实现：`yourpkg/document_pipeline.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
from typing import Optional

import fitz  # PyMuPDF
import mammoth
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
import pypandoc


# -----------------------------
# 依赖准备：pandoc / chromium
# -----------------------------

def ensure_pandoc_available() -> None:
    """
    确保 pandoc 可用：
    - 若系统已有 pandoc：直接使用
    - 否则：运行时联网下载（你允许）
    """
    if shutil.which("pandoc"):
        return

    try:
        # 如果 pypandoc 已经能找到 pandoc（例如用户自己装了/缓存里已有）
        pypandoc.get_pandoc_version()
        return
    except OSError:
        pass

    try:
        pypandoc.download_pandoc()
        pypandoc.get_pandoc_version()
    except Exception as e:
        raise RuntimeError(
            "Pandoc is required for DOCX export. "
            "Auto-download failed. Please check network/proxy, "
            "or install pandoc manually."
        ) from e


def ensure_playwright_chromium_installed() -> None:
    """
    确保 playwright 的 chromium 已安装。
    由于 playwright 没有非常稳定的“纯 Python 检测 API”，采用策略：
    - 先尝试运行 `python -m playwright install chromium`
    - 若用户没装 yourpkg[pdf]，这里会失败并给出提示
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "Playwright is not installed. Install PDF extra: `pip install yourpkg[pdf]`."
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Failed to install Chromium via Playwright. "
            "Check network/proxy permissions.\n"
            f"stdout:\n{e.stdout}\n\nstderr:\n{e.stderr}"
        ) from e


# -----------------------------
# 输入：各种格式 -> Markdown
# -----------------------------

def _html_to_markdown_basic(html: str) -> str:
    """
    轻量 HTML->Markdown。
    目标：把 docx（经 mammoth）变成“适合 LLM 的 Markdown”，不追求 100% 还原排版。
    如需更强可换成 markdownify/html2text，并对表格做专门处理。
    """
    soup = BeautifulSoup(html, "lxml")
    root = soup.body or soup

    out: list[str] = []
    for el in root.descendants:
        name = getattr(el, "name", None)
        if name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(name[1])
            text = el.get_text(" ", strip=True)
            if text:
                out += ["#" * level + " " + text, ""]
        elif name == "p":
            text = el.get_text(" ", strip=True)
            if text:
                out += [text, ""]
        elif name == "li":
            text = el.get_text(" ", strip=True)
            if text:
                out.append(f"- {text}")

    md = "\n".join(out)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


def docx_to_markdown(path: str | Path) -> str:
    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f)
    return _html_to_markdown_basic(result.value)


def pdf_to_markdown_text(path: str | Path) -> str:
    """
    非扫描件 PDF：抽取文本并按页标注。
    对多栏/复杂表格/图文混排会有损失；你的需求暂时接受。
    """
    doc = fitz.open(str(path))
    parts: list[str] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            parts.append(f"<!-- page:{i} -->\n\n{text}\n")
    return "\n\n".join(parts).strip() + "\n"


def read_as_markdown(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()

    if ext in [".md", ".markdown"]:
        return path.read_text(encoding="utf-8", errors="ignore")

    if ext == ".docx":
        return docx_to_markdown(path)

    if ext == ".pdf":
        return pdf_to_markdown_text(path)

    raise ValueError(f"Unsupported input format: {ext}. Supported: .md .docx .pdf")


# -----------------------------
# 导出：Markdown -> DOCX / PDF
# -----------------------------

def markdown_to_docx(md: str, out_path: str | Path, reference_docx: Optional[str] = None) -> None:
    ensure_pandoc_available()

    out_path = str(out_path)
    extra_args = ["--standalone"]
    if reference_docx:
        extra_args.append(f"--reference-doc={reference_docx}")

    pypandoc.convert_text(
        md,
        to="docx",
        format="md",
        outputfile=out_path,
        extra_args=extra_args,
    )


def markdown_to_html(md: str, title: str = "Document") -> str:
    mdi = MarkdownIt("commonmark")
    body = mdi.render(md)

    css = """
    @page { size: A4; margin: 20mm; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial,
                   "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
      font-size: 12pt;
      line-height: 1.55;
      color: #111;
      word-wrap: break-word;
    }
    pre { background: #f6f8fa; padding: 10px; overflow-x: auto; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    h1, h2, h3 { page-break-after: avoid; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; }
    """

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


async def _html_to_pdf_async(html: str, out_path: str | Path) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="load")
        await page.pdf(path=str(out_path), format="A4", print_background=True)
        await browser.close()


def markdown_to_pdf(md: str, out_path: str | Path, title: str = "Document") -> None:
    # 只在需要时才要求 playwright extra
    try:
        import asyncio
        import playwright  # noqa: F401
    except Exception as e:
        raise RuntimeError("PDF export requires extra: `pip install yourpkg[pdf]`") from e

    html = markdown_to_html(md, title=title)

    # 第一次：直接尝试生成；若缺浏览器则安装 chromium 后重试
    import asyncio
    try:
        asyncio.run(_html_to_pdf_async(html, out_path))
    except Exception:
        ensure_playwright_chromium_installed()
        asyncio.run(_html_to_pdf_async(html, out_path))


# -----------------------------
# 你的主流程：读取 -> LLM -> 导出
# -----------------------------

@dataclass
class ProcessOptions:
    export_docx_path: Optional[str] = None
    export_pdf_path: Optional[str] = None
    reference_docx: Optional[str] = None
    pdf_title: str = "Document"


def process_file(
    input_path: str | Path,
    llm_fn,  # callable: (markdown_in: str) -> markdown_out: str
    options: ProcessOptions = ProcessOptions(),
) -> str:
    md_in = read_as_markdown(input_path)
    md_out = llm_fn(md_in)

    if options.export_docx_path:
        markdown_to_docx(md_out, options.export_docx_path, reference_docx=options.reference_docx)

    if options.export_pdf_path:
        markdown_to_pdf(md_out, options.export_pdf_path, title=options.pdf_title)

    return md_out
```

---

## 用户侧体验（你可以写到 README）

### 安装
```bash
pip install yourpkg
# 需要 PDF 导出
pip install "yourpkg[pdf]"
```

### 第一次导出 PDF / DOCX
- 首次导出 DOCX：会自动下载 pandoc（需要网络）
- 首次导出 PDF：会自动安装 Chromium（需要网络）

---

## 生产级建议（不改核心方案，但强烈建议加上）

1) **缓存与网络提示**  
   - pandoc/chromium 下载可能慢、可能需要代理。建议在异常信息里明确提示“可设置 HTTP(S)_PROXY”。

2) **PDF 文本清洗**（很影响 LLM 效果）  
   你至少做两条：
   - 合并断行（把同一段里被硬换行拆开的句子合并）
   - 删除重复页眉页脚（检测每页顶部/底部高频重复行）

3) **导出 DOCX 样式模板**  
   给用户一个 `reference.docx`（公司模板），用 `--reference-doc` 固定字体、标题层级、段落间距，让导出更“像正式文档”。

---

## 已知边界（和你当前假设一致）
- PDF 输入仅保证“文本型 PDF”效果较好；复杂版面会丢结构（但仍可给 LLM 做提取/总结）
- 不支持 `.doc`
- 不做 OCR

---

后面再补一份：
- 更稳的 `pdf_to_markdown` 清洗实现（断行合并/页眉页脚剔除/保留基本标题结构）
- 一个 `console_scripts` CLI（例如 `yourpkg convert input.pdf --to docx/pdf`），便于你测试与用户使用。

---
## 1) 更稳的 `pdf_to_markdown`（清洗 + 结构尽力还原）

目标：在“不做 OCR、只针对文本型 PDF”的前提下，让输出 Markdown 更适合喂给 LLM：
- 尽量减少乱断行
- 尽量去掉页眉页脚
- 保留分页标记
- 对“疑似标题行”给出 Markdown 标题（启发式）

依赖：仍用 `PyMuPDF (fitz)`，不额外引入重依赖。

把下面代码放到 `yourpkg/pdf_to_md.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from collections import Counter
from typing import Iterable, Optional

import fitz  # PyMuPDF


_WS_RE = re.compile(r"[ \t\u00A0]+")
_DASH_HYPHEN_RE = re.compile(r"(\w)-\n(\w)")  # 英文断词 hyphenation: exam-\nple
_TRAILING_PAGE_NUM_RE = re.compile(r"^\s*(\d+|第\s*\d+\s*页)\s*$")


def _norm_spaces(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _WS_RE.sub(" ", s)
    return s.strip()


def _looks_like_header_footer(line: str) -> bool:
    """
    很保守的过滤：只针对明显的页码/空行等。
    其余交给“跨页高频行”策略来删。
    """
    if not line:
        return True
    if _TRAILING_PAGE_NUM_RE.match(line):
        return True
    return False


def _merge_hardwrap_lines(lines: list[str]) -> list[str]:
    """
    合并段落内的硬换行：把“同一段被换行切碎”的行合并成一行。
    启发式规则：
    - 空行分段
    - 列表项/标题/引用/代码块起始不强合并
    - 行尾是句号/问号/叹号/冒号等，则更可能是段落结束
    - 下一行像新段落（缩进/列表符号/标题）则不合并
    """
    merged: list[str] = []
    buf: list[str] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        # 先用空格连接
        text = " ".join(x for x in buf if x)
        text = _norm_spaces(text)
        merged.append(text)
        buf = []

    def is_block_boundary(l: str) -> bool:
        if not l:
            return True
        if l.startswith(("```", "> ", "#")):
            return True
        if re.match(r"^\s*([-*+]|(\d+\.))\s+", l):
            return True
        return False

    end_punct = tuple("。！？.!?；;:：")

    for i, line in enumerate(lines):
        line = line.rstrip()
        if not line.strip():
            flush()
            merged.append("")
            continue

        l = _norm_spaces(line)

        if is_block_boundary(l):
            flush()
            merged.append(l)
            continue

        if not buf:
            buf = [l]
            continue

        prev = buf[-1]
        # 如果上一行结尾像句末标点，则倾向断段
        if prev.endswith(end_punct):
            flush()
            buf = [l]
            continue

        # 如果当前行像新段落开始（首字符大写+前一行很短等，这里保守）
        # 更保守：只有当前行明显是列表/标题/引用才算（已在 boundary 里处理）
        buf.append(l)

    flush()
    # 去掉多余空行
    while merged and merged[-1] == "":
        merged.pop()
    return merged


def _extract_page_lines(doc: fitz.Document, page_index: int) -> list[str]:
    page = doc.load_page(page_index)
    text = page.get_text("text")  # 按阅读顺序的纯文本（尽力）
    # 先做英文断词修复
    text = _DASH_HYPHEN_RE.sub(r"\1\2", text)
    # 切行并标准化
    raw_lines = [ln.strip("\n") for ln in text.split("\n")]
    lines = []
    for ln in raw_lines:
        ln = _norm_spaces(ln)
        if _looks_like_header_footer(ln):
            continue
        lines.append(ln)
    return lines


def _build_header_footer_blacklist(pages_lines: list[list[str]], top_k: int = 2, bottom_k: int = 2,
                                   min_pages: int = 3, min_ratio: float = 0.6) -> set[str]:
    """
    通过“跨页高频重复行”识别页眉/页脚：
    - 取每页前 top_k 行、后 bottom_k 行（非空）
    - 统计在多少页出现
    - 达到 min_pages 且出现比例 >= min_ratio 则加入黑名单
    """
    n = len(pages_lines)
    if n == 0:
        return set()

    counter = Counter()

    def pick(lines: list[str]) -> list[str]:
        non_empty = [x for x in lines if x]
        head = non_empty[:top_k]
        tail = non_empty[-bottom_k:] if bottom_k > 0 else []
        # 过滤太短/太通用的行
        picked = []
        for x in head + tail:
            if len(x) < 3:
                continue
            picked.append(x)
        return picked

    for lines in pages_lines:
        for x in set(pick(lines)):  # 同一页去重
            counter[x] += 1

    blacklist = set()
    for line, cnt in counter.items():
        if cnt >= min_pages and (cnt / max(n, 1)) >= min_ratio:
            blacklist.add(line)

    return blacklist


def _apply_blacklist(lines: list[str], blacklist: set[str]) -> list[str]:
    if not blacklist:
        return lines
    return [ln for ln in lines if ln not in blacklist]


def _guess_title_lines(lines: list[str]) -> list[str]:
    """
    非严格标题识别：
    - 全大写/短行/不以句号结尾
    - 或类似“1 引言”“一、xxx”“1.2 xxx”
    将其转成 Markdown 标题（##）。
    """
    out: list[str] = []
    for ln in lines:
        if not ln:
            out.append(ln)
            continue

        if ln.startswith(("#", "-", "*", "> ", "```")):
            out.append(ln)
            continue

        is_numbered = bool(re.match(r"^(\d+(\.\d+)*|[一二三四五六七八九十]+)[、.\s]\S+", ln))
        short = len(ln) <= 60
        no_end_punct = not ln.endswith(("。", ".", "!", "?", "；", ";", "：", ":"))
        mostly_upper = sum(c.isupper() for c in ln) >= max(8, int(0.6 * len(ln))) if re.search(r"[A-Za-z]", ln) else False

        if (is_numbered and short) or (short and no_end_punct and mostly_upper):
            out.append(f"## {ln}")
        else:
            out.append(ln)
    return out


@dataclass
class PdfToMarkdownOptions:
    page_marker: bool = True
    remove_headers_footers: bool = True
    top_k: int = 2
    bottom_k: int = 2
    min_pages: int = 3
    min_ratio: float = 0.6
    merge_hardwrap: bool = True
    guess_titles: bool = True
    max_pages: Optional[int] = None  # 用于测试/限流


def pdf_to_markdown(path: str | Path, options: PdfToMarkdownOptions = PdfToMarkdownOptions()) -> str:
    """
    稳健版：适合“文本型 PDF → 给 LLM 的 Markdown”。
    """
    doc = fitz.open(str(path))
    page_count = doc.page_count
    if options.max_pages is not None:
        page_count = min(page_count, options.max_pages)

    pages_lines: list[list[str]] = []
    for i in range(page_count):
        pages_lines.append(_extract_page_lines(doc, i))

    blacklist: set[str] = set()
    if options.remove_headers_footers and page_count >= options.min_pages:
        blacklist = _build_header_footer_blacklist(
            pages_lines,
            top_k=options.top_k,
            bottom_k=options.bottom_k,
            min_pages=options.min_pages,
            min_ratio=options.min_ratio,
        )

    parts: list[str] = []
    for idx, lines in enumerate(pages_lines, start=1):
        lines = _apply_blacklist(lines, blacklist)

        if options.merge_hardwrap:
            lines = _merge_hardwrap_lines(lines)

        if options.guess_titles:
            lines = _guess_title_lines(lines)

        page_text = "\n".join(lines).strip()
        if not page_text:
            continue

        if options.page_marker:
            parts.append(f"<!-- page:{idx} -->\n\n{page_text}\n")
        else:
            parts.append(page_text + "\n")

    md = "\n\n".join(parts).strip() + "\n"
    return md
```

你在原来的 `read_as_markdown()` 里，把 `.pdf` 分支换成这个即可：

```python
from yourpkg.pdf_to_md import pdf_to_markdown, PdfToMarkdownOptions

# ...
if ext == ".pdf":
    return pdf_to_markdown(path, PdfToMarkdownOptions())
```

---

## 2) CLI：用 `console_scripts`（便于你测试）

提供一个命令：`yourpkg`（或你喜欢的名字），支持：

- `yourpkg to-md input.pdf -o out.md`
- `yourpkg run input.pdf --to docx --out out.docx`（通过一个“示例 LLM”或占位处理，方便端到端测试）
- `yourpkg export out.md --to pdf --out out.pdf`

### 2.1 CLI 代码：`yourpkg/cli.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from yourpkg.convert import (
    read_as_markdown,
    markdown_to_docx,
    markdown_to_pdf,
)
from yourpkg.pdf_to_md import pdf_to_markdown, PdfToMarkdownOptions


def _read_input_to_md(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return pdf_to_markdown(path, PdfToMarkdownOptions())
    return read_as_markdown(path)


def _demo_llm(md: str) -> str:
    """
    用于本地测试管线的“假 LLM”：
    - 实际项目里用你的 LLM 调用替换
    """
    return (
        "# LLM Output (demo)\n\n"
        "下面是输入文档的前 2000 字符预览（用于测试流程）：\n\n"
        "```text\n"
        + md[:2000].replace("```", "'''")
        + "\n```\n"
    )


def cmd_to_md(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    md = _read_input_to_md(inp)

    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    inp = Path(args.input_md)
    md = inp.read_text(encoding="utf-8", errors="ignore")

    out = Path(args.out) if args.out else None
    to = args.to.lower()

    if to == "docx":
        if out is None:
            out = inp.with_suffix(".docx")
        markdown_to_docx(md, out, reference_docx=args.reference_docx)
        print(str(out))
        return 0

    if to == "pdf":
        if out is None:
            out = inp.with_suffix(".pdf")
        markdown_to_pdf(md, out, title=args.title)
        print(str(out))
        return 0

    raise SystemExit(f"Unsupported export format: {args.to} (use pdf/docx)")


def cmd_run(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    md_in = _read_input_to_md(inp)

    # 用 demo LLM 跑通流程；你可替换成真实 llm_fn
    md_out = _demo_llm(md_in)

    # 默认先把 markdown 输出到同目录
    md_path = Path(args.md_out) if args.md_out else inp.with_suffix(".llm.md")
    md_path.write_text(md_out, encoding="utf-8")
    print(f"[ok] wrote markdown: {md_path}")

    if args.to:
        to = args.to.lower()
        out = Path(args.out) if args.out else None
        if to == "docx":
            out = out or md_path.with_suffix(".docx")
            markdown_to_docx(md_out, out, reference_docx=args.reference_docx)
            print(f"[ok] exported docx: {out}")
        elif to == "pdf":
            out = out or md_path.with_suffix(".pdf")
            markdown_to_pdf(md_out, out, title=args.title)
            print(f"[ok] exported pdf: {out}")
        else:
            raise SystemExit(f"Unsupported --to: {args.to} (pdf/docx)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="yourpkg", description="Document -> Markdown -> LLM -> Export")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_to_md = sub.add_parser("to-md", help="Convert input (.pdf/.docx/.md) to Markdown")
    p_to_md.add_argument("input", help="Input file path")
    p_to_md.add_argument("-o", "--output", help="Output .md path (default: stdout)")
    p_to_md.set_defaults(func=cmd_to_md)

    p_export = sub.add_parser("export", help="Export Markdown to docx/pdf")
    p_export.add_argument("input_md", help="Input .md path")
    p_export.add_argument("--to", required=True, choices=["docx", "pdf"], help="Export format")
    p_export.add_argument("--out", help="Output path (default: same stem)")
    p_export.add_argument("--reference-docx", help="Pandoc reference docx for styling")
    p_export.add_argument("--title", default="Document", help="PDF title (HTML title)")
    p_export.set_defaults(func=cmd_export)

    p_run = sub.add_parser("run", help="End-to-end demo: input -> md -> demo-LLM -> export")
    p_run.add_argument("input", help="Input file (.pdf/.docx/.md)")
    p_run.add_argument("--md-out", help="Where to write the LLM output markdown")
    p_run.add_argument("--to", choices=["docx", "pdf"], help="Export format (optional)")
    p_run.add_argument("--out", help="Export output path (optional)")
    p_run.add_argument("--reference-docx", help="Pandoc reference docx for styling")
    p_run.add_argument("--title", default="Document", help="PDF title")
    p_run.set_defaults(func=cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
```

### 2.2 `pyproject.toml` 里加 console script

```toml
[project.scripts]
yourpkg = "yourpkg.cli:main"
```

---

## 3) 快速测试指令（你本地/CI 都能用）

### 3.1 PDF → Markdown
```bash
yourpkg to-md samples/a.pdf -o /tmp/a.md
```

### 3.2 Markdown → DOCX（首次会下载 pandoc）
```bash
yourpkg export /tmp/a.md --to docx --out /tmp/a.docx
```

### 3.3 Markdown → PDF（需要装 extra；首次会安装 chromium）
```bash
pip install "yourpkg[pdf]"
yourpkg export /tmp/a.md --to pdf --out /tmp/a.pdf
```

### 3.4 端到端 demo（不用真实 LLM 也能测通）
```bash
yourpkg run samples/a.pdf --to pdf
```

---

## 4) 两个小建议（让你更“稳”）

1) **给 PDF 清洗提供参数入口**  
你可以在 CLI 里加选项（例如 `--max-pages`、`--no-header-footer`），方便你调参定位“某个 PDF 抽得很差”的原因。

2) **把下载行为日志化**  
`pypandoc.download_pandoc()` 和 `playwright install` 建议打印“正在下载/安装，首次较慢”，避免用户误以为卡死。