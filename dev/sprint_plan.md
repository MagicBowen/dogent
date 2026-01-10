# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.16

### Story 1: Load Claude Commands into CLI
- User Value: Use project/user `.claude/commands` from Dogent with completion and help.
- Acceptance: `/help` lists Claude commands; tab completion includes them; unknown slash commands still error.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run in a workspace with `.claude/commands/*.md`.

### Story 2: Resolve Slash Command Conflicts
- User Value: Claude commands are clearly namespaced in Dogent CLI.
- Acceptance: All Claude commands (project + user + plugin) appear as `/claude:<name>` and forward to the underlying Claude command.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run with a conflicting command file.

### Story 3: Load Claude Plugins from Workspace Config
- User Value: Enable local Claude plugins configured per workspace.
- Acceptance: `.dogent/dogent.json` plugin paths are validated and passed to SDK; invalid entries warn and are skipped.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run with a valid plugin directory and an invalid one.

### Story 4: SDK Settings for Claude Assets
- User Value: Dogent loads project and user-level Claude assets (commands/agents/skills).
- Acceptance: SDK options include `setting_sources=["user","project"]`; skills/subagents work when configured.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for options; manual run with `.claude/skills` and `.claude/agents`.
