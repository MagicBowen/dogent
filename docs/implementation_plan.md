# Implementation Plan for Dogent

This plan tracks tasks and status.

## 1) Project Scaffolding
- [done] Add `pyproject.toml` with metadata, dependencies (`claude-agent-sdk`, `typer`, `rich`, `prompt_toolkit`, `pyyaml`, `httpx`, `pydantic`, `anyio`), entrypoint `dogent=dogent.cli:app`, Python 3.10+ requirement.
- [done] Create `src/dogent/` package with `__init__.py` and version constant.
- [done] Add `.gitignore` entries for `.dogent/dogent.json`, `.dogent/memory.md`, `/images/`, `__pycache__`, `.DS_Store`, and build artifacts.

## 2) Config and Guidelines
- [done] Implement `config.py`: load env vars, merge `.dogent/dogent.json` (fallback to legacy `.doc-config.yaml`), defaults (language/format/image_dir/max_section_tokens/research_provider), validation for required token/model, add config to `.gitignore`, flags for web/fs tool allow.
- [done] Implement `guidelines.py`: ensure `.dogent/dogent.md` template, migrate legacy `.claude.md`, and summarize rules.

## 3) Prompt Templates
- [done] Place in `src/dogent/prompts/`: `system.md`, `planner.md`, `researcher.md`, `writer.md`, `validator.md`, `polisher.md`, `command_handler.md`; Dogent-only system prompt (no Claude Code preset) with doc-writing focus, tool constraints, Chinese Markdown emphasis.

## 4) Runtime Integration with Claude Agent SDK
- [done] Implement `runtime.py`: build `ClaudeAgentOptions` with explicit allowed tools (`Read`/`Write`/`Edit`/`MultiEdit`/`WebSearch`/`WebFetch`), Dogent system prompt, single `model` from config/env, env overrides, cwd, partial streaming, setting_sources.
- [done] Stream via `receive_response` inside the client context for correct lifecycle; keep `interrupt()` support.
- [done] Add `can_use_tool` guard for cwd-limited FS access, delete confirmation denial, and basic bash safety.
- [pending] Hook/permission refinements (e.g., interactive delete confirmation, nuanced path prompts) if needed.

## 5) Context and Todo Management
- [done] Implement `context.py` (`@file` resolution + completions) and `todo.py` (status with colored panel + summary counts).

## 6) Images, Citations, Memory
- [done] Implement `images.py` (download to images/), `citations.py` (collect/render), `memory.py` (scratchpad lifecycle under `.dogent/`).

## 7) CLI / UX
- [done] Implement `cli.py` with Typer + prompt_toolkit REPL, slash commands `/init`, `/config`, `/todo`, `/info`, `/exit`; Rich Live dashboard (todo + activity), progress/interrupt hints; input submission; version flag.
- [done] Streaming output summarized (truncated logs) instead of full article; partial heartbeat and tool/result summaries.
- [pending] Optional single-line submit mode toggle and richer todo-sync from model output.

## 8) Workflow Orchestration
- [done] Basic `workflow.py` bootstrap todo; prompt orchestration relies on templates.
- [pending] Deeper model-driven todo syncing (parse validator output into todo updates) and section-by-section automation.

## 9) Documentation and Examples
- [done] Update `docs/design.md`, `docs/implementation_plan.md`, `docs/example_usage.md`, `README.md` for Dogent naming, usage, and prompts.
- [pending] Add a concrete sample project walkthrough with expected outputs.

## 10) Testing and Validation
- [done] Add tests: config precedence, guidelines template, @reference resolution, runtime option wiring (tool flags, model).
- [pending] More coverage: permission guard behavior (out-of-cwd denies), CLI smoke (slash commands, live dashboard), image/citation flows.
- [pending] Manual acceptance: run `/init`, `/config`, draft doc with web fetch + fs writes; validate interruptions and logs.
