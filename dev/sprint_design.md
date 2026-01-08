# Design

---

## Release 0.9.12

### Goals
- Require permission for tool access outside the workspace root (including `~/.dogent`) for `Read/Write/Edit`.
- Require permission for any deletion inside the workspace except explicit whitelist entries.
- Require permission for modifying existing `.dogent/dogent.md` and `.dogent/dogent.json` across all write paths (tool and CLI).
- Keep the agent session alive while awaiting permission; deny -> abort current task.

### Current Behavior (Summary)
- `should_confirm_tool_use` only guards `Read/Write/Edit` and `Bash/BashOutput`.
- `allowed_roots` includes workspace root and `~/.dogent`, so global access is treated as allowed.
- Delete confirmation uses `rm/rmdir/del` parsing; whitelist supports `.dogent/memory.md`.
- `permission_mode` defaults to `"default"` when a permission callback is supplied.
- CLI writes to `.dogent/dogent.md` and `.dogent/dogent.json` happen without a permission prompt.

### Proposed Changes
1) Permission rules (tool-driven)
   - Outside workspace:
     - Prompt for `Read/Write/Edit` when target path is outside workspace root.
     - This includes `~/.dogent` (treated as outside), and any absolute/relative path not under root.
   - Deletions inside workspace:
     - Continue prompting for delete commands (`rm/rmdir/del/mv`) inside the workspace,
       except whitelisted paths (e.g. `.dogent/memory.md`).
   - `.dogent/dogent.md` / `.dogent/dogent.json` protection:
     - If the file already exists, any modification (Write/Edit or Bash redirection)
       must prompt before proceeding.
     - First creation does not require the special prompt.

2) Tool coverage updates
   - Keep `should_confirm_tool_use` scoped to `Read/Write/Edit` and `Bash/BashOutput`.
   - Treat `~/.dogent` as outside by limiting allowed roots to workspace only.

3) Path detection
   - Reuse `_extract_file_path` for `Read/Write/Edit` tool inputs.
   - For Bash commands, keep `rm/rmdir/del` parsing and add `mv`.
   - Extend detection to notice redirections to existing `.dogent/dogent.md` /
     `.dogent/dogent.json` for modification prompts.

4) Permission flow
   - Keep the existing permission prompt mechanism and abort-on-deny logic.
   - Ensure the wait indicator stops during prompt and resumes after; do not disconnect
     the client while awaiting a response.
   - When `can_use_tool` is set, do not set `allowed_tools`. Allowlist decisions live
     inside `can_use_tool` (return `PermissionResultAllow` for always-allowed tools).
   - Keep the text prompt fallback for non-TTY/non-prompt_toolkit environments.
   - Use the existing "Aborted" panel/status on denial.

5) CLI-initiated file updates
   - Before overwriting existing `.dogent/dogent.md` or `.dogent/dogent.json`,
     prompt for authorization using the same yes/no UI.
   - First-time creation does not require authorization.

### Tests to Add/Update
- `tests/test_tool_permissions.py`:
  - `~/.dogent` treated as outside (prompt required).
  - Existing `.dogent/dogent.md` / `.dogent/dogent.json` write via `Write/Edit` requires confirmation.
  - Bash redirection to existing `.dogent/dogent.md` requires confirmation.
  - Bash `mv` delete-like operations prompt for confirmation when inside workspace.
  - Creation of `.dogent/dogent.md` / `.dogent/dogent.json` when missing does not trigger the special prompt.

- `tests/test_cli_permissions.py` (new):
  - Overwriting existing `.dogent/dogent.md` via `/init` or editor path prompts for approval.
  - Updating `.dogent/dogent.json` via CLI toggles prompts for approval.
  - First-time creation of `.dogent/dogent.md` / `.dogent/dogent.json` does not prompt.

---

## Release 0.9.13

### Goals
- Decide the target module layout and physical directory layout, keeping duplication low.
- Split oversized modules (especially `dogent/cli.py`) into cohesive, reusable subpackages.
- Externalize only complex multi-line prompts into files loaded at runtime.
- Reorganize package layout: move JSON schemas under `dogent/schema/` (workspace/global subdirs),
  rename `dogent/templates` to `dogent/resources`, and move document templates into `dogent/templates/`.
- Simplify startup panel content; expand help panel with comprehensive feature guidance.
- Add new architecture/design documentation and rewrite usage docs in English.

### Current Behavior (Summary)
- `dogent/cli.py` mixes command registry, input handling, editor UI, panels, and run loop logic in one large module.
- Some complex multi-line prompt strings (e.g., lesson drafting system prompts) are embedded in code.
- Templates live under `dogent/templates/` with `doc_templates/` nested inside.
- Schema JSON lives under `dogent/templates/` and `dogent/schemas/`, not under a unified schema directory.
- Startup panel includes verbose messaging; help panel is succinct.
- `docs/usage.md` and system design documentation are incomplete for end-to-end onboarding.

### Target Module Layout (Decided)
- `dogent/cli/` (interactive CLI surface)
  - `app.py`: `DogentCLI` orchestration + run loop (from `dogent/cli.py`).
  - `commands.py`: command registry and handlers (from `dogent/commands.py` + CLI portions).
  - `input.py`: prompt_toolkit session + fallback input helpers (from `dogent/terminal.py` + CLI portions).
  - `editor.py`: multiline editor + preview (from `dogent/outline_edit.py` + CLI portions).
  - `panels.py`: startup/help panels and formatting helpers (from `dogent/cli.py`).
  - `wizard.py`: init wizard flow (from `dogent/init_wizard.py`).
- `dogent/agent/` (LLM streaming and permission handling)
  - `runner.py`: `AgentRunner` (from `dogent/agent.py`).
  - `permissions.py`: tool permission policy/callbacks (from `dogent/tool_permissions.py`).
  - `wait.py`: `LLMWaitIndicator` (from `dogent/wait_indicator.py`).
- `dogent/config/` (config + resource loaders)
  - `manager.py`: `ConfigManager` (from `dogent/config.py`).
  - `paths.py`: `DogentPaths` (from `dogent/paths.py`).
  - `resources.py`: centralized loader for configs/prompts/schema via `importlib.resources`.
- `dogent/features/` (domain features, grouped to avoid many tiny packages)
  - `clarification.py` (from `dogent/clarification.py`).
  - `document_io.py` (from `dogent/document_io.py`).
  - `document_tools.py` (from `dogent/document_tools.py`).
  - `doc_templates.py` (from `dogent/doc_templates.py`).
  - `lesson_drafter.py` (from `dogent/lesson_drafter.py`).
  - `lessons.py` (from `dogent/lessons.py`).
  - `vision.py` (from `dogent/vision.py`).
  - `vision_tools.py` (from `dogent/vision_tools.py`).
  - `web_tools.py` (from `dogent/web_tools.py`).
- `dogent/core/` (shared utilities)
  - `file_refs.py` (from `dogent/file_refs.py`).
  - `history.py` (from `dogent/history.py`).
  - `session_log.py` (from `dogent/session_log.py`).
  - `todo.py` (from `dogent/todo.py`).
- Keep public entrypoints stable by re-exporting in `dogent/__init__.py`.

### Physical Directory Layout (Decided)
- `dogent/resources/` (strict rename, content unchanged)
  - `dogent_default.md`, `dogent_default.json`, `dogent_global_default.json`, `pdf_style.css`.
- `dogent/templates/` (document templates, strict rename)
  - Move from `dogent/templates/doc_templates/*` to `dogent/templates/*` (same content).
- `dogent/schema/`
  - `workspace/dogent.schema.json` (from `dogent/templates/dogent_schema.json`, unchanged).
  - `global/dogent.schema.json` (same content as workspace schema to satisfy scope split).
  - `clarification.schema.json` (from `dogent/schemas/clarification.schema.json`, unchanged).
- Keep `dogent/prompts/` as the single prompt directory; no new resource root to avoid duplication.
- Reduce duplication in code by using `config/resources.py` for all config/template/schema loads.

### Prompt Extraction (Scope)
- Only extract complex multi-line prompts into `dogent/prompts/`.
- Keep short/one-line prompts inline.
- Copy extracted prompt text verbatim (no content edits beyond file move).

### Startup/Help Panel Refactor
- Startup panel: keep minimal intro (usage hint + safety reminders).
- Help panel: expand with end-to-end workflow, commands, permissions model,
  config locations, and troubleshooting tips.

### Documentation
- Add `docs/dogent_design.md`:
  - Mermaid diagrams for logical and physical architecture.
  - Main responsibilities and module boundaries.
- Rewrite `docs/usage.md`:
  - English-only, step-by-step end-to-end usage with examples.

### Migration/Implementation Notes
- Use a staged refactor to minimize churn:
  1) Move resources (resources/templates/schema) and update loaders.
  2) Extract prompts into files and add template loader.
  3) Split `cli.py` into submodules and update imports/tests.
  4) Split agent/config/tools modules and update imports/tests.
- Ensure `pyproject.toml` package data includes new resource paths.
- Update tests for new import paths and any renamed resources.

### Tests to Add/Update
- Update unit tests that import `DogentCLI`, `ConfigManager`, `DogentPaths`, and tool modules.
- Add tests for new template loader (reading prompt/config files from new paths).
- Smoke test for help/startup panel output (if CLI snapshot tests exist).
