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

## Release 0.9.17

### Story 1: Profile Command & Config Updates
- User Value: Users can list and switch `llm_profile`, `web_profile`, and `vision_profile` from the CLI without editing JSON manually.
- Acceptance:
  - `/profile` shows current selections only (no interactive prompt).
  - `/profile llm|web|vision` lists available profiles from `~/.dogent/dogent.json` plus defaults; vision shows `none` only when no profiles exist and writes `null`.
  - `/profile llm <name>` (or web/vision) persists the selection; CLI completion lists values after a trailing space.
  - `/profile show` displays current selections and available profile keys in a Rich table.
  - Changing a profile writes `.dogent/dogent.json` and resets the active agent session.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for profile selection + config write; manual CLI check for `/profile`.

### Story 2: Debug Command & Config Normalization
- User Value: Users can enable logging with presets or custom choices via `/debug` and see the persisted config.
- Acceptance:
  - `/debug` shows the current debug configuration (no selection prompt).
  - `/debug <option>` persists `debug` as `null`, `"session"`, `"error"`, `"warn"`, `"info"`, `"debug"`, `"all"`, or `["session","error"]` as specified.
  - `off` (or `null/none`) writes `null`; `custom` opens the interactive selector (session on/off + level).
  - Level priority enforced: `error > warn > info > debug`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for debug normalization and command output; manual CLI check for `/debug`.

### Story 3: Logging Output + Instrumentation
- User Value: Logs help diagnose issues with clear structure and event levels in a single session file.
- Acceptance:
  - Log file stored in `.dogent/logs/dogent_session_<timestamp>.md`.
  - Entries are ordered newest to oldest, clearly labeled by `session` vs level, and group non-session logs around the same interaction period.
  - Exceptions and user-facing errors across CLI/config/features are logged when enabled.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for log output ordering and type tagging; manual run that triggers an error and confirms log entry.

### Story 4: Document Read Offsets
- User Value: Long documents can be read in segments via `mcp__dogent__read_document`.
- Acceptance:
  - Tool schema supports `offset` and `length`; `length` overrides `max_chars`.
  - Tool response includes paging metadata (`total_chars`, `next_offset`, `offset`, `returned`).
  - Reading with offsets returns the correct segment without failing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit test for offset/length slicing; manual tool call with offset + length.
