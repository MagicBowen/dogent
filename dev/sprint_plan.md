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

## Release 0.9.9

### Story 1: Unified Confirmation UX and Safe Interrupts
- User Value: Every confirmation prompt looks and behaves the same, with consistent cancel/skip behavior.
- Acceptance: All yes/no confirmations use the up/down selection UI; Esc cancels the flow; non-interactive mode keeps y/n input; selection prompts do not interrupt an active agent loop; Esc listener is paused while prompts are open and restarted after exit. Clarification prompts use up/down selection, Esc skips a single question (answer recorded as `user chose not to answer this question`), Ctrl+C cancels all clarifications; "Other (free-form answer)" immediately prompts for input; clarification JSON in thinking blocks is parsed for QA and the thinking panel is suppressed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI checks covering overwrite, lesson save, tool permissions, start writing, and initialize prompts.

### Story 2: Debug Session Logging
- User Value: Users can inspect LLM interactions for debugging when enabled.
- Acceptance: `debug: true` creates `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` JSONL logs; entries include `role`; logs capture all LLM calls (main agent, init wizard, lesson drafter); system prompt recorded once if unchanged; no log file when `debug` is false or missing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI run and log inspection.

### Story 3: /init Prompt Can Start Writing
- User Value: Users can begin writing immediately after initializing via `/init prompt`.
- Acceptance: `/init prompt` completes init (including overwrite choice) then asks whether to start writing; Yes runs the writing agent with the constructed prompt; No or Esc returns to CLI without starting the agent; other `/init` paths remain unchanged.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI flow for `/init prompt`.

### Story 4: Auto-Init When dogent.json Missing
- User Value: New projects can initialize seamlessly before the first request.
- Acceptance: If `.dogent/dogent.json` is missing on a user request, the CLI asks to initialize; Yes runs the init wizard with the user request, then offers the start-writing choice; No continues default handling; Esc cancels and returns to CLI; if the file exists, no init prompt is shown.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI flow in a fresh workspace.
