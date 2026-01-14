# Dogent Usage Guide

## Install
- Python 3.10+ is required.
- From the project root: `pip install -e .`
- Verify the CLI: `dogent -v` and `dogent -h`.

## Quick Start
1) `cd` into your project directory.
2) Run `dogent` to enter the interactive shell.
3) Run `/init` to create `.dogent/dogent.md` and `.dogent/dogent.json`.
4) Ask a request (for example: “Draft a project README outline”).
5) Use `/exit` to leave the CLI.

One-shot mode:
- `dogent -p "prompt"` runs once without the interactive shell.
- Add `--auto` to auto-approve permissions and skip clarifications.
- If `.dogent/dogent.json` is missing, one-shot mode initializes defaults automatically.

One-shot exit codes:
- `0`: completed successfully (prints `Completed.` after the summary).
- `1`: error.
- `2`: usage error.
- `10`: permission required (default `-p` fails fast).
- `11`: clarification required.
- `12`: outline edit required.
- `13`: awaiting input.
- `14`: interrupted.
- `15`: aborted.

## Configuration
Dogent reads configuration from both a global file and the workspace:

- Global config: `~/.dogent/dogent.json` (profiles and defaults).
- Workspace config: `.dogent/dogent.json` (overrides global defaults).
- Schema for editor validation: `~/.dogent/dogent.schema.json`.

Common workspace fields:
- `llm_profile`: name of the model profile in the global config.
- `web_profile`: `default` for native web tools, or a named profile.
- `vision_profile`: `null` to disable vision, or a named profile.
- `doc_template`: template name (`general`, `resume`, etc.).
- `primary_language`: response language for the CLI.
- `learn_auto`: enable automatic lesson capture.
- `editor_mode`: `default` or `vi`.
- `authorizations`: tool -> path patterns for remembered permissions (wildcards supported).
- `claude_plugins`: list of local plugin paths (absolute or workspace-relative).

If `llm_profile` is missing, Dogent falls back to environment variables.

## Profiles
Use `/profile` to check or update workspace profiles:
- `/profile` shows current selections.
- `/profile show` shows current selections and available profile keys.
- `/profile llm|web|vision <name>` updates the selection (completion lists values after a trailing space).
- Vision can be disabled by setting `vision_profile` to `null` (shown as `none` when no vision profiles exist).

## Debug Logging
Use `/debug` to inspect or update logging configuration:
- `/debug` shows the current config.
- `/debug off|session|error|session-errors|warn|info|debug|all` sets the config.
- `custom` opens the interactive selector for session and level.

Logs are stored in `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md` when enabled.

## Templates
Templates control output structure and formatting.

- Workspace templates: `.dogent/templates/<name>.md`
- Global templates: `~/.dogent/templates/<name>.md` (use `global:<name>`)
- Built-in templates: `dogent/templates/<name>.md` (use `built-in:<name>`)
- Default: `doc_general.md` (used when `doc_template=general`)

One-off template override in a prompt:
- Use `@@<template>` (example: `@@global:resume`).
- This does not modify config files.

## File References
Attach local files by prefixing with `@`:
- `@notes.md`
- `@data.xlsx#Sheet1`

Dogent resolves file paths inside the workspace and includes file metadata in prompts.

To read content explicitly, the agent can call `mcp__dogent__read_document`.
For long documents, pass `offset` and `length` to page through content; responses include
`total_chars` and `next_offset` in metadata.

## Document Export and Conversion
Dogent supports export and conversion tools:
- Export Markdown: `export_document` tool (PDF or DOCX).
- Convert documents: `convert_document` tool (DOCX/PDF/MD).

DOCX export includes local images referenced in Markdown or HTML, including:
- `![](../images/1.png)`
- `<div align="center"><img src="../images/2.png" width="70%"></div>`

## Web Tools
Two modes are supported:
- Native (default): uses Claude Agent SDK tools.
- Custom: set `web_profile` to a named profile under `web_profiles` in `~/.dogent/dogent.json`.

If the named web profile is missing, Dogent warns and falls back to native mode.

## Vision Tools
Vision is disabled by default.
- Set `vision_profile` in `.dogent/dogent.json` to enable.
- Provide the profile in `~/.dogent/dogent.json` under `vision_profiles`.
- Use local file paths for images/videos.

## Commands
- `/init` — initialize `.dogent` files.
- `/edit <path>` — open a workspace file in the Markdown editor.
- `/learn <text>` — save a lesson; `/learn on|off` toggles auto-learn.
- `/show history` — show recent history and latest todos.
- `/show lessons` — show recent lessons.
- `/clean [history|lesson|memory|all]` — clear workspace state.
- `/archive [history|lessons|all]` — archive history or lessons.
- `/exit` — exit the CLI.
- `/claude:<name>` — custom Claude command loaded from `.claude/commands`.
- `/claude:<plugin>:<name>` — custom command loaded from a configured plugin.

Shortcuts:
- `Esc` interrupts a running task.
- `Ctrl+E` opens the editor (Ctrl+P preview, Ctrl+Enter submit, Ctrl+Q return).
- `Alt/Option+Enter` inserts a newline.
- `Ctrl+C` exits.
- `!<command>` runs a shell command in the workspace.

## Permissions
Dogent requires confirmation for sensitive operations:
- File access outside the workspace root.
- Destructive commands (rm/rmdir/del/mv).
- Modifying existing `.dogent/dogent.md`.

If you deny a prompt, the task is aborted and the agent stops safely.
Choosing “Allow and remember” records the paths under `authorizations` in `.dogent/dogent.json` so future runs skip the prompt.

## Claude Commands & Plugins
- Place commands in `.claude/commands/*.md` (project) or `~/.claude/commands/*.md` (user).
- Dogent registers them with a `/claude:` prefix to avoid conflicts.
- Configure plugin roots in `.dogent/dogent.json` under `claude_plugins`:

```json
{
  "claude_plugins": ["./plugins/demo", "~/.claude/plugins/shared"]
}
```

- Plugin roots must contain `.claude-plugin/plugin.json`.

## Troubleshooting
- DOCX export requires Pandoc. Install Pandoc if auto-download fails.
- Web/vision profile errors usually mean missing or placeholder credentials in `~/.dogent/dogent.json`.
- If inline prompts do not render, Dogent falls back to text input in non-TTY environments.
