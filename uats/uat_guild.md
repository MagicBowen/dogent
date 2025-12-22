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
2) Confirm `.dogent/dogent.json` is created with `llm_profile` and `web_profile` fields (no embedded secrets); `.gitignore` should remain unchanged.
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
2) Expected: agent plans via todos, drafts in sections, mentions citations and (when needed) saving images under a user-chosen directory like `./images`, and references `.dogent/memory.md` for scratch use.

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
1) Run `/config`; verify `.dogent/dogent.json` does not contain an `images_path` setting.
2) When requesting an image download, explicitly specify a workspace-relative output directory in the request (e.g., “download to ./images”) so the model passes it to `dogent_web_fetch`.

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
2) In a session, request an image download and specify an output directory (e.g., `./images`) and verify the model passes it to `dogent_web_fetch` and references the returned Markdown snippet.

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

## Release 0.4

### Story 28 – Home Template Bootstrap
1) (Optional backup) Move or rename your real `~/.dogent` if present, or set a temp home: `export HOME=$(mktemp -d)`.
2) From repo root, run `dogent` once then exit. Expect `~/.dogent/prompts` and `~/.dogent/templates` to be created with `system.md`, `user_prompt.md`, `dogent_default.md`, `dogent_default.json`, `claude_default.json`.
3) In a fresh workspace (e.g., `uats/sample_workspace`), run `dogent` then `/init` and `/config`. Confirm `.dogent/dogent.md` and `.dogent/dogent.json` match the templates under `~/.dogent/templates` (open both to compare).
4) Edit `~/.dogent/templates/dogent_default.json` (e.g., change `llm_profile` to `custom-profile`), remove the workspace `.dogent/dogent.json`, rerun `/config`, and verify the regenerated file reflects the edited template.

User Test Results: PASS

### Story 29 – Flexible Prompt Injection
1) Edit `~/.dogent/prompts/system.md` to add markers such as `Profile={config:llm_profile}` and `HistoryLast={history:last}`; edit `~/.dogent/prompts/user_prompt.md` to include markers and `Missing={not_set}`.
2) In `uats/sample_workspace`, set `.dogent/dogent.json` with `"llm_profile": "uat-profile", "custom": {"nested": "hello"}`.
3) Create `.dogent/history.json` with a couple of JSON entries and `.dogent/memory.md` with sample text; ensure todos are empty.
4) Run `dogent` and send a short message. Observe in the first assistant system rendering that `{config:llm_profile}` (and legacy `{config:profile}`), `{history:last}`, and `{memory}` are injected; `{not_set}` renders empty.
5) Confirm a yellow warning appears about missing template values (for `{not_set}`) instead of a crash.
6) (Optional) Add `{config:custom.nested}` to the templates and rerun to see nested config values injected.

Note: history now lives in `.dogent/history.json` (structured JSON).

User Test Results: PASS

### Story 30 – English System UI
1) Start `dogent` and observe panels, errors, summaries, and banner titles; all UI labels should be English.
2) Send prompts in another language and confirm LLM responses keep their original language while UI labels stay English.

User Test Results: PASS

## Release 0.5

### Story 31 – History Command
1) In `uats/sample_workspace`, ensure `.dogent/history.json` has at least one entry (run a quick task if needed).
2) Start `dogent` and run `/history`.
3) Expect a structured history table (latest entries first) and a todo snapshot reflecting the last recorded todos; if history is empty, a friendly notice is shown.

User Test Results: PASS

### Story 32 – Home Template Version Refresh
1) Set a temp home: `export HOME=$(mktemp -d)` and run `dogent` once, then exit.
2) Edit `~/.dogent/prompts/system.md` to add a marker like `OLD_PROMPT` and set `~/.dogent/version` to `0.0.0`.
3) Run `dogent` again; expect a message that templates synced, `system.md` no longer contains `OLD_PROMPT`, `~/.dogent/version` matches `dogent -v`, and `~/.dogent/claude.json` remains unchanged.

User Test Results: PASS

### Story 33 – Profile Placeholder Warning
1) Use `~/.dogent/claude.json` with the default `replace-me` token under the `deepseek` profile.
2) In `uats/sample_workspace`, set `.dogent/dogent.json` `llm_profile` to `deepseek` (create via `/config` if missing).
3) Start `dogent` or run `/config`; expect a yellow alert telling you to update placeholder credentials before running tasks.

User Test Results: PASS

### Story 34 – Web Tool Result Clarity
1) Start a session and trigger a Dogent web tool call (e.g., ask for a web lookup or to fetch a URL).
2) Observe the tool result panels for `dogent_web_search` / `dogent_web_fetch` (tool IDs: `mcp__dogent__web_search` / `mcp__dogent__web_fetch`): they should say “Success: ...” on success and “Failed: <reason>” on failure, making the outcome obvious.

User Test Results: PASS

### Story 35 – Help Command
1) Start `dogent` and run `/help`.
2) Expect a panel showing current model, fast model, API, LLM profile, web profile, registered commands, and shortcuts for Esc/Alt+Enter/Ctrl+C.

User Test Results: PASS

### Story 36 – Clear History & Memory
1) In `uats/sample_workspace`, create `.dogent/history.json` with sample entries and `.dogent/memory.md` with any text (or run a task to populate history).
2) Start `dogent` and run `/clean all`.
3) Expect a confirmation panel listing cleared files; `.dogent/history.json` should contain an empty array, and `.dogent/memory.md` should be removed (and `.dogent/lessons.md` removed if present). Todos in the session reset to empty.

User Test Results: PASS

## Release 0.6

### Story 37 – Web Tool Config Bootstrap
1) Set a temp home: `export HOME=$(mktemp -d)`.
2) Run `dogent` once, then `/exit`. Expect `~/.dogent/web.json` to be created (alongside `~/.dogent/claude.json`).
3) In `uats/sample_workspace`, run `dogent` then `/config`. Confirm `.dogent/dogent.json` includes `web_profile` (default `default`).
4) Run `/help` and confirm it shows a “Web Profile” line.
5) With `web_profile` empty or set to `default`, ask for web research and confirm Dogent uses native `WebSearch`/`WebFetch`.

User Test Results: PASS

### Story 38 – Custom WebSearch Tool
1) Edit `~/.dogent/web.json` and configure a real provider profile (Google CSE or Bing). Set `.dogent/dogent.json` `web_profile` to that profile name.
2) Start `dogent` and ask: “Search the web for <topic> and list the top 3 links with 1-line summaries.”
3) Expect a tool call to `dogent_web_search` (tool ID: `mcp__dogent__web_search`) and structured results.

Fallback check (no keys):
- With placeholder keys, expect the tool result panel to clearly explain how to configure `~/.dogent/web.json` and `web_profile`.

User Test Results: PASS

### Story 39 – Custom WebFetch Tool (Text + Images)
1) Ask: “Fetch https://example.com and summarize the core content.”
2) Expect a tool call to `dogent_web_fetch` (tool ID: `mcp__dogent__web_fetch`) and readable extracted text (may be truncated).
3) Ask: “Search an image for <keyword> and download 1 image to ./images, then show the Markdown reference.”
4) Expect an image saved under `./images` and a Markdown snippet like `![image](images/...)`.

User Test Results: PASS

### Story 40 – Prompts & Tool Wiring
1) Verify `dogent/prompts/system.md` lists `dogent_web_search` and `dogent_web_fetch` (tool IDs: `mcp__dogent__web_search` / `mcp__dogent__web_fetch`).
2) Set `.dogent/dogent.json` `web_profile` to a real configured profile and request web research; confirm Dogent uses `dogent_web_search` / `dogent_web_fetch`.
3) Set `.dogent/dogent.json` `web_profile` to `default` (or empty) and request web research; confirm Dogent uses native `WebSearch` / `WebFetch`.
4) Set `.dogent/dogent.json` `web_profile` to a non-existent name; restart `dogent` and confirm a startup warning is shown and native tools are used.

User Test Results: PASS

## Release 0.7.0

### Story 41 – Lessons (Continuous Improvement)
Pre-check (clean start recommended):
1) From repo root: `cd uats/sample_workspace`
2) (Optional) Remove prior lessons to start clean: `rm -f .dogent/lessons.md`
3) Start `dogent`. If `.dogent/` is missing, run `/init` and `/config` first.
4) Run `/learn on` then `/lessons` (expect “No lessons recorded yet.” on a clean start).

Interrupt → auto lesson capture:
5) Send a prompt that forces todos and a long run, e.g.: “Use TodoWrite to create 3–5 steps for X, start executing step 1 slowly, and keep going until I interrupt.”
6) Once the Todo panel shows unfinished items, press `Esc`.
7) Expect Summary panel title `⛔ Interrupted` and a “Remaining Todos” section.
8) At the next `dogent>` prompt, type ONE message that includes your correction + a retry request, then press Enter.
9) Expect: “Save a lesson from the last failure/interrupt? [Y/n]” — press Enter for **Y**.
10) Expect a `📝 Learn` panel saying it saved to `.dogent/lessons.md`.
11) Run `/lessons` and confirm it shows recent titles; open `.dogent/lessons.md` and confirm a new `## ...` entry exists.

Manual save + toggle:
12) Run `/learn off`, repeat steps 5–7, then send any message; confirm you are NOT prompted to save a lesson automatically.
13) Run `/learn <free text>` and confirm `.dogent/lessons.md` is appended.
14) Restart `dogent` in the same workspace and confirm `/learn` remains `off` (it is persisted in `.dogent/dogent.json`).

Optional injection check:
15) Ask: “Summarize the Lessons section you have in your context.” Confirm it references what you saved in `.dogent/lessons.md`.

- Previous issues addressed:
  - Lesson drafting now prints an in-progress panel, so the CLI doesn’t look “stuck”.
  - Lessons now always include the user’s correction prompt verbatim under `### Correct Approach`.
  - Lesson drafting prompt was tightened for conciseness and clearer titles; removed `{remaining_todos}` from the lesson draft template.
  - `/learn on|off` is persisted to `.dogent/dogent.json` (default on when absent).
  - `/history` “started” status uses 🟢.
  - Command completion no longer shows the full command list after typing a space; `/learn ` suggests `on/off`.

- Fixes applied:
  - `dogent/templates/dogent_default.json` now includes `learn_auto` defaults, and `/config` merges defaults into an existing `.dogent/dogent.json` instead of overwriting it.
  - Lesson auto-capture now arms on any `error` / `interrupted` outcome (even if the todo list is empty), so you still get the “Save a lesson?” prompt after API errors or early interrupts.
  - The lesson drafter no longer warns about missing `remaining_todos` even if an old home template still contains that placeholder.
  - Command completion no longer re-suggests `/learn on/off` after you start typing free-form text; it only suggests args immediately after `/learn `.
  - Lesson drafting prompt now focuses on the user’s suggested fix/rule (the correction is the primary signal), producing shorter, more reusable lessons.


User Test Results: PASS


### Story 42 – Failure Summary Status Clarity
Goal: verify that when a run ends with unfinished todos (and you did not interrupt), the Summary is clearly marked as failed and history status is `error`.

1) In the same session, run `/learn off` (to avoid extra prompts during this story).
2) Send a prompt that leaves at least one todo unfinished at the end, e.g.:
   “Use TodoWrite to create 3 todos. Mark only the first as completed, leave the others pending, then stop and output a final result.”
3) Expect Summary panel title `❌ Failed` and content including “Result/Reason” and “Remaining Todos”.
4) Run `/history` and confirm the latest entry status is `error` (not `completed`); optionally verify in `.dogent/history.json`.

User Test Results: PASS

### Story 43 – Targeted Clear Command
1) In `uats/sample_workspace`, ensure you have `.dogent/history.json`, `.dogent/memory.md`, and `.dogent/lessons.md` (run any task, create a memory file, and record a lesson if needed).
2) Type `/clean ` and confirm the CLI dropdown suggests: `history`, `lesson`, `memory`, `all`.
3) Run `/clean memory`; confirm `.dogent/memory.md` is removed and other targets remain.
4) Run `/clean lesson`; confirm `.dogent/lessons.md` is removed and other targets remain.
5) Run `/clean history`; confirm `.dogent/history.json` is emptied.
6) (Optional) Recreate the files, then run `/clean all` and confirm all three targets are cleaned.

User Test Results: Pending
