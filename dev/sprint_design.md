# Design

---

## Release 0.9.16

### Goals
- Load project and user-level Claude assets (commands, agents, skills) from `.claude`.
- Register Claude custom slash commands into Dogent CLI with a `/claude:` prefix.
- Support Claude plugins configured from `.dogent/dogent.json`.
- Expose Claude commands/plugins in `/help` and tab completion.

### Assumptions
- SDK settings are loaded with `setting_sources=["user", "project"]`.
- Strict command handling remains: unknown slash commands are errors unless registered.
- Claude commands always use `/claude:<name>` to avoid conflicts.

### UX behavior
- At startup, scan `.claude/commands` in project and user scope and register as `/claude:<name>`.
- `/help` and completions list built-ins plus Claude commands (including aliased ones).
- Unknown slash commands remain an error (no auto-forward).

### Config changes
- Add a workspace config key (e.g., `claude_plugins`) in `.dogent/dogent.json`:
  - Type: list of strings (paths)
  - Each path points to a plugin root containing `.claude-plugin/plugin.json`.
  - Relative paths resolve from workspace root.

### Claude SDK integration
- Ensure `ClaudeAgentOptions(setting_sources=["user","project"])` to load:
  - `.claude/commands` (project + user)
  - `.claude/agents` (project + user)
  - `.claude/skills` (project + user)
- Ensure `allowed_tools` includes `Skill` and `Task` to permit skills/subagents.
- Pass plugin configs via `ClaudeAgentOptions.plugins=[{"type":"local","path":...}]`.
- Optionally capture `SystemMessage(subtype="init")` for `slash_commands` and
  verify loaded plugins/commands for display (non-blocking).

### CLI command registration
- Create a Claude command loader that:
  - Scans `~/.claude/commands` and `<workspace>/.claude/commands` for `*.md`.
  - Parses optional frontmatter `description` (fallback to "Claude command").
  - Derives command name from filename (e.g., `refactor.md` -> `/refactor`).
- Prefixes all Claude commands with `/claude:` for Dogent CLI.
- Handler behavior:
  - For registered Claude commands, forward raw slash text to the agent.
  - Preserve arguments (e.g., `/refactor src/app.py`).

### Data flow overview
- ConfigManager:
  - Load `claude_plugins` from `.dogent/dogent.json`.
  - Normalize and validate plugin paths; warn and skip invalid entries.
- CLI:
  - Load/refresh Claude commands at startup.
  - Register commands in CommandRegistry for help + completion.
  - Use the same dispatch path as built-ins for consistent UX.

### Error handling
- Missing `.claude/commands` directories are ignored (no warnings).
- Invalid plugin path or missing `.claude-plugin/plugin.json`:
  - Warn once per entry; skip plugin.
- Unknown slash command remains an error panel (strict mode).

### Tests
- Command loader:
  - Registers commands from both project and user paths.
  - Parses frontmatter description or uses fallback.
- Generates `/claude:<name>` for all Claude commands.
- Config:
  - Normalizes plugin path list and validates plugin root.
  - Maps to `ClaudeAgentOptions.plugins`.
- CLI:
  - `/help` includes Claude commands.
  - Completion list contains Claude commands and aliases.
