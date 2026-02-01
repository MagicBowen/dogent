# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

---

## Release 0.9.22

### Story 1 – Prompt History Recall Across Restarts
1) Run `dogent` in a workspace and send a normal prompt (e.g., "hello").
2) Run a command such as `/help`, then `/exit`.
3) Relaunch `dogent` in the same workspace.
4) Press ↑ to cycle history; expect the prompt and `/help` to appear within the last 30 items.
5) Run `/clean history`, exit, relaunch, press ↑; expect prior history cleared.

User Test Results: Passed

### Story 2 – Tool-Based Clarification / Outline Edit UI
1) Run `dogent` and request something ambiguous (e.g., "write a report") to trigger clarification.
2) Confirm the clarification UI appears (no raw JSON/tags) and answer the questions.
3) Trigger an outline-editing request (e.g., "draft a proposal outline") and confirm the outline editor UI appears.
4) Submit the outline edits and verify the agent continues with the updated outline.

User Test Results: Passed
