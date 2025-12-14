# UAT Guide for Dogent

Use the sample workspace at `uats/sample_workspace` unless a step says otherwise. Run commands from repo root.

## Release 0.1

### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending (retest after history.json migration)
- when enter dogent cli, show the llm model using and api url in the Dogent prompt and help message.

### Story 2 – Workspace Bootstrap
1) From repo root: `cd uats/sample_workspace && dogent`
2) Run `/init`. Verify `.dogent/dogent.md` exists (no `memory.md` or `images/` auto-created) and prior files remain untouched.
3) Type `/` to see command suggestions.

User Test Results: PASS

### Story 3 – Config & Profiles
1) In the same session, run `/config`.
2) Confirm `.dogent/dogent.json` is created with a profile field only (no embedded secrets); `.gitignore` should remain unchanged.
3) Create `~/.dogent/claude.json` with a profile and check merged values by re-entering the session (Dogent reconnects with new settings).

User Test Results: PASS

### Story 4 – Prompt Templates
1) Edit `.dogent/dogent.md` with a short constraint (e.g., “输出中文 Markdown”).
2) Send a prompt like “说明写作约束”. Expected: response reflects the constraint; prompts are sourced from `dogent/prompts/*.md`.

User Test Results: PASS

### Story 5 – Todo Panel Sync
1) Ask: “规划写作任务，使用 TodoWrite 输出 todo 列表。”
2) Expect the Tasks panel in the CLI to refresh to the latest TodoWrite output; no seeded todos before the tool runs.

User Test Results: PASS

### Story 6 – @file References
1) In `uats/sample_workspace`, send: “阅读 @context.txt 总结要点。”
2) Expected: CLI shows the file loaded; response includes the file content summary with truncation notice absent (file is small).
3) Type a prompt ending with `@` to trigger file suggestions, select `context.txt`, and send.

User Test Results: PASS

### Story 7 – Interactive Session
1) Start `dogent` in an empty temp directory (no `.dogent/`).
2) Confirm the session starts without failure; `/config` can be run later to add settings; tool calls/results stream via Rich panels.

User Test Results: PASS

### Story 8 – Writing Workflow Prompting
1) With `.dogent/dogent.md` filled, ask for a multi-section document plan (Chinese Markdown) and completion.
2) Expected: agent plans via todos, drafts in sections, mentions citations and images path `./images`, and references `.dogent/memory.md` for scratch use.

User Test Results: PASS

### Story 11 – Usage Docs & Tests
1) From repo root: `python -m unittest discover -s tests -v`
2) Expected: all tests pass; docs for usage are in `README.md` and `docs/usage.md`.

User Test Results: PASS

## Release 0.2
### Story 12 – Single Source Versioning
1) Run `dogent -v` after install.
2) Compare with `pyproject.toml` and `importlib.metadata.version("dogent")`.

User Test Results: PASS

### Story 13 – Home Bootstrap & Default Profile
1) Ensure `~/.dogent` is absent (clean HOME).
2) Run `dogent`; expect `~/.dogent/claude.json` template created with an edit prompt.

User Test Results: PASS

### Story 14 – ASCII Welcome Banner
1) Run `dogent`.
2) Expect ASCII/Unicode art “dogent” banner centered within the welcome panel before the info; panel footer should not show extra subtitles.

User Test Results: PASS

### Story 15 – History Persistence
1) Run a task to completion; open `.dogent/history.json` to see a structured entry.
2) Restart `dogent` in the same directory; history is available for continuity and records every user request/result; `/init` echoes only created files.

User Test Results: PASS

### Story 16 – Ephemeral Memory
1) After `/init`, verify `.dogent/memory.md` is absent.
2) Ask agent to jot temporary notes; file is created on demand and cleaned after use.

User Test Results: PASS

### Story 17 – Configurable Images Path
1) Run `/config`; verify `.dogent/dogent.json` contains `images_path` (default `./images`).
2) Confirm no `images/` dir from `/init`; set custom path and ensure agent references it.

User Test Results: PASS

### Story 18 – Interrupt with Esc
1) Start a long-running task; press `Esc`.
2) Task is interrupted via Claude Agent SDK, progress recorded to `.dogent/history.json`, and prompt returns; the next user prompt should include history so the agent resumes without emitting an extra summary.

User Test Results: PASS

### Story 19 – Remove `/todo` Command
1) Run `dogent` and type `/`; confirm `/todo` is not offered.
2) Trigger TodoWrite; todos auto-render without a command.

User Test Results: PASS

### Story 20 – Enhanced Summary Presentation
1) Complete a task; observe the completion panel.
2) Expect emoji title (📝 Session Summary), summary first, then metrics; sections like “File Reference” also have emoji titles.

User Test Results: PASS

## Release 0.3

### Story 21 – Command Registration
1) Run `dogent`; banner should list registered commands from the registry (no hardcoded list).
2) Type an unknown slash command; the error panel should list available commands from the registry.

User Test Results: PASS

### Story 22 – Externalized Templates
1) Inspect `dogent/templates/dogent_default.md` and confirm `/init` uses it to create `.dogent/dogent.md`.
2) Update the template file, rerun `/init` in a fresh workspace, and confirm the new content is used.

User Test Results: PASS

### Story 23 – Prompt Optimization
1) Inspect `dogent/prompts/system.md` and `dogent/prompts/user_prompt.md` to confirm best-practice structure and no hardcoded image paths.
2) In a session, set a custom images path in `.dogent/dogent.json`; verify the system prompt reflects it by observing agent behavior.

User Test Results: PASS

### Story 24 – Code Structure & Clean Code
1) Review `AGENTS.md` and module layout to see core CLI/agent code separated from role-specific prompts/templates.
2) Confirm command handling and prompt files are decoupled and documented.

User Test Results: PASS

### Story 25 – Multi-line Input Support
1) Start `dogent` and type a prompt; press Alt/Option+Enter to insert a newline.
2) Submit and ensure the full multi-line prompt is sent once Enter is pressed.

User Test Results: PASS

### Story 26 – Graceful Ctrl+C Exit
1) Start a task, then press Ctrl+C while idle or during streaming.
2) Expect a clean exit with a friendly message and no uncaught exceptions.

User Test Results: PASS

### Story 27 – Architectural Guidelines
1) Open `AGENTS.md` and verify Release 0.3 principles (registry, template externalization, CLI/core separation, language rules) are documented.
2) Ensure guidelines mention updating `docs/todo.md` and `uats/uat_guild.md` per story.

User Test Results: PASS

### Story 28 – English System UI
1) Start `dogent` and observe panels, errors, summaries, and banner titles; all UI labels should be English.
2) Send prompts in another language and confirm LLM responses keep their original language while UI labels stay English.

User Test Results: PASS

## Release 0.4

### Story 28 – Home Template Bootstrap
1) (Optional backup) Move or rename your real `~/.dogent` if present, or set a temp home: `export HOME=$(mktemp -d)`.
2) From repo root, run `dogent` once then exit. Expect `~/.dogent/prompts` and `~/.dogent/templates` to be created with `system.md`, `user_prompt.md`, `dogent_default.md`, `dogent_default.json`, `claude_default.json`.
3) In a fresh workspace (e.g., `uats/sample_workspace`), run `dogent` then `/init` and `/config`. Confirm `.dogent/dogent.md` and `.dogent/dogent.json` match the templates under `~/.dogent/templates` (open both to compare).
4) Edit `~/.dogent/templates/dogent_default.json` (e.g., change profile to `custom-profile`), remove the workspace `.dogent/dogent.json`, rerun `/config`, and verify the regenerated file reflects the edited template.

User Test Results: PASS

### Story 29 – Flexible Prompt Injection
1) Edit `~/.dogent/prompts/system.md` to add markers such as `Profile={config:profile}` and `HistoryLast={history:last}`; edit `~/.dogent/prompts/user_prompt.md` to include `ConfigImages={config:images_path}` and `Missing={not_set}`.
2) In `uats/sample_workspace`, set `.dogent/dogent.json` with `"profile": "uat-profile", "images_path": "/tmp/uat-images", "custom": {"nested": "hello"}`.
3) Create `.dogent/history.json` with a couple of JSON entries and `.dogent/memory.md` with sample text; ensure todos are empty.
4) Run `dogent` and send a short message. Observe in the first assistant system rendering that `{config:profile}`, `{history:last}`, `{memory}`, and `{config:images_path}` are injected; `{not_set}` renders empty.
5) Confirm a yellow warning appears about missing template values (for `{not_set}`) instead of a crash.
6) (Optional) Add `{config:custom.nested}` to the templates and rerun to see nested config values injected.

Note: history now lives in `.dogent/history.json` (structured JSON).

User Test Results: PASS
