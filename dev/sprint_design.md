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
