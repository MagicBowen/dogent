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

## Release 0.9.31

### Story 1: Persistent Session Context Across Tasks
- User Value: Users can have multi-turn conversations where the agent remembers all previous interactions within the same session, without re-entering context.
- Acceptance: After completing a task and submitting a new prompt, the agent has full conversation context from all prior turns in the session. The ClaudeSDKClient stays connected across completed, errored, and interrupted tasks. History injection via `{history}` / `{history:last}` continues to work for cross-session context. Non-interactive mode (`dogent -p`) still creates a fresh client per run.
- Dev Status: Todo
- Acceptance Status: Pending
- Verification: Automated tests for multi-turn context persistence, disconnect behavior, and non-interactive isolation.

### Story 2: Session Lifecycle Management (`/context reset`, Profile Changes, Exit)
- User Value: Users can explicitly clear conversation context mid-session with `/context reset`, and context is automatically cleared when changing profiles or exiting Dogent. The `/context` command is extensible for future subcommands (e.g., `compact`).
- Acceptance: `/context reset` disconnects the agent client and clears internal state, starting a fresh session without exiting Dogent. `/context` without arguments shows current session context info. Profile changes (`/profile llm/web/vision/image`) trigger an automatic session reset. `/exit` cleanly disconnects the agent. A confirmation panel shows after `/context reset` confirming the session was cleared. CLI completion suggests `reset` after `/context `.
- Dev Status: Todo
- Acceptance Status: Pending
- Verification: Automated tests for `/context reset` command, `/context` info display, auto-reset on profile change, and exit cleanup.
