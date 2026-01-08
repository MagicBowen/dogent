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

### Story 1 – Permission Pipeline Uses `can_use_tool` Only
1) `cd sample`
2) Run `dogent`.
3) Ask: "Read ./README.md." Expect no permission prompt for workspace paths.
4) Ask: "Read /etc/hosts." Expect a permission prompt and successful completion after approval.

User Test Results: PASS

### Story 2 – Tool Permissions for Outside Access and Deletes
1) `cd sample`
2) Run `mkdir -p .dogent && touch .dogent/memory.md && printf "delete me" > temp_delete.txt`
3) Run `dogent`.
4) Ask: "Delete temp_delete.txt." Expect a permission prompt; deny -> task aborted, allow -> file deleted.
5) Recreate `temp_delete.txt`, ask: "Move temp_delete.txt to temp_moved.txt." Expect a permission prompt for `mv`.
6) Ask: "Delete .dogent/memory.md." Expect no permission prompt due to whitelist.

User Test Results: PASS

### Story 3 – Protect Existing `.dogent` Files
1) `cd sample`
2) Run `mkdir -p .dogent && printf "config" > .dogent/dogent.md && printf "{}" > .dogent/dogent.json`
3) Run `dogent`.
4) Ask: "Append a line to .dogent/dogent.md." Expect a permission prompt before write.
5) Ask: "Update .dogent/dogent.json to add a field." Expect a permission prompt before write.
6) Ask: "Use a shell command to append to .dogent/dogent.md." Expect a permission prompt before the command runs.
7) Run `rm .dogent/dogent.md` and ask: "Create .dogent/dogent.md with a short heading." Expect no special permission prompt for creation.

User Test Results: PASS

### Story 4 – CLI Authorization for `.dogent` Updates
1) `cd sample`
2) Run `dogent`.
3) Run `/init` to create `.dogent/dogent.md` and `.dogent/dogent.json`. Expect no permission prompt on first creation.
4) Run `/learn off` then `/learn on`. Expect a permission prompt before updating `.dogent/dogent.json`; deny -> config not updated.
5) Run `/init` again. Expect permission prompts before overwriting `.dogent/dogent.md` and `.dogent/dogent.json`; deny -> file not updated.

User Test Results: PASS

### Story 5 – Permission Prompt UX Defaults to Yes
1) `cd sample`
2) Run `dogent`.
3) Ask: "Read /etc/hosts." Confirm the permission prompt defaults to Yes.
4) Use Up/Down to switch selection; confirm no `^[[A`/`^[[B` characters appear.
5) Approve and confirm the task continues; repeat and deny to see the abort panel.

User Test Results: PASS

---

## Release 0.9.13

### Story 1 – Resource Layout & Loader Consolidation
1) `cd sample`
2) Backup and remove `~/.dogent/dogent.schema.json` and `~/.dogent/pdf_style.css` if they exist.
3) Run `dogent`, then exit. Expect both files recreated in `~/.dogent/`.
4) Run `dogent` and execute `/init`, then choose a built-in template (e.g., `built-in:resume`).
5) Confirm `.dogent/dogent.md` reflects the selected built-in template and no errors appear.

User Test Results: PASS

### Story 2 – Complex Multi-line Prompts Externalized
1) Verify prompt files exist: `dogent/prompts/lesson_drafter_system.md` and `dogent/prompts/vision_analyze.md`.
2) Confirm `dogent/lesson_drafter.py` no longer contains the lesson drafter system prompt text.
3) Confirm `dogent/vision.py` no longer contains the vision analysis prompt text.

User Test Results: PASS

### Story 3 – CLI Module Split
1) `cd sample`
2) Run `dogent` and confirm the startup panel renders without errors.
3) Run `/help` and `/show history` to confirm commands still work.
4) Run `/edit README.md`, then cancel; confirm you return to the prompt.
5) Exit with `/exit`.

User Test Results: PASS

### Story 4 – Agent/Config/Core/Feature Modules Split
1) Confirm directories exist: `dogent/agent`, `dogent/config`, `dogent/core`, `dogent/features`.
2) Confirm old single-file modules are removed (for example `dogent/agent.py`, `dogent/config.py`, `dogent/todo.py`).
3) Run `python -m unittest discover -s tests -v` and confirm all tests pass.
4) `cd sample`, run `dogent`, then `/help`, then `/exit`.

User Test Results: PASS