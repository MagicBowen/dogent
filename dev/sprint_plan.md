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

---

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

---

## Release 0.9.25
### Story 1: Rename Plugins Config Key
- User Value: Configure Claude plugins using `plugins` (new key) consistently across workspace/global configs and docs.
- Acceptance:
  - `claude_plugins` renamed to `plugins` in workspace and global config defaults.
  - Code reads `plugins` only (no backward compatibility).
  - Docs and schemas reflect `plugins`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests covering config defaults + plugin load with `plugins`.

### Story 2: Safe-Root Permissions + Temp File Deletes
- User Value: Read/execute in `~/.dogent/plugins` and `~/.claude` without prompts, and delete Dogent temp files within a task without authorization prompts.
- Acceptance:
  - Read/execute under `~/.dogent/plugins` and `~/.claude` do not trigger permission prompts.
  - Writes/deletes outside workspace still prompt unless deleting a tracked temp file.
  - Commands from `~/.claude/plugins` appear as `/claude:<plugin>:<command>`; commands from `~/.dogent/plugins` appear as `/<plugin>:<command>`.
  - Temp-file delete exceptions are scoped to a single task and cleared after it ends.
  - Permissions docs updated accordingly.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for permissions + temp-file delete tracking.

### Story 3: Export + PPTX Documentation Notes
- User Value: Know PDF dependencies and current PPTX generation status with the official Claude skill.
- Acceptance:
  - `docs/04-document-export.md` mentions Pandoc + Chrome dependency prompts.
  - `docs/04-document-export.md` notes PPTX uses “Claude PPTX skill” with the provided GitHub link.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Doc review.
