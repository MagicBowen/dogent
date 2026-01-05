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

### Story 1: Outside Workspace Permission Coverage
- User Value: Users are prompted before the agent accesses any paths outside the workspace, including `~/.dogent`, across read/list tools.
- Acceptance: `Read`, `Ls`, `ListFiles`, `Glob`, `Grep`, and `mcp__dogent__read_document` all require permission when targeting paths outside the workspace; in-workspace paths do not prompt.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Delete Command Permission Enforcement
- User Value: Users are prompted before the agent deletes files in the workspace, except whitelisted files.
- Acceptance: `rm/rmdir/del` inside the workspace always prompt unless the target is in the whitelist (e.g. `.dogent/memory.md`); delete prompts remain blocked for outside paths.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`

### Story 3: Protect Existing `.dogent/dogent.md`
- User Value: Users must approve any modification to existing `.dogent/dogent.md` regardless of the write path.
- Acceptance: If `.dogent/dogent.md` exists, `Write/Edit/NotebookEdit` and Bash redirections targeting it prompt for permission; if it does not exist, creation proceeds without this special prompt.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`

### Story 4: Permission Prompt Keeps Session Alive
- User Value: When permission is requested, the agent stays active and resumes correctly after the user answers.
- Acceptance: During a permission prompt, the client session remains open and continues after approval; denial aborts the task cleanly.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual interactive test (CLI).
