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

User Test Results: Accepted
