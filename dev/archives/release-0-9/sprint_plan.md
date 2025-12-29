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
