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

## Release 0.9.12

### Story 1: Permission Pipeline Uses `can_use_tool` Only
- User Value: Users get consistent permission gating because tool allow/deny flows run through the permission callback rather than a static allowlist.
- Acceptance: When `can_use_tool` is set, `allowed_tools` is not set in `ClaudeAgentOptions`; the permission callback decides which tools proceed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Tool Permissions for Outside Access and Deletes
- User Value: Users are prompted before the agent reads/writes outside the workspace or deletes workspace files.
- Acceptance: `Read/Write/Edit` require permission for paths outside workspace (including `~/.dogent`); `rm/rmdir/del/mv` inside workspace always prompt unless the target is whitelisted (e.g. `.dogent/memory.md`).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: Protect Existing `.dogent` Files
- User Value: Users must approve any modification to existing `.dogent/dogent.md` or `.dogent/dogent.json`.
- Acceptance: If these files exist, tool-based `Write/Edit` and Bash redirections prompt for permission; first-time creation does not prompt.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: CLI Authorization for `.dogent` Updates
- User Value: CLI actions cannot overwrite `.dogent/dogent.md` or `.dogent/dogent.json` without explicit approval.
- Acceptance: CLI writes to existing `.dogent/dogent.md` or `.dogent/dogent.json` prompt for authorization each time and skip updates on denial; first-time creation proceeds without prompts.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 5: Permission Prompt UX Defaults to Yes
- User Value: Permission prompts are fast to approve and do not leak raw escape sequences while selecting.
- Acceptance: Permission prompts default to yes and allow up/down selection when prompt_toolkit is available; text fallback remains when it is not.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual interactive test (CLI).
