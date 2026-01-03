# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

User Test Results Status: Pending | Accepted | Rejected

---

## Release 0.9.9

### Story 1 – Unified Confirmation UX and Safe Interrupts
1) In a workspace with `.dogent/dogent.md`, run `/init`. When the overwrite prompt appears, verify it uses the up/down selection UI; press Esc and confirm the init flow cancels and returns to the CLI prompt.
2) Trigger a lesson prompt: run a request, press Esc to interrupt the agent, then enter another request. When "Save lesson?" appears, verify the up/down UI, select No to continue, then repeat and press Esc to cancel the request entirely (no agent run).
3) Trigger a tool permission prompt by asking the agent to read a file outside the workspace (e.g., `/etc/hosts`). Verify the up/down UI and that Esc cancels the flow (agent aborts) without a separate Esc interrupt from the background listener.
4) Trigger a clarification flow (ask a request missing key details). Confirm options are provided when reasonable; press Esc to skip one question and verify the summary marks the answer as `user chose not to answer this question`. Press Ctrl+C to cancel the whole clarification flow and confirm the task aborts. If the clarification JSON appears in a thinking block, confirm the thinking panel is suppressed and the QA UI still appears (no Failed panel).
5) In a clarification question with "Other (free-form answer)", select it and verify the prompt immediately switches to `Other (free-form answer): ` input.

User Test Results: PASS (Accepted)

### Story 2 – Debug Session Logging
1) Set `.dogent/dogent.json` to include `"debug": true`, then run `dogent` and execute a simple request.
2) Verify `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` is created with JSONL entries containing `role`, `source`, `event`, and `content`.
3) Confirm system prompt is only logged once per source unless it changes.
4) Set `"debug": false` (or remove the key), run another request, and verify no new log file is created.

User Test Results: PASS (Accepted)

### Story 3 – /init Prompt Can Start Writing
1) Run `/init <prompt text>` (use a prompt that is not a template name).
2) Complete the init flow; when prompted to start writing, select Yes and confirm the agent runs with the constructed prompt.
3) Repeat and select No; confirm Dogent returns to the CLI without starting the agent.

User Test Results: PASS (Accepted)

### Story 4 – Auto-Init When dogent.json Missing
1) In a fresh workspace (no `.dogent/dogent.json`), enter a normal request.
2) When asked to initialize, select Yes; complete the wizard and confirm the start-writing prompt appears.
3) Select No at start-writing and verify Dogent returns to the CLI.
4) Repeat and select No at the initialize prompt; confirm the request proceeds normally without init.
5) Repeat and press Esc at the initialize prompt; confirm Dogent returns to the CLI prompt without running the agent.

User Test Results: PASS (Accepted)
