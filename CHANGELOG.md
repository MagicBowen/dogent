# Changelog

All notable changes to this project will be documented in this file.

## 0.9.35 - 2026-08-23

### Added
- Added ready-made GLM-5.3 and DeepSeek V4 Flash Vision Exp LLM profiles to fresh and upgraded global configurations.
- Added a DeepSeek V4 Flash Vision Exp vision profile for JPEG, PNG, GIF, and WebP analysis through the existing media-analysis workflow.

### Changed
- Raised the minimum supported `claude-agent-sdk` version to `0.2.144` and kept Dogent's bundled MCP tools compatible with both MCP 1.x and 2.x runtimes.

### Fixed
- DeepSeek vision requests now report clear local errors for video and unsupported image formats and preserve existing GLM image/video behavior.

## 0.9.34 - 2026-07-13

### Fixed
- Mermaid diagrams exported to PDF now use valid scalable vector graphics, keeping complex labels sharp and preventing broken-image placeholders.
- Display formulas wrapped in `$$` now render across standard, single-line, and multiline delimiter layouts.
- Inline formulas wrapped in `$` now render as typeset math while currency, escaped dollars, inline code, and fenced code remain literal.

## 0.9.33 - 2026-07-12

### Added
- The interactive TUI now shows a polished idle status line with the active LLM model, live context-window usage, and normalized workspace path.
- `/context` now reports exact normalized token usage and resolved context capacity for diagnostics.

### Changed
- Context capacity resolves from the documented Claude override, a model `[1m]` suffix, the Models API when available, or a 256K fallback.
- The idle status line is suspended during agent turns so the timed `Waiting for LLM response` indicator and streaming output retain exclusive control of the bottom line.

### Fixed
- Context usage no longer double-counts cache tokens from gateways that report inclusive input totals.
- Status rendering now inherits the terminal background, keeps highlighted foreground colors and a green usage meter, and restores cleanly after the Markdown editor, resize, interruption, and profile or context reset.

## 0.9.32 - 2026-07-10

### Added
- Agent-aware permission and clarification prompts identify the main agent or originating sub-agent and serialize concurrent requests through one FIFO interaction queue.
- Background task lifecycle feedback now handles terminal SDK task updates and consolidates completed sub-agent results before presenting the final response.

### Changed
- The minimum supported `claude-agent-sdk` version is now `0.2.115`, with skill configuration and permission suggestions aligned to the current SDK interfaces.
- Sub-agent permission denial stops only that sub-agent, while main-agent denial continues to abort the whole Dogent turn; later retries remain separately attributed and require a new permission decision.

### Fixed
- Main-agent output no longer overwrites an active sub-agent prompt, and simultaneous agent questions no longer interleave their options.
- Dogent no longer presents an incomplete “Completed” result while background agents are still working or waiting to be collected.
- Clean exit after background work no longer reports stale hook callback or closed permission-stream errors.
- Package resource loading is compatible with Python 3.14 while retaining the Python 3.10 minimum.

## 0.9.31 - 2026-06-07

### Added
- Persistent session context: the agent now remembers all previous interactions within the same interactive session, so users do not need to re-enter information from earlier turns.
- `/context` command shows current session info (turn count, session status).
- `/context reset` clears conversation context mid-session without exiting Dogent.

### Changed
- The agent client stays connected across completed, errored, and interrupted tasks within an interactive session.
- Changing an LLM/web/vision/image profile automatically resets the session context.
- Exiting Dogent cleanly disconnects the agent.

---

## 0.9.30 - 2026-05-04

### Added
- `claude/skills` is now managed as a Git submodule of `https://github.com/anthropics/skills` so maintainers can sync upstream Anthropic skills directly.
- Added a manifest-driven preparation script for bundled Claude plugin skills, including update-or-fallback handling for the skills submodule.

### Changed
- Built-in Claude plugin skill packaging now copies only manifest-selected skills from the submodule before building release artifacts.
- The default Claude plugin bundle keeps the `pptx` skill and no longer bundles `skill-creator`.
- The minimum supported `claude-agent-sdk` version is now `0.1.72`.

---

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
