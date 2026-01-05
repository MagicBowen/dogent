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

## Release 0.9.12

### Story 1 – Outside Workspace Permission Coverage
1) `cd sample`
2) Run `dogent`.
3) Ask: "List /etc and read /etc/hosts." Expect a permission prompt for each outside path.
4) Ask: "List ./docs and read ./README.md." Expect no permission prompt for workspace paths.

User Test Results: Pending

### Story 2 – Delete Command Permission Enforcement
1) `cd sample`
2) Run `mkdir -p .dogent && touch .dogent/memory.md && printf "delete me" > temp_delete.txt`
3) Run `dogent`.
4) Ask: "Delete temp_delete.txt." Expect a permission prompt; deny -> task aborted, allow -> file deleted.
5) Ask: "Delete .dogent/memory.md." Expect no permission prompt due to whitelist.

User Test Results: Pending

### Story 3 – Protect Existing `.dogent/dogent.md`
1) `cd sample`
2) Run `mkdir -p .dogent && printf "config" > .dogent/dogent.md`
3) Run `dogent`.
4) Ask: "Append a line to .dogent/dogent.md." Expect a permission prompt before write.
5) Ask: "Use a shell command to append to .dogent/dogent.md." Expect a permission prompt before the command runs.
6) Run `rm .dogent/dogent.md` and ask: "Create .dogent/dogent.md with a short heading." Expect no special permission prompt for creation.

User Test Results: Pending

### Story 4 – Permission Prompt Keeps Session Alive
1) `cd sample`
2) Run `dogent`.
3) Ask: "Read /etc/hosts." When prompted, wait at the permission dialog and confirm the session stays active.
4) Approve the permission; confirm the task continues to completion.
5) Repeat and deny permission; confirm the task is aborted and the session remains usable for a new request.

User Test Results: Pending
