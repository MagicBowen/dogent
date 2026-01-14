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

## Release 0.9.17

### Story 1 – Profile Command & Config Updates
1) Edit `~/.dogent/dogent.json` to include sample profiles under `llm_profiles`, `web_profiles`, and optionally `vision_profiles`.
2) Run `dogent` in a workspace and execute `/profile`; verify it only shows current selections.
3) Run `/profile show`; verify current selections and available profile keys are listed.
4) Run `/profile llm ` (note trailing space) and choose a non-default profile from the drop list; verify `.dogent/dogent.json` updates `llm_profile` and the next request uses the new profile (banner or settings).
5) Run `/profile web ` and choose a custom profile; verify `.dogent/dogent.json` updates `web_profile`.
6) Remove all `vision_profiles` entries, run `/profile vision ` and choose `none`; confirm `.dogent/dogent.json` stores `"vision_profile": null`.

User Test Results: PASS

### Story 2 – Debug Command & Config Normalization
1) Run `/debug`; verify it shows the current debug configuration (no selection prompt).
2) Run `/debug session-errors`; verify `.dogent/dogent.json` contains `"debug": ["session", "error"]`.
3) Run `/debug warn`; verify `.dogent/dogent.json` contains `"debug": "warn"`.
4) Run `/debug off`; verify `.dogent/dogent.json` contains `"debug": null`.

User Test Results: PASS

### Story 3 – Logging Output + Instrumentation
1) Run `/debug`, choose “All (session + all levels)”.
2) Run a normal prompt and confirm a log file appears in `.dogent/logs/dogent_session_<timestamp>.md`.
3) Open the log file and verify newest entries are at the top, session entries are tagged with `session/...`, and level entries are tagged with `error/warn/info/debug`.
4) Trigger an error (e.g., run `!false` or open a missing file) and verify a corresponding level log entry appears near the top with the same interaction id as nearby session logs.

User Test Results: PASS

### Story 4 – Document Read Offsets
1) Place a long text file in the workspace (e.g., `sample.txt` with > 200 chars).
2) Call `mcp__dogent__read_document` with `offset: 0`, `length: 100`; verify the content is the first 100 chars and metadata includes `total_chars` and `next_offset`.
3) Call `mcp__dogent__read_document` with `offset: <next_offset>`, `length: 100`; verify the next segment is returned and `next_offset` advances.

User Test Results: PASS
