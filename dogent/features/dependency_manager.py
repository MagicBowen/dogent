from __future__ import annotations

import asyncio
import importlib
import os
import re
import shutil
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from .document_io import _package_mode, _resolve_pandoc_binary, _resolve_playwright_browsers_path

DEP_PYPANDOC = "pypandoc"
DEP_PANDOC = "pandoc"
DEP_PLAYWRIGHT = "playwright"
DEP_PLAYWRIGHT_CHROMIUM = "playwright_chromium"
DEP_PYMUPDF = "pymupdf"
DEP_OPENPYXL = "openpyxl"

DEPENDENCY_LABELS = {
    DEP_PYPANDOC: "pypandoc (DOCX support)",
    DEP_PANDOC: "Pandoc binary (DOCX support)",
    DEP_PLAYWRIGHT: "Playwright (PDF export)",
    DEP_PLAYWRIGHT_CHROMIUM: "Playwright Chromium (PDF export)",
    DEP_PYMUPDF: "PyMuPDF (PDF read)",
    DEP_OPENPYXL: "openpyxl (XLSX read)",
}

PYTHON_MODULE_MAP = {
    DEP_PYPANDOC: "pypandoc",
    DEP_PLAYWRIGHT: "playwright",
    DEP_PYMUPDF: "fitz",
    DEP_OPENPYXL: "openpyxl",
}
PYTHON_PACKAGE_MAP = {
    DEP_PYPANDOC: "pypandoc",
    DEP_PLAYWRIGHT: "playwright",
    DEP_PYMUPDF: "pymupdf",
    DEP_OPENPYXL: "openpyxl",
}


@dataclass(frozen=True)
class InstallStep:
    label: str
    command: list[str]
    env: dict[str, str] | None = None


def missing_dependencies_for_tool(tool_name: str, input_data: dict) -> list[str]:
    required = _required_dependencies_for_tool(tool_name, input_data)
    missing: list[str] = []
    for dep in required:
        if not _dependency_available(dep):
            missing.append(dep)
    return _dedupe_ordered(missing)


def dependency_summary(missing: Iterable[str]) -> str:
    missing_list = [DEPENDENCY_LABELS.get(dep, dep) for dep in missing]
    if not missing_list:
        return "All dependencies are available."
    lines = ["Missing dependencies:"]
    lines.extend(f"- {item}" for item in missing_list)
    return "\n".join(lines)


def manual_instructions(missing: Iterable[str]) -> str:
    missing_set = set(missing)
    if not missing_set:
        return "No missing dependencies."
    os_name = _os_name()
    lines = ["Install missing dependencies, then retry:"]
    if DEP_PANDOC in missing_set:
        lines.extend(_pandoc_manual_instructions(os_name))
    if DEP_PLAYWRIGHT in missing_set:
        lines.append("Playwright (Python): python -m pip install playwright")
    if DEP_PLAYWRIGHT_CHROMIUM in missing_set:
        lines.extend(_playwright_chromium_instructions(os_name))
    if DEP_PYMUPDF in missing_set:
        lines.append("PyMuPDF: python -m pip install pymupdf")
    if DEP_OPENPYXL in missing_set:
        lines.append("openpyxl: python -m pip install openpyxl")
    if DEP_PYPANDOC in missing_set and DEP_PANDOC not in missing_set:
        lines.append("pypandoc: python -m pip install pypandoc")
    return "\n".join(lines)


def build_install_steps(missing: Iterable[str]) -> list[InstallStep]:
    missing_set = set(missing)
    steps: list[InstallStep] = []
    if DEP_PANDOC in missing_set:
        steps.append(
            InstallStep(
                label="Install Pandoc (pypandoc-binary)",
                command=[
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--progress-bar",
                    "raw",
                    "pypandoc-binary",
                ],
                env={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
            )
        )
        missing_set.discard(DEP_PYPANDOC)
    python_packages = [
        PYTHON_PACKAGE_MAP[dep] for dep in missing_set if dep in PYTHON_PACKAGE_MAP
    ]
    if python_packages:
        steps.append(
            InstallStep(
                label="Install Python packages",
                command=[
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--progress-bar",
                    "raw",
                    *python_packages,
                ],
                env={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
            )
        )
    if DEP_PLAYWRIGHT_CHROMIUM in missing_set:
        steps.append(
            InstallStep(
                label="Install Playwright Chromium",
                command=[sys.executable, "-m", "playwright", "install", "chromium"],
            )
        )
    return steps


async def install_missing_dependencies(
    missing: Iterable[str], console: Console
) -> tuple[bool, str | None]:
    steps = build_install_steps(missing)
    if not steps:
        return True, None
    for step in steps:
        ok, error = await _run_install_step(step, console)
        if not ok:
            return False, error
    return True, None


def extract_progress_percent(text: str) -> int | None:
    percent_match = re.findall(r"(\d{1,3})(?:\.\d+)?%", text)
    if percent_match:
        value = int(percent_match[-1])
        return max(0, min(100, value))
    fraction_match = re.search(
        r"(\d+(?:\.\d+)?)\s*([KMG]?B)\s*/\s*(\d+(?:\.\d+)?)\s*([KMG]?B)",
        text,
        re.IGNORECASE,
    )
    if fraction_match:
        current = _size_to_bytes(float(fraction_match.group(1)), fraction_match.group(2))
        total = _size_to_bytes(float(fraction_match.group(3)), fraction_match.group(4))
        if total > 0:
            return max(0, min(100, int(current / total * 100)))
    return None


def _required_dependencies_for_tool(tool_name: str, input_data: dict) -> list[str]:
    if tool_name == "mcp__dogent__export_document":
        fmt = str(input_data.get("format") or "").strip().lower()
        if fmt == "docx":
            return [DEP_PYPANDOC, DEP_PANDOC]
        if fmt == "pdf":
            return [DEP_PLAYWRIGHT, DEP_PLAYWRIGHT_CHROMIUM]
        return []
    if tool_name == "mcp__dogent__read_document":
        path = str(input_data.get("path") or "")
        return _dependencies_for_path(path)
    if tool_name == "mcp__dogent__convert_document":
        input_path = str(input_data.get("input_path") or "")
        output_path = str(input_data.get("output_path") or "")
        return _dependencies_for_conversion(input_path, output_path)
    return []


def _dependencies_for_path(path: str) -> list[str]:
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return [DEP_PYPANDOC, DEP_PANDOC]
    if ext == ".pdf":
        return [DEP_PYMUPDF]
    if ext == ".xlsx":
        return [DEP_OPENPYXL]
    return []


def _dependencies_for_conversion(input_path: str, output_path: str) -> list[str]:
    input_format = _detect_format(input_path)
    output_format = _detect_format(output_path)
    deps: list[str] = []
    if input_format == "docx" or output_format == "docx":
        deps.extend([DEP_PYPANDOC, DEP_PANDOC])
    if input_format == "pdf":
        deps.append(DEP_PYMUPDF)
    if output_format == "pdf":
        deps.extend([DEP_PLAYWRIGHT, DEP_PLAYWRIGHT_CHROMIUM])
    if input_format == "xlsx":
        deps.append(DEP_OPENPYXL)
    return _dedupe_ordered(deps)


def _dependency_available(dep: str) -> bool:
    if dep in PYTHON_MODULE_MAP:
        return _module_available(PYTHON_MODULE_MAP[dep])
    if dep == DEP_PANDOC:
        return _pandoc_available()
    if dep == DEP_PLAYWRIGHT_CHROMIUM:
        return _playwright_chromium_available()
    return True


def _module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def _pandoc_available() -> bool:
    if _package_mode() == "full":
        return bool(_resolve_pandoc_binary())
    if shutil.which("pandoc"):
        return True
    try:
        import pypandoc

        pypandoc.get_pandoc_version()
        return True
    except Exception:
        return False


def _playwright_chromium_available() -> bool:
    if _package_mode() == "full":
        return bool(_resolve_playwright_browsers_path())
    env_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend(_default_playwright_paths())
    for base in candidates:
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir() and child.name.startswith("chromium"):
                    return True
    return False


def _default_playwright_paths() -> list[Path]:
    home = Path.home()
    if sys.platform == "win32":
        return [home / "AppData" / "Local" / "ms-playwright"]
    if sys.platform == "darwin":
        return [home / "Library" / "Caches" / "ms-playwright"]
    return [home / ".cache" / "ms-playwright"]


def _pandoc_manual_instructions(os_name: str) -> list[str]:
    if os_name == "macos":
        return ["Pandoc: brew install pandoc"]
    if os_name == "windows":
        if shutil.which("winget"):
            return ["Pandoc: winget install --id JohnMacFarlane.Pandoc -e"]
        if shutil.which("choco"):
            return ["Pandoc: choco install pandoc"]
        return ["Pandoc: install from https://pandoc.org/installing.html"]
    if shutil.which("apt-get"):
        return ["Pandoc: sudo apt-get install pandoc"]
    if shutil.which("dnf"):
        return ["Pandoc: sudo dnf install pandoc"]
    if shutil.which("yum"):
        return ["Pandoc: sudo yum install pandoc"]
    return ["Pandoc: install via your distro package manager"]


def _playwright_chromium_instructions(os_name: str) -> list[str]:
    if os_name == "linux":
        return [
            "Playwright Chromium: python -m playwright install --with-deps chromium"
        ]
    return ["Playwright Chromium: python -m playwright install chromium"]


async def _run_install_step(step: InstallStep, console: Console) -> tuple[bool, str | None]:
    env = os.environ.copy()
    if step.env:
        env.update(step.env)
    try:
        proc = await asyncio.create_subprocess_exec(
            *step.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"Failed to start installer: {exc}"

    recent_lines: deque[str] = deque(maxlen=12)

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )
    task_id = progress.add_task(step.label, total=100)

    current_progress = 0

    def handle_segment(segment: str) -> None:
        cleaned = segment.strip()
        if cleaned:
            recent_lines.append(cleaned)
        percent = extract_progress_percent(segment)
        nonlocal current_progress
        if percent is not None and percent > current_progress:
            current_progress = percent
            progress.update(task_id, completed=percent)

    with progress:
        await asyncio.gather(
            _drain_stream(proc.stdout, handle_segment),
            _drain_stream(proc.stderr, handle_segment),
        )
        await proc.wait()
        progress.update(task_id, completed=100)

    if proc.returncode != 0:
        tail = "\n".join(recent_lines)
        return False, f"Installer failed (code {proc.returncode}).\n{tail}"
    return True, None


async def _drain_stream(
    stream: asyncio.StreamReader | None, handler: Callable[[str], None]
) -> None:
    if stream is None:
        return
    buffer = ""
    while True:
        chunk = await stream.read(1024)
        if not chunk:
            break
        buffer += chunk.decode(errors="replace")
        buffer = _emit_segments(buffer, handler)
    if buffer:
        handler(buffer)


def _emit_segments(buffer: str, handler: Callable[[str], None]) -> str:
    while True:
        idx = _find_separator(buffer)
        if idx < 0:
            return buffer
        segment = buffer[:idx]
        handler(segment)
        buffer = buffer[idx + 1 :]


def _find_separator(text: str) -> int:
    candidates = [pos for pos in (text.find("\n"), text.find("\r")) if pos >= 0]
    return min(candidates) if candidates else -1


def _detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in {".md", ".markdown"}:
        return "md"
    if ext == ".docx":
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext == ".xlsx":
        return "xlsx"
    return ""


def _size_to_bytes(value: float, unit: str) -> float:
    unit = unit.upper()
    if unit == "KB":
        return value * 1024
    if unit == "MB":
        return value * 1024 * 1024
    if unit == "GB":
        return value * 1024 * 1024 * 1024
    return value


def _os_name() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    return "linux"


def _dedupe_ordered(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered
