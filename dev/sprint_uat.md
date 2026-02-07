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

## Release 0.9.23
### Story 1 - Markdown Editor @/@@ Completion
1) In a workspace with files (e.g., `README.md`) and templates available, run `dogent`.
2) Open the markdown editor (Ctrl+E) from the prompt. Type `@` and confirm the dropdown lists workspace-root paths (including directories). Use arrow keys + Enter to accept; confirm the path is inserted.
3) Type `@@` and confirm the dropdown lists `general` plus workspace/global/built-in templates. Accept one; confirm it is inserted.
4) Type `@@` and then press Enter without selecting a completion (or dismiss the menu by continuing to type). Confirm the literal `@@` remains and a newline is inserted.
5) Repeat steps 2–4 in a file edit (`/edit some.md`) and during a clarification editor (trigger any clarification, then Ctrl+E).

User Test Results: Accepted (2026-02-07)

---

## Release 0.9.24
### Story 1 – Built-in Claude Plugin Packaging + Install
1) In a fresh shell, set a temp home to avoid touching real config: `export HOME=$(mktemp -d)`.
2) From repo root, run `dogent` once to trigger bootstrap.
3) Verify builtin plugin install:
   - `~/.dogent/plugins/claude/.claude-plugin/plugin.json` exists.
   - `~/.dogent/plugins/claude/skills/pptx/SKILL.md` exists.
4) Verify global defaults: open `~/.dogent/dogent.json` and confirm `workspace_defaults.claude_plugins` contains `~/.dogent/plugins/claude`.
5) New workspace default: delete `sample/.dogent` if present, run `dogent` inside `sample/`, and confirm `sample/.dogent/dogent.json` includes `claude_plugins` with `~/.dogent/plugins/claude`.
6) Existing workspace not injected: create `sample/.dogent/dogent.json` with `{ "doc_template": "general" }`, run `dogent` in `sample/`, and confirm the file still has no `claude_plugins` key.
7) Overwrite behavior: create `~/.dogent/plugins/claude/stale.txt`, run `dogent` again, and confirm `stale.txt` is removed.

User Test Results: Accepted

---

## Release 0.9.25
### Story 1 – Rename Plugins Config Key
1) Set a temp home: `export HOME=$(mktemp -d)`.
2) Run `dogent` once to bootstrap.
3) Open `~/.dogent/dogent.json` and confirm `workspace_defaults.plugins` exists.
4) In `sample/`, remove `.dogent` if present and run `dogent`. Confirm `sample/.dogent/dogent.json` includes `plugins` with `~/.dogent/plugins/claude`.

User Test Results: Accepted (2026-02-07)

### Story 2 – Safe-Root Permissions + Temp File Deletes
1) In `dogent`, ask it to read `~/.dogent/plugins/claude/.claude-plugin/plugin.json` and confirm no permission prompt appears.
2) Ask it to read any file under `~/.claude` (e.g., `~/.claude/commands` if present) and confirm no permission prompt appears.
3) Ask it to write to `~/.claude/test.txt` and confirm a permission prompt appears.
4) Ask Dogent to create a temp file under `/tmp` (e.g., write `/tmp/dogent-temp.txt`) and then delete it via Bash (`rm -f /tmp/dogent-temp.txt`). Confirm the delete does not trigger a permission prompt.
5) Put a plugin under `~/.claude/plugins/<plugin>/commands/<cmd>.md`, run `dogent`, and confirm it appears as `/claude:<plugin>:<cmd>`.
6) Put a plugin under `~/.dogent/plugins/<plugin>/commands/<cmd>.md`, run `dogent`, and confirm it appears as `/<plugin>:<cmd>`.

User Test Results: Accepted (2026-02-07)

### Story 3 – Export + PPTX Documentation Notes
1) Open `docs/04-document-export.md`.
2) Confirm it mentions Pandoc + Chrome dependency prompts for PDF export/convert.
3) Confirm it mentions “Claude PPTX skill” and includes the GitHub link.

User Test Results: Accepted (2026-02-07)
