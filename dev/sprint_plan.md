# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.23
### Story 1: Markdown Editor @/@@ Completion
- User Value: While using the markdown editor (prompt, clarification, file edit), I can insert file references and doc templates via dropdown completion like single-line input.
- Acceptance: Typing `@` suggests workspace-root paths (including directories). Typing `@@` suggests `general` plus workspace/global/built-in templates. Enter accepts a suggestion only when the menu is open; otherwise Enter inserts a newline and literal `@`/`@@` remain.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for completion acceptance vs newline.

## Release 0.9.24
### Story 1: Built-in Claude Plugin Packaging + Install
- User Value: Dogent ships with the official PPTX skill as a built-in Claude plugin that installs to `~/.dogent/plugins` and is available by default in new workspaces.
- Acceptance:
  - Package includes `dogent/plugins/claude` with valid `.claude-plugin/plugin.json` and `skills/pptx` contents.
  - On startup, built-in plugins are copied to `~/.dogent/plugins`, overwriting existing files.
  - New workspace configs include `claude_plugins: ["~/.dogent/plugins/claude"]`.
  - Existing `.dogent/dogent.json` without `claude_plugins` remains empty (no auto-injection).
  - Docs mention built-in plugin install location and default behavior.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for config defaults and builtin plugin install + manual CLI run.
