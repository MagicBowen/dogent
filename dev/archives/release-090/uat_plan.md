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
1) In the same session, run `/init` (confirm overwrite if prompted).
2) Confirm `.dogent/dogent.json` is created with `llm_profile`, `web_profile`, and `doc_template` fields (no embedded secrets); `.gitignore` should remain unchanged.
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
2) Confirm the session starts without failure; `/init` can be run later to add settings; tool calls/results stream via Rich panels.

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
1) Run `/init`; verify `.dogent/dogent.json` does not contain an `images_path` setting.
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
2) From repo root, run `dogent` once then exit. Expect only `~/.dogent/claude.json` and `~/.dogent/web.json` to be created.
3) In a fresh workspace (e.g., `uats/sample_workspace`), run `dogent` then `/init`. Confirm `.dogent/dogent.md` and `.dogent/dogent.json` are generated from packaged templates.

User Test Results: PASS

### Story 29 – Flexible Prompt Injection
1) Edit `dogent/prompts/system.md` to add markers such as `Profile={config:llm_profile}` and `HistoryLast={history:last}`; edit `dogent/prompts/user_prompt.md` to include markers and `Missing={not_set}`.
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
2) Start `dogent` and run `/show history`.
3) Expect a structured history table (latest entries first) and a todo snapshot reflecting the last recorded todos; if history is empty, a friendly notice is shown.

User Test Results: PASS

### Story 32 – Home Template Version Refresh
1) Set a temp home: `export HOME=$(mktemp -d)` and run `dogent` once, then exit.
2) Confirm `~/.dogent/version`, `~/.dogent/prompts`, and `~/.dogent/templates` are not created.
3) Run `dogent` again; confirm `~/.dogent/claude.json` and `~/.dogent/web.json` remain unchanged.

User Test Results: PASS

### Story 33 – Profile Placeholder Warning
1) Use `~/.dogent/claude.json` with the default `replace-me` token under the `deepseek` profile.
2) In `uats/sample_workspace`, set `.dogent/dogent.json` `llm_profile` to `deepseek` (create via `/init` if missing).
3) Start `dogent` or run `/init`; expect a yellow alert telling you to update placeholder credentials before running tasks.

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
3) In `uats/sample_workspace`, run `dogent` then `/init`. Confirm `.dogent/dogent.json` includes `web_profile` (default `default`).
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
3) Start `dogent`. If `.dogent/` is missing, run `/init` first.
4) Run `/learn on` then `/show lessons` (expect “No lessons recorded yet.” on a clean start).

Interrupt → auto lesson capture:
5) Send a prompt that forces todos and a long run, e.g.: “Use TodoWrite to create 3–5 steps for X, start executing step 1 slowly, and keep going until I interrupt.”
6) Once the Todo panel shows unfinished items, press `Esc`.
7) Expect Summary panel title `⛔ Interrupted` and a “Remaining Todos” section.
8) At the next `dogent>` prompt, type ONE message that includes your correction + a retry request, then press Enter.
9) Expect: “Save a lesson from the last failure/interrupt? [Y/n]” — press Enter for **Y**.
10) Expect a `📝 Learn` panel saying it saved to `.dogent/lessons.md`.
11) Run `/show lessons` and confirm it shows recent titles; open `.dogent/lessons.md` and confirm a new `## ...` entry exists.

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
  - `/show history` “started” status uses 🟢.
  - Command completion no longer shows the full command list after typing a space; `/learn ` suggests `on/off`.

- Fixes applied:
  - `dogent/templates/dogent_default.json` now includes `learn_auto` defaults, and `/init` merges defaults into an existing `.dogent/dogent.json` instead of overwriting it.
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
4) Run `/show history` and confirm the latest entry status is `error` (not `completed`); optionally verify in `.dogent/history.json`.

User Test Results: PASS

### Story 43 – Targeted Clear Command
1) In `uats/sample_workspace`, ensure you have `.dogent/history.json`, `.dogent/memory.md`, and `.dogent/lessons.md` (run any task, create a memory file, and record a lesson if needed).
2) Type `/clean ` and confirm the CLI dropdown suggests: `history`, `lesson`, `memory`, `all`.
3) Run `/clean memory`; confirm `.dogent/memory.md` is removed and other targets remain.
4) Run `/clean lesson`; confirm `.dogent/lessons.md` is removed and other targets remain.
5) Run `/clean history`; confirm `.dogent/history.json` is emptied.
6) (Optional) Recreate the files, then run `/clean all` and confirm all three targets are cleaned.

User Test Results: Pending

## Release 0.8.0

### Story 44 – Document Templates + /init Picker
1) In `uats/sample_workspace`, ensure `.dogent/` exists (run `dogent` if needed).
2) Create a workspace template at `.dogent/templates/local.md` (any content).
3) Type `/init ` (with a trailing space) and confirm the dropdown lists `local` plus prefixed entries like `built-in:resume`.
4) Run `/init built-in:resume`, confirm overwrite if prompted.
5) Verify `.dogent/dogent.json` sets `doc_template` to `built-in:resume`.
6) Verify `.dogent/dogent.md` uses the minimal scaffold and references the selected template.

User Test Results: PASS

### Story 45 – /init Wizard (Free-Form Prompt)
1) Run `/init Write a Chinese market research brief for EV adoption in 2024.` (non-matching prompt).
2) Confirm the wizard runs and generates a new `.dogent/dogent.md`.
3) Verify `.dogent/dogent.json` sets `doc_template` to `general`.
4) Open `.dogent/dogent.md` and confirm it includes configured preferences inferred from the prompt (format, length, etc.), but does not include template or primary language fields.

User Test Results: PASS

## Release 0.9.0

### Story 46 – Needs Clarification Status
1) Start `dogent` in `uats/sample_workspace`.
2) Send a request that lacks key details, e.g., “Write a report but ask me which industry and audience before you proceed.”
3) Expect the assistant to ask a question and the Summary panel title to show `❓ Needs clarification`.
4) Confirm the sentinel line is not visible in the reply, and `.dogent/history.json` records `needs_clarification`.
5) Reply with the missing details and confirm you are NOT prompted to “Save a lesson?” (no auto lesson capture).

User Test Results: PASS

### Story 47 – LLM Wait Indicator
1) Run `/init Write a short project summary` to trigger the init wizard.
2) Confirm a spinner/timer appears while the wizard runs and stops when results display.
3) Run `/learn Use pathlib consistently` and confirm a wait indicator appears while the lesson draft is generated.
4) Send a long prompt and confirm the wait indicator appears until the first response arrives.

User Test Results: PASS

### Story 48 – Unified /show Command
1) Type `/` and confirm `/show` is listed while `/history` and `/lessons` are not.
2) Run `/show history` and verify the history table + todo snapshot appear.
3) Run `/show lessons` and verify recent lesson titles (or a “No lessons recorded yet.” notice).

User Test Results: PASS

### Story 49 – Shell Command Shortcut
1) Run `!pwd` or `!ls` from the Dogent prompt.
2) Confirm output and exit code are shown in a “Shell Result” panel.
3) Enter a normal message that includes `!` not at the start and confirm it is treated as a normal LLM prompt.

User Test Results: PASS

## Release 0.9.1

### Story 50 – Multiline History Navigation
1) Start `dogent` in `uats/sample_workspace` and send a short prompt (e.g., “ping”) to create a history entry.
2) At the next prompt, enter `line 1`, press Alt/Option+Enter, enter `line 2`, press Alt/Option+Enter, then enter `line 3`.
3) Press Up twice; the cursor should move from line 3 to line 2, then to line 1 without leaving the input.
4) Press Up once more; the previous history entry should appear.
5) Press Down to return to the multi-line input, then press Down twice to move from line 1 to line 2, then line 3; pressing Down once more from the last line should move to the next history entry.

User Test Results: PASS

### Story 51 – Template Intro Fallback
1) In `uats/sample_workspace`, create `.dogent/templates/no-intro.md` with six lines and no `## Introduction` section.
2) From repo root, run:
   ```bash
   python - <<'PY'
   from pathlib import Path
   from dogent.doc_templates import DocumentTemplateManager
   from dogent.paths import DogentPaths

   paths = DogentPaths(Path("uats/sample_workspace"))
   print(DocumentTemplateManager(paths).describe_templates())
   PY
   ```
3) Confirm the `no-intro` summary uses the first five lines from the template.

User Test Results: PASS

### Story 52 – Alt+Backspace Clear
1) Start `dogent` in `uats/sample_workspace`.
2) Type a multi-line input (use Alt/Option+Enter) and place the cursor somewhere in the middle of a line.
3) Press Alt+Backspace; confirm only the current line content before the cursor is deleted.
4) Type a short sentence and press Alt+Backspace; confirm all text before the cursor is deleted.

User Test Results: PASS

## Release 0.9.2

### Story 53 – /archive Command
1) Start `dogent` in `uats/sample_workspace` and send a short prompt (e.g., “ping”) to create history.
2) Ensure `.dogent/lessons.md` has at least one `##` entry (add one manually if needed).
3) Run `/archive history`; confirm `.dogent/archives/history_YYYYMMDD_HHMMSS.json` is created and `.dogent/history.json` resets to `[]`.
4) Run `/archive lessons`; confirm `.dogent/archives/lessons_YYYYMMDD_HHMMSS.md` is created and `.dogent/lessons.md` resets to `# Lessons` header.
5) Run `/archive all` when one target is empty or missing; confirm the CLI skips that target and reports it.

User Test Results: PASS

### Story 54 – Wrapped CJK Cursor Movement
1) Start `dogent` in `uats/sample_workspace`.
2) Type a long Chinese sentence without line breaks (e.g., “这是一个很长的中文句子用于测试终端自动换行时的光标移动表现”) until it wraps to multiple lines.
3) Press Up/Down to move within the wrapped lines; confirm the cursor moves line-by-line without getting stuck or jumping to history until reaching the start/end.

User Test Results: PASS

## Release 0.9.3

### Story 0 - Document MCP tools registered
1) Run `dogent` from any workspace.
2) Prompt: `List your tools.`
3) Expect: tools include `mcp__dogent__read_document` and `mcp__dogent__export_document`.

User Test Results: PASS

### Story 1 - Read PDF/DOCX/XLSX @file attachments
1) In `sample/`, place a text-based PDF (`text.pdf`), a DOCX (`sample.docx`), and an XLSX (`sample.xlsx`) with two sheets (Sheet1, Sheet2).
2) Run `dogent` from `sample/`.
3) Prompt: `Please summarize @text.pdf and @sample.docx. Also show the first sheet of @sample.xlsx and Sheet2 via @sample.xlsx#Sheet2.`
4) Expect: CLI shows referenced @file paths only; the agent calls `mcp__dogent__read_document` for each file/sheet.
5) Replace `text.pdf` with a scanned/no-text PDF and prompt again.
6) Expect: CLI warns "Unsupported PDF: no extractable text" and the attachment is marked as failed.

User Test Results: PASS

### Story 2 - Output format resolution
1) In `sample/.dogent/dogent.md`, add a line: `Output Format: docx`.
2) Run `dogent` from `sample/` and ask for a short report with no explicit file name.
3) Expect: model writes Markdown, then calls `mcp__dogent__export_document` to produce DOCX (same stem as the Markdown file).
4) Prompt again with an explicit path, e.g., `Please output as report.pdf`.
5) Expect: prompt overrides dogent.md and `report.pdf` is created.

User Test Results: PASS

### Story 3 - Export to PDF/DOCX with runtime setup
1) From `sample/`, request a PDF output (e.g., `Create a one-page summary and output as summary.pdf`).
2) Expect: if pandoc/chromium are missing, tool call bootstraps them or shows a clear, actionable error.
3) Re-run the same request.
4) Expect: output file is generated without re-downloading dependencies.

User Test Results: PASS

## Release 0.9.4

### Story 0 - Vision profile configuration
1) If `~/.dogent/vision.json` exists, move it aside.
2) Run `dogent` from any workspace.
3) Expect: `~/.dogent/vision.json` is created with a `glm-4.6v` profile stub.
4) In `sample/.dogent/dogent.json`, confirm `vision_profile` exists and can be set to `glm-4.6v`.

User Test Results: PASS

### Story 1 - On-demand vision analysis for @image/@video
1) In `sample/`, add an image file (e.g. `photo.png`) and a short video file (e.g. `clip.mp4`).
2) Update `~/.dogent/vision.json` with a valid GLM-4.6V API key and ensure `sample/.dogent/dogent.json` sets `vision_profile` to `glm-4.6v`.
3) Run `dogent` from `sample/` and prompt: `Summarize @photo.png and @clip.mp4 in a few sentences.`
4) Expect: agent calls `mcp__dogent__analyze_media` for each file and the response includes details that reference the image/video content.
5) Set `vision_profile` to a missing profile name or set `api_key` to `replace-me`.
6) Prompt again with `@photo.png`.
7) Expect: request fails fast with a clear, user-friendly message indicating the vision profile/config is invalid.

User Test Results: PASS

## Release 0.9.5

### Story 0 - Confirm out-of-workspace file access
1) From `sample/`, start `dogent`.
2) Prompt: `Please read /etc/hosts and summarize it.`
3) Expect: a permission prompt appears requesting confirmation for an outside-path read.
4) Choose `n`.
5) Expect: task aborts with status `aborted` and a clear reason.
6) Prompt again and choose `y`.
7) Expect: task proceeds and reads the file.

User Test Results: PASS

### Story 1 - Confirm delete commands
1) From `sample/`, start `dogent`.
2) Prompt: `Run the bash command rm -f temp.txt.`
3) Expect: a permission prompt appears for the delete command.
4) Choose `n`.
5) Expect: task aborts with status `aborted`.
6) Prompt again and choose `y`.
7) Expect: command runs and the file is deleted if it exists.

User Test Results: PASS


## Release 0.9.6
### Story 1 – Layered Config Defaults
1) Ensure `~/.dogent/dogent.json` exists; set `"web_profile": "default"` and `"doc_template": "general"`; leave out `llm_profile`.
2) In `sample/`, delete any existing `sample/.dogent/dogent.json`.
3) Run `dogent` in `sample/` and execute `/init`.
4) Verify `sample/.dogent/dogent.json` includes global defaults and does not add `llm_profile`.
5) Edit `sample/.dogent/dogent.json` and override `doc_template` or `primary_language`; restart `dogent` and confirm the override applies.

User Test Results: PASS

### Story 2 – Vision Disabled by Default
1) In `sample/.dogent/dogent.json`, set `"vision_profile": null`.
2) Start `dogent` and reference an image with `@images/sample.png` (or any existing image).
3) Confirm Dogent shows a fail-fast error and does not proceed to the LLM.
4) Set `vision_profile` to a valid profile and retry; confirm the request proceeds and vision tool is available.

User Test Results: PASS

### Story 3 – Prompt-Level Doc Template Override
1) In `sample/.dogent/templates/`, add a template `demo.md` with a recognizable intro line.
2) Start `dogent` and type `@@` to confirm the template list appears; choose `demo`.
3) Submit a prompt with `@@demo` and verify the template applies only to that request.
4) Send another prompt without `@@`; confirm it uses the configured `doc_template` in `sample/.dogent/dogent.json`.

User Test Results: PASS

### Story 4 – Unified Global Config File
1) Delete any existing `~/.dogent/claude.json`, `~/.dogent/web.json`, and `~/.dogent/vision.json`.
2) Start `dogent` once; confirm only `~/.dogent/dogent.json` is created.
3) Edit `~/.dogent/dogent.json` to add a `llm_profiles` entry and set `.dogent/dogent.json` `llm_profile` to it; confirm Dogent loads the profile.
4) Add a `web_profiles` entry and set `.dogent/dogent.json` `web_profile` to it; confirm custom web tools register.
5) Add a `vision_profiles` entry and set `.dogent/dogent.json` `vision_profile` to it; confirm vision tool is available.

User Test Results: PASS

### Story 5 – Versioned Global Config Upgrade
1) In `~/.dogent/dogent.json`, set `"version"` to `"0.0.1"` and remove a known top-level key (e.g., delete `vision_profiles`).
2) Start `dogent`; confirm a warning or upgrade message appears.
3) Re-open `~/.dogent/dogent.json`; confirm the missing key was added and `"version"` updated to the current Dogent version.
4) Set `"version"` to a higher value (e.g., `"99.0.0"`) and restart `dogent`; confirm a warning about newer config version appears.

User Test Results: PASS

---

## Release 0.9.7
### Story 1 – Configurable PDF Style
1) Start `dogent` once to ensure `~/.dogent/pdf_style.css` is created.
2) Edit `~/.dogent/pdf_style.css` to apply a visible change (e.g., `body { font-size: 18pt; }`).
3) In `sample/`, create a simple markdown file and request a PDF export (via prompt or tool). Confirm the PDF reflects the global style.
4) Create `sample/.dogent/pdf_style.css` with a different visible style (e.g., `body { font-size: 10pt; }`).
5) Export to PDF again; confirm the workspace style overrides the global style.
6) Optional: make `sample/.dogent/pdf_style.css` unreadable and export again; confirm Dogent warns and falls back to the global style.

User Test Results: PASS

### Story 2 – Template Override in User Prompt
1) In `sample/.dogent/templates/`, add a template `override.md` with a recognizable line (e.g., `## Introduction` content).
2) Start `dogent` and submit a prompt like `@@override Draft a short report`.
3) Confirm the system prompt does not include the override template content (optional: enable debug/logging if available).
4) Confirm the user prompt includes a "Template Remark" section containing the override template content.
5) Verify the response follows the override template even if `.dogent/dogent.json` or `.dogent/dogent.md` specify a different template.

User Test Results: PASS

### Story 3 – Graceful Exit Without Pipe Errors
1) Start `dogent` and run `/exit`.
2) Confirm the CLI exits without any `EPIPE` or write errors.
3) Optional: run `dogent` in a piped environment (e.g., inside a wrapper/PTY) and repeat `/exit`.

User Test Results: PASS

---

## Release 0.9.8
### Story 1 – Structured Clarification Payloads
1) Start `dogent` in `sample/`.
2) Ask an underspecified request (e.g., “Write a report about our product.”).
3) Confirm Dogent opens the clarification Q&A flow instead of printing raw JSON.
4) Confirm the clarification title/preface is shown and questions appear one by one.

User Test Results: PASS

### Story 2 – Interactive Q&A Flow
1) Trigger clarification as in Story 1.
2) For a multiple-choice question, verify the cursor defaults to the recommended (or first) option and that ↑/↓ changes selection.
3) If a free-form option is present, select it and enter a custom answer.
4) Press Esc during a question to abort and confirm the task is interrupted.
5) (Optional) Set `API_TIMEOUT_MS` to a low value in the active LLM profile and confirm a timeout aborts the task.

User Test Results: PASS

### Story 3 – Session Continuity + History Recording
1) Trigger clarification and answer all questions.
2) Confirm Dogent continues the original task without losing context.
3) Run `/show history` and confirm a clarification entry is recorded with the Q/A summary.

User Test Results: PASS

---

## Release 0.9.9

### Story 1 – Unified Confirmation UX and Safe Interrupts
1) In a workspace with `.dogent/dogent.md`, run `/init`. When the overwrite prompt appears, verify it uses the up/down selection UI; press Esc and confirm the init flow cancels and returns to the CLI prompt.
2) Trigger a lesson prompt: run a request, press Esc to interrupt the agent, then enter another request. When "Save lesson?" appears, verify the up/down UI, select No to continue, then repeat and press Esc to cancel the request entirely (no agent run).
3) Trigger a tool permission prompt by asking the agent to read a file outside the workspace (e.g., `/etc/hosts`). Verify the up/down UI and that Esc cancels the flow (agent aborts) without a separate Esc interrupt from the background listener.
4) Trigger a clarification flow (ask a request missing key details). Confirm options are provided when reasonable; press Esc to skip one question and verify the summary marks the answer as `user chose not to answer this question`. Press Ctrl+C to cancel the whole clarification flow and confirm the task aborts. If the clarification JSON appears in a thinking block, confirm the thinking panel is suppressed and the QA UI still appears (no Failed panel).
5) In a clarification question with "Other (free-form answer)", select it and verify the prompt immediately switches to `Other (free-form answer): ` input.

User Test Results: PASS (Accepted)

### Story 2 – Debug Session Logging
1) Set `.dogent/dogent.json` to include `"debug": true`, then run `dogent` and execute a simple request.
2) Verify `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` is created with JSONL entries containing `role`, `source`, `event`, and `content`.
3) Confirm system prompt is only logged once per source unless it changes.
4) Set `"debug": false` (or remove the key), run another request, and verify no new log file is created.

User Test Results: PASS (Accepted)

### Story 3 – /init Prompt Can Start Writing
1) Run `/init <prompt text>` (use a prompt that is not a template name).
2) Complete the init flow; when prompted to start writing, select Yes and confirm the agent runs with the constructed prompt.
3) Repeat and select No; confirm Dogent returns to the CLI without starting the agent.

User Test Results: PASS (Accepted)

### Story 4 – Auto-Init When dogent.json Missing
1) In a fresh workspace (no `.dogent/dogent.json`), enter a normal request.
2) When asked to initialize, select Yes; complete the wizard and confirm the start-writing prompt appears.
3) Select No at start-writing and verify Dogent returns to the CLI.
4) Repeat and select No at the initialize prompt; confirm the request proceeds normally without init.
5) Repeat and press Esc at the initialize prompt; confirm Dogent returns to the CLI prompt without running the agent.

User Test Results: PASS (Accepted)

---

## Release 0.9.10

### Story 1 – Multiline Markdown Editor for Inputs
1) At the `dogent>` prompt, type a short line (e.g., `# Draft outline`) and press Ctrl+E. Verify the multiline editor opens with the typed text and shows live Markdown highlighting (heading, inline code, tasks, quotes).
2) Press Ctrl+P to toggle full preview. Confirm it is read-only and toggles back to edit mode.
3) In the editor, press Enter to insert a new line (ensure it does not submit). Then use the submit shortcut shown in the footer (Ctrl+Enter or fallback) and confirm the full multi-line prompt is sent to the agent.
4) Press Ctrl+Q to return from the editor with dirty content. Confirm the dialog offers Discard/Submit/Save/Cancel. Choose Save, enter a relative path, and confirm the file is written. Repeat with an existing path and verify overwrite confirmation.
5) Trigger a clarification flow with "Other (free-form answer)". Select it and verify the editor opens immediately. Press Ctrl+Q and choose Discard to return to the single-line free-form input without submitting.

User Test Results: Accepted

---

## Release 0.9.11

### Story 1 – Markdown Debug Logs + Hidden Debug Default
1) Initialize a fresh workspace and open `.dogent/dogent.json`. Confirm there is no `debug` field by default.
2) Set `"debug": true`, run a simple prompt, and confirm a log file is created at `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md`.
3) Open the log file and verify chronological event sections with system/user prompts, streaming blocks, tool use/result, and final result. Confirm unchanged system prompts are logged only once per source.
4) Trigger an exception (e.g., force a tool error) and confirm the log contains an `exception` entry with message, traceback, and location.

User Test Results: PASS

### Story 2 – Editor Mode Config + Return Dialog Semantics
1) Set `"editor_mode": "vi"` in `.dogent/dogent.json`, open the editor with Ctrl+E, and confirm a `VI: ...` status indicator plus expected vi navigation/insert behavior.
2) In prompt input, press Ctrl+Q with dirty content and confirm the return dialog shows Discard/Submit/Save/Cancel (no Abandon task).
3) Choose Save, provide a path, and confirm the saved file. Submit and confirm the CLI shows the user-edited content in a fenced `markdown` code block with a saved-file note.
4) Trigger a clarification with free-form input. Submit an editor answer and confirm the clarification summary wraps only that answer in a fenced `markdown` code block.
5) In a clarification free-form editor, choose Discard and confirm the summary uses the exact skip text: "user chose not to answer this question".

User Test Results: PASS

### Story 3 – Outline Editing in Editor (In-Loop)
1) Ask for a long-form document so the agent returns an outline edit payload and opens the editor. Confirm the outline appears in the editor (default or vi mode per config).
2) Edit the outline, choose Save, and confirm the saved file path exists. Submit and verify the follow-up message includes the outline in a fenced `markdown` code block plus a note that the file stores the outline.
3) Re-run and choose Discard; confirm the task proceeds using the original outline (still fenced in a code block).
4) Re-run and choose Abandon task; confirm the current task is interrupted.

User Test Results: PASS

### Story 4 – /edit Command (File Editing + Optional Submit)
1) Create `notes.md` in the workspace, run `/edit notes.md`, and confirm the editor opens with the file content.
2) Run `/edit drafts/new-note.md` (non-existent). Confirm a create prompt appears; choose Yes and verify the file is created empty and opened in the editor.
3) In the editor, use Ctrl+Q to open the return dialog and choose:
   - Save: file is written and the editor exits without sending to the LLM.
   - Save As: file is written to the new path and exits without sending to the LLM.
   - Submit: file is saved, then a prompt asks what to send to the LLM. Confirm the message includes `@<saved_path>`.
   - Save As + Submit: file is saved to a new path, then the LLM prompt is sent with `@<saved_path>`.
4) Run `/edit data.csv` and confirm an unsupported file type error.
5) Run `/edit /absolute/path/inside/workspace.md` and confirm it opens.

User Test Results: PASS

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

---

## Release 0.9.14

### Story 1 – DOCX Export Embeds Markdown Images
1) `cd sample`
2) Create `docs/images` and add two images (for example `docs/images/1.png` and `docs/images/2.png`).
3) Create `docs/notes.md` with:
   - `![](../images/1.png)`
   - `<div align="center"><img src="../images/2.png" width="70%"></div>`
   - A fenced code block (language tag included).
   - A Markdown table.
4) Run `dogent` and ask: “Export docs/notes.md to docs/notes.docx”.
5) Open `docs/notes.docx` and confirm both images render; the second image respects width; code block is styled; table layout is preserved.

User Test Results: PASS

### Story 2 – Startup Panel Simplified + Markdown Help Panel
1) `cd sample`
2) Run `dogent` and confirm the startup panel shows name/version, model/profile info, and 1–2 reminders only.
3) Run `/help` and confirm the help content renders in a framed panel with Markdown styling (headings/lists/code).
4) Exit the CLI with `/exit`.

User Test Results: PASS

### Story 3 – English End-to-End Usage Guide
1) Open `docs/usage.md`.
2) Confirm the doc is English-only and covers install -> configure -> run -> tools/templates -> permissions -> troubleshooting.
3) Confirm examples are present (CLI commands and/or config snippets).

User Test Results: PASS

---

## Release 0.9.15

### Story 1 – XLSX Multi-Sheet Markdown Export
1) `cd sample`
2) Create a workbook with multiple sheets (example using openpyxl):
   - Run:
     ```
     python - <<'PY'
     from pathlib import Path
     import openpyxl

     root = Path(".")
     docs = root / "docs"
     docs.mkdir(parents=True, exist_ok=True)
     path = docs / "sample.xlsx"

     wb = openpyxl.Workbook()
     ws1 = wb.active
     ws1.title = "SheetOne"
     ws1.append(["ColA", "ColB"])
     for i in range(1, 65):
         ws1.append([f"Row {i}", i])

     ws2 = wb.create_sheet("SheetTwo")
     ws2.append(["Note"])
     for i in range(1, 65):
         ws2.append([f"Note {i}"])

     wb.save(path)
     PY
     ```
3) Run `dogent` and ask: “Read docs/sample.xlsx”.
4) Confirm the output uses `# sample` as the H1 title and includes `## <sheet name>` for each sheet.
5) Confirm there is a blank line between each sheet section.
6) Confirm each sheet section ends with its own truncation note (because of the 50-row cap).
7) Ask: “Convert docs/sample.xlsx to docs/sample.md”. Confirm the output file exists and contains the same H1/H2 structure.

User Test Results: PASS

### Story 2 – Windows Terminal Parity
1) On Windows, `cd sample`.
2) Run `dogent` and trigger a permission prompt (for example, ask it to read a file outside the workspace).
3) Confirm arrow-key selection works and no raw escape sequences appear.
4) Start a long task and press `Esc` to interrupt; confirm it stops cleanly.

User Test Results: Pending

### Story 3 – Full/Lite Packaging for Pandoc + Playwright
1) Set `DOGENT_PACKAGE_MODE=full` and ensure bundled tools exist under `dogent/resources/tools/` for your platform.
2) Run `dogent` and export a Markdown file to DOCX and PDF; confirm no runtime downloads occur.
3) Set `DOGENT_PACKAGE_MODE=lite` and repeat; confirm it uses system/downloaded tools when needed.

User Test Results: Pending
