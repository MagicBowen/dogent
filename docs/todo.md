# Dogent User Stories (Ordered Simple → Complex)

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted

## Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.

## Story 2: Workspace Bootstrap
- User Value: Scaffold templates without prior setup.
- Acceptance: `/init` creates `.dogent/dogent.md`, `.dogent/memory.md`, `./images` without overwriting existing files; slash commands suggest available actions.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_init_files_created`.

## Story 3: Config & Profiles
- User Value: Configure credentials via `/config`, profiles, env fallback.
- Acceptance: `.dogent/dogent.json` references profile; profile overrides env; env used when missing.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_config.py::test_profile_and_project_resolution`, `tests/test_config.py::test_profile_md_supported_and_gitignore_not_modified`.

## Story 4: Prompt Templates
- User Value: System/user prompts isolated and editable.
- Acceptance: Prompts live under `dogent/prompts/*.md`; system injects `.dogent/dogent.md`; user prompt includes todos and @files; CLI streams tool/todo updates.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_prompts.py::test_prompts_include_todos_and_files`.

## Story 5: Todo Panel Sync
- User Value: Tasks panel reflects `TodoWrite` updates live.
- Acceptance: TodoWrite tool inputs/results replace todo list; rendered in CLI; no default todos. Scrolling tool messages are concise with emoji titles; TodoWrite logs are summarized without duplicate Todo panels.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_todo.py::test_agent_updates_todo_from_tool`.

## Story 6: @file References
- User Value: Inject file contents into a turn.
- Acceptance: `@path` loads file content (with truncation notice) and echoes loaded files in CLI; only within workspace; entering `@` suggests files.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `tests/test_prompts.py::test_prompts_include_todos_and_files`.

## Story 7: Interactive Session
- User Value: Streaming chat with Claude Agent SDK.
- Acceptance: Starts session even without `.dogent/`; `/config` reconnects; streams tool use/results with Rich panels.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual chat smoke.

## Story 8: Writing Workflow Prompting
- User Value: Agent guided to plan → research → section drafts → validate → polish in Chinese Markdown.
- Acceptance: System prompt enforces steps, todo usage, citations, images path `./images`, memory file hints.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual e2e content check.

## Story 9: Research & Images
- User Value: Agent can search web and download images into `./images` and reference them.
- Acceptance: Network/search tool enabled; download helper or workflow instructions present; images saved and referenced.
- Dev Status: Todo
- Acceptance Status: Accepted
- Verification: Manual e2e once implemented.

## Story 10: Validation & Citations
- User Value: Agent validates facts, tracks checks in todo, and emits reference list at end.
- Acceptance: Validation tasks appear in todos; output includes “参考资料” links; consistency checks logged.
- Dev Status: Todo
- Acceptance Status: Pending
- Verification: Manual e2e once implemented.

## Story 11: Usage Docs & Tests
- User Value: Clear setup/run/test instructions.
- Acceptance: `README.md` and `docs/usage.md` describe install, commands, profiles, tests; unit tests runnable.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`.
