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

---

## Release 0.9.26
### Story 1 – Preserve CTRL+E Prompt Recall History
1) Run `dogent` in a sample workspace.
2) At the main prompt, press `Ctrl+E` to open the markdown editor.
3) Enter a multiline prompt, for example:
   ```markdown
   Summarize these notes:

   - item 1
   - item 2
   ```
4) Submit from the editor with `Ctrl+J`.
5) After the task returns to the prompt, press Up Arrow once.
6) Confirm the recalled prompt content is exactly the same as what was submitted from the editor, including blank lines, list markers, and spacing.
7) Edit the recalled prompt directly in the main prompt and confirm the text is editable.
8) With the recalled prompt still loaded, press `Ctrl+E` again and confirm the editor opens with the same recalled content prefilled.
9) Open the editor once more, type some text, then exit without submitting. Press Up Arrow again and confirm the discarded text was not added as a new history entry.

User Test Results: Accepted (2026-03-06)

---

## Release 0.9.27
### Story 1 – SDK Permission + Tool-Control Alignment
1) In a fresh shell, set a temp home: `export HOME=$(mktemp -d)`.
2) From repo root, install editable if needed: `pip install -e .`.
3) Run `dogent` in `sample/`.
4) Ask Dogent to read a safe file inside the workspace. Confirm no unexpected permission prompt appears.
5) Ask Dogent to write or edit a file outside the workspace (for example under `~/.claude/` or another protected path). Confirm Dogent still shows the normal approval UI.
6) When prompted, choose the equivalent of "Allow and remember". Confirm the task continues and the remembered authorization is written into `sample/.dogent/dogent.json`.
7) Repeat the same operation in the same workspace. Confirm Dogent does not ask again for the remembered path/pattern.
8) Trigger a helper flow that should have restricted tool access (for example `/init`). Confirm it does not unexpectedly read/write unrelated files or invoke unrelated tools just because `allowed_tools=[]` was previously used.

User Test Results: Accepted (2026-03-29)

### Story 2 – Native Clarification with AskUserQuestion
1) Run `dogent` in a sample workspace.
2) Give Dogent a task that is intentionally ambiguous but should only need a short multiple-choice clarification, for example a request with two plausible output styles.
3) Confirm Dogent presents a simple SDK-style clarification question with selectable options instead of falling back to a normal text reply.
4) Select one option and confirm Dogent continues the task using that answer.
5) Give Dogent a task that requires outline editing or richer custom input.
6) Confirm Dogent uses the existing Dogent outline-edit / richer-input flow instead of forcing the same SDK multiple-choice question UI.

User Test Results: Accepted (2026-03-29)

### Story 3 – Structured Output for the Init Wizard
1) In a fresh sample workspace, remove any existing `.dogent` directory if present.
2) Run `dogent` and invoke `/init`.
3) Answer the init request with enough detail to generate a workspace setup.
4) Confirm the init flow completes successfully and writes the expected setup content without showing malformed raw JSON in the CLI.
5) Open the generated workspace config/content files and confirm the chosen `doc_template`, `primary_language`, and generated `dogent_md` content are applied correctly.
6) Repeat once with a slightly different prompt and confirm the wizard still returns a clean result rather than failing due to fragile JSON text parsing.

User Test Results: Accepted (2026-03-29)

### Story 4 – Project Builtin Commands + Skills + Subagents
1) In a sample workspace, create `<workspace>/.claude/commands/test-claude.md` with a simple description line.
2) Create `<workspace>/.dogent/commands/test-dogent.md` with a simple description line.
3) Run `dogent` and confirm both commands appear in the available command/help listing with distinct names.
4) Add `<workspace>/.claude/skills/test-claude-skill/SKILL.md` with a short description, then restart `dogent`.
5) Add `<workspace>/.dogent/skills/test-dogent-skill/SKILL.md` with a short description, then restart `dogent`.
6) Run a task that should use subagent support. Confirm Dogent aligns with `Agent` as the primary tool naming and does not regress if any SDK output still references legacy `Task`.
7) Confirm the project `.claude` / `.dogent` capability roots are active for skills/subagents and that existing plugin-provided commands still appear after the discovery changes.

User Test Results: Accepted (2026-03-29)

### Story 5 – Tool Metadata + Runtime Feedback + Opt-in Partial Streaming
1) Run `dogent` in a sample workspace with debug/session logging enabled according to the release implementation notes.
2) Trigger a task that uses read-only Dogent MCP tools (for example document reading or web/vision analysis if configured). Confirm the task still works after tool annotations are added.
3) Run a longer task and confirm the final output still renders normally.
4) Check the relevant debug/session log output and confirm cumulative usage fields, task progress/notification events, and any rate-limit warnings are recorded or surfaced as designed.
5) Enable the new opt-in partial streaming mode by setting `"partial_streaming": true` in `<workspace>/.dogent/dogent.json`, then restart `dogent`.
6) Run another long output task and confirm partial response updates appear during generation.
7) Confirm interrupt handling and the final completed response still behave correctly when partial streaming is enabled.

User Test Results: Accepted (2026-03-29)
