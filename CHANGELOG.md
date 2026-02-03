# Changelog

All notable changes to this project will be documented in this file.

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
