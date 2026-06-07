# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Accepted (2026-02-03)
```

---

## Release 0.9.31

### Story 1 – Persistent Session Context Across Tasks
1. Start `dogent` in a workspace with a configured LLM profile.
2. Send: "My name is Alice and I'm working on a quarterly report for Q2 2026. Remember this."
3. Wait for the agent to complete the response.
4. Send a new prompt: "What is my name and what am I working on?"
5. Expect the agent to correctly answer "Alice" and "quarterly report for Q2 2026" without the user re-entering this information.
6. Send a third prompt: "Summarize everything we've discussed so far in this session."
7. Expect the agent to reference all three turns (the name/project, the question about name/project, and the summary request).
8. Press Esc during a long-running task to interrupt it, then send a new prompt.
9. Expect the agent to still have context from previous turns after the interruption.

User Test Results: Pending

### Story 2 – Session Lifecycle Management (`/context reset`, Profile Changes, Exit)
1. Start `dogent` and send a prompt to establish session context.
2. Run `/context` and confirm a panel shows current session context info (e.g., turn count, status).
3. Run `/context reset` and confirm a panel appears indicating the session was cleared.
4. Send: "What is my name?" (or reference any previous context).
5. Expect the agent to NOT remember anything from before the reset.
6. Send a new prompt to establish context again, then run `/profile llm ` and select a different LLM profile (or the same one).
7. Send: "What did we discuss before the profile change?"
8. Expect the agent to NOT remember context from before the profile change (session was auto-reset).
9. Start a fresh session, send a prompt, then run `/exit`.
10. Restart `dogent` in the same workspace and send: "Do you remember our last session?"
11. Expect the agent to only have cross-session history from `.dogent/history.json` (if any), not the full conversation from the previous session.
12. Type `/context ` (with trailing space) and confirm the dropdown suggests `reset`.

User Test Results: Pending
