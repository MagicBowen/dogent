"""CLI entrypoint for Dogent."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Callable, List

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.live import Live

from . import __version__
from .config import Settings, load_settings, write_config
from .context import Reference, list_reference_candidates, resolve_references
from .guidelines import GUIDELINES_FILENAME, ensure_guidelines, load_guidelines
from .paths import ensure_dogent_dir
from .runtime import AgentRuntime
from .todo import TodoManager
from .workflow import bootstrap_todo


console = Console()
app = typer.Typer(add_completion=False)


SLASH_COMMANDS = ["/init", "/config", "/todo", "/info", "/exit"]


class DocCompleter(Completer):
    def __init__(self, commands: List[str], file_supplier: Callable[[], List[str]]):
        self.commands = commands
        self.file_supplier = file_supplier

    def get_completions(self, document, complete_event):  # type: ignore[override]
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)
        if text.startswith("/"):
            for cmd in self.commands:
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
        if "@" in text:
            after_at = text[text.rfind("@") + 1 :]
            for path in self.file_supplier():
                if path.startswith(after_at):
                    yield Completion(path, start_position=-len(after_at))


def _history_file(cwd: Path) -> Path:
    return ensure_dogent_dir(cwd) / "history.md"


def render_header(cwd: Path, settings: Settings) -> None:
    model_name = settings.anthropic_model or settings.anthropic_small_fast_model or "-"
    console.print(
        Panel(
            f"[bold cyan]Dogent[/bold cyan]\n工作目录: {cwd}\n模型: {model_name}",
            border_style="cyan",
        )
    )


def interactive_config(cwd: Path) -> Settings:
    """Prompt user for config and write .dogent/dogent.json."""
    current = load_settings(cwd)
    base_url = typer.prompt(
        "Anthropic base URL",
        default=current.anthropic_base_url or "https://api.deepseek.com/anthropic",
        show_default=True,
    )
    token = typer.prompt("Anthropic auth token", default=current.anthropic_auth_token or "", hide_input=True)
    model = typer.prompt("Main model", default=current.anthropic_model or "deepseek-reasoner")
    small_model = typer.prompt("Fast model", default=current.anthropic_small_fast_model or "deepseek-chat")
    timeout = typer.prompt("API timeout ms", default=str(current.api_timeout_ms or 600000))
    language = typer.prompt("Language", default=current.language)
    default_format = typer.prompt("Default format", default=current.default_format)
    image_dir = typer.prompt("Image directory", default=current.image_dir)
    max_section_tokens = typer.prompt("Max section tokens", default=str(current.max_section_tokens))
    data = {
        "anthropic_base_url": base_url,
        "anthropic_auth_token": token,
        "anthropic_model": model,
        "anthropic_small_fast_model": small_model,
        "api_timeout_ms": int(timeout),
        "language": language,
        "default_format": default_format,
        "image_dir": image_dir,
        "max_section_tokens": int(max_section_tokens),
        "claude_code_disable_nonessential_traffic": current.claude_code_disable_nonessential_traffic,
    }
    write_config(cwd, data)
    console.print("[green]已写入 .dogent/dogent.json 并更新 .gitignore[/green]")
    return load_settings(cwd)


async def handle_slash_command(
    command: str,
    cwd: Path,
    todo: TodoManager,
    runtime: AgentRuntime,
) -> bool:
    cmd = command.strip()
    if cmd.startswith("/init"):
        path = ensure_guidelines(cwd)
        console.print(f"[green]已确保指南文件存在：{path}[/green]")
        return True
    if cmd.startswith("/config"):
        new_settings = interactive_config(cwd)
        runtime.settings = new_settings
        return True
    if cmd.startswith("/todo"):
        console.print(todo.render_panel())
        return True
    if cmd.startswith("/info"):
        info = await runtime.get_server_info()
        console.print(info)
        return True
    if cmd.startswith("/exit"):
        return False
    console.print(f"[yellow]未知指令: {cmd}[/yellow]")
    return True


async def run_repl() -> None:
    cwd = Path.cwd()
    settings = load_settings(cwd)
    guidelines = load_guidelines(cwd)
    todo = TodoManager()
    bootstrap_todo(todo)
    runtime = AgentRuntime(cwd=cwd, settings=settings, guidelines=guidelines, todo=todo)
    render_header(cwd, settings)

    session = PromptSession(
        completer=DocCompleter(SLASH_COMMANDS, lambda: list_reference_candidates(cwd)),
        history=FileHistory(str(_history_file(cwd))),
        multiline=True,
    )

    def truncate(text: str, limit: int = 160) -> str:
        if len(text) <= limit:
            return text
        return f"{text[:limit]} ... (+{len(text) - limit} chars)"

    def append_history(user_text: str, summary: str) -> None:
        hist_path = _history_file(cwd)
        ts = datetime.now().isoformat(timespec="seconds")
        entry = (
            f"## {ts}\n\n"
            f"**User:** {user_text.strip() or '(empty)'}\n\n"
            f"**Summary:** {summary.strip() or '(empty)'}\n\n"
        )
        with hist_path.open("a", encoding="utf-8") as f:
            f.write(entry)

    def make_log_table(logs: List[dict]) -> Table:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Type", width=12)
        table.add_column("Summary")
        for entry in logs[-12:]:
            table.add_row(entry["type"], entry["text"])
        if not logs:
            table.add_row("-", "等待任务")
        return table

    def render_dashboard(logs: List[dict]) -> Columns:
        log_panel = Panel(make_log_table(logs), title="Activity", border_style="blue")
        summary = todo.render_summary_counts()
        todo_panel = todo.render_panel()
        todo_panel.title = f"Tasks ({summary})"
        return Columns([todo_panel, log_panel])

    logs: List[dict] = []

    while True:
        try:
            text = await session.prompt_async("> ")
        except (KeyboardInterrupt, EOFError):
            break
        if not text:
            continue
        stripped = text.strip()
        if stripped.startswith("/"):
            cont = await handle_slash_command(stripped, cwd, todo, runtime)
            if not cont:
                break
            # reload guidelines if init changed
            guidelines = load_guidelines(cwd)
            runtime.guidelines = guidelines
            continue

        refs: List[Reference] = resolve_references(stripped, cwd)
        logs.clear()
        console.print("[blue]开始处理...（按 ESC 或 Ctrl+C 可中断）[/blue]")
        try:
            try:
                runtime.settings.require()
            except ValueError as e:
                console.print(f"[red]{e}，请先运行 /config 设置凭据。[/red]")
                append_history(stripped, str(e))
                continue
            interrupted = False
            assistant_chunks: List[str] = []
            result_meta = ""
            with Live(render_dashboard(logs), console=console, refresh_per_second=4) as live:
                async for event in runtime.stream_query(stripped, refs):
                    etype = event["type"]
                    if etype == "partial":
                        # Show a light heartbeat without flooding
                        if not logs or logs[-1]["type"] != "写作":
                            logs.append({"type": "写作", "text": "写作中..."})
                    elif etype == "assistant":
                        assistant_chunks.append(event["text"])
                        logs.append({"type": "回复", "text": truncate(event["text"], 200)})
                    elif etype == "tool_use":
                        logs.append({"type": "工具", "text": truncate(event["text"], 160)})
                    elif etype == "tool_result":
                        logs.append({"type": "结果", "text": truncate(event["text"], 160)})
                    elif etype == "result":
                        result_meta = event["text"] or result_meta
                        logs.append({"type": "完成", "text": event["text"] or "完成"})
                    # keep log list bounded
                    if len(logs) > 30:
                        logs[:] = logs[-30:]
                    live.update(render_dashboard(logs))
            summary_parts = []
            if assistant_chunks:
                summary_parts.append(truncate(" ".join(assistant_chunks), 400))
            if result_meta:
                summary_parts.append(result_meta)
            summary = " | ".join(summary_parts) if summary_parts else "无摘要"
            append_history(stripped, summary)
        except KeyboardInterrupt:
            console.print("[yellow]中断请求，尝试停止...[/yellow]")
            await runtime.interrupt()
            interrupted = True
            append_history(stripped, "已中断")
        console.print("")  # newline spacer
        # After completion or interrupt, show prompt hint
        if interrupted:
            console.print("[cyan]已中断，继续输入以重新开始。[/cyan]")
        else:
            console.print("[green]完成。可以继续输入下一条指令。[/green]")

    console.print("[cyan]Bye[/cyan]")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """Dogent CLI."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        asyncio.run(run_repl())


if __name__ == "__main__":
    app()
