# Design

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
