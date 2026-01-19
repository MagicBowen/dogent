# User Stories Backlog

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted

## Release 0.1

### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Pending (retest after history.json migration)
- Verification: Manual install/run check.

### Story 2: Workspace Bootstrap
- User Value: Scaffold templates without prior setup.
- Acceptance: `/init` creates `.dogent/dogent.md` without overwriting existing files; slash commands suggest available actions. Memory/images dirs are not auto-created.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_init_files_created`.

### Story 3: Config & Profiles
- User Value: Configure credentials via `/init` (dogent.json), profiles, env fallback.
- Acceptance: `.dogent/dogent.json` references `llm_profile`; the selected profile overrides env; env used when missing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_profile_and_project_resolution`, `tests/test_config.py::test_profile_md_supported_and_gitignore_not_modified`.

### Story 4: Prompt Templates
- User Value: System/user prompts isolated and editable.
- Acceptance: Prompts live under `dogent/prompts/*.md`; system injects `.dogent/dogent.md`; user prompt includes todos and @files; CLI streams tool/todo updates.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_prompts.py::test_prompts_include_todos_and_files`.

### Story 5: Todo Panel Sync
- User Value: Tasks panel reflects `TodoWrite` updates live.
- Acceptance: TodoWrite tool inputs/results replace todo list; rendered in CLI; no default todos. Scrolling tool messages are concise with emoji titles; TodoWrite logs are summarized without duplicate Todo panels.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_todo.py::test_agent_updates_todo_from_tool`.

### Story 6: @file References
- User Value: Inject file contents into a turn.
- Acceptance: `@path` loads file content (with truncation notice) and echoes loaded files in CLI; only within workspace; entering `@` suggests files.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_prompts.py::test_prompts_include_todos_and_files`.

### Story 7: Interactive Session
- User Value: Streaming chat with Claude Agent SDK.
- Acceptance: Starts session even without `.dogent/`; `/init` can be run later to add settings; streams tool use/results with Rich panels.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual chat smoke.

### Story 8: Writing Workflow Prompting
- User Value: Agent guided to plan → research → section drafts → validate → polish in Chinese Markdown.
- Acceptance: System prompt enforces steps, todo usage, citations, and image download guidance via `dogent_web_fetch` with per-call `output_dir`; memory hints (create on demand, clean after use).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual e2e content check.

### Story 9: Research & Images
- User Value: Agent can search web and download images into `./images` and reference them.
- Acceptance: Web tools enabled; image download workflow uses `dogent_web_fetch` with `output_dir` (e.g., `./images`); images saved and referenced via returned Markdown snippet.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_web_tools.py::test_web_fetch_downloads_image`, UAT Release 0.6 Story 39.

### Story 10: Validation & Citations
- User Value: Agent validates facts, tracks checks in todo, and emits reference list at end.
- Acceptance: Validation tasks appear in todos; output includes “参考资料” links; consistency checks logged.
- Dev Status: Todo
- Acceptance Status: Pending
- Verification: Manual e2e once implemented.

### Story 11: Usage Docs & Tests
- User Value: Clear setup/run/test instructions.
- Acceptance: `README.md` and `docs/usage.md` describe install, commands, profiles, tests; unit tests runnable.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`.

## Release 0.2

### Story 12: Single Source Versioning
- User Value: `dogent -v` shows the published package version without drift.
- Acceptance: Version defined once and shared between `pyproject.toml` and `dogent/__init__.py`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Test asserting both sources match; `dogent -v` reflects that value.

### Story 13: Home Bootstrap & Default Profile
- User Value: Fresh installs are guided to set credentials.
- Acceptance: On install/first run, create `~/.dogent` if missing, write default `claude.json`, and prompt user to edit.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Simulated clean home run shows scaffold and prompt.

### Story 14: ASCII Welcome Banner
- User Value: CLI greets with a Dogent ASCII/Unicode art banner.
- Acceptance: Banner appears centered inside the welcome panel before prompts; no footer subtitle.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Visual/manual check.

### Story 15: History Persistence
- User Value: Resume prior progress seamlessly.
- Acceptance: Structured progress appended to `.dogent/history.json` each task (requests, summaries, todos); system prompt instructs loading history on re-entry; CLI echoes only actually created files on `/init`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Test/inspection of history write/read and prompt content.

### Story 16: Ephemeral Memory
- User Value: Temporary notes don’t linger.
- Acceptance: System prompt instructs creating `.dogent/memory.md` only when needed and auto-cleaning after use.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Prompt review; behavioral test ensuring no eager creation.

### Story 17: Configurable Images Path
- User Value: Control where images download.
- Acceptance: `/init` adds default image path config; no `images/` dir created by default; defaults to `./images` if unset.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Config content check; no auto-created dir on init; path resolution test.

### Story 18: Interrupt with Esc
- User Value: Stop a task without killing the CLI and keep progress.
- Acceptance: Esc interrupts Claude Agent SDK task (per SDK docs), records progress to `.dogent/history.json`, then returns to prompt; next prompt should include history so the agent resumes, not just a summary.
- Important Tips: Refer to the corresponding document and example codes in claude-agent-sdk folder for how interrupt claude agent sdk
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual/integration test simulating interrupt; history write check.

### Story 19: Remove `/todo` Command
- User Value: Simplified CLI without redundant commands.
- Acceptance: `/todo` command removed; todos still auto-render on updates.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: CLI command list and behavior; tests ensure no `/todo` handling.

### Story 20: Enhanced Summary Presentation
- User Value: Clear session summaries with visual distinction.
- Acceptance: “Session Summary” uses emoji title; summary content shown before metrics (time, cost); other sections (e.g., “File Reference”) also prefixed with emojis.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual/automated output check at task completion.

## Release 0.3

### Story 21: Command Registration
- User Value: CLI commands are extensible without core code edits.
- Acceptance: Commands (listing, banner hints, unknown-command message) come from a registry; adding a command requires registration only.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Registry-driven banner/unknown-command output; manual CLI check.

### Story 22: Externalized Templates
- User Value: Prompts/config templates editable without code changes.
- Acceptance: Embedded templates (e.g., doc template) moved to standalone files and loaded at runtime.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Template files exist and are loaded; fallback behavior tested.

### Story 23: Prompt Optimization
- User Value: Clear, best-practice system/user prompts without hardcoded image paths.
- Acceptance: System prompt rewritten per guidelines; image paths derived from config; user prompt clarified.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Prompt content inspection; tests assert no hardcoded image path and presence of new sections.

### Story 24: Code Structure & Clean Code
- User Value: Core agent/CLI decoupled from role-specific configs/templates; improved readability.
- Acceptance: Core interactive agent separated from writing role configs; comments and structure updated; `AGENTS.md` reflects architecture.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Code review; doc update.

### Story 25: Multi-line Input Support
- User Value: Users can add line breaks with Alt/Option+Enter.
- Acceptance: CLI supports multi-line input via shortcut.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual/integration test; keybinding test if feasible.

### Story 26: Graceful Ctrl+C Exit
- User Value: Clean exit without stack traces.
- Acceptance: Ctrl+C triggers graceful shutdown, resource cleanup, and friendly message.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual/integration test; handler logic (Ctrl+C while task running interrupts and returns to prompt).

### Story 27: Architectural Guidelines
- User Value: Future contributors follow clear extensibility principles.
- Acceptance: `AGENTS.md` updated with Release 0.3 design principles (command registry, template externalization, core/role separation).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Docs review.

## Release 0.4

### Story 28: Home Template Bootstrap
- User Value: Home bootstrap creates credential config files without copying prompts/templates.
- Acceptance: On first start, only `~/.dogent/claude.json` and `~/.dogent/web.json` are created; prompts/templates remain packaged.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_home_bootstrap_creates_only_profile_and_web`, `tests/test_config.py::test_config_template_ignores_home_templates`, UAT Release 0.8.0.

### Story 29: Flexible Prompt Injection
- User Value: Prompt templates can reference workspace state and config keys safely even after user edits.
- Acceptance: Templates support placeholders for working dir, history (full/recent), memory, todo list, user input, attachments, and `config:<key>` paths; missing values render empty and warn the user; README lists available parameters.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_prompts.py::test_template_warns_on_missing_and_reads_config_values`, README template parameter section, UAT Release 0.4.

### Story 30: English System UI
- User Value: Consistent English UI labels while respecting LLM output language.
- Acceptance: System prompts/panel titles in the interactive CLI remain in English; model output retains original language.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UI inspection; prompt/title checks in CLI.

## Release 0.5

### Story 31: History Display
- User Value: Quickly review recent sessions and todo outcomes without leaving the CLI.
- Acceptance: `/show history` shows recent history entries in a structured view plus the latest todo snapshot; handles empty history gracefully with friendly messaging.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_history_command.py::test_history_command_shows_recent_entries_and_todos`.

### Story 32: Home Template Version Refresh
- User Value: Home templates stay current after Dogent upgrades without manual copying.
- Acceptance: `~/.dogent/version` records the installed Dogent version; when the version changes, prompts/templates under `~/.dogent` are refreshed from packaged defaults while keeping `~/.dogent/claude.json` intact; user is notified on sync.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_home_templates_updated_on_version_change`.

### Story 33: Profile Placeholder Warning
- User Value: Avoid running with placeholder credentials.
- Acceptance: If `.dogent/dogent.json` references an `llm_profile` whose token in `~/.dogent/claude.json` is missing or still set to `replace-me`, Dogent prints an alert prompting the user to update credentials.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_warns_on_placeholder_profile`.

### Story 34: Web Tool Result Clarity
- User Value: Understand web tool outcomes without guessing.
- Acceptance: WebFetch/WebSearch results show explicit success or failure with the reason when failures occur; displayed in the CLI result panels.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_help_and_tools.py::test_web_tool_result_states_success_and_failure`.

### Story 35: Help Command
- User Value: Quick in-CLI reference to models, API, profiles, and available commands.
- Acceptance: `/help` renders a panel with current model/API/LLM profile/web profile, command descriptions, and shortcut tips.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_help_and_tools.py::test_help_command_shows_usage`.

### Story 36: Clean History & Memory
- User Value: Start a new session without leftover context.
- Acceptance: `/clean` empties `.dogent/history.json`, removes `.dogent/memory.md` if present, and resets in-memory todos with a confirmation panel; handles missing files gracefully.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_clear_command.py::test_clear_command_resets_history_and_memory`.

## Release 0.6

### Story 37: Web Tool Config Bootstrap
- User Value: Configure reliable web search/fetch providers without editing code.
- Acceptance: On first run, Dogent creates `~/.dogent/web.json` (kept on upgrades); workspace `.dogent/dogent.json` can select `web_profile`; if `web_profile` is missing/empty/`default`, Dogent uses native `WebSearch`/`WebFetch`; `/help` shows the active web mode/profile and LLM profile.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_home_bootstrap_copies_prompts_and_templates`, config fallback tests, UAT Release 0.6.

### Story 38: Custom WebSearch Tool
- User Value: Perform reliable web + image search even when native WebSearch fails.
- Acceptance: A custom tool `dogent_web_search` (tool ID: `mcp__dogent__web_search`) uses `~/.dogent/web.json` provider config to return structured results for web and image queries; missing/placeholder config returns a clear error message.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_web_tools.py::test_web_search_returns_structured_results`, `tests/test_web_tools.py::test_parse_google_cse_results_image_mode`.

### Story 39: Custom WebFetch Tool (Text + Images)
- User Value: Fetch readable page content and download images for documents.
- Acceptance: A custom tool `dogent_web_fetch` (tool ID: `mcp__dogent__web_fetch`) fetches URLs, extracts core readable text for HTML, and downloads images into a workspace-relative `output_dir` (creating it on demand) with safe filenames and a Markdown reference snippet.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_web_tools.py::test_web_fetch_extracts_text`, `tests/test_web_tools.py::test_web_fetch_downloads_image`, `tests/test_web_tools.py::test_extract_text_from_html_strips_noise`.

### Story 40: Prompts & Tool Wiring
- User Value: Agent consistently uses Dogent’s reliable web tools during research and image workflows.
- Acceptance: System prompt explains both native and Dogent web tools; Dogent registers MCP tools only when `web_profile` is set to a real profile; otherwise it uses native `WebSearch`/`WebFetch`; invalid `web_profile` warns at startup and falls back to native tools.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: config fallback tests, `dogent/prompts/system.md` tool section check.

## Release 0.7.0

### Story 41: Lessons (Continuous Improvement)
- User Value: Dogent avoids repeating the same mistakes by recording failures + correct approaches and reusing them in later tasks.
- Acceptance:
  - Lessons are stored in `.dogent/lessons.md` (project-only, user-editable).
  - Failure/interrupt signal:
    - If the user interrupts (Esc/Ctrl+C), the run is recorded in `.dogent/history.json` with status `interrupted`.
    - If the agent run fails or ends prematurely (and the user did not interrupt), the run is recorded in `.dogent/history.json` with status `error` (not `completed`).
    - Do not detect failure by parsing free-form summary text.
  - After a run with status `error` or `interrupted`, the next user message triggers a “Save a lesson?” prompt with default **Y**.
  - If accepted, Dogent uses the LLM to draft a structured lesson using the last failure Summary and the user’s correction message as context, appends it to `.dogent/lessons.md`, then proceeds with the user’s request (retry).
  - `/learn <free text>` appends a new lesson (LLM rewrites into a consistent format).
  - `/learn on|off` toggles the automatic “Save a lesson?” prompt.
  - `/show lessons` displays a short list of recent lessons and points to `.dogent/lessons.md` for editing.
  - The full `.dogent/lessons.md` content is injected into prompt context on each new task (no relevance filtering for now; truncation with notice is allowed if needed).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_lessons.py`, `tests/test_cli_learn.py`, UAT Release 0.7.0.

### Story 42: Failure Summary Status Clarity
- User Value: Immediately understand that the run failed (or was interrupted) and why, and use it as a reliable trigger for lesson capture.
- Acceptance:
  - When a run exits the agent loop with unfinished todos, the Summary panel title clearly shows status (e.g., `❌ Failed` / `⛔ Interrupted` / `✅ Completed`).
  - Summary content includes the result/reason and a concise “Remaining Todos” section when todos exist.
  - `.dogent/history.json` records status as `error` for failures and `interrupted` for user interrupts (not `completed`).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_agent_display.py::test_unfinished_todos_marks_run_failed_and_preserves_todos`, UAT Release 0.7.0.

### Story 43: Targeted Clean Command
- User Value: Selectively clear history, lessons, or memory without wiping everything.
- Acceptance:
  - `/clean` supports a single optional target arg: `history`, `lesson`, `memory`, or `all`.
  - `/clean` without args defaults to `all`.
  - When the user types `/clean `, the CLI shows a dropdown completion list with these target options.
  - `/clean history` clears `.dogent/history.json`.
  - `/clean memory` removes `.dogent/memory.md` if present.
  - `/clean lesson` removes `.dogent/lessons.md` if present.
  - `/clean all` clears history and removes memory + lessons.
  - Each run prints a confirmation panel listing which targets were cleared.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: Add unit tests for selective clearing and completion options; add UAT steps under Release 0.7.0.

## Release 0.8.0

### Story 44: Document Templates + Init Picker
- User Value: Select a document template and scaffold project writing constraints quickly.
- Acceptance:
  - Workspace templates live in `.dogent/templates` and are unprefixed; global/built-in templates require prefixes.
  - `/init ` shows local names without prefix plus prefixed global/built-in templates.
  - `/init <template>` scaffolds a minimal `.dogent/dogent.md` and sets `doc_template` in `.dogent/dogent.json`.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_doc_templates.py`, UAT Release 0.8.0.

### Story 45: Init Wizard
- User Value: Generate `.dogent/dogent.md` from a free-form project prompt without editing templates.
- Acceptance:
  - `/init <free-form prompt>` runs the wizard and writes `.dogent/dogent.md`.
  - `doc_template` is set to `general` when no template is selected.
  - The wizard uses a dedicated system prompt and outputs JSON with `doc_template` and `dogent_md`.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `dogent/prompts/init_wizard_system.md`, UAT Release 0.8.0.

## Release 0.9.0

### Story 46: Clarification Status (Needs Clarification)
- User Value: Distinguish clarification questions from failures so users know to answer instead of retrying.
- Acceptance:
  - System prompt instructs the model to append `[[DOGENT_STATUS:NEEDS_CLARIFICATION]]` when it must ask a blocking question.
  - The CLI detects the sentinel, strips it from display, and records `needs_clarification` in `.dogent/history.json`.
  - Summary panel title shows `❓ Needs clarification` with the question and remaining todos if any.
  - Runs marked `needs_clarification` do not arm lesson capture.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_agent_display.py::test_needs_clarification_status_when_sentinel_present`, UAT Release 0.9.0.

### Story 47: LLM Wait Indicator
- User Value: Avoid the impression that the CLI is stuck during long LLM operations.
- Acceptance:
  - A spinner/timer appears during all LLM waits (chat requests, `/init` wizard, `/learn` drafting).
  - The indicator stops once a response starts streaming or completes.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_wait_indicator.py`, UAT Release 0.9.0.

### Story 48: Unified Show Command
- User Value: Fewer commands for display-only info.
- Acceptance:
  - `/history` and `/lessons` are removed from the registry.
  - `/show history` displays the history table and todo snapshot.
  - `/show lessons` displays recent lesson titles and the lessons file path.
  - CLI completion lists `history` and `lessons` after `/show `.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_history_command.py`, `tests/test_cli_completer.py`, UAT Release 0.9.0.

### Story 49: Shell Command Shortcut
- User Value: Run quick shell checks without leaving the CLI.
- Acceptance:
  - Input starting with `!` runs as a shell command in the current workspace.
  - Output (stdout/stderr and exit code) is shown in a dedicated panel.
  - `!` is only treated as a shell prefix when it is the first character of the input line.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: UAT Release 0.9.0.

## Release 0.9.1

### Story 50: Multiline History Navigation
- User Value: Cursor moves between lines before jumping to history.
- Acceptance:
  - When the input has multiple lines, Up/Down moves the cursor within the input.
  - Up only moves to history when pressed at the first line; Down only moves to history at the last line.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: Add unit test coverage for cursor movement decision; UAT Release 0.9.1.

### Story 51: Template Intro Fallback
- User Value: Template summaries still render when no Introduction section exists.
- Acceptance:
  - Template summaries use the `## Introduction` section when present.
  - When missing, summaries fall back to the first 5 lines of the document.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: Add unit test coverage for intro fallback; UAT Release 0.9.1.

### Story 52: Alt+Backspace Clear
- User Value: Quickly delete text before the cursor.
- Acceptance:
  - Pressing Alt+Backspace deletes input before the cursor.
  - When the input has multiple lines, only the current line content before the cursor is deleted.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: Add unit test coverage for clear count; UAT Release 0.9.1.

## Release 0.9.2

### Story 53: Archive Command
- User Value: Archive history/lessons for a clean slate while keeping backups.
- Acceptance:
  - `/archive [history|lessons|all]` writes timestamped files under `.dogent/archives`.
  - Missing or empty targets are skipped with a notice.
  - History resets to `[]`; lessons reset to `# Lessons` header after archiving.
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_archive_command.py`, `tests/test_cli_completer.py`, UAT Release 0.9.2.

### Story 54: Wrapped CJK Cursor Movement
- User Value: Up/Down navigation works on line-wrapped Chinese input.
- Acceptance:
  - Up/Down moves within wrapped lines even with CJK wide characters.
  - Cursor position stays consistent (no stuck or scrambled positions).
- Dev Status: Done
- Acceptance Status: PASS
- Verification: `tests/test_cli_input.py`, UAT Release 0.9.2.

## Release 0.9.3

### Story 0: Document MCP tools registered
- User Value: Document read/export capabilities are exposed as MCP tools for Claude Agent SDK.
- Acceptance: `mcp__dogent__read_document` and `mcp__dogent__export_document` are registered and visible; tools operate within workspace boundaries.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual prompt "list your tools" and unit tests for tool handlers.

### Story 1: Read PDF/DOCX/XLSX @file attachments
- User Value: User can reference .pdf/.docx/.xlsx and the agent reads usable text.
- Acceptance: @file references are listed without content; the agent calls `mcp__dogent__read_document` to read PDFs/DOCX/XLSX (first sheet by default, named sheet supported). Scanned PDFs return a clear tool error.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for readers + manual check in `sample/`.

### Story 2: Output format resolution
- User Value: User can request output format in prompt or in `.dogent/dogent.md`.
- Acceptance: Prompt or `.dogent/dogent.md` informs the LLM to write Markdown and call `mcp__dogent__export_document` for pdf/docx output.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual prompt/dogent.md checks with tool calls.

### Story 3: Export to PDF/DOCX with runtime setup
- User Value: Generated Markdown is exported to PDF or DOCX with minimal setup.
- Acceptance: Pandoc/Chromium auto-download on first use via MCP tool; conversion errors are surfaced with actionable messages; output file is created at the requested path or derived from the Markdown file name.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests with mocks + manual export in `sample/`.

## Release 0.9.4

### Story 0: Vision profile configuration
- User Value: User can configure a vision model profile and select it per workspace.
- Acceptance: `~/.dogent/vision.json` is created on first run with a `glm-4.6v` stub; `.dogent/dogent.json` includes `vision_profile` and respects user overrides.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests + manual config check.

### Story 1: On-demand vision analysis for @image/@video
- User Value: The agent can analyze images/videos on demand via a vision MCP tool without bloating the user prompt.
- Acceptance: Attachments include only core file metadata; when the user requests media understanding, the agent calls `mcp__dogent__analyze_media` using the configured vision profile; failures (missing profile/placeholder/unsupported provider) are surfaced clearly and the agent stops to request config fixes.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests with mocked vision responses + manual prompt with media files.

## Release 0.9.5

### Story 0: Confirm out-of-workspace file access
- User Value: The user explicitly approves any tool reads/writes outside the workspace.
- Acceptance: For built-in `Read`/`Write`/`Edit` tool calls targeting paths outside the workspace, Dogent pauses mid-run and asks for confirmation; deny aborts with status `aborted` and a clear reason; allow continues the task.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for permission checks + manual tool call checks.

### Story 1: Confirm delete commands
- User Value: The user explicitly approves delete operations.
- Acceptance: For `Bash` commands starting with `rm`, `rmdir`, or `del`, Dogent asks for confirmation before execution; deny aborts with status `aborted`; allow continues.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for delete parsing + manual shell command check.

## Release 0.9.6
### Story 1: Layered Config Defaults
- User Value: Global config in `~/.dogent/dogent.json` provides defaults for new workspaces; local overrides remain scoped to the workspace.
- Acceptance: `load_project_config()` merges defaults -> global -> local; if no local config, global values are used; if global lacks `llm_profile`, env fallback remains; `/init` creates `.dogent/dogent.json` using global defaults without overwriting existing keys.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for merge behavior and config template creation.

### Story 2: Vision Disabled by Default
- User Value: Vision tools are opt-in; image references fail fast when `vision_profile` is `null` or missing.
- Acceptance: Default `vision_profile` is `null`; vision MCP tools are not registered when disabled; CLI blocks image/video attachments with a clear error when vision is disabled.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for tool registration and CLI attachment blocking.

### Story 3: Prompt-Level Doc Template Override
- User Value: Users can temporarily select a doc template per request using a selector token without editing config files.
- Acceptance: Typing `@@` triggers template completion; `@@<template>` overrides `doc_template` only for that request and is stripped from the outgoing user message.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for token parsing and prompt rendering with overrides.

### Story 4: Unified Global Config File
- User Value: All global profiles and defaults live in a single `~/.dogent/dogent.json`.
- Acceptance: LLM/web/vision profiles are read from `llm_profiles`/`web_profiles`/`vision_profiles` in the global config; legacy separate files are no longer referenced; warnings and docs point to `~/.dogent/dogent.json`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for profile loading and web/vision tool behavior.

### Story 5: Versioned Global Config Upgrade
- User Value: Dogent upgrades the global config when new keys are added, without overwriting user settings.
- Acceptance: `~/.dogent/dogent.json` includes `version`; on startup, if config version < Dogent version, merge in missing keys only and update `version`; if config version > Dogent version, warn.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for upgrade behavior and warnings.

---

## Release 0.9.7

### Story 1: Configurable PDF Style
- User Value: Users can customize PDF output styling globally and override it per workspace.
- Acceptance: Default PDF CSS is installed to `~/.dogent/pdf_style.css` on first run; `.dogent/pdf_style.css` overrides global when present; PDF export applies the resolved CSS; unreadable style files fall back with a warning.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for style resolution and warnings; manual PDF export check; UAT PASS in dev/sprint_uat.md.

### Story 2: Template Override in User Prompt
- User Value: Users can temporarily select a writing template with `@@` and have it applied explicitly for that request.
- Acceptance: When `@@<template>` is used, the system prompt does not include the template content; the user prompt includes a separate "Template Remark" section with the selected template content; the system prompt instructs to prioritize that remark over `.dogent.json`/`.dogent.md`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for prompt rendering and override flow; UAT PASS in dev/sprint_uat.md.

### Story 3: Graceful Exit Without Pipe Errors
- User Value: `/exit` closes Dogent cleanly without terminal pipe errors.
- Acceptance: Running `/exit` exits the CLI without raising `EPIPE` or other write errors.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual `/exit` check in a terminal and in a piped environment; UAT PASS in dev/sprint_uat.md.

---

## Release 0.9.8

### Story 1: Structured Clarification Payloads
- User Value: When Dogent needs clarification, it can present questions in a consistent, machine-readable format for a smoother Q&A flow.
- Acceptance: System prompt instructs the model to emit a tagged JSON payload for clarifications; a JSON schema exists for the payload; Dogent extracts and validates the payload, falling back to the legacy clarification sentinel on failures.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for payload parsing/validation and system prompt updates; UAT PASS in dev/sprint_uat.md.

### Story 2: Interactive Q&A Flow
- User Value: Users answer clarification questions in a guided UI with recommended choices and optional free-form input.
- Acceptance: Clarification questions display as a dedicated Q&A interface with progress, multiple-choice selection (defaulting to recommended/first), optional free-form entry, Esc abort, and per-question timeout based on API_TIMEOUT_MS.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for Q&A selection logic and timeout/abort handling; UAT PASS in dev/sprint_uat.md.

### Story 3: Session Continuity + History Recording
- User Value: Clarification answers are recorded and the agent continues without losing context.
- Acceptance: When clarifications are requested, the agent keeps the session open, sends a follow-up with the Q/A block, and history records the questions and answers.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for session reuse and history entries; UAT PASS in dev/sprint_uat.md.

---

## Release 0.9.9

### Story 1: Unified Confirmation UX and Safe Interrupts
- User Value: Every confirmation prompt looks and behaves the same, with consistent cancel/skip behavior.
- Acceptance: All yes/no confirmations use the up/down selection UI; Esc cancels the flow; non-interactive mode keeps y/n input; selection prompts do not interrupt an active agent loop; Esc listener is paused while prompts are open and restarted after exit. Clarification prompts use up/down selection, Esc skips a single question (answer recorded as `user chose not to answer this question`), Ctrl+C cancels all clarifications; "Other (free-form answer)" immediately prompts for input; clarification JSON in thinking blocks is parsed for QA and the thinking panel is suppressed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI checks covering overwrite, lesson save, tool permissions, start writing, and initialize prompts.

### Story 2: Debug Session Logging
- User Value: Users can inspect LLM interactions for debugging when enabled.
- Acceptance: `debug: true` creates `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` JSONL logs; entries include `role`; logs capture all LLM calls (main agent, init wizard, lesson drafter); system prompt recorded once if unchanged; no log file when `debug` is false or missing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI run and log inspection.

### Story 3: /init Prompt Can Start Writing
- User Value: Users can begin writing immediately after initializing via `/init prompt`.
- Acceptance: `/init prompt` completes init (including overwrite choice) then asks whether to start writing; Yes runs the writing agent with the constructed prompt; No or Esc returns to CLI without starting the agent; other `/init` paths remain unchanged.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI flow for `/init prompt`.

### Story 4: Auto-Init When dogent.json Missing
- User Value: New projects can initialize seamlessly before the first request.
- Acceptance: If `.dogent/dogent.json` is missing on a user request, the CLI asks to initialize; Yes runs the init wizard with the user request, then offers the start-writing choice; No continues default handling; Esc cancels and returns to CLI; if the file exists, no init prompt is shown.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI flow in a fresh workspace.

## Release 0.9.10

### Story 1: Multiline Markdown Editor for Inputs
- User Value: Users can comfortably author and edit multi-line Markdown prompts and free-form answers.
- Acceptance: Single-line input remains default. Pressing Ctrl+E opens a multiline editor for the main prompt and free-form clarification answers; selecting "Other (free-form answer)" opens the editor directly. The editor uses live Markdown highlighting in the edit view, and Ctrl+P toggles a read-only full preview. Enter inserts new lines; Ctrl+Enter submits (fallback shown in footer). Ctrl+Q returns; Esc does not exit the editor. On return with dirty content, prompt to Discard/Submit/Save/Cancel (save prompts for path, confirms overwrite). Footer lists prominent actions and fallback shortcuts. Esc listener is paused while the editor is open.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT passed in dev/sprint_uat.md.

## Release 0.9.11

### Story 1: Markdown Debug Logs + Hidden Debug Default
- User Value: Debug logs are readable and comprehensive without cluttering default configs.
- Acceptance: `debug` is removed from default templates; runtime default stays false. When debug is enabled, logs are written to `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md` in chronological order and include system/user prompts, streaming blocks, tool use/results, final result, and exceptions with traceback/location. System prompts are logged once per source if unchanged.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Editor Mode Config (default|vi) + Return Dialog Semantics
- User Value: Users can choose vi editing while retaining the same editor flow for prompts, clarifications, and outline edits.
- Acceptance: `editor_mode` is supported in `dogent.json` and schema. When set to `vi`, editor uses vi mode and shows vi state in the status line. Return dialog options match scenario-specific behavior (prompt input, clarification answers, outline editing) with save/submit/abandon logic as designed. Editor-submitted content is wrapped in fenced `markdown` code blocks for both CLI display and LLM messages.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: Outline Editing in Editor (In-Loop)
- User Value: Users can edit and confirm LLM-generated outlines without losing agent context.
- Acceptance: New outline-edit JSON tag/payload is recognized. The editor opens with the outline text; Submit/Save sends edited outline to the LLM (Save includes file path note), Discard keeps original, Abandon interrupts, Cancel stays in editor. Uses configured editor mode.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: /edit Command for Local Files
- User Value: Users can open and edit workspace text files in the markdown editor, optionally sending saved content to the LLM.
- Acceptance: `/edit <path>` opens an existing or newly created text file (prompting on missing). Only plain-text extensions are allowed. Return dialog offers Save/Submit/Save As/Save As + Submit/Discard/Cancel. Submit saves first, prompts for a message, and sends `<prompt> @<saved_path>` to the LLM. Works for relative paths, subdirectories, and absolute paths inside the workspace.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

## Release 0.9.12

### Story 1: Permission Pipeline Uses `can_use_tool` Only
- User Value: Users get consistent permission gating because tool allow/deny flows run through the permission callback rather than a static allowlist.
- Acceptance: When `can_use_tool` is set, `allowed_tools` is not set in `ClaudeAgentOptions`; the permission callback decides which tools proceed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Tool Permissions for Outside Access and Deletes
- User Value: Users are prompted before the agent reads/writes outside the workspace or deletes workspace files.
- Acceptance: `Read/Write/Edit` require permission for paths outside workspace (including `~/.dogent`); `rm/rmdir/del/mv` inside workspace always prompt unless the target is whitelisted (e.g. `.dogent/memory.md`).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: Protect Existing `.dogent` Files
- User Value: Users must approve any modification to existing `.dogent/dogent.md` or `.dogent/dogent.json`.
- Acceptance: If these files exist, tool-based `Write/Edit` and Bash redirections prompt for permission; first-time creation does not prompt.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: CLI Authorization for `.dogent` Updates
- User Value: CLI actions cannot overwrite `.dogent/dogent.md` or `.dogent/dogent.json` without explicit approval.
- Acceptance: CLI writes to existing `.dogent/dogent.md` or `.dogent/dogent.json` prompt for authorization each time and skip updates on denial; first-time creation proceeds without prompts.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 5: Permission Prompt UX Defaults to Yes
- User Value: Permission prompts are fast to approve and do not leak raw escape sequences while selecting.
- Acceptance: Permission prompts default to yes and allow up/down selection when prompt_toolkit is available; text fallback remains when it is not.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual interactive test (CLI).

---

## Release 0.9.13

### Story 1: Resource Layout & Loader Consolidation
- User Value: Configs, templates, and schemas live in predictable locations with a single loader, reducing confusion and duplicate logic.
- Acceptance: `dogent/templates` is renamed to `dogent/resources`; `dogent/resources/doc_templates` content moves to `dogent/templates`; schemas live under `dogent/schema/workspace` and `dogent/schema/global` (same content); `dogent/schemas/clarification.schema.json` moves under `dogent/schema/`; all loads go through one resource loader.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Complex Multi-line Prompts Externalized
- User Value: Prompts are easier to audit and update without touching code.
- Acceptance: Only complex multi-line prompts are moved into `dogent/prompts/` files with content unchanged; short prompts stay inline; runtime loads via the centralized loader.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: CLI Module Split
- User Value: The CLI codebase is easier to maintain and extend without cross-cutting edits.
- Acceptance: `dogent/cli.py` and related CLI helpers are split into the `dogent/cli/` package per the design; CLI behavior remains unchanged; imports/tests updated.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: Agent/Config/Core/Feature Modules Split
- User Value: Core services and feature modules are clearly separated, reducing coupling and duplication.
- Acceptance: `dogent/agent`, `dogent/config`, `dogent/core`, and `dogent/features` packages are created per the design; public entrypoints remain stable; tests updated.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 5: Panels + English Documentation Refresh
- User Value: Users see a concise startup panel, an expanded help panel, and complete English documentation.
- Acceptance: Startup panel is minimal; help panel documents end-to-end usage; `docs/dogent_design.md` added with mermaid diagrams; `docs/usage.md` rewritten in English with step-by-step examples.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual review of panels/docs.

---

## Release 0.9.14

### Story 1: DOCX Export Embeds Markdown Images
- User Value: Users get DOCX exports that include all local images referenced in Markdown or HTML.
- Acceptance: Markdown and HTML image references (relative or absolute local paths) appear in the DOCX output; width/height/style attributes are preserved where possible; code blocks and tables render correctly with a syntax-highlighted theme; conversion uses a normalized Markdown copy and proper resource paths.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Startup Panel Simplified + Markdown Help Panel
- User Value: Startup UI is concise while help remains comprehensive and readable.
- Acceptance: Startup panel shows name/version, model/profile info, and 1-2 key reminders only; `/help` renders Markdown directly in the normal CLI panel.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI review.

### Story 3: English End-to-End Usage Guide
- User Value: New users can install, configure, and use Dogent with step-by-step examples.
- Acceptance: `docs/usage.md` is fully rewritten in English with end-to-end flow (install -> configure -> run -> tools/templates -> permissions -> troubleshooting) and includes examples.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Doc review.

---

## Release 0.9.15

### Story 1: XLSX Multi-Sheet Markdown Export
- User Value: Users can convert entire XLSX files into a single Markdown output without manually listing sheets.
- Acceptance: When `sheet` is omitted, output uses the full filename stem as H1 and includes all sheets in order with H2 sheet titles, blank lines between sheets, and per-sheet truncation notes; when `sheet` is specified, behavior remains single-sheet; `convert_document` supports XLSX -> Markdown.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Windows Terminal Parity
- User Value: Windows users get the same non-blocking input, selection prompts, and escape handling as Unix users.
- Acceptance: Terminal functions use Windows console modes with proper get/set/restore; escape listener works; selection prompts and key handling are stable on Windows.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual Windows CLI run + unit tests (mocked).

### Story 3: Full/Lite Packaging for Pandoc + Playwright
- User Value: Users on poor networks can run conversions without runtime downloads by installing a full package build.
- Acceptance: `DOGENT_PACKAGE_MODE=full` uses bundled pandoc and Playwright Chromium under `dogent/resources/tools/...` without downloading; `lite` retains download-on-demand; missing bundled tools raise clear errors.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Unit tests for path resolution + manual packaging smoke.


---

## Release 0.9.16

### Story 1: Load Claude Commands into CLI
- User Value: Use project/user `.claude/commands` from Dogent with completion and help.
- Acceptance: `/help` lists Claude commands; tab completion includes them; unknown slash commands still error.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run in a workspace with `.claude/commands/*.md`.

### Story 2: Resolve Slash Command Conflicts
- User Value: Claude commands are clearly namespaced in Dogent CLI.
- Acceptance: All Claude commands (project + user + plugin) appear as `/claude:<name>` and forward to the underlying Claude command.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run with a conflicting command file.

### Story 3: Load Claude Plugins from Workspace Config
- User Value: Enable local Claude plugins configured per workspace.
- Acceptance: `.dogent/dogent.json` plugin paths are validated and passed to SDK; invalid entries warn and are skipped.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run with a valid plugin directory and an invalid one.

### Story 4: SDK Settings for Claude Assets
- User Value: Dogent loads project and user-level Claude assets (commands/agents/skills).
- Acceptance: SDK options include `setting_sources=["user","project"]`; skills/subagents work when configured.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for options; manual run with `.claude/skills` and `.claude/agents`.

---

## Release 0.9.17

### Story 1: Profile Command & Config Updates
- User Value: Users can list and switch `llm_profile`, `web_profile`, and `vision_profile` from the CLI without editing JSON manually.
- Acceptance:
  - `/profile` shows current selections only (no interactive prompt).
  - `/profile llm|web|vision` lists available profiles from `~/.dogent/dogent.json` plus defaults; vision shows `none` only when no profiles exist and writes `null`.
  - `/profile llm <name>` (or web/vision) persists the selection; CLI completion lists values after a trailing space.
  - `/profile show` displays current selections and available profile keys in a Rich table.
  - Changing a profile writes `.dogent/dogent.json` and resets the active agent session.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for profile selection + config write; manual CLI check for `/profile`.

### Story 2: Debug Command & Config Normalization
- User Value: Users can enable logging with presets or custom choices via `/debug` and see the persisted config.
- Acceptance:
  - `/debug` shows the current debug configuration (no selection prompt).
  - `/debug <option>` persists `debug` as `null`, `"session"`, `"error"`, `"warn"`, `"info"`, `"debug"`, `"all"`, or `["session","error"]` as specified.
  - `off` (or `null/none`) writes `null`; `custom` opens the interactive selector (session on/off + level).
  - Level priority enforced: `error > warn > info > debug`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for debug normalization and command output; manual CLI check for `/debug`.

### Story 3: Logging Output + Instrumentation
- User Value: Logs help diagnose issues with clear structure and event levels in a single session file.
- Acceptance:
  - Log file stored in `.dogent/logs/dogent_session_<timestamp>.md`.
  - Entries are ordered newest to oldest, clearly labeled by `session` vs level, and group non-session logs around the same interaction period.
  - Exceptions and user-facing errors across CLI/config/features are logged when enabled.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for log output ordering and type tagging; manual run that triggers an error and confirms log entry.

### Story 4: Document Read Offsets
- User Value: Long documents can be read in segments via `mcp__dogent__read_document`.
- Acceptance:
  - Tool schema supports `offset` and `length`; `length` overrides `max_chars`.
  - Tool response includes paging metadata (`total_chars`, `next_offset`, `offset`, `returned`).
  - Reading with offsets returns the correct segment without failing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for offset/length slicing; manual tool call with offset + length.

---

## Release 0.9.18

### Story 1: Non-Interactive Prompt Mode
- User Value: Users can run a one-shot prompt via `dogent -p` (with optional `--auto`) and get a clear exit status.
- Acceptance:
  - `dogent -p "prompt"` runs without entering the interactive loop and auto-initializes defaults if needed.
  - Default `-p` fails fast on permission requests or clarifications, returning distinct non-zero exit codes and error text.
  - `dogent -p "prompt" --auto` auto-approves permissions and auto-skips clarifications, still erroring on outline edits/awaiting input.
  - Successful runs print a fixed `Completed.` line after the normal agent summary.
  - Exit codes map to run outcomes as designed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for argument parsing + exit-code mapping; manual one-shot run with/without `--auto`.

### Story 2: Authorization Persistence + dogent.json Exceptions
- User Value: Users can persist tool authorizations in `.dogent/dogent.json`, and config edits are not blocked by permission prompts.
- Acceptance:
  - `.dogent/dogent.json` supports an `authorizations` map of tool -> path patterns (wildcards allowed).
  - Interactive permission prompts include “allow + remember” and record all relevant paths under the tool key.
  - Stored authorizations apply to all permission types in `dogent/agent/permissions.py`.
  - CLI command edits and agent tool edits to `.dogent/dogent.json` no longer prompt for permission.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for authorization matching + recording; manual permission prompt record and reuse.

 
---

## Release 0.9.19

### Story 1: Image Generation Profiles + CLI Selection
- User Value: Users can configure image generation providers and select them via `/profile` without editing JSON manually.
- Acceptance:
  - Global config supports `image_profiles` in `~/.dogent/dogent.json`; workspace config supports `image_profile`.
  - `/profile image` lists available image profiles; `/profile image <name>` updates `.dogent/dogent.json`.
  - `/profile show` includes Image profile, and the banner shows the current image profile.
  - If no image profiles exist, `none` sets `image_profile` to `null`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT passed in dev/sprint_uat.md.

### Story 2: Image Generation Tool
- User Value: The agent can generate images via a tool and save them in the workspace.
- Acceptance:
  - New tool `mcp__dogent__generate_image` with params `prompt`, `size` (default `1280x1280`), `watermark_enabled` (default true), `output_path` (optional).
  - Validates `size` as `WxH` within 512-2048 and multiples of 32.
  - Missing `output_path` saves to `./assets/images/dogent_image_<timestamp>.<ext>`; extension derived from response content type, fallback `.png`.
  - Downloads the returned URL and writes to the workspace; returns the URL and saved path in tool output.
  - Missing or placeholder API key returns a clear config error referencing `image_profiles`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT passed in dev/sprint_uat.md.

---

## Release 0.9.20

### Story 1: Dependency Precheck + Manual Install Guidance for Document Tools
- User Value: Users immediately see missing dependencies for document tools and clear OS-specific manual install steps instead of waiting.
- Acceptance:
  - Before `mcp__dogent__export_document`, `mcp__dogent__read_document`, and `mcp__dogent__convert_document` run, Dogent checks required dependencies for the target format(s).
  - If dependencies are missing in interactive mode, Dogent prompts with Install now / Install manually / Cancel.
  - Choosing Install manually aborts the task and shows OS-specific install commands for each missing dependency.
  - Document IO no longer auto-downloads dependencies without user confirmation.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT in dev/sprint_uat.md.

### Story 2: Auto-Install with Progress + Continue Execution
- User Value: Users can let Dogent install missing dependencies with visible progress and continue the tool automatically.
- Acceptance:
  - Choosing Install now runs per-dependency installers with percent progress; non-pip installs show separate Download and Install bars (pip installs may be single-phase).
  - Downloads are cached under `~/.dogent/cache` for pip installs; Playwright Chromium uses its default cache location.
  - In noninteractive mode, Dogent auto-installs missing dependencies; on failure, it exits with manual install instructions.
  - After successful install, the tool proceeds without requiring re-run.
  - ESC during download/install shows ⛔ Interrupted and manual instructions; install-phase interrupts mention the download location.
  - Download/install failures show ❌ Failed and exit the current run.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT pending retest in dev/sprint_uat.md.
