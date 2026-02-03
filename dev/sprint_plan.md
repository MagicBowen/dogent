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
