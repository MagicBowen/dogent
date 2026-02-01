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

## Release 0.9.22

### Story 1: Prompt History Recall Across Restarts
- User Value: Reuse prior user prompts and `/` commands with ↑ after restarting Dogent.
- Acceptance:
  - After restarting, ↑ cycles through the last 30 items from `.dogent/history.json` where `prompt` is present.
  - `/` commands are included in recall; clarification answers are stored in history but not in recall.
  - `/clean history` clears recall; `/archive history` archives and clears recall for the session.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual run; unit tests for history seeding/filters.

### Story 2: Tool-Based Clarification / Outline Edit UI
- User Value: Clarification and outline edit flows reliably trigger the correct UI without brittle tag parsing.
- Acceptance:
  - LLM uses `mcp__dogent__ui_request` tool to request clarification or outline edit UI.
  - CLI renders clarification/outline edit UI based on tool payload and resumes with user answers.
  - Tag-based parsing is removed; only tool-based UI requests are supported.
  - System prompt instructions updated to enforce tool usage.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for tool payload handling + manual CLI check.
