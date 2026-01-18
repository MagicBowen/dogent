# Design

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
  - For pip downloads, use `pip --progress-bar raw` to emit parseable progress.
  - For pandoc, implement a small downloader with progress callbacks if pypandoc does not emit percent.
  - For Playwright Chromium install, parse `playwright install` output percent lines.

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
