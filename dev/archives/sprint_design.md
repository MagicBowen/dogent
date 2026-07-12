# Design

## Release 0.9.1

### Goals
- Read @file references for .pdf, .docx, and .xlsx.
- Export .pdf/.docx when user specifies format in prompt or "Output Format" in .dogent/dogent.md.
- Keep behavior text-only for PDFs; fail fast for scanned/unsupported PDFs.

### Decisions
- DOCX read uses pandoc (tracked changes fidelity).
- PDF read uses PyMuPDF (fitz) text extraction.
- XLSX read uses openpyxl; default to first sheet unless user names one.
- PDF export uses Markdown -> HTML (markdown-it-py) -> Playwright/Chromium print.
- DOCX export uses pypandoc + pandoc.
- Dependencies installed by default in pyproject.

### Architecture
- Add `dogent/document_io.py` for format detection and conversion.
- `read_document(path, ...)` returns Markdown text + metadata.
- `export_markdown(md_path, target_format, target_path)` handles docx/pdf generation.
- `FileAttachment` stores only the referenced path (and optional sheet); no content is attached.
- `FileReferenceResolver` only extracts referenced file paths (no content), so the LLM must call document MCP tools to read.
- User prompt lists referenced file paths only; no attachment content or output format is embedded.
- Output conversion is performed by the LLM via MCP tools (no host-side auto-export).

### MCP Tool Integration
- Add `dogent/document_tools.py` with MCP tools:
  - `read_document` (inputs: `path`, optional `sheet`, optional `max_chars`)
  - `export_document` (inputs: `md_path`, `output_path`, `format`)
- Tools call the same functions in `document_io` to avoid duplicate logic.
- Register an in-process MCP server via `create_sdk_mcp_server` and include tools in `allowed_tools`.
- Update `ConfigManager.build_options` to include both web and document MCP servers when applicable.
- Extend tool display name mapping so CLI panels show friendly names for the new tools.

### Attachment Handling
- Attachment list includes only `@file` references (and `#SheetName` when provided).
- The LLM calls `read_document`:
  - PDF read: if all pages return empty text, return tool error "Unsupported PDF: no extractable text (scanned PDF not supported)."
  - XLSX read: default to first sheet; allow `sheet` parameter to pick a named sheet.
  - Apply size limit after conversion to Markdown, not before.

### Export Flow
- The LLM determines requested output format from the user prompt or `.dogent/dogent.md`.
- If export is required:
  - Write Markdown to a .md file.
  - Call `export_document` with `md_path`, `output_path`, and `format`.
  - If output path is not specified, derive it from the Markdown file name.
- Conversion errors are returned via tool error responses.

### Dependencies
- Core dependencies: pypandoc, pymupdf, openpyxl, markdown-it-py, playwright.
- Runtime bootstrapping:
  - `pypandoc.download_pandoc()` on demand.
  - `python -m playwright install chromium` on first PDF export.

### Tests
- Unit tests for reading: pdf (text), pdf (no text -> error), docx, xlsx (first sheet + named sheet).
- Unit tests ensure user prompts list `@file` references but not file contents.
- Export tests with mocks for pandoc/playwright to avoid heavy binaries in CI.

## Release 0.9.2

### Goals
- Keep user prompts lean by only listing core file info for attachments (path/name/type).
- Expose vision analysis via an MCP tool so the agent can call it on demand.
- Support multiple vision providers via profiles, configurable in workspace config, with only GLM-4.6V implemented initially.
- Fail fast on vision analysis errors with a user-friendly message.
- No local caching for media analysis.

### Decisions
- Add `vision_profile` to `.dogent/dogent.json` and a new global config file `~/.dogent/vision.json`.
- Default `vision_profile` to `glm-4.6v` in the template; if the profile is missing or has placeholder credentials, the vision tool returns a clear configuration error.
- Implement a provider registry with a `VisionClient` interface; only `glm-4.6v` is wired initially.
- Attachments in the user prompt include only JSON file metadata; media content is accessed via the vision MCP tool.

### Architecture
- Add `dogent/vision.py`:
  - `VisionProfile` dataclass with fields: `provider`, `model`, `base_url`, `api_key`, optional `extra`.
  - `VisionClient` protocol: `analyze_image(path) -> dict`, `analyze_video(path) -> dict`.
  - `GLM4VClient` implementation using the BigModel chat completions API.
  - `VisionManager` loads profiles, validates placeholders, and dispatches to providers.
- Add `dogent/vision_tools.py`:
  - MCP tool `mcp__dogent__analyze_media` (inputs: `path`, optional `media_type`).
  - Tool resolves `vision_profile` from workspace config and calls `VisionManager`.
- Extend `DogentPaths` to include `global_vision_file` (`~/.dogent/vision.json`).
- Extend `ConfigManager` to:
  - Create `vision.json` template on first run with a `glm-4.6v` profile stub.
  - Normalize `vision_profile` in project config.
- Attachment handling:
  - Attachments only list metadata (path/name/type); no media content in the user prompt.

### Vision Request/Response Contract
- For GLM-4.6V, use `POST https://open.bigmodel.cn/api/paas/v4/chat/completions`.
- Request uses `image_url` or `video_url` with base64 data URLs for local files.
- The prompt instructs the model to return strict JSON only, with a single summary field:
  - Example response:
    ```
    {"summary": "...", "tags": ["..."], "text": "..."}
    ```
- Parse JSON strictly; if parsing fails or the API returns an error, fail the user request with guidance.

### Prompt Injection
- Update the user prompt attachments section to emit JSON metadata only, e.g.:
  ```
  [
    {"path": "assets/photo.png", "name": "photo.png", "type": "png"},
    {"path": "clips/demo.mp4", "name": "demo.mp4", "type": "mp4"}
  ]
  ```
- If no attachments exist, emit an empty array.

### Failure Behavior
- If a media file needs analysis and the MCP tool fails:
  - The tool returns an error payload describing how to fix `vision_profile` or credentials.
  - System prompt instructs the agent to stop and ask the user to fix config.
- No retries or caching in 0.9.6.

### Tests
- Config tests for `vision_profile` defaults and tool registration.
- Unit tests for attachment JSON formatting (no media content).
- Vision manager tests with mocked responses and a tool handler test.

## Release 0.9.3

### Goals
- Require explicit user confirmation before any tool reads or writes outside the workspace.
- Require explicit confirmation before delete commands that target files (inside or outside the workspace).
- Denied confirmations must abort the run with a clear "aborted" status and reason.
- Treat `~/.dogent/*` as inside for permission checks.

### Decisions
- Gate only built-in tools: `Read`, `Write`, `Edit`, and `Bash`.
- Detect delete operations only for explicit `rm`, `rmdir`, and `del` commands.
- Use the Claude Agent SDK `PreToolUse` hook to enforce confirmations before tool execution.
- Show an inline yes/no selector during prompts (left/right + Enter, default highlighted) to avoid full-screen dialogs.

### Architecture
- Add `dogent/tool_permissions.py` for:
  - Parsing tool inputs and bash commands.
  - Resolving paths and checking allowed roots.
  - Determining whether a confirmation is required and returning a human-readable reason.
- Extend `AgentRunner` to:
  - Register a `PreToolUse` hook and invoke the permission prompt.
  - Track `_aborted_reason` and render a `🛑 Aborted` summary when denied.
- Extend `DogentCLI` to:
  - Provide an inline yes/no selector for permission prompts and lesson capture prompts.
  - Pause the Esc listener while prompts are active.

### Failure Behavior
- On denial: the tool call is blocked, the run ends with status `aborted`, and history records the reason.
- On approval: the run continues normally with no other side effects.

### Tests
- Unit tests for `should_confirm_tool_use` and delete target parsing.
- Coverage for inside/outside path checks and delete detection.


## Release 0.9.4
- Unified global config
  - Merge `claude.json`, `web.json`, and `vision.json` into `~/.dogent/dogent.json`.
  - New global structure: `version`, `workspace_defaults`, `llm_profiles`, `web_profiles`, `vision_profiles`.
  - On startup, compare config `version` with Dogent version; if older, merge missing keys from defaults without overwriting existing settings and update `version`.
  - If config `version` is newer than Dogent, warn the user.
  - Workspace `.dogent/dogent.json` continues to select profiles via `llm_profile`, `web_profile`, `vision_profile`.
  - Update warnings/errors/docs to reference the unified config file.

- Configuration layering
  - Add global config path `~/.dogent/dogent.json` (new `DogentPaths.global_config_file`).
  - Resolve config in order: built-in defaults -> global config -> workspace `.dogent/dogent.json`.
  - Keep local overrides scoped to the current workspace; only merge missing keys from global/defaults.
  - Normalize `web_profile`, `vision_profile`, `doc_template`, `primary_language`, `learn_auto` after merge.
  - `load_settings()` continues to use env fallback when `llm_profile` is unset in the merged config.
  - `create_config_template()` uses global config (if present) as defaults; otherwise uses packaged defaults.

- Vision profile `null`
  - Change default `vision_profile` to `null` (config normalization + `dogent/templates/dogent_default.json`).
  - When `vision_profile` is missing or `null`, do not register vision MCP tools or allow `mcp__dogent__analyze_media`.
  - Add a fast failure when the user references image/video attachments while vision is disabled.
  - Update CLI help/banner and system prompt copy to reflect when vision is unavailable.

- Temporary doc template selection in prompt
  - Introduce a template selector token (symbol `@@`) that triggers prompt-toolkit completion with template names.
  - Parse the token from user input, apply the selected `doc_template` for that request only, and avoid persisting to config.
  - Inject the override into prompt rendering (system + user prompt) by passing a per-call config override.

- Tests and docs
  - Add tests for global/local config merge, default vision_profile behavior, and vision tool registration.
  - Add tests for prompt-level doc_template override parsing and rendering.
  - Update usage docs to describe global config, vision_profile default, and template selector token.

- Decisions
  - Template selector token: `@@`; strip the token from the user message before sending to the LLM.
  - Auto-create `~/.dogent/dogent.json` on first run; omit `llm_profile` unless the user sets it (env fallback remains).
  - If `vision_profile` is missing or `null` and the user references image/video attachments, block the request with a fail-fast error panel.

---

## Release 0.9.5
- PDF style override support
  - Introduce a `pdf_style.css` template file under `dogent/templates/` with the current default CSS.
  - On first startup, bootstrap `~/.dogent/pdf_style.css` if missing (global default).
  - Workspace override: use `.dogent/pdf_style.css` when it exists; otherwise fall back to global, then built-in.
  - Do not auto-create workspace `pdf_style.css`; only use it when the user adds it.
  - Expand the default CSS with readable comments, code block highlighting, and header/footer styling hooks.
  - Enable header/footer + page numbers in PDF export via Playwright templates.

- PDF rendering pipeline
  - Update Markdown -> HTML to accept injected CSS text.
  - Add a resolver to locate and read the style file in the priority order above.
  - Apply the resolved CSS to all Markdown -> PDF conversions (including DOCX -> PDF via MD).
  - If a style file is unreadable, fall back to the next source and surface a warning to the user.

- Tests and docs
  - Add unit tests for style precedence, missing styles fallback, and unreadable style warnings.
  - Document CSS locations and precedence in README.

- Template override in user prompt
  - Keep `@@<template>` as the selector but do not inject the selected template into the system prompt.
  - Clear the system prompt template content when an override is present (no template content in system prompt).
  - Resolve the selected template content and append it to the user prompt as a distinct "Template Remark" section.
  - Update system prompt instructions to prioritize the user prompt template remark over `.dogent.json`/`.dogent.md`.
  - Add tests to ensure system prompt excludes the override template while the user prompt includes it.

- Graceful exit handling
  - Guard console output against `EPIPE`/broken pipe errors during `/exit`.
  - Catch broken pipe errors at CLI entrypoint to avoid tracebacks on exit.

---

## Release 0.9.8
- Structured clarification payloads
  - Update `dogent/prompts/system.md` to require a tagged JSON response whenever the model needs clarification.
  - Keep a dedicated tag to identify clarification payloads (e.g., `[[DOGENT_CLARIFICATION_JSON]]`), with a fallback to the existing sentinel `[[DOGENT_STATUS:NEEDS_CLARIFICATION]]` for backward compatibility.
  - JSON fields include: `title`, `preface`, and `questions[]` with `id`, `question`, `options[]`, `recommended`, `allow_freeform`, `placeholder`.
  - Add a JSON schema file for validation, stored under `dogent/schemas/clarification.schema.json` and loaded via `importlib.resources`.
  - Validate parsed JSON against the schema before entering the Q&A flow; on validation failure, fall back to the plain clarification text + sentinel handling.

- Q&A interface + flow
  - Add a dedicated Q&A UI in `dogent/cli.py` that:
    - Shows progress (`Question i/n`) and the total question count.
    - Presents multiple-choice answers with the cursor on `recommended` (or first option).
    - Supports optional free-form entry when `allow_freeform` is true.
    - Uses prompt_toolkit for interactive selection; falls back to numbered input if not available.
  - Use `Esc` to abort the Q&A flow without conflicting with the runtime Esc interrupt listener.
  - Enforce a timeout for each question based on `api_timeout_ms` from the active LLM profile. If unset, treat as no timeout.
  - On timeout or Esc abort, mark the run as aborted and close the agent session.

- Session continuity
  - When clarification is needed, keep the `ClaudeSDKClient` session open instead of disconnecting at the end of the first response.
  - After collecting answers, send a follow-up user message that concatenates Q/A as plain text (one block) and continue streaming within the same session.
  - Only disconnect after the follow-up response completes or the run is aborted.

- History updates
  - Record the clarification Q/A in `.dogent/history.json` by appending a history entry with a concise summary and the full Q/A block stored in `prompt`.
  - Continue to record a final outcome after the follow-up response as usual.

- Decisions
  - Clarification payload tag: `[[DOGENT_CLARIFICATION_JSON]]` (plus support for the existing `[[DOGENT_STATUS:NEEDS_CLARIFICATION]]` sentinel).
  - Default option selection: `recommended`, else first option.
  - Answer payload sent to the LLM: plain text Q/A block.

---

## Release 0.9.9

### UX consistency for confirmations
- Replace inline left/right yes-no prompt with the same up/down list UI used by clarification questions.
- Apply to all yes-no confirmations: overwrite dogent.md, save lesson, tool permission, start writing now, and initialize now.
- Esc cancels the entire flow (treat as hard cancel). Non-interactive fallback keeps y/n input.

### Esc listener and agent loop safety
- Pause or stop the Esc listener entirely while any selection UI is active, then restart after the prompt exits.
- Do not interrupt an active agent loop while waiting for a selection choice (tool permission or other in-flight prompts).

### Debug logging configuration
- Add `debug: false` to `.dogent/dogent.json` defaults and schema.
- Debug disabled when the key is missing.

### Session log format and scope
- When debug is enabled, create `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` in JSONL format.
- Each line is a JSON object with at least: `timestamp`, `role` (system|user|assistant|tool), `source`, `event`, `content`.
- Log all LLM calls: main agent, init wizard, and lesson drafter.
- Log system prompts once per source when changed (including template injection).
- Log every user prompt.
- Log assistant streaming blocks as they arrive (text, thinking, tool_use, tool_result), using role `assistant` for text/thinking/tool_use and role `tool` for tool_result.

### Init wizard flow change
- Only for `/init prompt` (wizard path): after config creation and overwrite decision, show a selection to start writing.
- If user selects Yes, construct a prompt:
  `The user has initialized the current dogent project, and the user's initialization prompt is "<prompt>". Please continue to fulfill the user's needs.`
  and start the writing agent immediately.
- If user selects No or presses Esc, finish init and return to the CLI prompt.

### Auto-init on first request without dogent.json
- On user request, if `.dogent/dogent.json` and `.dogent/dogent.md` are missing, ask whether to initialize.
- If Yes, run the wizard using the user request as the init prompt, then ask to start writing (same as above).
- If No, proceed with current default processing (send the request to the agent without init).
- If Esc, cancel the flow and return to the CLI prompt.

---

## Release 0.9.10

### Multiline Markdown editor for prompts and free-form answers
- Default input stays single-line for the main CLI prompt and free-form clarification answers.
- Add Ctrl+E to open a dedicated multiline editor (prompt_toolkit TextArea) for:
  - Main CLI prompt input (pre-filled with current buffer text).
  - Free-form clarification answers (including "Other (free-form answer)" and freeform-only questions).
- Selecting "Other (free-form answer)" in the clarification choice list opens the editor immediately.
- Editor UX:
  - Single editor view with lightweight, real-time Markdown rendering (syntax highlighting only; no layout changes).
  - Full preview toggle with Ctrl+P (read-only; toggle back to edit).
  - Multiline editing with standard prompt_toolkit shortcuts plus GUI-like bindings:
    - Word skip (Alt+Left/Right, Alt+B/F), line start/end (Ctrl+A/E), undo/redo (Ctrl+Z/Y).
    - Select word/line with Ctrl+W/Ctrl+L (footer lists fallback shortcuts).
  - Enter inserts new lines; Ctrl+Enter submits the editor content (fallback Ctrl+J shown in footer).
  - Ctrl+Q returns from the editor (Esc does not exit the editor).
  - Return behavior (dirty only): prompt to Discard / Submit / Save to file / Cancel.
    - Save prompts for a path (relative or absolute) and confirms overwrite when the file exists.
  - Footer shows prominent action labels and shortcut hints.
  - Dark theme with styled headings, code blocks, inline code, math spans, tasks, quotes, and table pipes.
  - Only save-on-return; no explicit save keybinding.
- While the editor is open, pause the Esc interrupt listener (reuse the same guard as selection prompts).
- Non-interactive fallback remains single-line text input with no editor.

## Release 0.9.11

### Debug logging to Markdown
- Remove `debug` from project/global default templates so new configs do not include it by default.
- Add `llm_profile: "default"` to project/global default templates to make ENV-backed behavior explicit.
- Keep runtime default `debug=false` in config normalization; only persist if user sets it.
- Session logs move to `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md`.
- Log events in chronological order. Each event includes timestamp, role, source, event name, and content in fenced blocks.
- System prompts are logged once per source if unchanged; user prompts logged per call.
- Capture streaming blocks (assistant text/thinking/tool use/tool result) as separate events.
- Add exception logging with message, traceback, and location, and call it from CLI/agent error paths.

### Editor mode config (default|vi)
- Add `editor_mode` to schema and config normalization; default to `default`.
- When `editor_mode=vi`, set `Application(editing_mode=EditingMode.VI)` for the editor.
- Show vi state in the footer (`VI: NORMAL/INSERT/REPLACE/VISUAL`) when in vi mode, plus the most common mode-specific shortcuts.
- Replace custom shortcut hints with vim-native hints in vi mode; keep non-vi shortcuts as secondary fallbacks only when needed.
- Provide a vim-style command line at the bottom of the footer (triggered by `:` in normal mode) for ex commands.

### Return dialog options and behavior (by scenario)
- Prompt input:
  - Discard: return to CLI without submitting.
  - Submit: return text to send to the agent.
  - Save & Submit: save, then return text to send to the agent.
  - Cancel: remain in editor.
- Clarification answers:
  - Discard: skip the question (same as "user chose not to answer").
  - Submit: return the answer text.
  - Save & Submit: save, then return the answer text.
  - Cancel: remain in editor.
- Outline editing:
  - Discard: continue with the original outline (send original text to LLM).
  - Submit: send edited outline to the LLM.
  - Save & Submit: save, then send edited outline plus file path to the LLM.
  - Cancel: remain in editor.
- /edit file editing:
  - Discard: exit without saving.
  - Save: write to the opened file path and exit (no LLM submission).
  - Submit: save and send the file content to the LLM.
  - Save As: write to a new path and exit (no LLM submission).
  - Save As + Submit: write to a new path, then send the file content to the LLM.
  - Cancel: remain in editor.
- Return dialog only appears when the buffer is dirty.

### Vim ex commands (map to return dialog semantics)
- The goal is to mirror the Ctrl+Q return dialog behavior via vim-native commands.
- Prompt input:
  - `:q` → return dialog if dirty; otherwise return without submitting.
  - `:q!` → discard and return to CLI.
  - `:w [path]` → save to file and keep editing.
  - `:wq` / `:x` → save (prompt for path if missing) and submit.
- Clarification answers:
  - `:q` → return dialog if dirty; otherwise skip.
  - `:q!` → skip (same as discard).
  - `:w [path]` → save to file and keep editing.
  - `:wq` / `:x` → save and submit answer.
- Outline editing (only when editing immediately):
  - `:q` → return dialog if dirty; otherwise discard edits and keep the original outline.
  - `:q!` → discard edits and keep the original outline.
  - `:w [path]` → save to file and keep editing.
  - `:wq` / `:x` → save and submit edits.
- /edit file editing:
  - `:q` → return dialog if dirty; otherwise exit.
  - `:q!` → discard and exit.
  - `:w [path]` → save (current path by default) and keep editing (no LLM submission).
  - `:wq` / `:x` → save (current path by default) and submit content to the LLM.

### Outline editing workflow (selection first)
- Extend the system prompt with a new outline edit response format:
  - Tag on first non-empty line: `[[DOGENT_OUTLINE_EDIT_JSON]]`
  - JSON payload (no code fences) with `response_type="outline_edit"`, `title`, and `outline_text`.
- Parse outline edit payloads in the agent (similar to clarification).
- When received, show a selection prompt (same UI as clarification choices):
  1) Adopt outline (continue writing with the current outline).
  2) Edit immediately (open the configured editor with the outline text).
  3) Save to file then edit (choose auto file name or input a file name).
- If “Adopt outline”: send a follow-up user message that approves the outline and continue.
- If “Edit immediately”: open the editor and then follow the normal outline-edit return behavior.
- If “Save to file then edit”: write the outline to disk and pause the current agent task; prompt the user to edit the file and resume writing later via the CLI.

### Editor-submitted content formatting (LLM + CLI display)
- Track when text is submitted from the multiline editor (prompt input, clarification answers, outline edits).
- When sending editor-submitted content to the LLM, wrap the edited text in a fenced Markdown code block using the `markdown` language tag to prevent it from affecting surrounding formatting.
- In CLI output, echo editor-submitted content as a standalone fenced code block only (no extra label) to visually separate it from surrounding text.
- For clarification summaries, wrap only the editor-entered answer text inside a code block (keep the question/labels as plain text).
- For prompt input Save-to-file, include the saved file path note along with the code-wrapped content (same pattern as outline edits).
- Apply consistent wrapping in all editor scenarios, while preserving scenario-specific metadata (e.g., outline file path notes).

### Preview scroll behavior
- Preview mode supports mouse wheel scrolling and keyboard navigation (Up/Down, PageUp/PageDown, Home/End) while staying read-only.

### /edit command (open text files)
- Add `/edit <path>` CLI subcommand; it opens a file in the configured markdown editor (default or vi).
- Completion: after `/edit `, show a dropdown of eligible text files (relative paths from workspace root). The list should allow navigating into subdirectories (directories shown with `/` suffix).
- Validation:
  - Path must resolve within the workspace root.
  - If the path does not exist, prompt the user to create it; on yes, create the file (and any missing parent directories) and open it empty.
  - When a path exists, it must be a file (not a directory).
  - Only allow plain-text extensions (default list: `.md`, `.markdown`, `.mdown`, `.mkd`, `.txt`).
  - If the file fails UTF-8 decode, treat it as unsupported and show an error.
- Editor semantics:
  - Save: writes to the original file path and exits (no LLM submission).
  - Save As: writes to a chosen path and exits (no LLM submission).
  - Submit: saves to the original file path (or a Save As path if chosen) and then asks the user for a prompt to send to the LLM. Compose the outbound prompt as: `<user prompt> @<saved_file_path>`.
  - Save As + Submit: saves to a chosen path, then asks for a prompt and sends `<user prompt> @<saved_file_path>`.
  - Discard exits without saving.
  - Cancel keeps editing.
  - Submit is allowed even if the buffer is unchanged.
  - Show a confirmation panel on save/discard with the target path.

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

---

## Release 0.9.14

### Goals
- Ensure Markdown -> DOCX conversion embeds local images referenced via Markdown or HTML.
- Simplify the startup panel to name/version, model/profile info, and 1-2 key reminders.
- Render `/help` as Markdown in the normal CLI panel (not editor preview).
- Rewrite `docs/usage.md` in English as a complete end-to-end guide with examples.

### Current Behavior (Summary)
- `_markdown_to_docx` calls pandoc with default Markdown parsing and no resource path;
  HTML `<img>` blocks and some relative image references are not embedded in DOCX.
- Startup panel contains verbose messaging.
- `/help` renders through the editor preview workflow instead of a normal CLI panel.
- `docs/usage.md` is incomplete for end-to-end onboarding.

### Proposed Changes
1) Markdown -> DOCX image handling
   - Preprocess Markdown before pandoc conversion:
     - Convert HTML `<img>` tags (including those nested in `<div align=...>`) into
       Markdown image syntax with Pandoc attribute blocks.
     - Parse and preserve all HTML attributes (including `width`, `height`, `style`,
       `alt`, `title`, `align`, `class`, `id`, and custom `data-*` attributes) by
       translating them into Pandoc image attributes where possible.
     - Extract width/height from `style` when present (e.g., `width:70%` or `width:240px`)
       and include as explicit `width`/`height` attributes alongside any remaining style.
     - Resolve local relative image paths against the Markdown file directory.
     - Allow absolute local paths; ignore remote URLs (leave unchanged or emit warning).
   - Run pandoc with explicit Markdown extensions:
     - Use `format="markdown+raw_html+link_attributes+pipe_tables+multiline_tables+grid_tables+fenced_code_blocks"`.
     - Supply `--resource-path` including the Markdown directory (and workspace root if available)
       to ensure relative image paths resolve correctly.
     - Keep `--standalone` for DOCX output.
     - Use a syntax highlight style (e.g. `--highlight-style=tango`) for code blocks.
   - Use a temporary normalized Markdown copy for conversion to avoid mutating user files.

2) Startup panel simplification
   - Reduce to a small header with:
     - Name + version.
     - Model/fast model and LLM profile.
     - Web/vision profile (if configured).
     - 1-2 reminders (proposed: `/help` for usage, `Esc` to interrupt).

3) Help panel rendering
   - Render `/help` as Markdown directly in the normal CLI panel.
   - Keep the help content in Markdown format to allow headings, lists, and code blocks.

4) Documentation rewrite
   - Rewrite `docs/usage.md` in English with end-to-end flow:
     - Install, initialize, run a task, use templates, attach files, use tools,
       permissions model, troubleshooting.
   - Ensure examples include CLI commands and expected outcomes.

### Tests to Add/Update
- `tests/test_document_io.py`:
  - Verify HTML `<img>` is converted into Markdown image syntax with attributes.
  - Verify style width/height extraction logic (percent and px).
  - Mock `pypandoc.convert_file` to assert `format` and `--resource-path` arguments.
- Add a small unit test for help rendering to confirm Markdown is passed into the panel
  (if a panel snapshot or render test pattern exists).

---

## Release 0.9.15

### Goals
- XLSX to Markdown: if no sheet is specified, include all sheets in one Markdown output with H1/H2 structure and per-sheet truncation notes.
- Windows terminal parity: ensure non-blocking input, selection prompts, and escape handling work on Windows without termios.
- Packaging modes: support "lite" (download-on-demand) and "full" (bundled pandoc + Playwright/Chromium) builds.

### Current Behavior (Summary)
- `_read_xlsx` reads only one sheet: the requested sheet or the first sheet.
- `dogent/cli/terminal.py` has Windows stubs but does not manage console modes; escape listener expects termios-like behavior.
- PDF/DOCX conversion tooling downloads pandoc/Chromium at runtime if missing.

### Proposed Changes
1) XLSX multi-sheet Markdown rendering
   - Keep current behavior when `sheet` is specified (single-sheet only).
   - When `sheet` is omitted:
     - Use the full filename stem (e.g., `report.v2.xlsx` -> `report.v2`) as the H1 title.
     - Iterate `workbook.sheetnames` in order.
     - For each sheet, emit:
       - `## <sheet name>`
       - The Markdown table (or `(empty sheet)`), followed by a truncation note if that sheet was capped.
     - Insert a blank line between sheet sections.
   - Metadata:
     - For multi-sheet reads, include `sheets` list and per-sheet metadata (rows/cols/truncated).
     - For single-sheet reads, keep current `sheet` + rows/cols metadata.
   - Update `dogent/prompts/system.md`: when no sheet is specified, read all sheets (not just the first).

2) Windows terminal parity
   - Implement Windows console mode handling in `dogent/cli/terminal.py`:
     - Use `ctypes` + `kernel32.GetConsoleMode/SetConsoleMode` to capture and restore console modes.
     - `tcgetattr` returns a settings object containing the original mode.
     - `setcbreak` disables line input/echo/processed input to allow immediate key reads.
     - `tcsetattr` restores the saved mode.
     - `kbhit/getch` remain `msvcrt`-based (prefer `getwch` for Unicode).
   - Ensure all low-level terminal usage remains centralized through `dogent/cli/terminal.py`.
   - Validate selection prompts and escape listener behavior on Windows.

3) Packaging mode: lite vs full
   - Add a build-time packaging mode indicator (e.g., `DOGENT_PACKAGE_MODE=full|lite`).
   - Full mode bundles:
     - Pandoc binaries
     - Playwright Chromium browser assets
     - Under `dogent/resources/tools/<tool>/<platform>/...`
   - Add resolver helpers in `dogent/features/document_io.py`:
     - `_resolve_pandoc_binary()` returns bundled pandoc in full mode, otherwise system/`pypandoc`.
     - `_resolve_playwright_browser_path()` points Playwright to bundled Chromium in full mode.
   - `*_ensure_*` helpers:
     - Full mode uses bundled assets and skips downloads.
     - Lite mode retains current download-on-demand behavior.
   - Update packaging config (`pyproject.toml`) to include `dogent/resources/tools/**`.

### Tests to Add/Update
- `tests/test_document_io.py`:
  - Multi-sheet XLSX produces H1 + H2 structure, blank lines between sheets, and per-sheet truncation notes.
  - When `sheet` is specified, output remains single-sheet.
  - Metadata includes `sheets` + per-sheet rows/cols/truncated for multi-sheet reads.
- Add platform-guarded tests for terminal helpers (mock `msvcrt` and `ctypes` to validate Windows-path code without requiring Windows).
- Add tests for packaging mode resolution helpers (full vs lite) using environment patching and temp bundled paths.

---

## Release 0.9.16

### Goals
- Load project and user-level Claude assets (commands, agents, skills) from `.claude`.
- Register Claude custom slash commands into Dogent CLI with a `/claude:` prefix.
- Support Claude plugins configured from `.dogent/dogent.json`.
- Expose Claude commands/plugins in `/help` and tab completion.

### Assumptions
- SDK settings are loaded with `setting_sources=["user", "project"]`.
- Strict command handling remains: unknown slash commands are errors unless registered.
- Claude commands always use `/claude:<name>` to avoid conflicts.

### UX behavior
- At startup, scan `.claude/commands` in project and user scope and register as `/claude:<name>`.
- `/help` and completions list built-ins plus Claude commands (including aliased ones).
- Unknown slash commands remain an error (no auto-forward).

### Config changes
- Add a workspace config key (e.g., `claude_plugins`) in `.dogent/dogent.json`:
  - Type: list of strings (paths)
  - Each path points to a plugin root containing `.claude-plugin/plugin.json`.
  - Relative paths resolve from workspace root.

### Claude SDK integration
- Ensure `ClaudeAgentOptions(setting_sources=["user","project"])` to load:
  - `.claude/commands` (project + user)
  - `.claude/agents` (project + user)
  - `.claude/skills` (project + user)
- Ensure `allowed_tools` includes `Skill` and `Task` to permit skills/subagents.
- Pass plugin configs via `ClaudeAgentOptions.plugins=[{"type":"local","path":...}]`.
- Optionally capture `SystemMessage(subtype="init")` for `slash_commands` and
  verify loaded plugins/commands for display (non-blocking).

### CLI command registration
- Create a Claude command loader that:
  - Scans `~/.claude/commands` and `<workspace>/.claude/commands` for `*.md`.
  - Parses optional frontmatter `description` (fallback to "Claude command").
  - Derives command name from filename (e.g., `refactor.md` -> `/refactor`).
- Prefixes all Claude commands with `/claude:` for Dogent CLI.
- Handler behavior:
  - For registered Claude commands, forward raw slash text to the agent.
  - Preserve arguments (e.g., `/refactor src/app.py`).

### Data flow overview
- ConfigManager:
  - Load `claude_plugins` from `.dogent/dogent.json`.
  - Normalize and validate plugin paths; warn and skip invalid entries.
- CLI:
  - Load/refresh Claude commands at startup.
  - Register commands in CommandRegistry for help + completion.
  - Use the same dispatch path as built-ins for consistent UX.

### Error handling
- Missing `.claude/commands` directories are ignored (no warnings).
- Invalid plugin path or missing `.claude-plugin/plugin.json`:
  - Warn once per entry; skip plugin.
- Unknown slash command remains an error panel (strict mode).

### Tests
- Command loader:
  - Registers commands from both project and user paths.
  - Parses frontmatter description or uses fallback.
- Generates `/claude:<name>` for all Claude commands.
- Config:
  - Normalizes plugin path list and validates plugin root.
  - Maps to `ClaudeAgentOptions.plugins`.
- CLI:
  - `/help` includes Claude commands.
  - Completion list contains Claude commands and aliases.

---

## Release 0.9.17

### Profile Command (CLI)
- Add a new slash command to manage workspace profiles (`llm_profile`, `web_profile`, `vision_profile`).
- Command name: `/profile` (with optional `/profile llm|web|vision|show`).
- UX flow:
  - `/profile`: show current selections only (no interactive selector).
  - `/profile llm|web|vision`: list available options (panel) and update `.dogent/dogent.json` when a value is provided.
  - CLI completions: `/profile ` shows targets; `/profile llm ` (or web/vision) shows available values in the drop list.
  - `/profile show`: show current selections and the available profile keys in a Rich table.
- Profile options source:
  - LLM: `~/.dogent/dogent.json` `llm_profiles` keys + `default`.
  - Web: `~/.dogent/dogent.json` `web_profiles` keys + `default (native)`.
- Vision: `~/.dogent/dogent.json` `vision_profiles` keys; only show a `none` option when there are no profiles, and it writes `null` in `.dogent/dogent.json`.
- Persist selections with new `ConfigManager` setters (similar to `set_doc_template` / `set_primary_language`) and show a success panel.
- Reset the active agent session after any profile change so the next request uses the new settings.
- Update `/help` to include the new command and mention the default/none semantics.

### Logging (debug config)
- Interpret `.dogent/dogent.json` `debug` as:
  - `null` or `false` or missing: logging disabled.
  - `true` or `all`: open all logging (store the string `"all"` when selected via command).
  - `session`: existing prompt/response logging (current `SessionLogger` behavior).
  - `error`, `warn`, `info`, `debug`: level-based logs.
  - The level indicates priority: `error > warn > info > debug`. Selecting one level auto-enables all higher-severity levels.
- Types vs levels:
  - `session` is a separate type from `info`; both can be enabled together or independently.
  - Levels cover non-session events (errors, warnings, info/debug notes).
- Logging output:
  - Use `.dogent/logs` under the current workspace.
  - Keep a per-session file (existing `dogent_session_<timestamp>.md`), but include entries from all enabled log types with a clear structure.
  - All logs are sorted by time from newest to oldest. Each entry includes a level/type badge and an interaction id when available so a reader can correlate session events with nearby non-session logs.
- Instrumentation:
  - Add logger calls in every `except` block and user-facing error branch (red panels, warnings) across CLI, config, and feature modules.
  - For exceptions（as the `error` level）, record type, message, traceback, and location (reuse/extend `log_exception`).
  - For explicit errors (e.g., invalid command, missing file), record a structured `error` event.
- Schema update:
  - Update dogent schema to allow `debug` as `null | boolean | string | array<string>`.
- Command:
  - Add a command `/debug` that reports the current debug configuration with no args.
  - `/debug <option>` sets the config; presets are discoverable via CLI completion drop list:
    - `off` (writes `null`)
    - `session` (writes `"session"`)
    - `error` (writes `"error"`)
    - `session-errors` (writes `["session","error"]`)
    - `warn` (writes `"warn"`, implies `error+warn`)
    - `info` (writes `"info"`, implies `error+warn+info`)
    - `debug` (writes `"debug"`, implies all levels)
    - `all` (writes `"all"`)
    - `custom` (opens advanced selection: toggle `session`, pick level)
  - When saving, show a success panel with the resolved enabled types/levels.
- Tests:
  - Add unit tests for debug normalization to log types.
  - Add tests for profile list + set behavior (read global profiles, write workspace config).

### Document Tool Offset Support
- Extend `mcp__dogent__read_document` to support segmented reads via offset + length for long files.
- Tool schema:
  - Add `offset` (integer, default `0`) to skip the first N characters.
  - Keep `max_chars` for backward compatibility; add `length` as the preferred alias (if provided, it overrides `max_chars`).
- Behavior:
  - Apply offset/length after conversion to text (PDF/DOCX/XLSX/text) so segmentation works consistently across formats.
  - Offset is measured in characters of the rendered text.
  - If `offset` exceeds content length, return empty content with `truncated=false`.
  - `truncated=true` when there is more content beyond the returned segment (after offset/length).
- Output:
  - Include paging metadata in the response (`offset`, `returned`, `total_chars`, `next_offset`) to make segmented reads predictable.
- Re-register with agent:
  - Update the MCP tool schema in `document_tools.create_dogent_doc_tools`.
  - Update prompt templates to mention offset/length usage for long documents.
- Tests:
  - Add unit tests for offset + length slicing on text reads (and at least one non-text format if feasible).

---

## Release 0.9.18

### Non-Interactive Prompt Mode (-p/--prompt)
- Add CLI flags `-p/--prompt` (single-run) and `--auto` (auto-approve + auto-skip clarifications).
- Flow:
  - Initialize `DogentCLI` in a non-interactive mode (no prompt_toolkit session, no escape listener).
  - Reuse template override or specify(`@@doc_template`) and `@file` attachment parsing, then run once and exit.
  - Auto-init the workspace with defaults if `.dogent/dogent.json` is missing.
  - Skip auto-init prompts and other interactive confirmations (init, tool permission, lesson save, outline edit, clarifications).
- Default `-p` behavior (fail fast):
  - If a permission check would prompt(not allowed in `.dogent/dogent.json`), abort and return a permission-required exit code.
  - If the agent returns `needs_clarification`, `needs_outline_edit`, or `awaiting_input`, stop and return distinct exit codes.
- `--auto` behavior:
  - Auto-approve all permissions (no prompt, no recording).
  - When clarification payloads are returned, auto-send skipped answers and continue.
  - Still return non-zero if `needs_outline_edit` or `awaiting_input` remains after the auto pass.
- Output:
  - Preserve the normal agent summary output.
  - On success, append a fixed line: `Completed.`

### Authorization Persistence (workspace config)
- Add `authorizations` in `.dogent/dogent.json` (workspace only).
- Format (tool -> list of path patterns):
  - Example: `"authorizations": { "Read": ["/abs/path.txt", "/abs/dir/**"], "Bash": ["./tmp/**"] }`
  - Paths can be absolute or workspace-relative; normalize to absolute for matching.
  - Support wildcards (`*`, `?`, `**`) with glob-style matching.
- Evaluation:
  - Extend `should_confirm_tool_use` to accept authorization rules and short-circuit prompts when all involved paths match configured patterns for the tool.
  - Apply to all permission checks in `dogent/agent/permissions.py` (outside workspace, protected file edits, delete targets, redirections).
  - For bash commands with multiple targets, all targets must be authorized to skip prompts.
- Recording:
  - Interactive permission prompt gains a third option: allow + remember.
  - When chosen, record the exact paths under the tool key (no wildcard added automatically).
  - For multi-target operations (e.g., `rm a b`), record all paths involved in the authorization decision.

### dogent.json Write Exceptions
- CLI commands that update `.dogent/dogent.json` (init/profile/debug/learn/etc.) should not prompt for permission.
- Agent tool edits to `.dogent/dogent.json` should also skip permission prompts.

### Exit Codes
- `0`: completed.
- `1`: error/exception.
- `2`: argument/usage error (argparse).
- `10`: permission required (non-interactive default).
- `11`: needs clarification.
- `12`: needs outline edit.
- `13`: awaiting input.
- `14`: interrupted.
- `15`: aborted.

### Tests
- Add unit tests for parsing `-p/--prompt` and `--auto` and non-interactive execution flow.
- Add tests for exit-code mapping by `RunOutcome` status.
- Add tests for authorization persistence (match rules, record rules, skip prompts).


---

## Release 0.9.19

### Goals
- Add image generation capability based on `dev/spikes/image_generate.md`.
- Expose image generation parameters as tool inputs (prompt, size, quality, watermark).
- Add image generation profiles in global config and select via `/profile`.

### Decisions
- Implement a new MCP tool `mcp__dogent__generate_image` (display name `dogent_generate_image`).
- Use HTTP requests (urllib) for GLM-Image to avoid new dependencies (align with vision tool style).
- Require `image_profile` to be configured in `.dogent/dogent.json`; return a clear configuration error if missing.
- Tool downloads the generated image URL and saves it to a workspace path provided by `output_path`.
- Tool parameters: `prompt`, `size` (default `1280x1280`), `watermark_enabled` (default true), `output_path`.
- If `output_path` is omitted, default to `./assets/images` with an auto-generated filename.
- File extension is derived from the image response content type when possible; fallback to `.png`.

### Architecture
- Add `dogent/features/image_generation.py`:
  - `ImageProfile` dataclass (provider, model, base_url, api_key, options).
  - `ImageManager.generate(...)` dispatches to provider client.
  - `GLMImageClient` implements request/response parsing per spike.
- Add `dogent/features/image_tools.py`:
  - MCP tool schema: `prompt` (required), `size`, `watermark_enabled`, `output_path`.
  - Validate `size` as `WxH` within 512-2048 and multiples of 32.
  - Resolve `output_path` to a workspace path (create parent dirs), download the URL, and write bytes.
  - When `output_path` is missing, create `./assets/images/dogent_image_<timestamp>.<ext>`.
  - Return tool output as JSON text with URL, saved path, and metadata.
- Update `ConfigManager`:
  - Add `image_profile` to project defaults and normalization.
  - Add `image_profiles` to global config (`~/.dogent/dogent.json`) and schema.
  - Provide `list_image_profiles()` and `set_image_profile()`.
  - Register image generation tools and allowlist entry when `image_profile` is set.
- Update CLI:
  - `/profile` supports `image` target (completion, table, banner, setters).
  - Banner displays current image profile.
- Update tool display names mapping to include the new image generation tool.

### Error Handling
- Missing/placeholder API key: tool returns an actionable error referencing `image_profiles`.
- HTTP errors return status code + body where available.
- Invalid `size` returns tool errors before making the API call.

### Tests
- Config tests for `image_profile` selection and `image_profiles` discovery.
- Tool registration tests when `image_profile` is set/unset.
- Tool handler tests with mocked HTTP response for URL parsing and validation errors.

### Open Questions
- None.

---

## Release 0.9.20

### Goals
- Avoid long stalls by checking external dependencies before document tools run.
- Prompt users to install missing dependencies with progress and allow manual install.
- In noninteractive mode, auto-install when possible and fail fast with instructions.

### Decisions
- Run dependency checks before tool execution using the tool-permission hook so we can prompt users.
- Cover these dependency groups:
  - DOCX read/export/convert: `pypandoc` + a working `pandoc` binary.
  - PDF export: `playwright` Python package + Chromium (bundled in full mode or installed).
  - PDF read: `pymupdf` (import `fitz`).
  - XLSX read: `openpyxl`.
- For `DOGENT_PACKAGE_MODE=full`, still prompt to install if bundled tools are missing.
- Use `pip` for missing Python packages and platform-aware commands for external tools.
- Auto-install pandoc via `pypandoc-binary` to reuse pip progress reporting; manual install uses OS-specific pandoc commands.
- If user chooses manual install, display OS-specific instructions and interrupt the task.
- Cache pip downloads under `~/.dogent/cache` while letting Playwright use its default cache location.

### Architecture
- Add a dependency manager module (e.g., `dogent/features/dependency_manager.py`) with:
  - `DependencySpec` (id, label, check_fn, install_steps, manual_instructions).
  - `InstallStep` (label, command, progress_parser).
  - `missing_for_tool(tool_name, input_data, package_mode)` to compute required deps.
  - `install(missing, console, noninteractive)` to run installers and render progress.
- Extend `AgentRunner`:
  - Add a `dependency_prompt` callback (similar to permission prompt).
  - In `_can_use_tool`, before allowing a tool, check missing dependencies for that tool.
  - If missing:
    - Interactive: prompt with options (install now / install manually / cancel).
    - Noninteractive: attempt auto-install; on failure abort with instructions.
  - If user installs now, run installs and continue the tool automatically.
  - If user chooses manual, interrupt the run with a clear instruction panel.
- CLI integration:
  - Implement `_prompt_dependency_install` using `_prompt_choice`.
  - Wire `dependency_prompt` into `AgentRunner` at CLI initialization.
- Progress UI:
  - Use `rich.progress.Progress` with one task per install step.
  - Parse percent from installer output (regex for `NN%` and `current/total`).
  - For pip installs, use `pip --progress-bar raw` to emit parseable progress (single-phase).
  - For Playwright Chromium install, render separate Download and Install bars and parse `playwright install` output percent lines.

### Error Handling
- If install fails, stop the tool and show a concise failure summary plus manual steps.
- If dependencies are still missing after install, treat as a hard failure with instructions.
- Respect `DOGENT_PACKAGE_MODE=full`: missing bundled assets are handled as installable or manual.

### Manual Install Messaging
- Instructions are OS-specific:
  - macOS: `brew install pandoc`; Playwright via `python -m pip install playwright` then `python -m playwright install chromium`.
  - Linux: `sudo apt-get install pandoc` (or `sudo dnf install pandoc`); Playwright via `python -m pip install playwright` then `python -m playwright install --with-deps chromium`.
  - Windows: `winget install --id JohnMacFarlane.Pandoc -e` (or `choco install pandoc`); Playwright via `python -m pip install playwright` then `python -m playwright install chromium`.
- Python-only dependencies use `python -m pip install <package>` on all OSes.

### Tests
- Unit tests for dependency resolution per tool (pdf/docx/xlsx paths).
- Tests for noninteractive auto-install path (mock installer and assert failure path).
- Progress parsing tests for percent extraction.

### Open Questions
- None.

---

## Release 0.9.21
### Overview
- Auto-create `.dogent/dogent.json` and `.dogent/history.json` on the very first CLI launch in a workspace (no init prompt).
- Add a `poe-claude` LLM profile to the global config template (`~/.dogent/dogent.json` seed).
- Update docs/sample configs to mention the new `poe-claude` profile.

### Behavior Changes
- First CLI launch in a workspace:
  - Ensure `.dogent/` exists.
  - Create `.dogent/dogent.json` if missing using existing template merge rules (no prompt).
  - Create `.dogent/history.json` if missing (empty list).
  - Continue normal flow (do not require `/init`).
- The existing `/init` command continues to create `.dogent/dogent.md` and respects user overrides.

### Design / Implementation Notes
- **Config bootstrap on first launch**
  - Current behavior prompts to initialize when `.dogent/dogent.json` is missing; change to auto-create during CLI startup.
  - Preferred hook: call `ConfigManager.create_config_template()` and `HistoryManager._ensure_history_file()` (via a small public helper) early in CLI startup path (interactive and non-interactive).
  - Keep `.dogent/dogent.md` creation tied to `/init` (no change) unless we explicitly decide to auto-create it later.

- **Global template update**
  - Add `poe-claude` under `llm_profiles` in `dogent/resources/dogent_global_default.json`.
  - Ensure template is merged on first-run bootstrap and during global config upgrades.

- **Docs/sample configs**
  - Update configuration docs to include the `poe-claude` profile snippet and brief usage note.
  - Update any sample configs that show `llm_profiles` to include `poe-claude`.

### Tests
- Add/extend unit tests to assert:
  - On first CLI launch in a workspace with no `.dogent/dogent.json`, it is created automatically.
  - `.dogent/history.json` is created on first launch (empty list).
  - `poe-claude` exists in the global default template used to seed `~/.dogent/dogent.json`.

### Risks / Edge Cases
- Ensure auto-creation does not overwrite existing `.dogent/dogent.json`.
- Avoid triggering interactive prompts on first launch.
- Keep global config upgrade logic idempotent if user already added a `poe-claude` profile.

---

## Release 0.9.22

### Goals
- Persist input recall across restarts for user prompts (from `.dogent/history.json`) and `/` commands.
- Replace tag+JSON clarification/outline edit outputs with MCP tool-based UI calls.

### Design Overview
#### 1) Input recall across restarts (prompts + `/` commands)
- **Source of prompts + commands:** use existing `.dogent/history.json` entries (`HistoryManager.append(..., prompt=...)`) for both user prompts and `/` commands.
- **Lifecycle:** `/clean history` clears both prompts and `/` command recall.
- **Limit:** seed prompt history with the **latest 30** combined items (prompts + commands).
- **Exclude:** clarification answers are stored in history but not used for recall.

**Seeding strategy**
- Load prompts from `history.json` (filter non-empty `prompt`).
- Sort by timestamp, take last 30, preserve chronological order.
- Preload `prompt_toolkit` history using `InMemoryHistory`.

**Write path**
- When `_handle_command(...)` receives a valid `/` command, append a history entry with `prompt` set to the raw command (e.g. `/show history`) and a distinct status (e.g. `status="command"`), so it is eligible for recall.

#### 2) Tool-based UI requests for clarification/outline edit
- **New MCP tool:** `mcp__dogent__ui_request` via SDK MCP server.
- **Schema (input):**
  - `type`: `"clarification" | "outline_edit"`
  - `title`: string
  - `preface?`: string (clarification only)
  - `questions?`: clarification schema (same as current JSON schema)
  - `outline_text?`: string (outline_edit only)
- **Tool-only:** remove tag+JSON parsing paths; only tool calls trigger clarification/outline edit UI.

**Runtime flow**
1. Model calls `mcp__dogent__ui_request`.
2. `AgentRunner` intercepts `ToolUseBlock`:
   - Validate payload based on `type`.
   - Set `_needs_clarification` / `_needs_outline_edit` and store payload.
   - Interrupt streaming to avoid further assistant output.
3. CLI renders the appropriate UI:
   - Clarification → existing Q&A prompts.
   - Outline edit → existing multiline editor (using `outline_text`).
4. CLI sends user answers back as a normal user message (same as current flow).

**Tool execution**
- The MCP tool implementation can return a minimal placeholder response (e.g. “UI request received”) if executed; `AgentRunner` should still interrupt on `ToolUseBlock` and ignore any subsequent tool result blocks.

**Prompt updates**
- Update `dogent/prompts/system.md` to require tool calls for clarification/outline edit.
- Remove or de-emphasize tag+JSON instructions; keep fallback sentinel guidance only for non-tool-capable runtimes.

### Affected Modules
- `dogent/cli/app.py`: preload history; record `/` commands into history; intercept UI tool use.
- `dogent/core/history.py`: reuse for prompt sources.
- `dogent/features/ui_tools.py` (new): define `ui_request` tool + schema.
- `dogent/config/manager.py`: register UI tool in MCP server + allowed tools.
- `dogent/agent/runner.py`: handle `ToolUseBlock` for UI tool; remove tag parsing logic.
- `dogent/features/clarification.py` and `dogent/outline_edit.py`: remove tag parsing helpers.
- `dogent/prompts/system.md`: update clarification/outline rules (tool-only).

### Testing Notes
- Add unit tests for:
  - merging prompt+command history (limit 30, ordering).
  - command history persistence in `.dogent/history.json`.
  - tool-use interception sets `needs_clarification/needs_outline_edit`.

---

## Release 0.9.23

### Goal
- Add @ file and @@ doc template dropdown completion in the multiline markdown editor.
- Keep completion behavior aligned with single-line input.
- Preserve literal @/@@ when nothing is selected.

### Current Baseline
- Single-line prompt uses `DogentCompleter` for `@` file and `@@` template suggestions.
- Multiline editor uses `TextArea` without a completer.
- File references are resolved on submission via `FileReferenceResolver` and template override parsing.

### UX + Behavior
- Typing `@` in the editor shows file/path suggestions relative to the workspace root.
- Typing `@@` shows template suggestions, including `general`, workspace, global, and built-in templates.
- Directory entries appear with a trailing `/` and can be completed to navigate deeper (same as single-line).
- If a completion menu is open, pressing Enter accepts the current suggestion.
- If no completion is selected, Enter inserts a newline and the literal `@`/`@@` stays in the text.
- Completions are enabled in all editor contexts: prompt, clarification, and file edit.

### Implementation Plan
- Reuse `DogentCompleter` for the editor `TextArea`:
  - `root=self.root`
  - `template_provider=self.doc_templates.list_display_names`
  - `commands` can be the existing registry list (safe) or an empty list (to avoid `/` suggestions).
  - `complete_while_typing=True`
- Add an editor key binding for Enter in `_open_multiline_editor`:
  - If `buffer.complete_state.current_completion` exists, apply it and return.
  - Otherwise insert a newline (`buffer.insert_text("\n")`) and keep existing editor behavior.
  - Scope the binding to `edit_active & editor_focus` so overlays and preview mode are unaffected.
- Do not change file/template resolution logic; completion only affects text insertion.

### Edge Cases + Notes
- `@@` completions should not fall through to file completion when template completions are available.
- Completion acceptance should not submit the editor (submission remains Ctrl+Enter or vi :wq).
- Text is only modified on explicit completion acceptance, satisfying the "treat @/@@ as normal characters" rule.

### Tests
- Add a unit test that simulates a buffer with completion state and verifies Enter applies the completion.
- Add a unit test that verifies Enter inserts a newline when no completion is active.
- Skip tests if prompt_toolkit is unavailable (consistent with existing optional dependency handling).

---

## Release 0.9.24

### Goal
- Ship a built-in Claude plugin that wraps the PPTX skill under `dogent/plugins/claude`.
- Auto-install all built-in plugins to `~/.dogent/plugins` on startup (overwrite/update).
- New workspace configs include the built-in Claude plugin path by default; existing projects remain unchanged unless edited.

### Current Baseline
- Claude plugins are loaded from `.dogent/dogent.json` via `claude_plugins`; defaults are empty.
- Plugin roots must contain `.claude-plugin/plugin.json`.
- Startup bootstrap creates `~/.dogent` config/schema files but does not install plugins.

### Plugin Layout (Package)
- Plugin root: `dogent/plugins/claude`.
- Manifest: `dogent/plugins/claude/.claude-plugin/plugin.json` (name `claude`, version, description).
- Skills: `dogent/plugins/claude/skills/pptx` (copied from `claude/skills/skills/pptx`, including SKILL.md, scripts, ooxml, and LICENSE.txt).
- Follow Claude plugin structure (see `claude/examples/plugins`) so SDK loads skills correctly.

### Install Flow (Startup)
- Add `DogentPaths.global_plugins_dir` -> `~/.dogent/plugins`.
- Implement `ConfigManager._install_builtin_plugins()` and call it from `_ensure_home_bootstrap()` after `~/.dogent` exists.
- Source: `importlib.resources.files("dogent") / "plugins"` (skip if missing).
- For each directory under source, copy to `~/.dogent/plugins/<name>` with `shutil.copytree(..., dirs_exist_ok=True)` to overwrite/update.
- On permission errors, warn and continue (do not block CLI startup).

### Default Config Behavior
- Update `dogent/resources/dogent_global_default.json`:
  - `workspace_defaults.claude_plugins = ["~/.dogent/plugins/claude"]`.
- Ensure existing projects are not auto-updated:
  - If `.dogent/dogent.json` exists and lacks `claude_plugins`, treat it as an explicit empty list so global defaults do not inject the built-in plugin.
  - New workspaces created via `create_config_template()` inherit the default plugin path.

### Packaging
- Add `plugins/**` to `tool.setuptools.package-data` for the `dogent` package so built-in plugins ship with the distribution.

### Docs
- Update `docs/07-commands.md` and `docs/10-claude-compatibility.md`:
  - Mention built-in plugins are installed to `~/.dogent/plugins`.
  - Note only the built-in Claude plugin is included in default `claude_plugins`; others require manual addition.

### Tests
- Add a unit test for config behavior:
  - New workspace config includes `~/.dogent/plugins/claude`.
  - Existing workspace config without `claude_plugins` yields an empty list.
- Add a unit test for builtin plugin install (helper takes a source dir in tests, copies into a temp `~/.dogent/plugins`).

---

## Release 0.9.25

### Goal
- Rename config key `claude_plugins` to `plugins` in workspace and global configs (no backward compatibility).
- Update docs for PDF dependency prompts and PPTX status.
- Expand permission exceptions for read/execute in `~/.dogent/plugins` and `~/.claude`.
- Allow deletion of Dogent-generated temporary files within the same task without prompting.

### Current Baseline
- Config key is `claude_plugins`; schemas and docs mention it.
- Permissions are enforced for all paths outside workspace, with a delete whitelist only for `.dogent/memory.md`.
- No central tracking of temp files created during a task.

### Config + Schema Changes
- Rename all references of `claude_plugins` to `plugins` in:
  - `dogent/resources/dogent_default.json`
  - `dogent/resources/dogent_global_default.json` (`workspace_defaults.plugins`)
  - `dogent/config/manager.py` normalization, loading, and options build
  - docs and schemas (`dogent/schema/**` and `docs/*`)
- No backward compatibility: if users still have `claude_plugins`, it will be ignored.

### Permissions Changes
- Introduce read/execute safe roots: `~/.dogent/plugins` and `~/.claude`.
- For file tools:
  - `Read` under safe roots does not require confirmation.
  - `Write/Edit` under safe roots still require confirmation if outside workspace (except temp-file deletes below).
- For Bash:
  - Allow commands that only touch safe-root paths without confirmation.
  - Writes/deletes outside workspace still prompt unless the target is a tracked temp file.
- Expose plugin commands differently by location:
  - `~/.claude/plugins` => `/claude:<plugin>:<command>`
  - `~/.dogent/plugins` => `/<plugin>:<command>`

### Temporary File Tracking
- Track temp files created by Dogent during a single task run (store resolved paths on the runner).
- When a delete occurs in the same task (Bash `rm`/`mv` or Write/Edit delete semantics), skip permission prompts if the target matches a tracked temp file.
- Clear the list at task end (on completion/abort) to avoid cross-task leakage.

### Docs
- `docs/04-document-export.md`:
  - Note PDF generation/conversion requires pandoc + Chrome; prompt to download if missing.
  - Note PPTX generation is not fully solved; default to “Claude PPTX skill” with link to `https://github.com/anthropics/skills/tree/main/skills/pptx`.
- Update config key names in `docs/07-commands.md`, `docs/08-configuration.md`, `docs/10-claude-compatibility.md`.
- Update permissions doc to mention safe roots.

### Tests
- Config tests: new key `plugins` used in defaults and options.
- Permission tests:
  - Read in `~/.dogent/plugins` or `~/.claude` does not prompt.
  - Write outside workspace still prompts (unless temp delete).
- Temp file tests:
  - Track a temp file and ensure delete via Bash skips confirmation.
  - Ensure list clears between tasks.

---

## Release 0.9.26

### Goal
- Preserve prompts submitted from the `Ctrl+E` multiline editor in the same prompt history used by Up Arrow recall.
- When recalled, restore the exact submitted text so the user can edit inline immediately or reopen the editor with `Ctrl+E`.

### Current Baseline
- Main prompt input uses `PromptSession` with `LimitedInMemoryHistory`, seeded from `HistoryManager.prompt_history_strings()`.
- Normal prompt submissions entered directly in the prompt session are added to prompt_toolkit history automatically.
- `Ctrl+E` returns a `MultilineEditRequest`, opens `_open_multiline_editor()`, and on submit returns the edited text from `_read_input()`.
- That editor-submit path does not explicitly append the final text into `self.session.history`, so the Up Arrow recall list can miss the edited prompt during the current session.
- Durable prompt history in `.dogent/history.json` is populated later by `HistoryManager.append(..., user_input=...)` when the request is actually sent to the agent.

### UX + Behavior
- After a user submits text from the `Ctrl+E` editor with `Ctrl+J`, pressing Up Arrow from the main prompt recalls that exact text.
- Recalled text must match the final editor submission byte-for-byte, including newlines and spacing.
- Recalled editor-submitted prompts behave the same as normal recalled prompts:
  - the user can edit inline in the main prompt;
  - the user can press `Ctrl+E` again to continue editing from that recalled content.
- History behavior remains limited to user prompts; no new command-history behavior is introduced.

### Implementation Plan
- Add a small helper on `DogentCLI` to append submitted prompt text into the active prompt session history:
  - no-op when `self.session` or `self.session.history` is unavailable;
  - ignore empty or whitespace-only text;
  - call `append_string()` when supported by the history object.
- In `_read_input(...)`, when an editor outcome is submitted and the context is the main prompt flow, append `editor_outcome.text` to session history before returning it.
- Keep the durable history source unchanged:
  - agent request logging continues to write `user_input` into `.dogent/history.json`;
  - future sessions still rebuild prompt recall from `HistoryManager.prompt_history_strings()`.
- Do not append editor cancellations/discards to history.
- Avoid double-recording:
  - direct prompt submissions continue to rely on prompt_toolkit's normal history handling;
  - only the editor-submit path gets the explicit append.

### Edge Cases + Notes
- Multi-line prompts must remain a single history entry, not one entry per line.
- Recalling a multiline prompt should preserve line breaks so Up Arrow enters multiline editing/navigation behavior consistently.
- The helper should be safe with alternate history implementations and degrade silently if `append_string` is unavailable.
- Clarification/file-edit editor flows should not be changed unless they intentionally use the same main prompt history semantics.

### Tests
- Add a unit test for `_read_input(...)` showing that a `MultilineEditRequest` followed by editor submit appends the final text to session history.
- Add a unit test that the appended history text preserves embedded newlines exactly.
- Add a unit test that editor discard/cancel does not append anything to prompt history.
- Keep existing prompt history limit behavior unchanged; reuse `LimitedInMemoryHistory` in tests where possible.

---

## Release 0.9.27

### Goal
- Align Dogent's Claude Agent SDK integration with the `claude-agent-sdk>=0.1.51` behavior already referenced in `pyproject.toml`.
- Make tool approvals and SDK-native user questions reliable under the documented Python streaming pattern.
- Stop treating `allowed_tools` as a hard tool-surface restriction in helper flows.
- Switch Dogent's primary subagent tool naming from `Task` to `Agent` while preserving compatibility with SDK outputs that may still mention `Task`.
- Support project builtin commands/skills/sub-agents under both `<workspace>/.claude/` and `<workspace>/.dogent/`.
- Use SDK structured output for suitable one-shot flows that currently depend on free-text JSON parsing.
- Improve runtime permission handling with SDK permission suggestions/updates.
- Add better tool metadata, runtime observability, and opt-in partial streaming where the new SDK provides clear value.

### Current Baseline
- `pyproject.toml` already requires `claude-agent-sdk>=0.1.51`, so this release is mainly an integration-alignment release rather than only a dependency bump.
- `ConfigManager.build_options()` currently uses `allowed_tools` as the main built-in tool list when `can_use_tool` is absent, and omits `allowed_tools` entirely when `can_use_tool` is present.
- `InitWizard` and `ClaudeLessonDrafter` both use `allowed_tools=[]`, which no longer guarantees a no-tools workflow under the current SDK permission semantics.
- `AgentRunner._can_use_tool()` handles permission prompts only; it has no dedicated `AskUserQuestion` branch.
- `AgentRunner._can_use_tool()` ignores `ToolPermissionContext.suggestions` and does not return `updated_permissions`.
- The main system prompt currently requires all clarification and outline-edit interactions to go through `mcp__dogent__ui_request`.
- Dogent's default built-in tool list still includes `Task` instead of `Agent`.
- Dogent already loads `.claude/commands`, configured plugin commands, and plugin roots, but it does not yet treat project `.dogent` commands/skills/agents as first-class SDK-facing capability roots.
- Dogent currently renders completed assistant blocks and cost, but it does not surface partial messages, cumulative usage fields, cache-token fields, or documented rate-limit / task progress events.
- Dogent's custom MCP tools currently provide no `ToolAnnotations`.

### SDK Alignment Strategy
- Keep Dogent's main interactive agent on the normal Claude Code tool preset surface, plus Dogent MCP tools/plugins, and treat `allowed_tools` only as auto-approval input, not as the source of truth for what tools exist.
- For helper flows that need an actual restricted tool surface, use the SDK `tools` option explicitly:
  - `tools=[]` for no-tool one-shot generation flows.
  - `tools=[..., "AskUserQuestion"]` only when a restricted helper flow must still ask simple clarifying questions.
- Use `disallowed_tools` only where Dogent needs an explicit deny rule in Python; do not rely on `allowed_tools=[]` to mean "Claude cannot call tools".

### Permissions + Tool Approval Design
- Add the documented dummy `PreToolUse` hook for sessions that pass `can_use_tool`, so Python streaming stays open long enough for approvals and `AskUserQuestion`.
- Keep Dogent's existing permission UX and persistent authorization storage in `.dogent/dogent.json` for normal tool approvals.
- Extend `_can_use_tool()` with an early `AskUserQuestion` branch before normal permission evaluation:
  - parse SDK question payloads;
  - collect answers through the CLI;
  - return `PermissionResultAllow(updated_input={...})` with the original `questions` and the collected `answers`.
- Continue routing risky built-in tools such as `Bash`, `Write`, and `Edit` through Dogent's current permission checks after the `AskUserQuestion` fast path.
- When the user chooses "Allow" or "Allow and remember", use SDK `context.suggestions` and `PermissionResultAllow(updated_permissions=...)` where they match Dogent's runtime intent, while still persisting remembered authorizations into `.dogent/dogent.json`.
- Preserve existing temp-file and safe-root permission exceptions from earlier releases.

### Clarification + Outline Editing Design
- Update the main system prompt so the agent uses:
  - `AskUserQuestion` for simple clarification only;
  - `mcp__dogent__ui_request` for outline editing and any clarification that needs richer Dogent-specific semantics.
- Treat "simple clarification" as the SDK-supported shape:
  - up to 1-4 short questions;
  - 2-4 options per question;
  - no rich outline editing;
  - no dependency on custom schema fields such as `placeholder` for correctness.
- Keep Dogent's existing clarification UI code for `mcp__dogent__ui_request` because it still covers:
  - outline editing;
  - richer free-text collection;
  - current custom fields such as `recommended`, `allow_freeform`, and `placeholder`.
- Since the SDK docs say `AskUserQuestion` is not currently available inside subagents, Dogent should not rely on it as the only clarification path in subagent-driven flows.

### Project Commands + Skills + Subagents Design
- Replace `Task` with `Agent` in Dogent's default tool configuration and prompt/docs where Dogent describes the current SDK tool name.
- Keep compatibility checks for both `Task` and `Agent` in any streamed-message inspection, display, or denial-handling logic that interprets SDK output, because the local SDK docs note mixed naming may still appear in some message fields.
- Extend project capability discovery so Dogent supports builtin commands/skills/sub-agents under both:
  - `<workspace>/.claude/`
  - `<workspace>/.dogent/`
- Keep current `.claude/commands` support, and add parallel project `.dogent/commands` discovery for builtin Dogent-facing commands.
- Extend SDK capability roots so project `.dogent` and project `.claude` can both contribute skills/agents/hooks using the latest filesystem/plugin structure expected by the SDK.
- Treat the SDK skill-first/plugin-agent structure as the preferred direction, while keeping existing command loading behavior compatible during the transition.

### Structured Output Design
- Migrate the init wizard to SDK structured output first because it already expects a machine-readable payload with:
  - `doc_template`
  - `primary_language`
  - `dogent_md`
- Replace the current free-text JSON extraction path in `InitWizard` with:
  - `tools=[]`;
  - `output_format={"type": "json_schema", "schema": ...}`;
  - reading `ResultMessage.structured_output` as the primary success path.
- Keep a defensive fallback for malformed or missing structured output during the transition so CLI failures remain diagnosable instead of silently producing bad config.
- Leave `ClaudeLessonDrafter` on free-text output for now unless the implementation reveals a concrete need for structured fields there; the release requirement asks to start using structured output in suitable one-shot flows, not to convert every helper workflow at once.

### Tool Annotation Design
- Add `ToolAnnotations` to Dogent MCP tools where the SDK can benefit from stronger behavior hints.
- Initial targets:
  - document read/export/convert tools where read-only semantics are clear;
  - `analyze_media`;
  - custom web tools;
  - `ui_request`.
- Keep annotations conservative; only mark a tool read-only or open-world when the tool behavior actually matches that contract.

### Observability + Streaming Design
- Extend Dogent's result/event handling so SDK runtime metadata is captured and surfaced where useful:
  - cumulative `ResultMessage.usage`;
  - cache-token related usage fields when present;
  - `RateLimitEvent`;
  - `TaskStartedMessage`, `TaskProgressMessage`, and `TaskNotificationMessage`.
- Preserve the current concise CLI by default:
  - log full usage/event detail in debug/session logging;
  - surface user-facing warnings for rate limits and important background-task status changes.
- Add optional partial-response rendering using the SDK partial-message API (`include_partial_messages` / `StreamEvent`) for long-running outputs.
- Keep partial streaming opt-in for this release rather than default-on, matching the reviewed decision from the spike.

### Implementation Plan
- Update `ConfigManager.build_options()` to separate:
  - true tool-surface restriction (`tools`);
  - auto-approval hints (`allowed_tools`);
  - runtime approval handling (`can_use_tool` + hooks).
- Add a reusable helper for the documented dummy `PreToolUse` hook and apply it whenever Dogent passes `can_use_tool`.
- Extend `AgentRunner` with `AskUserQuestion` input parsing and answer collection, reusing the existing CLI interaction layer where possible.
- Extend permission responses to use SDK runtime permission updates where they improve the current flow without replacing Dogent's persistent authorization model.
- Update prompts/docs so the model knows when to choose `AskUserQuestion` versus `mcp__dogent__ui_request`.
- Update command/capability discovery so `.dogent` and `.claude` project roots can both contribute builtin commands/skills/sub-agents.
- Update `InitWizard` to use structured output and true no-tool restriction.
- Add annotations to selected Dogent MCP tools.
- Extend runner/logging code to capture usage/rate-limit/background-task events and support opt-in partial streaming.
- Update any helper-flow option builders that still depend on `allowed_tools=[]` as if it disables tools.

### Edge Cases + Notes
- If a restricted flow specifies a `tools` array and still needs SDK clarification, `AskUserQuestion` must be included explicitly or Claude cannot call it.
- If `AskUserQuestion` input is malformed or exceeds SDK limits, Dogent should deny that request cleanly and let the session surface an actionable error instead of falling into the normal permission prompt.
- SDK `updated_permissions` should be treated as session-scoped runtime state, not as a replacement for Dogent's persistent workspace authorization file.
- Project `.dogent` capability discovery must not break existing `.dogent/dogent.json` config/bootstrap responsibilities.
- Structured-output failures should remain observable in logs/tests; Dogent should not silently fall back to partial free text that looks valid but misses required fields.
- Partial streaming must not corrupt the existing final-message rendering, interrupt handling, or history/session logs.
- Release `0.9.27` still postpones file checkpointing / rewind and broader session-management commands from the SDK upgrade analysis.

### Tests
- Config tests:
  - verify helper flows use `tools=[]` or explicit `tools=[...]` when true restriction is intended;
  - verify default interactive options use `Agent` as the primary subagent tool name;
  - verify the documented `PreToolUse` hook is attached when `can_use_tool` is enabled.
- Command / capability discovery tests:
  - verify project `.dogent/commands` and `.claude/commands` are both discovered correctly;
  - verify project capability roots for `.dogent` and `.claude` are passed to the SDK as intended.
- Agent runner tests:
  - `AskUserQuestion` requests are intercepted before normal permission evaluation;
  - collected answers are returned through `PermissionResultAllow(updated_input=...)`;
  - runtime permission updates use SDK suggestions/updated permissions without regressing persistent authorization writes;
  - normal tool approvals still follow the current permission prompt path.
- Prompt/behavior tests:
  - system prompt instructions distinguish simple clarification from outline editing.
- Wizard tests:
  - successful structured output populates `WizardResult`;
  - missing/invalid structured output fails in a controlled way;
  - the wizard no longer depends on free-text JSON scraping as the primary path.
- Tool metadata / observability tests:
  - selected MCP tools expose the intended annotations;
  - usage / rate-limit / task-progress events are logged or surfaced in the expected paths;
  - partial streaming stays opt-in and does not break final response rendering.

## Release 0.9.28

### Goal

Refactor Dogent document templates from the current single-file Markdown format into a standard skill-style directory format, remove legacy-format compatibility, preserve `/init` and `@@` template selection through dropdown completion, and add a native `/template` command that can list templates and trigger built-in create/optimize flows.

### Current Baseline

- Document templates are currently loaded from flat Markdown files:
  - workspace: `.dogent/templates/<name>.md`
  - global: `~/.dogent/templates/<name>.md`
  - built-in: `dogent/templates/<name>.md`
- `DocumentTemplateManager` only understands single `.md` files and extracts introductions from inline `## Introduction` sections.
- `/init` and `@@` already use template completion, but they depend on the flat-file loader.
- Dogent auto-enables its built-in Dogent plugin under `~/.dogent/plugins/dogent`, and native CLI commands can invoke agent runs directly.
- `/profile` already establishes the desired command UX pattern:
  - `/profile` with no subcommand shows an overview instead of failing.
  - `/profile <target>` with no value shows available options for that target.
  - command completion proposes target values after the user types `/profile `.

### Template Format Design

- The only supported document-template format after this release is a skill-style directory:
  - workspace: `.dogent/templates/<template_name>/SKILL.md`
  - global: `~/.dogent/templates/<template_name>/SKILL.md`
  - built-in: `dogent/templates/<template_name>/SKILL.md`
- Legacy flat files such as `.dogent/templates/resume.md` are not loaded, not listed, and not migrated automatically.
- Each template directory must contain `SKILL.md`. Companion files should follow the new layout:
  - `templates/`: reusable output-structure references
  - `examples/`: sample outputs
  - `assets/`: multimedia assets when needed
- Built-in templates will be rewritten into the same directory-based format so workspace/global/built-in templates follow one consistent mental model.

### Template Content Assembly

- `DocumentTemplateManager` should treat a template as a directory resource rather than a single file.
- The template display name continues to use existing source prefixes:
  - workspace: `resume`
  - global: `global:resume`
  - built-in: `built-in:resume`
- Template introduction/description for lists, `/init`, and `@@` completion should come from the head YAML frontmatter in `SKILL.md`, using `description` as the primary field.
- When Dogent injects template guidance into prompts, it should build a normalized template text block from:
  - `SKILL.md`, with the title/introduction block removed before prompt injection
  - optional Markdown reference files under `templates/`, appended in deterministic sorted order
- `SKILL.md` acts as the human-facing entry point and should describe the template purpose, background, precautions, and companion files.
- If `SKILL.md` contains an explicit `## Introduction` section, Dogent should omit that section from the injected template body because the summary already comes from YAML metadata.
- If no `## Introduction` section exists, Dogent may trim the leading boilerplate lines from the top of `SKILL.md` before injecting the body so the prompt focuses on actionable template rules.
- This keeps the authoring format aligned with skills while still letting document templates split summary metadata, usage scenarios, output format, and other instructions into separate files.

### `/init` and `@@` Selection Behavior

- `/init` template completion must continue to show all available template keys from workspace, global, and built-in sources.
- `@@<template>` completion must continue to work for inline prompt overrides.
- The init wizard template overview should describe templates using the new metadata extraction logic so standard skill-style templates remain selectable without special casing.
- General/default template behavior remains unchanged from a user perspective, but the built-in general template also moves to the new directory format.

### Native `/template` Command Design

- Add a native built-in `/template` command.
- Command intent:
  - `/template` with no subcommand shows the available templates, equivalent to `/template list`.
  - typing `/template ` should offer dropdown completion entries for `create` and `optimize`, matching the discoverability pattern the user requested.
  - `/template list` shows all available templates grouped by source with one-line descriptions.
  - `/template optimize` with no template key should show the available templates and usage guidance, similar to `/profile <target>` showing options when the value is missing.
- Expected subcommands:
  - `list`
  - `create`
  - `optimize`
- `create` and `optimize` are the primary interactive workflows; `list` exists mainly as an explicit equivalent to bare `/template`.

### `/template` Workflow Behavior

- `/template create <brief>` should run an agent task that explicitly asks the model to use the built-in document-template-creator skill and create a new template in workspace scope unless the user says otherwise.
- The free text after `/template create` is the authoritative creation brief and may contain template purpose, audience, structure, language, style, and other related requirements in one natural-language string.
- `/template create` with no brief should show usage guidance or prompt for the missing request in interactive mode rather than silently doing nothing.
- `/template optimize <template-key> <brief>` should run an agent task that explicitly asks the model to use the built-in document-template-creator skill to refine the named template.
- `/template optimize <template-key>` should still be valid and ask the skill to improve the template using the template’s existing content as the baseline.
- `/template optimize` with no template key should show the available templates and usage guidance instead of guessing a target.
- The command should reuse existing confirmation/update patterns when the agent proposes edits under `.dogent/templates/`.

### Built-in Skill Design

- Add a built-in Claude skill dedicated to document-template authoring and optimization.
- Suggested packaged location:
  - `dogent/plugins/dogent/skills/doc-template-creator/`
- The skill should:
  - generate templates in the new skill-style directory layout
  - explain where to place introduction, usage scenarios, output format, and supporting material
  - support both create and optimize requests
  - prefer workspace templates by default unless the user requests global scope
- The native `/template` command should be a thin UX wrapper around this skill rather than reimplementing template-authoring logic inside the CLI.

### Implementation Direction

- Update template discovery and resolution code to scan template directories with `SKILL.md` instead of flat `.md` files.
- Update built-in resource loading helpers to support directory-based template resources.
- Rewrite shipped templates (`general`, `resume`, `research_report`, `technical_blog`) into directory-based resources.
- Add `/template` command registration, handler logic, help text, and command completion support.
- Reuse the existing command/completion style used by `/profile` so blank-command and missing-argument behaviors stay predictable.
- Ensure docs and examples are updated from `<name>.md` paths to `<name>/SKILL.md` paths wherever they describe template authoring.

### Edge Cases

- If a template directory exists without `SKILL.md`, it should be ignored and should not appear in completion.
- If multiple reference files exist, ordering must be deterministic so generated prompts are stable for tests.
- If `SKILL.md` frontmatter is malformed, Dogent should skip description extraction gracefully instead of trying to recover summary text from the body.
- If a user keeps old `<name>.md` files after upgrading, Dogent should not silently load them, because this release explicitly drops compatibility.
- `/template optimize` must reject unknown template keys with an option list instead of starting a vague agent task.

### Tests

- Add unit tests for directory-based template listing, YAML description extraction, prompt-content assembly, introduction stripping, and prefix resolution across workspace/global/built-in sources.
- Add tests that legacy flat `.md` templates are ignored.
- Add CLI completion tests for `/template ` and any subsequent argument completion rules.
- Add CLI command tests for:
  - `/template`
  - `/template list`
  - `/template optimize` with missing template key
  - `/template create ...`
- Add CLI command tests confirming `/template create <free text>` preserves the full free-text brief when building the agent request.
- Update existing `/init` and template-override tests to use the new directory-based fixtures.

## Release 0.9.29

### Goal

Restore reliable execution of Dogent's built-in MCP tools on the latest Claude Agent SDK / MCP package stack, ensure the fix follows the current low-level MCP server contract, and add regression coverage for real MCP tool round-trips.

### Problem Summary

- Dogent's built-in MCP tools are registered through the SDK `@tool` surface, but the runtime path that turns those tool definitions into an in-process MCP server is no longer compatible with the currently installed SDK/MCP combination.
- The visible symptom is that built-in tools such as `mcp__dogent__read_document` and `mcp__dogent__web_fetch` appear available but fail before their actual tool logic runs.
- Direct unit tests of tool handlers are not enough to catch this class of failure because the bug lives in the MCP server registration / call path.

### Design Direction

- Keep Dogent's tool definitions on the current Claude Agent SDK `SdkMcpTool` + `@tool(...)` surface.
- Move Dogent's in-process MCP server registration to a Dogent-owned builder that targets the current `mcp.server.lowlevel.Server` request-handler contract directly.
- Register `tools/list` and `tools/call` using the current `mcp.types` request/result models, while preserving the same tool names, schemas, and `ToolAnnotations`.
- Use the Dogent MCP server builder wherever Dogent creates its own in-process MCP server config.

### Tool Call Behavior

- `tools/list` should return the existing Dogent tool definitions with their JSON schemas and annotations intact.
- `tools/call` should:
  - validate arguments against the registered input schema;
  - call the Dogent tool handler with the original argument payload;
  - normalize the tool response into `mcp.types.CallToolResult` content blocks without a second wrap/unwrap layer;
  - preserve `is_error` from the Dogent tool result as `isError` in MCP responses.

### Scope

- Update Dogent's main MCP server registration path used by `ConfigManager.build_options`.
- Update any other Dogent-owned MCP server factory that still routes through the older helper path.
- Do not change the user-facing MCP tool IDs or the actual tool business logic unless needed for the server registration fix.

### Test Strategy

- Keep existing annotation tests.
- Add regression tests that exercise real Dogent MCP `tools/list` and `tools/call` round-trips for built-in tool families:
  - document tools
  - UI tools
  - web tools
  - vision tools
  - image tools
- Run the full `python -m unittest discover -s tests -v` suite before release.

### Release Hygiene

- Replace any credential-like repo default profile values with placeholders before publishing the release.

### Added Scope: Pre-rendered Markdown Export

- Requirement source: the second `Release 0.9.29` block in `dev/requirement.md` adds Markdown-to-PDF/DOCX rendering scope after the already accepted MCP runtime work.

### Markdown Export Goal

Ensure Markdown-source exports to PDF and DOCX render visual blocks that require preprocessing, starting with Mermaid fenced code blocks, so the final files show diagrams instead of raw Mermaid source.

### Markdown Export Baseline

- `_markdown_to_pdf` renders Markdown to HTML through `markdown-it-py` and prints it with Playwright; Mermaid fences currently remain ordinary code blocks in the final PDF.
- `_markdown_to_docx` normalizes image tags and then sends Markdown directly to pandoc; Mermaid fences currently remain raw code blocks in the final DOCX.
- `convert_document_async` reuses the same Markdown export helpers for `md -> pdf` and `md -> docx`, so the current limitation exists on both tool paths.

### Markdown Export Direction

- Add a shared Markdown pre-render step before both `_markdown_to_pdf` and `_markdown_to_docx`.
- The pre-render step should scan fenced code blocks for renderable languages. Release `0.9.29` scope only requires `mermaid`, but the dispatcher should remain extensible for future renderable block types.
- For each Mermaid block, render a local diagram asset in a temporary working directory using a Dogent-owned HTML template plus bundled Mermaid JavaScript executed in Playwright Chromium.
- Replace each Mermaid fence in the temporary Markdown copy with a standard Markdown image reference to the rendered asset, so both pandoc and the HTML/PDF path consume the same pre-rendered result.
- Keep ordinary code fences unchanged.
- Keep the user source file unchanged; only temporary Markdown and render assets participate in conversion.

### Markdown Export Failure And Dependencies

- Do not silently fall back to raw Mermaid source if a Mermaid block is detected but rendering fails. Return a clear export/conversion error instead.
- Reuse Playwright Chromium as the rendering runtime instead of introducing a separate Node or Mermaid CLI dependency.
- PDF export already depends on Playwright Chromium. Extend DOCX export/conversion dependency checks so Markdown sources that contain Mermaid fences also request Playwright and Chromium before conversion starts.
- In full package mode, reuse bundled Chromium and ship Mermaid JavaScript in Dogent resources so rendering stays offline and deterministic.

### Markdown Export Edge Cases

- Multiple Mermaid blocks in one Markdown file should render to stable distinct filenames inside the temp workspace so repeated exports do not collide.
- Existing relative image references in the Markdown must continue to resolve correctly after Mermaid block replacement.
- Mermaid syntax errors should surface a readable error that points to the failing block instead of generating blank output.
- This scope changes only Markdown-source export/conversion paths; DOCX/PDF read paths remain unchanged.

### Markdown Export Tests

- Add unit tests for Mermaid fence detection and replacement, while confirming non-Mermaid code fences remain untouched.
- Add export-path tests that mock the Mermaid renderer and verify `_markdown_to_pdf`, `_markdown_to_docx`, and `convert_document_async` all run through the shared pre-render step for Markdown-source conversions.
- Add dependency-manager tests covering `export_document` and `convert_document` for DOCX outputs with and without Mermaid fences.
- Keep the full `python -m unittest discover -s tests -v` suite green after the change.

## Release 0.9.30

### Goal

Make Dogent's reference copy of Anthropic skills syncable from the upstream `https://github.com/anthropics/skills` repository, and replace the currently hardcoded bundled Claude plugin skills with a manifest-driven packaging selection.

### Current Baseline

- `claude/skills` is currently a normal checked-in directory containing the upstream skills repository content.
- `dogent/plugins/claude/skills` currently vendors two skills directly:
  - `pptx`
  - `skill-creator`
- Dogent package data includes `dogent/plugins/**`, and `ConfigManager._install_builtin_plugins` copies packaged plugin directories into `~/.dogent/plugins` at startup.
- The built-in Claude plugin manifest already lives at `dogent/plugins/claude/.claude-plugin/plugin.json`.

### Design Direction

- Convert `claude/skills` into a Git submodule that points to `https://github.com/anthropics/skills`.
- Remove the checked-in bundled copies of `dogent/plugins/claude/skills/pptx` and `dogent/plugins/claude/skills/skill-creator`.
- Add a Dogent-owned manifest file at `dogent/plugins/claude/skills_manifest.json`.
- The manifest is the source of truth for which upstream skills Dogent bundles into the packaged Claude plugin.
- Add a deterministic packaging preparation step that first attempts to update the `claude/skills` submodule to the newest upstream version, then reads `skills_manifest.json`, copies selected skills from `claude/skills/skills/<name>` into `dogent/plugins/claude/skills/<name>`, and fails clearly when a manifest entry does not exist in the available submodule checkout.

### Manifest Format

Use a small JSON file so it can be edited without code changes:

```json
{
  "source": "claude/skills/skills",
  "target": "dogent/plugins/claude/skills",
  "skills": [
    "pptx"
  ]
}
```

- `source` is repo-root relative and should point inside the `claude/skills` submodule.
- `target` is repo-root relative and should point to the package plugin skill directory.
- `skills` is an ordered list of skill directory names to copy.
- The initial default should include only `pptx`, preserving the previously shipped PPTX capability while no longer bundling `skill-creator` by default.
- Empty `skills` is valid and produces a Claude plugin with no bundled skills.

### Packaging Preparation Behavior

- Add a script such as `scripts/prepare_claude_plugin_skills.py`.
- The script should:
  - load `dogent/plugins/claude/skills_manifest.json`;
  - resolve source and target paths relative to repo root;
  - attempt to update `claude/skills` to the newest upstream submodule version before copying;
  - continue with the currently checked-out `claude/skills` version if the update command fails, while printing a warning that names the failed update step;
  - remove and recreate only the target `skills` directory;
  - copy each selected skill directory from the submodule into the target directory;
  - preserve nested files, scripts, references, assets, and license files;
  - print the submodule commit used and copied skill names for release verification;
  - return a non-zero exit code with a clear error when the submodule is missing, the manifest is invalid, or a requested skill does not exist.
- The packaging/release workflow should run this script before `python -m build` so packaged artifacts contain exactly the manifest-selected skills.

### Git Submodule Behavior

- `.gitmodules` should contain a `claude/skills` submodule entry with URL `https://github.com/anthropics/skills`.
- Existing local `claude/skills` content should be replaced by the submodule checkout, not duplicated elsewhere.
- Release/update documentation should tell maintainers to initialize and update the submodule before preparing packages:
  - `git submodule update --init --recursive`
  - `git submodule update --remote claude/skills` when intentionally syncing upstream.
- The preparation script should automate the remote update attempt during packaging, but network or upstream failures must not block packaging when a usable current submodule checkout already exists.

### Compatibility And Install Behavior

- Keep the built-in Claude plugin root and plugin manifest path unchanged so `ConfigManager._install_builtin_plugins` can continue installing `~/.dogent/plugins/claude`.
- Keep package data inclusion for `dogent/plugins/**`.
- Do not add `~/.dogent/plugins/claude` back to default workspace `plugins`; current built-in plugin loading behavior should remain unchanged unless a separate requirement changes it.
- Runtime startup should not require network access or a checked-out submodule. The package must already contain the manifest-selected skills after the packaging preparation step.

### Edge Cases

- If the submodule is not initialized, the preparation script should fail with guidance instead of producing an empty plugin accidentally.
- If the submodule remote update fails but the existing checkout is usable, the preparation script should warn and continue from that checkout.
- If `skills_manifest.json` names `skill-creator`, the script may copy it, but the default manifest should not include it.
- If `dogent/plugins/claude/skills` contains stale files from an earlier build, the preparation script should remove them before copying selected skills.
- If upstream changes a selected skill layout, Dogent should copy the directory as-is and rely on package/build tests to verify expected `SKILL.md` files exist.

### Tests

- Add tests for manifest parsing and copying selected skills into a temporary plugin target.
- Add tests that submodule update failure falls back to the current checkout and emits a warning.
- Add tests that stale target skills are removed before copy.
- Add tests that missing source skills and missing submodule/source directory produce clear failures.
- Update config/bootstrap tests to expect the installed Claude plugin to contain only manifest-selected bundled skills after the packaging preparation step.
- Keep the full `python -m unittest discover -s tests -v` suite green.

## Release 0.9.31

### Goal

Keep the Claude Agent SDK conversation context persistent across all user prompts within a single Dogent interactive session, so users do not need to re-enter information from previous interactions.

### Current Baseline

- After each task completes, `AgentRunner._safe_disconnect()` destroys the `ClaudeSDKClient`, clearing all conversation state.
- The next prompt creates a fresh client with no conversation history.
- Context between tasks is only available through history injection (`{history}` / `{history:last}` template variables in prompts), which provides summaries from `.dogent/history.json`, not the actual conversation messages.
- The client IS kept alive for follow-up states (`needs_clarification`, `needs_outline_edit`, `awaiting_input`), demonstrating the SDK naturally accumulates messages when the same client instance persists across `query()` calls.

### Design Direction

- Keep the `ClaudeSDKClient` connected throughout the interactive session, regardless of task outcome (completed, error, interrupted, aborted).
- Only disconnect on explicit session termination: user exit, profile change, or user-initiated reset.
- The SDK automatically accumulates conversation history when the same client instance receives multiple `query()` calls.

### Changes to AgentRunner

1. **Remove automatic disconnect after task completion.**
   - In `send_message()`, remove the conditional disconnect after streaming completes.
   - The client stays alive regardless of `last_outcome.status`.

2. **Add a `reset()` method.**
   - Disconnects the current client via `_safe_disconnect()`.
   - Clears all internal state (same cleanup as current fresh-start behavior).
   - Called by the CLI on profile changes, explicit reset, and exit.

3. **Keep interrupt handling intact.**
   - The existing interrupt drain logic already handles keeping the client alive for follow-up states; extend this to all states.

4. **Update system prompt between turns.**
   - The existing `self._client.options.system_prompt = system_prompt` update already works for reusing the client.
   - No change needed here; the SDK applies the new system prompt to the next turn while preserving conversation history.

### Changes to DogentCLI

1. **Call `agent.reset()` on `/exit`.** Ensures clean disconnection.
2. **Call `agent.reset()` on profile changes.** When the user changes an LLM, web, vision, or image profile, the underlying model or API endpoint may change, requiring a new client.
3. **Add a `/context` command.** Manages session context with subcommand parameters:
   - `/context reset` — disconnects the agent client and clears internal state, starting a fresh session without exiting Dogent.
   - `/context` without arguments — shows current session context info (e.g., turn count, status).
   - The command is extensible for future subcommands (e.g., `/context compact` for context window summarization).

### History Injection

- Keep existing `{history}` and `{history:last}` template variables unchanged.
- They remain valuable for cross-session context (when Dogent is restarted in the same workspace with existing `.dogent/history.json`).
- Within a session, the SDK's accumulated conversation history provides the primary context.
- Minor token redundancy from history summaries is acceptable for this release.

### Non-Interactive Mode

- `dogent -p "prompt"` continues to create a fresh client and disconnect after the single task.
- Persistent sessions apply only to interactive mode.

### Edge Cases

- **Very long sessions** may approach context window limits. For this release, accept the SDK's natural behavior (the SDK will error if the context window is exceeded). A future release can add automatic summarization or truncation.
- **Client corruption**: if an unrecoverable SDK error occurs mid-session, the CLI should call `agent.reset()` and inform the user that context was cleared.
- **Interrupt during persistent session**: the existing interrupt drain logic should continue to work; the drained partial response does not affect the next turn.
- **Profile change mid-session**: auto-reset ensures the new model/API takes effect immediately without stale session state.

### Tests

- Add a test for session persistence: send two messages through the runner without disconnecting, verify the second response has context from the first.
- Add a test for `reset()` properly disconnecting and clearing state.
- Add a test for the `/context reset` command.
- Add a test that non-interactive mode still disconnects after the run.
- Ensure the full `python -m unittest discover -s tests -v` suite passes.

## Release 0.9.32

### Goal

Upgrade Dogent's Claude Agent SDK baseline from `0.1.72` to `0.2.115`, adapt the SDK integration to relevant upstream changes, and reliably present human confirmation and question prompts originating from main agents or sub-agents, including when several agents request input concurrently.

### Upstream Review

The upstream changelog from `0.1.72` (exclusive) through `0.2.115` and the examples at the `v0.2.115` tag were reviewed. Most releases in this range only update the bundled Claude CLI. The Dogent-relevant changes are:

- `0.1.73`: eager session-store flushing. Dogent does not use `session_store`; no change is required.
- `0.1.74`: hook-event streaming, deferred tool use, strict MCP configuration, richer permission context, `xhigh` effort, and subprocess cleanup. Dogent should consume the richer permission context for its TUI. The other features are not required for this release.
- `0.1.76`: permission suggestions are now deserialized into `PermissionUpdate` objects, and `ResultMessage` exposes `api_error_status`. This fixes the live path used by Dogent's “Allow and remember” response; add coverage using SDK-shaped suggestions. Record the safe HTTP status in failure diagnostics when present.
- `0.1.77`: bare `"Skill"` entries in `allowed_tools` are deprecated in favor of the `skills` option, and SDK errors now preserve actionable result text. Migrate Dogent's explicit skill enablement and verify error rendering.
- `0.2.82`: public `EffortLevel`, stderr isolation, and tighter permission-suggestion typing. Dogent does not configure effort or a stderr callback; the tighter typing agrees with the permission migration above.
- `0.2.88`: Trio compatibility for session stores. Dogent uses asyncio and no session store; no change is required.
- `0.2.96`: the SDK pins `mcp<2`. Dogent receives this transitively; no direct dependency change is required.
- `0.2.101`: terminal background-task state can arrive only as `TaskUpdatedMessage`, without `TaskNotificationMessage`. Dogent must handle both forms so task state and TUI feedback do not remain stale.
- `0.2.111`: cancellation-safe subprocess cleanup, robust large-NDJSON parsing, defensive content parsing, and a warning when `can_use_tool` is shadowed by broad allow rules. The first three are transparent fixes. Dogent must retain `permission_mode="default"` and avoid broad `allowed_tools` entries whenever its callback is active.
- `0.2.112` through `0.2.115`, and the other versions not called out above, update the bundled Claude CLI only. They require runtime regression testing rather than API changes.

The `v0.2.115` examples confirm the integration patterns Dogent already uses: long-lived `ClaudeSDKClient` sessions use `connect()`/`query()`/`receive_response()`, permission callbacks use `permission_mode="default"` without broad allow rules, hooks are asynchronous, custom agents are enabled through SDK options, and `tools=[]` is valid for restricted helper clients. The only example changes between the two target tags are session-store documentation and the S3 adapter, which Dogent does not use.

### Current Baseline and Root Cause

- `pyproject.toml` currently declares `claude-agent-sdk>=0.1.72`.
- `ConfigManager.build_options()` uses a bare `"Skill"` allow entry in the no-callback path.
- `AgentRunner` handles `TaskStartedMessage`, `TaskProgressMessage`, and `TaskNotificationMessage`, but not `TaskUpdatedMessage`.
- The SDK spawns each incoming control request in a separate asynchronous task. Parallel agents can therefore invoke Dogent's `can_use_tool` callback concurrently.
- Dogent forwards each callback directly into a `prompt_toolkit` selection UI. There is no shared lock or queue across permission and `AskUserQuestion` prompts, so concurrent callbacks can compete for the terminal.
- `ToolPermissionContext.agent_id`, `tool_use_id`, and the new display fields are discarded. As a result, the TUI cannot identify a sub-agent request even when the SDK supplies attribution.

### SDK Upgrade and Compatibility Changes

1. Raise the dependency floor to `claude-agent-sdk>=0.2.115`, preserving the project's existing minimum-version constraint style.
2. Replace the deprecated bare `"Skill"` allow entry with the SDK's `skills` option in paths that explicitly auto-enable skills. Keep callback-enabled sessions free of broad allow entries so tool requests can reach Dogent's permission handler.
3. Audit every direct SDK construction path (`AgentRunner`, init wizard, lesson drafter, MCP helpers, web/vision/image tools) against the `0.2.115` types and examples. Do not adopt unrelated new features merely because they exist.
4. Continue using `permission_mode="default"` with `can_use_tool`. Add an options-level regression test proving callback-enabled sessions do not contain broad `allowed_tools` rules that would shadow confirmations.
5. Use the SDK-deserialized `PermissionUpdate` suggestions for “Allow and remember”; malformed or absent suggestions remain non-fatal.
6. Include `ResultMessage.api_error_status` in logged/displayed failure diagnostics when available, without logging response content beyond Dogent's existing error handling.

### Agent-Aware Human Interaction Gate

Introduce a single FIFO gate in `AgentRunner` for all SDK-driven terminal interaction: tool permission confirmations and SDK-native `AskUserQuestion` prompts.

1. Create an internal request model carrying the interaction kind, `agent_id`, `tool_use_id`, tool name/input, SDK display metadata, and Dogent's policy reason.
2. Serialize requests with one async lock/queue before entering any CLI `prompt_toolkit` application. Only one prompt may own stdin at a time; queued requests are shown in arrival order.
3. Re-check abort/interruption state after acquiring the gate. If the task was cancelled while a request waited, return a denying/interrupted result without opening stale UI.
4. Keep the wait indicator stopped while any human prompt is active. Resume it only after the active prompt closes, the request was allowed, and no abort is pending.
5. Pass attribution into both CLI callback types. `agent_id=None` is rendered as “Main agent”; otherwise render a shortened, stable “Sub-agent <id>” label. Log the full opaque ID and tool-use ID in debug/session events.
6. Prefer the SDK's `title`, `display_name`, `description`, `decision_reason`, and `blocked_path` when present, while retaining Dogent's local permission evaluation as the authorization source of truth.
7. Route sub-agent `AskUserQuestion` requests through the same gate and attribution model so confirmations and questions cannot overlap.
8. Scope permission denial by origin. A main-agent Deny or cancellation aborts the current Dogent turn. A sub-agent Deny or cancellation returns an interrupting permission denial only for that sub-agent and does not set Dogent's global abort state or interrupt the shared SDK client, allowing the main agent and sibling agents to continue. “Allow and remember” continues to apply the SDK's session suggestions and Dogent's stored path authorization.
9. A scoped sub-agent denial is not a session-wide deny rule for the target file or operation. The main model may independently decide to retry or reassign unfinished work from the user's original request; any such main-agent action is evaluated as a new tool request and must receive its own main-agent permission decision.

### TUI Scheme

Permission prompts retain the existing numbered selection interaction, but make origin and consequence explicit:

```text
╭─ Permission required · Sub-agent a1b2c3 ─────────────────────╮
│ Read file                                                     │
│ /etc/hosts                                                    │
│                                                               │
│ Reason: Path is outside the current workspace.                │
│                                                               │
│ * 1) Allow                                                    │
│   2) Allow and remember                                       │
│   3) Deny (stop this sub-agent)                               │
╰───────────────────────────────────────────────────────────────╯
```

- Main-agent prompts use the same layout with “Main agent” and retain the explicit `Deny (abort current Dogent task)` consequence.
- SDK question panels add the same origin label to the existing clarification title and retain single-select, multi-select, default, free-form, cancel, and timeout behavior.
- When several agents request input together, Dogent shows complete panels one at a time. It must never start parallel prompt applications or print interleaved option lists.

#### UAT Refinement: Dedicated Prompt Area

The first Story 2 UAT found that normal main-agent output could overwrite an active sub-agent prompt. The terminal layout is refined as follows:

```text
┌─ Main-agent output / scrollback ──────────────────────────────┐
│ New streamed output and task events are written above.        │
└───────────────────────────────────────────────────────────────┘
┌─ Permission required · Sub-agent a1b2c3 ─────────────────────┐
│ Active prompt and choices remain fixed at the terminal bottom.│
│                                                              │
│ > Allow                                                      │
│   Allow and remember                                         │
│   Deny (abort current Dogent task)                           │
│                                                              │
│ Active: Sub-agent a1b2c3 | 2 queued requests                 │
└───────────────────────────────────────────────────────────────┘
```

- Run interactive permission and SDK-question applications inside `prompt_toolkit.patch_stdout(raw=True)`. Output produced while the prompt is active is routed above the application, after which the bottom prompt area is redrawn.
- Use a framed bottom area for single-select and multi-select questions. Multi-select uses Up/Down to move, Space to toggle, and Enter to confirm.
- Continue processing concurrent requests through the FIFO gate. The footer identifies the active agent and the number of requests waiting behind it; after resolution, the next queued request replaces the bottom panel.
- Non-interactive/text fallback retains numbered text prompts and includes the same active/queued status line.

### Background Task Lifecycle

1. Import and handle `TaskUpdatedMessage` plus `TERMINAL_TASK_STATUSES` in the response stream.
2. On a terminal update, clear `_last_task_progress` even if no notification arrives, log the update, and render a completion/failure/stopped panel using the patch data available.
3. Avoid duplicate terminal panels when both a terminal update and a later `TaskNotificationMessage` arrive for the same task. Maintain a small per-turn set of finalized task IDs and clear it on reset/new turn.
4. Unknown or non-terminal patches remain available to debug logging but do not create noisy panels.

#### UAT Refinement: Final Background-Task Reconciliation

The Story 3 UAT showed that the SDK can emit a successful `ResultMessage` while spawned sub-agents are still active, or with result text that explicitly says Dogent is still waiting for their output. Treat that first result as provisional instead of presenting it as the completed turn.

1. Track task IDs started during the current turn, independently of the short-lived progress display state.
2. If a successful result arrives while a tracked task is active, or its text states that background agents are still working/waiting, suppress that incomplete result and issue one internal follow-up query on the same persistent client.
3. The follow-up directs the main agent to wait through the SDK task tools, collect every sub-agent result, and return one consolidated final answer. Limit reconciliation to one attempt per user turn so an uncooperative model cannot loop indefinitely.
4. Remove the legacy no-op `PreToolUse` keepalive hook from callback-enabled SDK options. The `0.2.115` permission callback works without a dummy hook, and leaving that hook pending caused an exit-time `hook_0` / closed permission-stream error.

### Edge Cases

- Two or more parallel sub-agents request permission or ask questions at nearly the same time: requests remain serialized and attributable.
- A main-agent request arrives while a sub-agent prompt is open: it waits in the same FIFO order.
- Esc/Ctrl+C interrupts an active prompt or the overall task: the active UI exits cleanly, queued requests do not reopen, and SDK control requests receive denial/interruption responses.
- A sub-agent finishes while its prompt is queued: an SDK cancellation removes or safely denies that request without affecting terminal ownership.
- A sub-agent permission is denied while sibling agents are running: only that sub-agent is interrupted; queued sibling prompts and the main turn remain active.
- The main model retries work after a sub-agent denial: treat it as a new main-agent action, display a separately attributed permission prompt, and honor that new decision without silently carrying over the sub-agent's denial.
- Permission metadata is absent (older/custom CLI payload): fall back to Dogent's tool name and policy reason.
- Permission suggestions are empty or malformed: “Allow and remember” still records valid Dogent authorizations and skips invalid SDK updates.
- A background task emits both terminal message forms: task tracking is cleared once and the terminal panel is not duplicated.
- Non-interactive modes retain their current auto-allow/deny callback behavior and never open a TUI prompt.

### Tests

- Add SDK `0.2.115` option-construction tests for the dependency-facing behavior, `skills` migration, default permission mode, and absence of callback-shadowing broad allow rules.
- Add permission tests using `ToolPermissionContext` with `agent_id`, `tool_use_id`, rich display fields, and deserialized `PermissionUpdate` suggestions.
- Add asynchronous tests that issue parallel main/sub-agent permission and question requests, proving FIFO ordering and a maximum of one active CLI prompt.
- Add cancellation tests for active and queued human requests, including wait-indicator cleanup.
- Add CLI rendering tests for main-agent and sub-agent permission/question titles and the explicit Deny consequence.
- Add permission-result tests proving sub-agent denial leaves the global turn/client active while main-agent denial still aborts the whole turn.
- Add stream tests for terminal `TaskUpdatedMessage`, duplicate suppression with `TaskNotificationMessage`, and state cleanup on reset/new turn.
- Add stream tests proving an incomplete background-task result triggers exactly one consolidation turn and an already consolidated result does not trigger another query.
- Add result diagnostics coverage for `api_error_status` and actionable SDK error text.
- Run the full `python -m unittest discover -s tests -v` suite with `claude-agent-sdk 0.2.115` installed.

## Release 0.9.33 - Persistent Status Bar

### Goal

Add a polished, single-line status bar at the bottom of the idle interactive
Dogent terminal. It displays the active LLM model, current context-window usage
percentage, and workspace path. While the agent is working, suspend the status
bar and use the existing timed wait indicator instead.

### Confirmed behavior

- "Module name" in the requirement means the active LLM model name.
- The bar is visible while Dogent is idle and collecting user input. It is
  hidden for the complete lifetime of each active agent turn.
- While an agent turn is active, the existing `Waiting for LLM response`
  indicator with elapsed time owns the bottom line on demand.
- `/context reset` clears the SDK session and immediately clears the context
  measurement.
- The feature is for an interactive TTY. Non-interactive `dogent -p` output and
  redirected output do not render terminal control sequences or a status bar.
- The status bar belongs to Dogent's main TUI. The full-screen Markdown editor
  does not display it; the bar is restored when the user returns to the main UI.

### Current baseline

- `DogentCLI` uses `PromptSession` only while collecting input and Rich for
  output while commands and the agent run. A `PromptSession.bottom_toolbar`
  alone therefore cannot satisfy the persistent-display requirement.
- `AgentRunner` already receives the resolved model and usage dictionaries on
  `AssistantMessage`. `ResultMessage.usage` is cumulative across all API steps
  in a query, so it must not replace the most recent per-message context value.
- The existing context-clearing command is `/context reset`; it calls
  `AgentRunner.reset()`, which closes the SDK client and resets turn state.

### Status state and data flow

Introduce a small shared status model, owned by the CLI and updated by the
agent through a callback rather than by reaching into terminal-rendering code.
The model contains:

- configured model name and latest resolved main-agent model name;
- workspace root;
- resolved context-window capacity;
- latest main-agent input-token count and calculated percentage;

At startup, show the configured model, workspace path, and `Context --`.
For each main-agent `AssistantMessage` with usage, replace (do not accumulate)
the context token count with:

Use an explicit `total_input_tokens` value when a provider supplies it.
Otherwise, normalize the common provider variants before calculating usage:

- when `input_tokens` is smaller than the cache counters, treat it as fresh
  input and add cache-created plus cache-read tokens;
- when `input_tokens` is at least the combined cache counters, treat it as an
  inclusive provider total and do not add the cache fields again.

This prevents third-party gateways from double-counting cache tokens while
retaining Claude's split-counter behavior. Ignore output tokens, sub-agent
messages (`parent_tool_use_id` is set), missing usage, and duplicate messages
for accumulation purposes. Updating with the same message again is harmless
because the latest value replaces the previous value.

The percentage is clamped to `0..100` for rendering while retaining the raw
token values for diagnostics. Before a usable assistant measurement exists,
show `--` instead of a misleading `0%`.

When `/profile llm` changes the configured profile, atomically update the
displayed model, clear the old usage, and resolve capacity for the new model.
The resolved model reported by a later main-agent message may refine the label
(for example after fallback), but an explicit configured `[1m]` suffix remains
visible and continues to control capacity.

### Context-window capacity resolution

Resolve capacity once per selected model and cache it for the session. The
precedence is:

1. A valid positive `CLAUDE_CODE_MAX_CONTEXT_TOKENS` value when
   `DISABLE_COMPACT` is enabled, matching Claude Code's documented override.
2. An explicit case-insensitive `[1m]` suffix on the configured model name,
   which resolves to `1_000_000` tokens. Preserve the suffix in the displayed
   name even if Claude strips it before sending the provider model ID.
3. A non-blocking lookup of `max_input_tokens` from the Claude Models API when
   the configured endpoint supports it. Apply a short timeout, cache a valid
   response, and never expose credentials in logs.
4. A `256_000` token fallback for gateways, aliases, offline sessions, lookup
   failures, or malformed responses.

The lookup must not delay CLI startup or prevent the bar from rendering. When a
background lookup returns a valid capacity, recalculate and refresh the current
percentage. Do not use `CLAUDE_CODE_AUTO_COMPACT_WINDOW` as the denominator: it
controls compaction and can intentionally be smaller than the model's actual
window.

Relevant upstream behavior:

- Claude Code status lines receive `context_window.context_window_size` and
  calculate used percentage from input plus cache-created plus cache-read
  tokens: <https://code.claude.com/docs/en/statusline>
- Claude Code accepts `[1m]` on aliases and full model names:
  <https://code.claude.com/docs/en/model-config>
- Claude Code documents the context-related environment variables:
  <https://code.claude.com/docs/en/env-vars>
- The Models API exposes `max_input_tokens`:
  <https://platform.claude.com/docs/en/api/models/retrieve>

### Rendering architecture

Add a single status controller that owns terminal refreshes and prevents Rich
and prompt_toolkit from competing for the bottom row.

- While the normal prompt is active, render the shared formatter through a
  dynamic `PromptSession.bottom_toolbar` callable.
- While idle outside prompt_toolkit, use one non-periodic Rich live region.
- Suspend the status controller before starting an agent turn and restore it
  only after that turn completes. While suspended, it cannot start a Rich live
  region, return prompt toolbar fragments, or attach a status window to a
  confirmation or clarification layout.
- Let `LLMWaitIndicator` retain its original Rich status display while the
  status controller is suspended. It displays `Waiting for LLM response` with
  an elapsed timer and updates only while Dogent is waiting on the model.
- Add the status row to idle main-TUI prompt_toolkit layouts. Pause the status
  controller before opening the separate full-screen Markdown editor and
  restore it cleanly when returning to the main TUI; the editor itself does not
  render the status bar.
- Explicitly start/stop and restore each renderer at mode boundaries and on
  exceptions, interrupts, EOF, and graceful exit. Do not leave an alternate
  screen, reserved row, hidden cursor, or stale escape sequence behind.
- Serialize refreshes on the event-loop thread. Agent callbacks only mutate
  state and request invalidation; they do not write directly to the terminal.

### Visual design and responsive behavior

The wide layout is one restrained, high-contrast row:

`✦ claude-sonnet-4-6[1m]  │  Context [████░░░░░░░░░░░░░░░░] 20%  │  📁 ~/Codes/dogent`

- Do not set a status-bar background. Explicitly override prompt_toolkit's
  default bottom-toolbar background and use the same highlighted foreground
  palette in prompt_toolkit and Rich: bold cyan for model/context text, bold
  green for the meter and percentage, bold blue for the workspace, and a
  subdued separator.
- Keep labels and meaning available without relying on color alone.
- Display the workspace as a normalized absolute path with the home directory
  shortened to `~`.
- Recalculate on terminal resize. First middle-truncate the path, then shorten
  the model, then reduce/remove the ten-cell meter. The narrowest form remains
  meaningful: `<model> │ Ctx <pct> │ <folder>`.
- Sanitize model and path text so embedded control characters or Rich markup
  cannot alter terminal output. Render one physical row with ellipsis rather
  than wrapping.
- Use plain Unicode symbols already compatible with Dogent's CLI style, with a
  readable text fallback if the terminal cannot render them reliably.
- Capture interactive-TTY capability at CLI startup and reuse it across Rich
  and prompt_toolkit handoffs so temporary stdout wrappers cannot disable the
  Markdown editor.

### `/context reset` lifecycle

- Keep `reset` as the sole context-reset subcommand in completion and help.
- `/context reset` disconnects/resets the active SDK session and then atomically sets
  status usage back to unknown. The bar immediately reads `Context --`; model,
  capacity, and workspace remain visible.
- `/context` reports the exact normalized used-token count, resolved capacity,
  and rounded percentage for diagnosing provider usage semantics.
- The next main-agent response starts a fresh measurement. No pre-reset token
  value may flash or return from a stale/late callback.
- Use a context generation identifier so an update originating from a session
  that was reset cannot update the new status state.

### Failure and edge cases

- Missing model: display `model unavailable` without hiding the bar.
- Invalid context override or Models API result: log at debug level and use the
  next resolver/fallback; never fail the session.
- Usage keys may be absent, strings, negative, or malformed. Accept only
  non-negative integers and retain the previous valid value otherwise.
- LLM profile/model changes reset usage and capacity resolution so values from
  the previous model cannot be displayed under the new model name.
- A configured custom gateway may not implement the Models API. This is an
  expected fallback, not a user-facing error.
- Interrupts, permissions, clarification dialogs, multiline editing, terminal
  resize, and shell commands retain a single non-duplicated bottom row in the
  main TUI. Entering the full-screen editor removes the row with the main TUI,
  and returning restores exactly one row.
- Status rendering must not be written into session history/log content and
  must not consume model tokens.

### Automated tests

- Unit-test capacity precedence, `[1m]` parsing, environment validation, Models
  API success/failure/timeout, caching, and 256K fallback.
- Unit-test usage extraction, split and inclusive cache-counter normalization,
  output-token exclusion, main-agent filtering, malformed values, clamping,
  and generation-based stale update rejection.
- Unit-test wide/medium/narrow formatting, thresholds, path/model truncation,
  sanitization, and non-TTY suppression.
- Test renderer handoffs between prompt, Rich live output, main-TUI dialogs,
  editor pause/restore, and shutdown without nested live displays or leaked
  terminal state.
- Extend context-command tests for immediate status reset through the existing
  `/context reset` command while preserving its completion and help behavior.
- Run `python -m unittest discover -s tests -v`.
