# Changelog

All notable changes to this project will be documented in this file.

## 0.9.29 - 2026-04-05

### Fixed
- Built-in Dogent MCP tools now execute correctly again on the latest Claude Agent SDK / MCP runtime path instead of failing before their actual tool logic runs.
- Dogent's in-process MCP server registration now follows the current low-level MCP request/result contract for built-in document, UI, web, vision, and image tools.

### Changed
- Added regression coverage for real MCP `tools/list` and `tools/call` round-trips across all built-in Dogent MCP tool families.
- Cleaned the shipped global default profile template so repo defaults use placeholders instead of credential-like values.

---

## 0.9.28 - 2026-03-29

### Added
- Native `/template` workflows for listing, creating, and optimizing document templates from the CLI.
- A built-in Dogent `doc-template-creator` skill for template authoring and optimization.
- Support for using `@file` and `@@template` references inside `/template create` briefs, including interactive completion.

### Changed
- Document templates now use the skill-style `SKILL.md` directory format, with reusable references under `templates/`.
- Built-in document templates were migrated to the new layout and are still available through `/init` and `@@`.
- The Dogent built-in plugin under `~/.dogent/plugins/dogent` is now auto-enabled without requiring `dogent.json` configuration.

### Fixed
- `/template` inventory and generated template metadata now read descriptions reliably from YAML frontmatter.
- `/template` completion now includes `list` and keeps file/template completion available inside `/template create` free-text input.

---

## 0.9.27 - 2026-03-29

### Added
- SDK-native clarification for simple multiple-choice follow-up questions via `AskUserQuestion`.
- Project command and skill discovery from both workspace `.claude` and `.dogent` roots.
- SDK-aware runtime feedback for usage, task progress, rate-limit warnings, and opt-in partial response streaming.

### Changed
- `/init` now uses structured SDK output for `doc_template`, `primary_language`, and generated `dogent.md` content.
- Dogent now treats `Agent` as the primary subagent tool name while remaining compatible with legacy SDK `Task` references.
- Selected Dogent MCP tools now publish conservative `ToolAnnotations` to improve SDK behavior hints.

### Fixed
- Permission callbacks now follow the documented Claude Agent SDK streaming hook pattern and apply session-scoped permission suggestions without replacing persisted workspace authorizations.
- Restricted helper flows now use explicit SDK `tools` restrictions instead of relying on `allowed_tools=[]`.

---

## 0.9.26 - 2026-03-06

### Fixed
- Prompts submitted from the `Ctrl+E` markdown editor are now recorded in prompt recall history, so Up Arrow can restore them later in the same session.
- Recalled `Ctrl+E` prompts now preserve the exact submitted multiline content, including blank lines and spacing, for further inline editing or reopening in the editor.
- Discarded or cancelled `Ctrl+E` editor sessions no longer create prompt history entries.

---

## 0.9.25 - 2026-02-07

### Added
- Plugin command naming by location: `~/.claude/plugins` uses `/claude:<plugin>:<command>`, `~/.dogent/plugins` uses `/<plugin>:<command>`.
- Permission exception for reads under `~/.claude` and temp-file deletes within a task.
- Export docs note PDF dependencies (Pandoc + Chrome) and the default Claude PPTX skill.

### Changed
- Renamed config key `claude_plugins` to `plugins` (workspace + global defaults).

---

## 0.9.24 - 2026-02-07

### Added
- Built-in Claude plugin packaging (PPTX skill) and auto-install to `~/.dogent/plugins`.
- New workspace defaults include `~/.dogent/plugins/claude` in `claude_plugins`.

### Changed
- Built-in plugins overwrite/update on startup to keep assets in sync.

### Fixed
- Access to `~/.dogent/plugins` no longer triggers permission prompts.

---

## 0.9.23 - 2026-02-03

### Added
- Markdown editor dropdown completion for `@` file paths and `@@` doc templates (general/workspace/global/built-in).

### Fixed
- Arrow keys now navigate the completion menu in the markdown editor instead of moving the cursor.

---

## 0.9.22 - 2026-02-01

### Added
- Prompt history recall seeded from `.dogent/history.json`, including `/` commands, limited to the last 30 items.
- Tool-based UI flow for clarification and outline edits via `mcp__dogent__ui_request`.

### Changed
- Clarification answers and outline follow-up messages are still stored in history but excluded from up-arrow recall.
- Clarification/outline UI now relies on tool calls only; tag parsing paths are removed.

### Fixed
- Structured UI handling uses the current `outline_text` and no longer mixes tag parsing with tool payloads.
