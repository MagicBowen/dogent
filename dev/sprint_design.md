# Design

---

## Release 0.9.23

### Goal
- Add @ file and @@ doc template dropdown completion in the multiline markdown editor.
- Keep completion behavior aligned with single-line input.
- Preserve literal @/@@ when nothing is selected.

### Current Baseline
- Single-line prompt uses `DogentCompleter` for `@` file and `@@` template suggestions.
- Multiline editor uses `TextArea` without a completer.
- File references are resolved on submission via `FileReferenceResolver` and template override parsing.

### UX + Behavior
- Typing `@` in the editor shows file/path suggestions relative to the workspace root.
- Typing `@@` shows template suggestions, including `general`, workspace, global, and built-in templates.
- Directory entries appear with a trailing `/` and can be completed to navigate deeper (same as single-line).
- If a completion menu is open, pressing Enter accepts the current suggestion.
- If no completion is selected, Enter inserts a newline and the literal `@`/`@@` stays in the text.
- Completions are enabled in all editor contexts: prompt, clarification, and file edit.

### Implementation Plan
- Reuse `DogentCompleter` for the editor `TextArea`:
  - `root=self.root`
  - `template_provider=self.doc_templates.list_display_names`
  - `commands` can be the existing registry list (safe) or an empty list (to avoid `/` suggestions).
  - `complete_while_typing=True`
- Add an editor key binding for Enter in `_open_multiline_editor`:
  - If `buffer.complete_state.current_completion` exists, apply it and return.
  - Otherwise insert a newline (`buffer.insert_text("\n")`) and keep existing editor behavior.
  - Scope the binding to `edit_active & editor_focus` so overlays and preview mode are unaffected.
- Do not change file/template resolution logic; completion only affects text insertion.

### Edge Cases + Notes
- `@@` completions should not fall through to file completion when template completions are available.
- Completion acceptance should not submit the editor (submission remains Ctrl+Enter or vi :wq).
- Text is only modified on explicit completion acceptance, satisfying the "treat @/@@ as normal characters" rule.

### Tests
- Add a unit test that simulates a buffer with completion state and verifies Enter applies the completion.
- Add a unit test that verifies Enter inserts a newline when no completion is active.
- Skip tests if prompt_toolkit is unavailable (consistent with existing optional dependency handling).

---

## Release 0.9.24

### Goal
- Ship a built-in Claude plugin that wraps the PPTX skill under `dogent/plugins/claude`.
- Auto-install all built-in plugins to `~/.dogent/plugins` on startup (overwrite/update).
- New workspace configs include the built-in Claude plugin path by default; existing projects remain unchanged unless edited.

### Current Baseline
- Claude plugins are loaded from `.dogent/dogent.json` via `claude_plugins`; defaults are empty.
- Plugin roots must contain `.claude-plugin/plugin.json`.
- Startup bootstrap creates `~/.dogent` config/schema files but does not install plugins.

### Plugin Layout (Package)
- Plugin root: `dogent/plugins/claude`.
- Manifest: `dogent/plugins/claude/.claude-plugin/plugin.json` (name `claude`, version, description).
- Skills: `dogent/plugins/claude/skills/pptx` (copied from `claude/skills/skills/pptx`, including SKILL.md, scripts, ooxml, and LICENSE.txt).
- Follow Claude plugin structure (see `claude/examples/plugins`) so SDK loads skills correctly.

### Install Flow (Startup)
- Add `DogentPaths.global_plugins_dir` -> `~/.dogent/plugins`.
- Implement `ConfigManager._install_builtin_plugins()` and call it from `_ensure_home_bootstrap()` after `~/.dogent` exists.
- Source: `importlib.resources.files("dogent") / "plugins"` (skip if missing).
- For each directory under source, copy to `~/.dogent/plugins/<name>` with `shutil.copytree(..., dirs_exist_ok=True)` to overwrite/update.
- On permission errors, warn and continue (do not block CLI startup).

### Default Config Behavior
- Update `dogent/resources/dogent_global_default.json`:
  - `workspace_defaults.claude_plugins = ["~/.dogent/plugins/claude"]`.
- Ensure existing projects are not auto-updated:
  - If `.dogent/dogent.json` exists and lacks `claude_plugins`, treat it as an explicit empty list so global defaults do not inject the built-in plugin.
  - New workspaces created via `create_config_template()` inherit the default plugin path.

### Packaging
- Add `plugins/**` to `tool.setuptools.package-data` for the `dogent` package so built-in plugins ship with the distribution.

### Docs
- Update `docs/07-commands.md` and `docs/10-claude-compatibility.md`:
  - Mention built-in plugins are installed to `~/.dogent/plugins`.
  - Note only the built-in Claude plugin is included in default `claude_plugins`; others require manual addition.

### Tests
- Add a unit test for config behavior:
  - New workspace config includes `~/.dogent/plugins/claude`.
  - Existing workspace config without `claude_plugins` yields an empty list.
- Add a unit test for builtin plugin install (helper takes a source dir in tests, copies into a temp `~/.dogent/plugins`).

---

## Release 0.9.25

### Goal
- Rename config key `claude_plugins` to `plugins` in workspace and global configs (no backward compatibility).
- Update docs for PDF dependency prompts and PPTX status.
- Expand permission exceptions for read/execute in `~/.dogent/plugins` and `~/.claude`.
- Allow deletion of Dogent-generated temporary files within the same task without prompting.

### Current Baseline
- Config key is `claude_plugins`; schemas and docs mention it.
- Permissions are enforced for all paths outside workspace, with a delete whitelist only for `.dogent/memory.md`.
- No central tracking of temp files created during a task.

### Config + Schema Changes
- Rename all references of `claude_plugins` to `plugins` in:
  - `dogent/resources/dogent_default.json`
  - `dogent/resources/dogent_global_default.json` (`workspace_defaults.plugins`)
  - `dogent/config/manager.py` normalization, loading, and options build
  - docs and schemas (`dogent/schema/**` and `docs/*`)
- No backward compatibility: if users still have `claude_plugins`, it will be ignored.

### Permissions Changes
- Introduce read/execute safe roots: `~/.dogent/plugins` and `~/.claude`.
- For file tools:
  - `Read` under safe roots does not require confirmation.
  - `Write/Edit` under safe roots still require confirmation if outside workspace (except temp-file deletes below).
- For Bash:
  - Allow commands that only touch safe-root paths without confirmation.
  - Writes/deletes outside workspace still prompt unless the target is a tracked temp file.
- Expose plugin commands differently by location:
  - `~/.claude/plugins` => `/claude:<plugin>:<command>`
  - `~/.dogent/plugins` => `/<plugin>:<command>`

### Temporary File Tracking
- Track temp files created by Dogent during a single task run (store resolved paths on the runner).
- When a delete occurs in the same task (Bash `rm`/`mv` or Write/Edit delete semantics), skip permission prompts if the target matches a tracked temp file.
- Clear the list at task end (on completion/abort) to avoid cross-task leakage.

### Docs
- `docs/04-document-export.md`:
  - Note PDF generation/conversion requires pandoc + Chrome; prompt to download if missing.
  - Note PPTX generation is not fully solved; default to “Claude PPTX skill” with link to `https://github.com/anthropics/skills/tree/main/skills/pptx`.
- Update config key names in `docs/07-commands.md`, `docs/08-configuration.md`, `docs/10-claude-compatibility.md`.
- Update permissions doc to mention safe roots.

### Tests
- Config tests: new key `plugins` used in defaults and options.
- Permission tests:
  - Read in `~/.dogent/plugins` or `~/.claude` does not prompt.
  - Write outside workspace still prompts (unless temp delete).
- Temp file tests:
  - Track a temp file and ensure delete via Bash skips confirmation.
  - Ensure list clears between tasks.

---

## Release 0.9.26

### Goal
- Preserve prompts submitted from the `Ctrl+E` multiline editor in the same prompt history used by Up Arrow recall.
- When recalled, restore the exact submitted text so the user can edit inline immediately or reopen the editor with `Ctrl+E`.

### Current Baseline
- Main prompt input uses `PromptSession` with `LimitedInMemoryHistory`, seeded from `HistoryManager.prompt_history_strings()`.
- Normal prompt submissions entered directly in the prompt session are added to prompt_toolkit history automatically.
- `Ctrl+E` returns a `MultilineEditRequest`, opens `_open_multiline_editor()`, and on submit returns the edited text from `_read_input()`.
- That editor-submit path does not explicitly append the final text into `self.session.history`, so the Up Arrow recall list can miss the edited prompt during the current session.
- Durable prompt history in `.dogent/history.json` is populated later by `HistoryManager.append(..., user_input=...)` when the request is actually sent to the agent.

### UX + Behavior
- After a user submits text from the `Ctrl+E` editor with `Ctrl+J`, pressing Up Arrow from the main prompt recalls that exact text.
- Recalled text must match the final editor submission byte-for-byte, including newlines and spacing.
- Recalled editor-submitted prompts behave the same as normal recalled prompts:
  - the user can edit inline in the main prompt;
  - the user can press `Ctrl+E` again to continue editing from that recalled content.
- History behavior remains limited to user prompts; no new command-history behavior is introduced.

### Implementation Plan
- Add a small helper on `DogentCLI` to append submitted prompt text into the active prompt session history:
  - no-op when `self.session` or `self.session.history` is unavailable;
  - ignore empty or whitespace-only text;
  - call `append_string()` when supported by the history object.
- In `_read_input(...)`, when an editor outcome is submitted and the context is the main prompt flow, append `editor_outcome.text` to session history before returning it.
- Keep the durable history source unchanged:
  - agent request logging continues to write `user_input` into `.dogent/history.json`;
  - future sessions still rebuild prompt recall from `HistoryManager.prompt_history_strings()`.
- Do not append editor cancellations/discards to history.
- Avoid double-recording:
  - direct prompt submissions continue to rely on prompt_toolkit's normal history handling;
  - only the editor-submit path gets the explicit append.

### Edge Cases + Notes
- Multi-line prompts must remain a single history entry, not one entry per line.
- Recalling a multiline prompt should preserve line breaks so Up Arrow enters multiline editing/navigation behavior consistently.
- The helper should be safe with alternate history implementations and degrade silently if `append_string` is unavailable.
- Clarification/file-edit editor flows should not be changed unless they intentionally use the same main prompt history semantics.

### Tests
- Add a unit test for `_read_input(...)` showing that a `MultilineEditRequest` followed by editor submit appends the final text to session history.
- Add a unit test that the appended history text preserves embedded newlines exactly.
- Add a unit test that editor discard/cancel does not append anything to prompt history.
- Keep existing prompt history limit behavior unchanged; reuse `LimitedInMemoryHistory` in tests where possible.

---

## Release 0.9.27

### Goal
- Align Dogent's Claude Agent SDK integration with the `claude-agent-sdk>=0.1.51` behavior already referenced in `pyproject.toml`.
- Make tool approvals and SDK-native user questions reliable under the documented Python streaming pattern.
- Stop treating `allowed_tools` as a hard tool-surface restriction in helper flows.
- Switch Dogent's primary subagent tool naming from `Task` to `Agent` while preserving compatibility with SDK outputs that may still mention `Task`.
- Support project builtin commands/skills/sub-agents under both `<workspace>/.claude/` and `<workspace>/.dogent/`.
- Use SDK structured output for suitable one-shot flows that currently depend on free-text JSON parsing.
- Improve runtime permission handling with SDK permission suggestions/updates.
- Add better tool metadata, runtime observability, and opt-in partial streaming where the new SDK provides clear value.

### Current Baseline
- `pyproject.toml` already requires `claude-agent-sdk>=0.1.51`, so this release is mainly an integration-alignment release rather than only a dependency bump.
- `ConfigManager.build_options()` currently uses `allowed_tools` as the main built-in tool list when `can_use_tool` is absent, and omits `allowed_tools` entirely when `can_use_tool` is present.
- `InitWizard` and `ClaudeLessonDrafter` both use `allowed_tools=[]`, which no longer guarantees a no-tools workflow under the current SDK permission semantics.
- `AgentRunner._can_use_tool()` handles permission prompts only; it has no dedicated `AskUserQuestion` branch.
- `AgentRunner._can_use_tool()` ignores `ToolPermissionContext.suggestions` and does not return `updated_permissions`.
- The main system prompt currently requires all clarification and outline-edit interactions to go through `mcp__dogent__ui_request`.
- Dogent's default built-in tool list still includes `Task` instead of `Agent`.
- Dogent already loads `.claude/commands`, configured plugin commands, and plugin roots, but it does not yet treat project `.dogent` commands/skills/agents as first-class SDK-facing capability roots.
- Dogent currently renders completed assistant blocks and cost, but it does not surface partial messages, cumulative usage fields, cache-token fields, or documented rate-limit / task progress events.
- Dogent's custom MCP tools currently provide no `ToolAnnotations`.

### SDK Alignment Strategy
- Keep Dogent's main interactive agent on the normal Claude Code tool preset surface, plus Dogent MCP tools/plugins, and treat `allowed_tools` only as auto-approval input, not as the source of truth for what tools exist.
- For helper flows that need an actual restricted tool surface, use the SDK `tools` option explicitly:
  - `tools=[]` for no-tool one-shot generation flows.
  - `tools=[..., "AskUserQuestion"]` only when a restricted helper flow must still ask simple clarifying questions.
- Use `disallowed_tools` only where Dogent needs an explicit deny rule in Python; do not rely on `allowed_tools=[]` to mean "Claude cannot call tools".

### Permissions + Tool Approval Design
- Add the documented dummy `PreToolUse` hook for sessions that pass `can_use_tool`, so Python streaming stays open long enough for approvals and `AskUserQuestion`.
- Keep Dogent's existing permission UX and persistent authorization storage in `.dogent/dogent.json` for normal tool approvals.
- Extend `_can_use_tool()` with an early `AskUserQuestion` branch before normal permission evaluation:
  - parse SDK question payloads;
  - collect answers through the CLI;
  - return `PermissionResultAllow(updated_input={...})` with the original `questions` and the collected `answers`.
- Continue routing risky built-in tools such as `Bash`, `Write`, and `Edit` through Dogent's current permission checks after the `AskUserQuestion` fast path.
- When the user chooses "Allow" or "Allow and remember", use SDK `context.suggestions` and `PermissionResultAllow(updated_permissions=...)` where they match Dogent's runtime intent, while still persisting remembered authorizations into `.dogent/dogent.json`.
- Preserve existing temp-file and safe-root permission exceptions from earlier releases.

### Clarification + Outline Editing Design
- Update the main system prompt so the agent uses:
  - `AskUserQuestion` for simple clarification only;
  - `mcp__dogent__ui_request` for outline editing and any clarification that needs richer Dogent-specific semantics.
- Treat "simple clarification" as the SDK-supported shape:
  - up to 1-4 short questions;
  - 2-4 options per question;
  - no rich outline editing;
  - no dependency on custom schema fields such as `placeholder` for correctness.
- Keep Dogent's existing clarification UI code for `mcp__dogent__ui_request` because it still covers:
  - outline editing;
  - richer free-text collection;
  - current custom fields such as `recommended`, `allow_freeform`, and `placeholder`.
- Since the SDK docs say `AskUserQuestion` is not currently available inside subagents, Dogent should not rely on it as the only clarification path in subagent-driven flows.

### Project Commands + Skills + Subagents Design
- Replace `Task` with `Agent` in Dogent's default tool configuration and prompt/docs where Dogent describes the current SDK tool name.
- Keep compatibility checks for both `Task` and `Agent` in any streamed-message inspection, display, or denial-handling logic that interprets SDK output, because the local SDK docs note mixed naming may still appear in some message fields.
- Extend project capability discovery so Dogent supports builtin commands/skills/sub-agents under both:
  - `<workspace>/.claude/`
  - `<workspace>/.dogent/`
- Keep current `.claude/commands` support, and add parallel project `.dogent/commands` discovery for builtin Dogent-facing commands.
- Extend SDK capability roots so project `.dogent` and project `.claude` can both contribute skills/agents/hooks using the latest filesystem/plugin structure expected by the SDK.
- Treat the SDK skill-first/plugin-agent structure as the preferred direction, while keeping existing command loading behavior compatible during the transition.

### Structured Output Design
- Migrate the init wizard to SDK structured output first because it already expects a machine-readable payload with:
  - `doc_template`
  - `primary_language`
  - `dogent_md`
- Replace the current free-text JSON extraction path in `InitWizard` with:
  - `tools=[]`;
  - `output_format={"type": "json_schema", "schema": ...}`;
  - reading `ResultMessage.structured_output` as the primary success path.
- Keep a defensive fallback for malformed or missing structured output during the transition so CLI failures remain diagnosable instead of silently producing bad config.
- Leave `ClaudeLessonDrafter` on free-text output for now unless the implementation reveals a concrete need for structured fields there; the release requirement asks to start using structured output in suitable one-shot flows, not to convert every helper workflow at once.

### Tool Annotation Design
- Add `ToolAnnotations` to Dogent MCP tools where the SDK can benefit from stronger behavior hints.
- Initial targets:
  - document read/export/convert tools where read-only semantics are clear;
  - `analyze_media`;
  - custom web tools;
  - `ui_request`.
- Keep annotations conservative; only mark a tool read-only or open-world when the tool behavior actually matches that contract.

### Observability + Streaming Design
- Extend Dogent's result/event handling so SDK runtime metadata is captured and surfaced where useful:
  - cumulative `ResultMessage.usage`;
  - cache-token related usage fields when present;
  - `RateLimitEvent`;
  - `TaskStartedMessage`, `TaskProgressMessage`, and `TaskNotificationMessage`.
- Preserve the current concise CLI by default:
  - log full usage/event detail in debug/session logging;
  - surface user-facing warnings for rate limits and important background-task status changes.
- Add optional partial-response rendering using the SDK partial-message API (`include_partial_messages` / `StreamEvent`) for long-running outputs.
- Keep partial streaming opt-in for this release rather than default-on, matching the reviewed decision from the spike.

### Implementation Plan
- Update `ConfigManager.build_options()` to separate:
  - true tool-surface restriction (`tools`);
  - auto-approval hints (`allowed_tools`);
  - runtime approval handling (`can_use_tool` + hooks).
- Add a reusable helper for the documented dummy `PreToolUse` hook and apply it whenever Dogent passes `can_use_tool`.
- Extend `AgentRunner` with `AskUserQuestion` input parsing and answer collection, reusing the existing CLI interaction layer where possible.
- Extend permission responses to use SDK runtime permission updates where they improve the current flow without replacing Dogent's persistent authorization model.
- Update prompts/docs so the model knows when to choose `AskUserQuestion` versus `mcp__dogent__ui_request`.
- Update command/capability discovery so `.dogent` and `.claude` project roots can both contribute builtin commands/skills/sub-agents.
- Update `InitWizard` to use structured output and true no-tool restriction.
- Add annotations to selected Dogent MCP tools.
- Extend runner/logging code to capture usage/rate-limit/background-task events and support opt-in partial streaming.
- Update any helper-flow option builders that still depend on `allowed_tools=[]` as if it disables tools.

### Edge Cases + Notes
- If a restricted flow specifies a `tools` array and still needs SDK clarification, `AskUserQuestion` must be included explicitly or Claude cannot call it.
- If `AskUserQuestion` input is malformed or exceeds SDK limits, Dogent should deny that request cleanly and let the session surface an actionable error instead of falling into the normal permission prompt.
- SDK `updated_permissions` should be treated as session-scoped runtime state, not as a replacement for Dogent's persistent workspace authorization file.
- Project `.dogent` capability discovery must not break existing `.dogent/dogent.json` config/bootstrap responsibilities.
- Structured-output failures should remain observable in logs/tests; Dogent should not silently fall back to partial free text that looks valid but misses required fields.
- Partial streaming must not corrupt the existing final-message rendering, interrupt handling, or history/session logs.
- Release `0.9.27` still postpones file checkpointing / rewind and broader session-management commands from the SDK upgrade analysis.

### Tests
- Config tests:
  - verify helper flows use `tools=[]` or explicit `tools=[...]` when true restriction is intended;
  - verify default interactive options use `Agent` as the primary subagent tool name;
  - verify the documented `PreToolUse` hook is attached when `can_use_tool` is enabled.
- Command / capability discovery tests:
  - verify project `.dogent/commands` and `.claude/commands` are both discovered correctly;
  - verify project capability roots for `.dogent` and `.claude` are passed to the SDK as intended.
- Agent runner tests:
  - `AskUserQuestion` requests are intercepted before normal permission evaluation;
  - collected answers are returned through `PermissionResultAllow(updated_input=...)`;
  - runtime permission updates use SDK suggestions/updated permissions without regressing persistent authorization writes;
  - normal tool approvals still follow the current permission prompt path.
- Prompt/behavior tests:
  - system prompt instructions distinguish simple clarification from outline editing.
- Wizard tests:
  - successful structured output populates `WizardResult`;
  - missing/invalid structured output fails in a controlled way;
  - the wizard no longer depends on free-text JSON scraping as the primary path.
- Tool metadata / observability tests:
  - selected MCP tools expose the intended annotations;
  - usage / rate-limit / task-progress events are logged or surfaced in the expected paths;
  - partial streaming stays opt-in and does not break final response rendering.
