# Dogent Detailed Design

## Objectives and Scope
- Provide a Claude Agent SDK-based interactive CLI (`dogent`) for professional long-form document generation within any working directory.
- Match Claude Code-style behaviors: inline commands (`/init`, `/config`, `/exit`), `@file` references with completion, `.claude` tool loading (including doc rules via `.claude.md`), visible todo list, and rich progress output.
- Use environment variables for Anthropic/deepseek configuration, overridden by project-local config generated via `/config`.
- Support full document workflow: planning, research, drafting in sections, validation, polishing, citation, image downloads, and temporary memory capture.
- Package as a standalone Python tool installable via pip/pipx with an executable entrypoint.

## User Experience and CLI Flow
- Entry: run `dogent` in any directory; Rich renders header, status panes (todo list, active step), and streaming assistant responses.
- Input loop powered by prompt_toolkit for history, multiline editing, and completions; `/exit` cleanly terminates.
- Commands:
- `/init` creates or updates doc rules in `.claude.md` (workspace root) with a filled template covering document type, audience, tone, style, length targets, format, language, citation policy, image policy, validation expectations, and default outline hints.
  - `/config` guides creation of `.doc-config.yaml` (or updates existing), then ensures `.gitignore` contains that path; once present, config values override env vars.
  - `/exit` leaves the REPL.
- `@` file references: prompt_toolkit completes paths from the working directory (and `.claude`), inserts as `@relative/path.ext`; references are resolved to file contents for context injection when requests are executed.
- Visible todo list: a Rich panel shows planned steps with status (planned/in-progress/done); updates stream as the agent executes.
- Output rendering: sections for agent reasoning (compact), actions (tool calls, downloads), and final content; streaming tokens via Claude Agent SDK callbacks.

## Configuration and Precedence
1) `.doc-config.yaml` in CWD (created by `/config`), fields:
   - `anthropic_base_url`, `anthropic_auth_token`, `anthropic_model`, `anthropic_small_fast_model`, `api_timeout_ms`, `claude_code_disable_nonessential_traffic`.
   - Optional defaults: `language`, `default_format`, `image_dir`, `max_section_tokens`, `research_provider` (if network tool configured).
2) Environment variables (per requirement) when project file absent.
3) Built-in safe fallbacks for non-secret values; token is mandatory.
`.doc-config.yaml` is added to `.gitignore` automatically.
- Explicitly set `setting_sources=["project","local","user"]` for the SDK so `.claude/` (and optional `.claude-local/`) commands/agents/skills load; default SDK behavior loads none if unspecified.

## Directory Conventions
- `.claude.md`: project writing guidelines produced by `/init`; users can edit directly in the workspace root.
- `.doc-config.yaml`: local runtime config produced by `/config`.
- `.memory.md`: transient scratchpad for ideas/notes; cleaned when tasks complete.
- `images/`: downloads of referenced online images; created on demand.
- `.claude/`: user-defined agents, commands, skills, MCP tool configs; auto-discovered and loaded.

## High-Level Architecture
- CLI Entrypoint (`dogent.__main__`): Typer/Cli wrapper that launches REPL, wires Rich layout, and injects configuration/context into the Agent runtime.
- Config Manager: merges env vars and optional `.doc-config.yaml`, validates required values, and exposes a typed settings object.
- Guideline Manager: ensures `.claude.md` exists; parses document constraints from `.claude.md` into structured guidance.
- Prompt Templates: stored under `dogent/prompts/` (system, planner, researcher, writer, validator, polisher, command handler). Loaded and interpolated at runtime with context (guidelines, todo, references).
- Agent Runtime: thin wrapper around Claude Agent SDK; registers tools (shell, fs, http fetch/download, MCP adapters, skills from `.claude`), streams tokens, and surfaces tool actions to the UI.
- Todo/Task Orchestrator: builds plan (sections, research, validation), tracks state, and updates the UI panel; persists in memory during session.
- Document Orchestrator: coordinates planning, research, drafting per section, validation, polishing, and citation assembly; manages `.memory.md` lifecycle.
- Context Loader: resolves `@file` references, loads `.claude` artifacts, and injects accessible skills/MCP tools into the agent’s runtime.
- Image Manager: handles URL validation and downloads to `images/`, returning Markdown paths.
- Citation Manager: deduplicates and orders citations, appends to final output.
- Logging/Telemetry: structured console logs via Rich; debug mode can emit raw Claude Agent SDK traces.

## Claude Agent SDK Usage
- Use `ClaudeSDKClient` (streaming, interruptible) with `ClaudeAgentOptions`:
  - Tools: explicitly allow `Read`/`Write`/`Edit`/`MultiEdit` and `WebSearch`/`WebFetch`; set `permission_mode="acceptEdits"` or `plan` based on safety posture.
- System prompt: use Dogent’s own system prompt (no Claude Code preset text), focused on document writing and the project rules.
  - Models: `model`/`fallback_model` wired to main vs fast env values; `max_thinking_tokens` for reasoning-heavy doc tasks.
  - Settings loading: `setting_sources=["project","local","user"]` to pick up `.claude` commands/agents/skills; `plugins` option to load local plugin directories (e.g., `.claude-plugin`).
  - MCP: pass `.claude` MCP configs plus in-process servers via `create_sdk_mcp_server` for doc-specific tools; allow external stdio/SSE servers.
  - Hooks: register `PreToolUse`/`PostToolUse`/`UserPromptSubmit`/`PreCompact` to enforce safety, enrich context, and update todo state; `can_use_tool` callback to gate/modify tool inputs.
  - Streaming: set `include_partial_messages=True` to surface `StreamEvent` tokens into the Rich UI; use `receive_messages` for concurrent render and `interrupt()` to stop long actions.
  - Budget/safety: `max_budget_usd`, `sandbox` for bash isolation, `cwd` pinned to user directory, `env` for model/base URL overrides, `extra_args` for CLI flags.
  - Control protocol: use `get_server_info` to surface available commands/tools; use `resume`/`fork_session` for long doc sessions.
- Register built-in tools: shell, filesystem, web fetch, downloads, plus doc-specific SDK MCP tools (outline expander, citation checker, image downloader wrapper).
- Load user-defined agents/commands/skills from `.claude` and plugins; expose them in CLI help and pass through to prompts so Claude can call them.
- Stream progress into Rich panels (todo updates, tool calls, partial text) using SDK callbacks.

## Document Writing Workflow
1) Initialize: ensure doc rules exist in `.claude.md` (seed via `/init` if missing); load config; prepare `.memory.md` and `images/` (lazy).
2) Intake: parse user request and `@` references; derive goals, audience, constraints from `.claude.md` doc rules.
3) Plan: generate a todo list (outline, research, drafting, validation, polish); surface to UI; attach as context in `planner` prompt and SDK hooks.
4) Research: perform web searches (via HTTP/MCP search tool), capture key facts with sources in `.memory.md`, download needed images to `images/`; keep citations structured.
5) Draft by sections: chunk work per outline; for each section, pull relevant facts, guidelines, and references; write Markdown in Chinese by default; embed images and diagrams when specified; use doc-specific `AgentDefinition` (writer) with `Read`/`Write`/`Bash` as needed.
6) Validation: run a validation prompt or validator agent over the draft (consistency, factuality, citation coverage, link check stubs); enqueue fixes in todo list; optionally use hooks to block unsafe edits.
7) Polish: final pass for tone, cohesion, and structure; ensure citations are appended and image references resolve to `./images/...`.
8) Output: stream final Markdown to the user; optionally write to a file if requested; `ResultMessage` cost/duration surfaced in UI.
9) Cleanup: clear `.memory.md` when temporary notes are no longer needed.

## Prompt Template Design (stored under `doc/prompts/`)
- `system.md`: establishes role, safety, command semantics, tool usage rules, CWD scope, Chinese Markdown default, adherence to `.claude.md` doc rules; uses Dogent’s own system prompt (no Claude Code preset).
- `planner.md`: creates actionable todo items and outlines, marks dependencies, and sizes sections.
- `researcher.md`: requests facts, URLs, image needs; mandates citation capture.
- `writer.md`: drafts a specific section respecting tone/length/format; requires inline references and image placement.
- `validator.md`: checks factual consistency, guideline alignment, citations, and broken references; outputs fix tasks.
- `polisher.md`: improves flow and unifies tone without changing meaning; ensures final citations list.
- `command_handler.md`: handles `/init`, `/config`, `/exit`, and general user intents, selecting models (fast vs main) based on complexity.
Templates interpolate: project settings, guideline summary, todo state, resolved file references, available tools, and MCP skills.

## Todo List Behavior
- Represented as structured items (`id`, `title`, `status`, `details`, `owner`, `section`, `refs`).
- Displayed continuously in a Rich panel; updates when plan changes, when sections complete, and when validation/polish pass.
- Exposed to the model in prompts so it can reference and update statuses through tool calls.

## Claude Code Parity via SDK (findings from upstream repo)
- SDK already bundles the Claude Code CLI; `cli_path` can override but default suffices.
- Default `setting_sources=None` loads no settings; set to `["project","local","user"]` so `.claude` commands, agents, skills, and MCP configs mirror Claude Code behavior. Respect `.claude-local/` for user-only overrides when present.
- Slash commands/plugins: pass `plugins=[{"type":"local","path":<plugin_dir>}]` (demo in examples/plugins) to expose custom commands; surface available slash commands via `get_server_info`.
- Custom agents: define doc-specific `AgentDefinition`s (planner, researcher, writer, validator) with tailored prompts/tools/models and route tasks to them.
- Tools and permissions: use `tools` preset for full suite; gate with `allowed_tools`/`disallowed_tools`; `can_use_tool` callback for runtime approval/rewrites; `permission_mode` toggles (default/acceptEdits/plan) map to Claude Code permission UX.
- Hooks: wire `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `PreCompact`, `Stop/SubagentStop` to enforce guardrails (e.g., block dangerous bash), inject context (todo state), or halt on errors.
- Streaming UX: enable `include_partial_messages` to surface `StreamEvent` for token-by-token UI; use `receive_messages` for concurrent display and `interrupt()` for user-initiated stop.
- Session control and budgets: support `resume`/`fork_session`, `max_turns`, `max_budget_usd`, `max_thinking_tokens`, `output_format` for structured outputs.

## File/Directory Layout (planned)
- `dogent/cli.py` (Typer/Rich REPL), `dogent/runtime.py` (Claude Agent SDK wrapper), `dogent/config.py`, `dogent/guidelines.py`, `dogent/prompts/`, `dogent/todo.py`, `dogent/workflow.py`, `dogent/context.py`, `dogent/images.py`, `dogent/citations.py`, `dogent/memory.py`.
- `docs/design.md` (this document), `requirements.md` (given), `pyproject.toml`/`setup.cfg` for packaging, `README.md` for usage.

## Packaging and Distribution
- Python project with `pyproject.toml` using setuptools; dependencies: `anthropic` (Claude Agent SDK), `rich`, `typer`, `prompt_toolkit`, `pyyaml`, `httpx`, `pydantic`, `requests` (if needed for downloads), and optional MCP helpers per SDK guidance.
- Entry point: console_scripts `dogent=dogent.cli:app`.
- Build: `pip install .` or `pipx install .`; produces `dogent` executable available in PATH.
- Add `__version__` to expose version; include `--version` CLI flag.

## Testing Strategy
- Unit tests for config precedence, guideline parsing, todo orchestration, prompt rendering, and options wiring (tools preset, setting_sources, plugins).
- Integration tests with mocked Claude Agent SDK to ensure tool registration, hooks, permission callbacks, and streaming callbacks.
- CLI smoke tests: `/init`, `/config`, `@file` completion, todo rendering, Claude Code parity loading `.claude`, plugin load, and `/exit`.
- Manual acceptance: generate a sample long-form doc with research, images, validation, and polish in a temp workspace.

## Risks and Mitigations
- Missing network/search capability: allow graceful degradation with local-only mode; surface warnings.
- Large files/sections: enforce chunking and `max_section_tokens`.
- Secrets leakage: keep tokens in config file only; redact from logs.
- Prompt drift: keep templates versioned and isolated for tuning; add checksum/version in settings.

## Next Implementation Steps
- Scaffold Python package and entrypoint.
- Implement config/guideline managers and prompt loading (Dogent system prompt only, no Claude Code preset).
- Wire Claude Agent SDK runtime with tools preset, setting sources, plugins, hooks, permission callback, and MCP discovery.
- Build Rich + prompt_toolkit REPL with slash commands and `@` completion plus partial-stream rendering and interrupt.
- Implement document workflow orchestrator, todo updates, and validation/polish flows.
- Add packaging metadata, .gitignore updates, and tests.
