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

## Release 0.9.10

### Story 1 – Multiline Markdown Editor for Inputs
1) At the `dogent>` prompt, type a short line (e.g., `# Draft outline`) and press Ctrl+E. Verify the multiline editor opens with the typed text and shows live Markdown highlighting (heading, inline code, tasks, quotes).
2) Press Ctrl+P to toggle full preview. Confirm it is read-only and toggles back to edit mode.
3) In the editor, press Enter to insert a new line (ensure it does not submit). Then use the submit shortcut shown in the footer (Ctrl+Enter or fallback) and confirm the full multi-line prompt is sent to the agent.
4) Press Ctrl+Q to return from the editor with dirty content. Confirm the dialog offers Discard/Submit/Save/Cancel. Choose Save, enter a relative path, and confirm the file is written. Repeat with an existing path and verify overwrite confirmation.
5) Trigger a clarification flow with "Other (free-form answer)". Select it and verify the editor opens immediately. Press Ctrl+Q and choose Discard to return to the single-line free-form input without submitting.

User Test Results: Accepted
