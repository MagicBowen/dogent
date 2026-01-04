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