# Design

---

## Release 0.9.8
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
