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
