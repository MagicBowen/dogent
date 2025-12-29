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
- Automatically analyze every `@image`/`@video` reference with a vision model and inject a JSON summary into the user prompt.
- Support multiple vision providers via profiles, configurable in workspace config, with only GLM-4.6V implemented initially.
- Fail fast on vision analysis errors with a user-friendly message.
- No local caching for media analysis.

### Decisions
- Add `vision_profile` to `.dogent/dogent.json` and a new global config file `~/.dogent/vision.json`.
- Default `vision_profile` to `glm-4.6v` in the template; if the profile is missing or has placeholder credentials, fail with a clear configuration error when media is referenced.
- Implement a provider registry with a `VisionClient` interface; only `glm-4.6v` is wired initially.
- Vision summaries are inserted into the user prompt as JSON (no markdown) alongside the attachment list.

### Architecture
- Add `dogent/vision.py`:
  - `VisionProfile` dataclass with fields: `provider`, `model`, `base_url`, `api_key`, optional `extra`.
  - `VisionClient` protocol: `analyze_image(path) -> dict`, `analyze_video(path) -> dict`.
  - `GLM4VClient` implementation using the BigModel chat completions API.
  - `VisionManager` loads profiles, validates placeholders, and dispatches to providers.
- Extend `DogentPaths` to include `global_vision_file` (`~/.dogent/vision.json`).
- Extend `ConfigManager` to:
  - Create `vision.json` template on first run with a `glm-4.6v` profile stub.
  - Load the selected `vision_profile` from workspace config and validate it.
- Extend attachment handling:
  - Detect media file extensions (image: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`; video: `.mp4`, `.mov`, `.mkv`, `.webm`).
  - Before building the user prompt, analyze each media attachment and attach a parsed JSON summary.
  - Non-media attachments are passed through unchanged.

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
- Update the user prompt attachments section to emit JSON, e.g.:
  ```
  [
    {"path": "assets/photo.png", "type": "image", "vision": {"summary": "..."}},
    {"path": "clips/demo.mp4", "type": "video", "vision": {"summary": "..."}}
  ]
  ```
- If no attachments exist, keep the existing "No @file references." sentinel.

### Failure Behavior
- If a media file is referenced and vision analysis fails:
  - Abort the request before sending to the writing LLM.
  - Render a clear error panel with next steps (configure `vision_profile`, check file size/format).
- No retries or caching in 0.9.6.

### Tests
- Config tests for `vision_profile` resolution and placeholder warnings.
- Unit tests for attachment JSON formatting with vision summaries.
- Vision manager tests with mocked providers to cover success and error paths.
