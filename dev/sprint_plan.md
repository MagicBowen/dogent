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

## Release 0.9.10

### Story 1: Multiline Markdown Editor for Inputs
- User Value: Users can comfortably author and edit multi-line Markdown prompts and free-form answers.
- Acceptance: Single-line input remains default. Pressing Ctrl+E opens a multiline editor for the main prompt and free-form clarification answers; selecting "Other (free-form answer)" opens the editor directly. The editor uses live Markdown highlighting in the edit view, and Ctrl+P toggles a read-only full preview. Enter inserts new lines; Ctrl+Enter submits (fallback shown in footer). Ctrl+Q returns; Esc does not exit the editor. On return with dirty content, prompt to Discard/Submit/Save/Cancel (save prompts for path, confirms overwrite). Footer lists prominent actions and fallback shortcuts. Esc listener is paused while the editor is open.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual CLI tests for prompt input and free-form clarification answers with Ctrl+E, preview toggle, submit/cancel behavior.
