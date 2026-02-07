# Changelog

All notable changes to this project will be documented in this file.

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
