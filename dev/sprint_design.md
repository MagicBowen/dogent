# Design

## Release 0.9.5

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

## Release 0.9.6

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

## Release 0.9.7

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
