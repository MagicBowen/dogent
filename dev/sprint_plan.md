# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.23
### Story 1: Markdown Editor @/@@ Completion
- User Value: While using the markdown editor (prompt, clarification, file edit), I can insert file references and doc templates via dropdown completion like single-line input.
- Acceptance: Typing `@` suggests workspace-root paths (including directories). Typing `@@` suggests `general` plus workspace/global/built-in templates. Enter accepts a suggestion only when the menu is open; otherwise Enter inserts a newline and literal `@`/`@@` remain.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for completion acceptance vs newline.

---

## Release 0.9.24
### Story 1: Built-in Claude Plugin Packaging + Install
- User Value: Dogent ships with the official PPTX skill as a built-in Claude plugin that installs to `~/.dogent/plugins` and is available by default in new workspaces.
- Acceptance:
  - Package includes `dogent/plugins/claude` with valid `.claude-plugin/plugin.json` and `skills/pptx` contents.
  - On startup, built-in plugins are copied to `~/.dogent/plugins`, overwriting existing files.
  - New workspace configs include `claude_plugins: ["~/.dogent/plugins/claude"]`.
  - Existing `.dogent/dogent.json` without `claude_plugins` remains empty (no auto-injection).
  - Docs mention built-in plugin install location and default behavior.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for config defaults and builtin plugin install + manual CLI run.

---

## Release 0.9.25
### Story 1: Rename Plugins Config Key
- User Value: Configure Claude plugins using `plugins` (new key) consistently across workspace/global configs and docs.
- Acceptance:
  - `claude_plugins` renamed to `plugins` in workspace and global config defaults.
  - Code reads `plugins` only (no backward compatibility).
  - Docs and schemas reflect `plugins`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests covering config defaults + plugin load with `plugins`.

### Story 2: Safe-Root Permissions + Temp File Deletes
- User Value: Read/execute in `~/.dogent/plugins` and `~/.claude` without prompts, and delete Dogent temp files within a task without authorization prompts.
- Acceptance:
  - Read/execute under `~/.dogent/plugins` and `~/.claude` do not trigger permission prompts.
  - Writes/deletes outside workspace still prompt unless deleting a tracked temp file.
  - Commands from `~/.claude/plugins` appear as `/claude:<plugin>:<command>`; commands from `~/.dogent/plugins` appear as `/<plugin>:<command>`.
  - Temp-file delete exceptions are scoped to a single task and cleared after it ends.
  - Permissions docs updated accordingly.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for permissions + temp-file delete tracking.

### Story 3: Export + PPTX Documentation Notes
- User Value: Know PDF dependencies and current PPTX generation status with the official Claude skill.
- Acceptance:
  - `docs/04-document-export.md` mentions Pandoc + Chrome dependency prompts.
  - `docs/04-document-export.md` notes PPTX uses “Claude PPTX skill” with the provided GitHub link.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Doc review.

---

## Release 0.9.26
### Story 1: Preserve CTRL+E Prompt Recall History
- User Value: After submitting a prompt from the `Ctrl+E` markdown editor, I can recall that exact prompt with Up Arrow and continue editing it inline or reopen it in the editor.
- Acceptance:
  - A prompt submitted from `Ctrl+E` is added to the same prompt history used by Up Arrow recall.
  - Recalled content exactly matches the submitted editor text, including multiline formatting and spacing.
  - Discarded/cancelled editor sessions do not create history entries.
  - Existing direct prompt submissions and prompt-history limits keep working unchanged.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-06)
- Verification: Unit tests for editor-submit history append, exact multiline preservation, discard behavior, plus full `python -m unittest discover -s tests -v`.

---

## Release 0.9.27
### Story 1: SDK Permission + Tool-Control Alignment
- User Value: Dogent approvals and restricted helper flows remain safe and predictable after the Claude Agent SDK `0.1.51` upgrade.
- Acceptance:
  - Sessions that use `can_use_tool` include the documented Python streaming hook support required for approvals and SDK-native user questions.
  - Dogent no longer relies on `allowed_tools` as a hard whitelist; helper flows that need true restriction use `tools` and related SDK controls correctly.
  - Existing workspace safety rules, temp-file exceptions, and persistent authorizations in `.dogent/dogent.json` keep working.
  - SDK permission `suggestions` / `updated_permissions` are used where appropriate without replacing Dogent's persistent authorization model.
  - Automated tests cover permission callback behavior and restricted helper-flow tool access.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Unit tests for config option building, approval callbacks, and helper-flow restriction behavior, plus full `python -m unittest discover -s tests -v`.

### Story 2: Native Clarification with AskUserQuestion
- User Value: For simple multiple-choice clarifications, Dogent can use the SDK-native clarification flow instead of relying only on a custom UI tool.
- Acceptance:
  - Dogent handles `AskUserQuestion` inside `can_use_tool` and returns answers in the SDK-required shape.
  - Simple clarification requests use `AskUserQuestion`; outline editing and richer input flows still use `mcp__dogent__ui_request`.
  - The system prompt and CLI behavior make the split between simple clarification and outline editing explicit.
  - Automated tests cover `AskUserQuestion` routing, answer collection, and non-regression of existing permission prompts.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Unit tests for `AskUserQuestion` routing, CLI answer collection, and prompt guidance, plus full `python -m unittest discover -s tests -v`.

### Story 3: Structured Output for the Init Wizard
- User Value: The `/init` wizard returns reliably structured setup data instead of depending on fragile free-text JSON parsing.
- Acceptance:
  - `dogent/cli/wizard.py` uses SDK structured output as the primary result path for `doc_template`, `primary_language`, and `dogent_md`.
  - The wizard uses a truly restricted no-tool helper configuration instead of relying on `allowed_tools=[]`.
  - Structured-output failures are handled in a controlled, diagnosable way.
  - Automated tests cover successful structured output and failure handling.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Unit tests for structured wizard parsing, fallback handling, and SDK option wiring, plus full `python -m unittest discover -s tests -v`.

### Story 4: Project Builtin Commands + Skills + Subagents
- User Value: Workspace-provided Claude/Dogent commands, skills, and subagents are available from both `.claude` and `.dogent` project roots under the latest SDK conventions.
- Acceptance:
  - Dogent treats `Agent` as the primary subagent tool name while remaining compatible with legacy `Task` references where SDK output still uses them.
  - Project builtin commands are discovered from both `<workspace>/.claude/commands` and `<workspace>/.dogent/commands`.
  - Project capability roots under `<workspace>/.claude/` and `<workspace>/.dogent/` are exposed to the SDK for skills/agents/hooks according to the chosen filesystem structure.
  - Existing plugin command discovery remains compatible.
  - Automated tests cover command discovery and SDK capability-root configuration.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Unit tests for `.claude` / `.dogent` command and skill discovery plus SDK capability-root wiring, and full `python -m unittest discover -s tests -v`.

### Story 5: Tool Metadata + Runtime Feedback + Opt-in Partial Streaming
- User Value: Dogent provides better SDK-aware tool metadata and clearer runtime feedback during long-running tasks, with optional partial streaming for improved responsiveness.
- Acceptance:
  - Selected Dogent MCP tools expose `ToolAnnotations` where the semantics are accurate.
  - Dogent captures and surfaces useful SDK runtime metadata including cumulative usage, cache-token related fields, rate-limit events, and task progress/notification events.
  - Partial response streaming is available as an opt-in CLI behavior and does not break final-message rendering or interrupt handling.
  - Automated tests cover annotations, runtime event handling, and opt-in partial streaming behavior.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Unit tests for annotations, runtime event handling, partial streaming suppression of duplicate reply panels, plus full `python -m unittest discover -s tests -v`.
