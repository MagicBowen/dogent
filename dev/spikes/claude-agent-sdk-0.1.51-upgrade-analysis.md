# Claude Agent SDK 0.1.51 Upgrade Analysis

## Scope

This spike reviews the local changes made in this repo for the Claude Agent SDK upgrade to `claude-agent-sdk>=0.1.51` in `pyproject.toml`, plus the updated and newly added materials under `claude/examples` and `claude/tutorials`.

Reviewed source changes:

- `pyproject.toml`
- Updated tutorials:
  - `claude/tutorials/python_sdk_guildline.md`
  - `claude/tutorials/control_execution_with_hooks.md`
  - `claude/tutorials/plugins_in_the_SDK.md`
  - `claude/tutorials/slash_commands_in_the_SDK.md`
  - `claude/tutorials/streaming_input.md`
  - `claude/tutorials/subagents_in_the_SDK.md`
  - `claude/tutorials/todo_lists.md`
  - `claude/tutorials/tracking_costs_and_usage.md`
- Updated examples:
  - `claude/examples/streaming_mode.py`
- New tutorials/examples that matter to Dogent:
  - `claude/tutorials/handle_approvals.md`
  - `claude/tutorials/structured_output.md`
  - `claude/tutorials/streaming_response.md`
  - `claude/tutorials/configure_permisions.md`
  - `claude/tutorials/file_checkpoint.md`
  - `claude/examples/filesystem_agents.py`

## Meaningful SDK Changes

### 1. Structured outputs are now a first-class SDK workflow

New/expanded docs:

- `claude/tutorials/structured_output.md`
- `claude/tutorials/python_sdk_guildline.md`

Key additions:

- `ClaudeAgentOptions.output_format`
- `ResultMessage.structured_output`
- Pydantic-based validation examples for Python

Why this matters:

- Dogent currently still parses JSON-like text manually in some places.
- The SDK now supports schema-validated final outputs instead of prompt-only formatting contracts.

Relevant Dogent code today:

- `dogent/cli/wizard.py`
- `dogent/features/lesson_drafter.py`
- `dogent/prompts/system.md`
- `dev/spikes/structure-format-message.md`

Assessment:

- High-value enhancement.
- Low risk for wizard-style one-shot flows.
- Especially useful where Dogent currently asks the model to return strict JSON in free text and then heuristically parses it.

### 2. Native approvals and native user-input handling are now much clearer

New/expanded docs:

- `claude/tutorials/handle_approvals.md`
- `claude/tutorials/configure_permisions.md`
- `claude/tutorials/python_sdk_guildline.md`

Key additions/clarifications:

- `AskUserQuestion` is the built-in tool for model-generated clarifying questions.
- `can_use_tool` is the callback for both approval requests and `AskUserQuestion`.
- `ToolPermissionContext` now documents `suggestions`.
- `PermissionResultAllow` now documents `updated_permissions`.
- Python docs explicitly require streaming mode plus a dummy `PreToolUse` hook to keep the stream open for `can_use_tool`.

Why this matters:

- Dogent already depends on `can_use_tool` in `dogent/agent/runner.py`.
- Dogent currently implements clarifications through a custom MCP tool `mcp__dogent__ui_request` instead of `AskUserQuestion`.
- The new docs expose a simpler native path for multiple-choice clarification, but not for outline editing.

Relevant Dogent code today:

- `dogent/agent/runner.py`
- `dogent/config/manager.py`
- `dogent/features/ui_tools.py`
- `dogent/features/clarification.py`
- `dogent/prompts/system.md`

Assessment:

- Upgrade-critical for permissions.
- High-value for clarification UX.
- `AskUserQuestion` can reduce prompt brittleness for simple clarification flows.
- `AskUserQuestion` does not replace Dogent's outline-edit flow.

### 3. Tool restriction semantics are more explicit

Expanded docs:

- `claude/tutorials/configure_permisions.md`
- `claude/tutorials/python_sdk_guildline.md`

Important clarification:

- `allowed_tools` auto-approves matching tools.
- `allowed_tools` does not mean "only these tools exist".
- Real restriction requires `tools`, `disallowed_tools`, permission rules, or callbacks.

Why this matters:

- Dogent currently uses `allowed_tools` as if it were a whitelist in several places.
- This is especially important in helper flows that expect zero or very limited tool access.

Relevant Dogent code today:

- `dogent/config/manager.py`
- `dogent/cli/wizard.py`
- `dogent/features/lesson_drafter.py`

Assessment:

- Highest priority design correction.
- This is both a safety issue and a correctness issue.

### 4. `Agent` is now the documented subagent tool name

Expanded docs:

- `claude/tutorials/subagents_in_the_SDK.md`
- `claude/tutorials/python_sdk_guildline.md`

Important change:

- The docs now describe the tool as `Agent`.
- `Task` is treated as the previous alias.

Why this matters:

- Dogent's default tool list still includes `Task`, not `Agent`, in `dogent/config/manager.py`.
- If Dogent wants real subagent support, it should stop treating `Task` as the primary name.

Relevant Dogent code today:

- `dogent/config/manager.py`
- `dev/requirement.md` pending requirement for sub-agents

Assessment:

- Medium urgency even if Dogent does not enable subagents immediately.
- Required if Dogent wants to align with current SDK naming and docs.

### 5. Filesystem agents, plugin agents, and skill-based workflows are better documented

Updated/new docs:

- `claude/tutorials/subagents_in_the_SDK.md`
- `claude/tutorials/plugins_in_the_SDK.md`
- `claude/tutorials/slash_commands_in_the_SDK.md`
- `claude/examples/filesystem_agents.py`

Important points:

- Filesystem subagents can live in `.claude/agents/`.
- Plugins can expose skills, agents, hooks, and MCP servers.
- Skill-first plugin structure is preferred over legacy `commands/`.

Why this matters:

- Dogent already loads plugins and already sets `setting_sources=["user", "project"]`.
- Dogent can likely support project-defined subagents with relatively small additional work.

Relevant Dogent code today:

- `dogent/config/manager.py`
- `dogent/cli/claude_commands.py`
- `dogent/plugins/claude/...`

Assessment:

- High-value enhancement.
- Strong fit with the existing pending requirement around built-in commands/skills/sub-agents.

### 6. Streaming responses now have a formal partial-message API

New docs:

- `claude/tutorials/streaming_response.md`
- updated `claude/examples/streaming_mode.py`

Key additions:

- `include_partial_messages`
- `StreamEvent`

Why this matters:

- Dogent currently renders completed `AssistantMessage` blocks, not token-level updates.
- Partial streaming could improve perceived responsiveness in long writing tasks.

Relevant Dogent code today:

- `dogent/agent/runner.py`

Assessment:

- Nice UX enhancement, but not required for the upgrade.

### 7. File checkpointing and rewind are now explicit SDK features

New docs:

- `claude/tutorials/file_checkpoint.md`

Key additions:

- `enable_file_checkpointing`
- `ClaudeSDKClient.rewind_files(...)`

Why this matters:

- Dogent writes and edits markdown heavily.
- Checkpointing could support "undo agent changes" or safer long-form editing.
- Limitation: SDK checkpointing only tracks built-in file-edit tools, not arbitrary `Bash` writes or Dogent document-export side effects.

Relevant Dogent code today:

- `dogent/agent/runner.py`
- `dogent/features/document_tools.py`

Assessment:

- Medium-value optional enhancement.
- Useful only if Dogent wants explicit rollback UX.

### 8. Session and runtime control APIs are broader

Expanded docs:

- `claude/tutorials/python_sdk_guildline.md`

New APIs documented:

- `list_sessions()`
- `get_session_messages()`
- `get_session_info()`
- `rename_session()`
- `tag_session()`
- `ClaudeSDKClient.set_permission_mode()`
- `ClaudeSDKClient.set_model()`
- `ClaudeSDKClient.get_mcp_status()`
- `ClaudeSDKClient.reconnect_mcp_server()`
- `ClaudeSDKClient.toggle_mcp_server()`
- `ClaudeSDKClient.stop_task()`
- `ClaudeSDKClient.get_server_info()`

Why this matters:

- Dogent currently maintains its own history and session logs.
- These APIs are useful mostly for optional CLI management features and debugging.

Assessment:

- Low priority for the current upgrade.

### 9. Cost, usage, rate-limit, and background-task types are richer

Updated docs:

- `claude/tutorials/tracking_costs_and_usage.md`
- `claude/tutorials/python_sdk_guildline.md`

Key points:

- Python exposes cumulative `ResultMessage.usage`, not per-step assistant usage.
- `RateLimitEvent`, `TaskStartedMessage`, `TaskProgressMessage`, and `TaskNotificationMessage` are documented.

Why this matters:

- Dogent currently displays cost only.
- Usage fields could be logged for analytics/debugging.
- Rate-limit events could surface better CLI warnings.

Relevant Dogent code today:

- `dogent/agent/runner.py`

Assessment:

- Useful observability enhancement.
- Not required for initial upgrade alignment.

### 10. Tool annotations can improve custom MCP tool behavior hints

Expanded docs:

- `claude/tutorials/python_sdk_guildline.md`

Key addition:

- `ToolAnnotations` on `@tool(...)`

Why this matters:

- Dogent exposes several custom MCP tools and currently provides no annotations.
- Read-only and open-world hints are a good fit for:
  - `read_document`
  - `analyze_media`
  - custom web tools
  - `ui_request`

Relevant Dogent code today:

- `dogent/features/document_tools.py`
- `dogent/features/web_tools.py`
- `dogent/features/vision_tools.py`
- `dogent/features/ui_tools.py`

Assessment:

- Low-risk cleanup.
- Helpful, but secondary.

## Dogent Impact Matrix

### Priority P0: Should be addressed before or during the SDK upgrade

1. Fix `can_use_tool` integration to match the documented Python streaming pattern.
   - Current gap: `dogent/agent/runner.py` passes `can_use_tool`, but does not add the dummy `PreToolUse` hook described in the new docs.
   - Risk: approval prompts or future `AskUserQuestion` handling may become brittle or fail unexpectedly after upgrade.

2. Stop relying on `allowed_tools` as a whitelist.
   - Current gap: `dogent/config/manager.py`, `dogent/cli/wizard.py`, and `dogent/features/lesson_drafter.py` rely on `allowed_tools` as if it constrains tool availability.
   - Risk: helper flows may have more tool access than intended.

3. Add `Agent` to Dogent's tool configuration and docs if subagents are in scope.
   - Current gap: Dogent still uses `Task` in `dogent/config/manager.py`.
   - Risk: Dogent stays on deprecated naming and misses current SDK subagent behavior.

### Priority P1: Strong enhancements with clear value

1. Replace manual JSON parsing with SDK structured outputs where possible.
   - Best initial target: `dogent/cli/wizard.py`.
   - Candidate follow-ups: lesson drafting, future planner/reviewer helpers, and any flow that returns machine-readable payloads.

2. Use `AskUserQuestion` for clarification-only flows.
   - Keep `mcp__dogent__ui_request` for outline editing.
   - Good fit when the question shape fits the SDK limits.

3. Support project/plugin subagents as a first-class Dogent capability.
   - Dogent already has the plugin foundation.
   - The pending requirement for built-in commands/skills/sub-agents aligns well with the new SDK materials.

4. Start using SDK permission suggestions/updates where appropriate.
   - Dogent can still keep persistent `.dogent/dogent.json` authorizations.
   - The SDK's `suggestions` and `updated_permissions` may simplify part of the flow.

### Priority P2: Useful but optional

1. Add `ToolAnnotations` to Dogent MCP tools.
2. Log `ResultMessage.usage` and cache-token fields.
3. Surface partial streaming with `include_partial_messages`.
4. Evaluate file checkpointing for document-writing safety.
5. Consider MCP/session management commands built on the new client APIs.

## Recommended Upgrade Strategy

### Phase 1: Safe alignment

- Align permission/tool configuration with the current SDK semantics.
- Add the documented hook support around `can_use_tool`.
- Add automated tests around approvals and restricted helper flows.

### Phase 2: Reliability improvements

- Migrate the init wizard to structured output.
- Decide whether clarifications should use native `AskUserQuestion`, custom `ui_request`, or a hybrid model.

### Phase 3: Capability expansion

- Add subagent support based on `Agent`, `.claude/agents`, and plugin-defined agents.
- Consider checkpointing, partial streaming, and richer runtime controls.

## Suggested Review Decisions

The following decisions should be made before implementation:

1. Should Dogent use `AskUserQuestion` only for simple clarifications, or fully replace the current clarification path?
ANSWER: Use `AskUserQuestion` for simple multiple-choice clarifications, but keep `mcp__dogent__ui_request` for complex outline-editing flows.

2. Should Dogent keep persistent authorization storage in `.dogent/dogent.json`, or partially adopt SDK `updated_permissions` as the runtime source of truth?
ANSWER: Dogent can keep persistent authorization storage in `.dogent/dogent.json` while partially adopting SDK `updated_permissions` as the runtime source of truth.

3. Should subagent support cover only filesystem/plugin agents first, or also include Dogent-defined built-in subagents?
ANSWER: support the project builtin commands/skills/sub-agents both in `<workspace>/.claude/` and `<workspace>/.dogent/`.

1. Should file checkpointing be enabled by default, opt-in, or postponed?
ANSWER: Postpone file checkpointing until there is a clear use case and UX design for it.

1. Should partial response streaming be on by default in the CLI, or kept as a later UX enhancement?
ANSWER: Start with opt-in and gather user feedback before making it the default.

## Additional Analysis After Review Decisions

This section extends the spike based on the reviewed decisions above.

### 1. How Dogent should handle `AskUserQuestion` when users may choose an option or enter free text

SDK behavior from `claude/tutorials/handle_approvals.md`:

- `AskUserQuestion` input includes:
  - `questions`
  - `question`
  - `header`
  - `options`
  - `multiSelect`
- The SDK docs do not define an `allow_freeform`, `placeholder`, or validation field in the tool input.
- The SDK docs explicitly say that if the application wants to support free text, the application should:
  - show an additional "Other" choice itself;
  - accept custom text from the user;
  - return that custom text as the answer value, not the literal word `"Other"`.

Implication for Dogent:

- Free-text support in `AskUserQuestion` is not schema-driven by Claude.
- It is an application-side UX choice implemented by Dogent.
- Therefore `AskUserQuestion` is best treated as:
  - native support for simple multiple-choice clarification;
  - optionally extended by Dogent with a local "Other / custom input" affordance.

Recommended Dogent handling:

1. Use `AskUserQuestion` only for simple clarification flows.
   - Good fit:
     - 1-4 short clarification questions
     - 2-4 options per question
     - no need for rich editing
     - no strong validation beyond choosing labels or entering one short custom answer
   - Bad fit:
     - outline editing
     - long-form user input
     - structured forms
     - cases needing placeholders, field-level validation, or richer UI semantics

2. Keep Dogent's own free-text policy instead of assuming the SDK provides one.
   - When Dogent decides that free text is acceptable for a simple clarification question, the CLI may expose:
     - numbered options from Claude
     - one additional local entry path for custom text
   - Dogent should then return:
     - the original `questions`
     - `answers[question_text] = user_custom_text`

3. Do not try to force all current clarification schema features into `AskUserQuestion`.
   - Dogent's existing clarification payload supports fields like:
     - `recommended`
     - `allow_freeform`
     - `placeholder`
   - `AskUserQuestion` does not natively carry the same semantics.
   - For cases where these fields materially affect UX or correctness, Dogent should keep `mcp__dogent__ui_request`.

Practical conclusion:

- The reviewed decision is sound: use `AskUserQuestion` for simple multiple-choice clarification only.
- Dogent may support free-text answers on top of it, but that is a Dogent UI extension, not an SDK-native question capability.
- If a clarification requires explicit free-text semantics as part of the protocol, Dogent should keep using `mcp__dogent__ui_request`.

### 2. When Dogent uses `AskUserQuestion`, does Dogent need to change permission-request handling?

Short answer:

- Yes, Dogent must change the `can_use_tool` handling path.
- No, Dogent does not need to replace its existing permission-selection UI for normal tool approvals.

SDK behavior from `claude/tutorials/handle_approvals.md` and `claude/tutorials/python_sdk_guildline.md`:

- Both normal tool approvals and `AskUserQuestion` arrive through the same `can_use_tool` callback.
- The callback receives:
  - `tool_name`
  - `input_data`
  - `context`
- For `AskUserQuestion`, the application must return `PermissionResultAllow(updated_input={...})` with:
  - the original `questions`
  - an `answers` object
- The SDK does not automatically render:
  - approval dialogs
  - question dialogs
  - "remember this choice" UX
- The SDK does provide lower-level helpers:
  - `ToolPermissionContext.suggestions`
  - `PermissionResultAllow.updated_permissions`

Implication for Dogent's current implementation:

- Dogent's current `_can_use_tool()` path in `dogent/agent/runner.py` is permission-oriented.
- It evaluates whether a tool needs confirmation, then routes to Dogent's own permission prompt.
- If Dogent introduces `AskUserQuestion`, it must add a special branch before normal permission evaluation:
  - `if tool_name == "AskUserQuestion": ...`
  - collect answers via Dogent CLI UI
  - return `PermissionResultAllow(updated_input={questions, answers})`

What should remain unchanged:

- Dogent's existing permission-selection UX for risky tools such as:
  - `Bash`
  - `Write`
  - `Edit`
  - protected-path operations
- The current options like:
  - Allow
  - Allow and remember
  - Deny

What can improve with the new SDK:

1. Dogent can keep its current persistent permission model.
   - Continue storing durable authorizations in `.dogent/dogent.json`.

2. Dogent can also adopt SDK runtime permission updates.
   - Use `context.suggestions` when present to understand the SDK's suggested rule updates.
   - Use `PermissionResultAllow(updated_permissions=...)` to apply runtime permission changes for the current session.

3. Dogent can map the current "Allow and remember" flow into two layers.
   - Runtime layer:
     - apply SDK `updated_permissions` where useful
   - Persistent layer:
     - continue writing authorized targets into `.dogent/dogent.json`

What the SDK does not provide as a full solution:

- It does not replace Dogent's approval UI.
- It does not provide a complete persistent authorization storage system for Dogent.
- It does not remove the need for Dogent's own policy decisions around workspace safety.

Practical conclusion:

- Dogent should separate the two cases inside `can_use_tool`:
  - `AskUserQuestion` -> collect answers, not a permission dialog
  - all other protected tools -> existing permission dialog flow
- Dogent should keep its current permission-selection UI for approval requests.
- The new SDK provides useful primitives for runtime permission updates, but not a turnkey replacement for Dogent's existing approval architecture.

## Proposed Potential Modifications

- Add an internal helper that builds the required dummy `PreToolUse` hook whenever Dogent passes `can_use_tool`.
- Replace whitelist-style `allowed_tools` usage with explicit `tools` and `disallowed_tools` decisions.
- Add `Agent` alongside any legacy `Task` handling and update docs/prompts accordingly.
- Add structured-output schemas and typed parsing for the init wizard first.
- Evaluate a hybrid clarification design:
  - `AskUserQuestion` for multiple-choice clarification
  - existing `mcp__dogent__ui_request` for outline editing and richer forms
- Add `ToolAnnotations` to Dogent MCP tools.
- Add tests that cover:
  - permission callback behavior
  - helper flows with restricted tool access
  - structured-output parsing
  - any new AskUserQuestion bridge

## Summary

The SDK update is not just a dependency bump. The biggest Dogent-relevant changes are:

1. Structured outputs now provide a better replacement for Dogent's fragile prompt-only JSON contracts.
2. The approvals/user-input path is better documented and exposes a native clarification tool (`AskUserQuestion`).
3. The docs make it clear Dogent should stop treating `allowed_tools` as a hard restriction.
4. Subagent support is now mature enough to align with Dogent's pending roadmap for commands/skills/sub-agents.

The most important near-term work is to harden Dogent's permission/tool configuration and then selectively adopt structured outputs and native clarification support.

## Draft Requirement

### Purpose

Define a reviewable requirement for aligning Dogent with the current Claude Agent SDK capabilities after upgrading the dependency to `claude-agent-sdk>=0.1.51`.

### Proposed Release

Release TBD: Claude Agent SDK alignment and capability upgrade

### Goal

Upgrade Dogent's Claude Agent SDK integration so that:

- current permission and tool-restriction behavior remains correct after the SDK update;
- Dogent adopts SDK-native structured outputs where they materially improve reliability;
- Dogent can use the current SDK approach for approvals, clarifying questions, and subagents where appropriate;
- Dogent's built-in plugin and SDK-facing features stay aligned with the latest SDK naming and behavior.

### Required Scope

#### 1. Permission and tool-control alignment

- Review all Dogent uses of `allowed_tools`.
- Replace any whitelist-style assumptions with the correct SDK mechanisms:
  - `tools`
  - `disallowed_tools`
  - permission rules
  - `can_use_tool`
- Ensure Dogent's Python streaming integration uses the SDK-documented pattern required for `can_use_tool`.
- Preserve Dogent's existing workspace safety rules and authorization UX.

#### 2. Structured-output adoption for machine-readable flows

- Replace prompt-only JSON parsing with SDK structured output where the result is consumed programmatically.
- Initial mandatory target:
  - `/init` wizard result generation in `dogent/cli/wizard.py`
- Optional follow-up targets may be included if they are low-risk and tested.

#### 3. Clarification and approval flow review

- Evaluate native `AskUserQuestion` support for clarification flows.
- Keep or extend Dogent's custom `ui_request` flow for cases not covered by `AskUserQuestion`, especially outline editing.
- Support the latest SDK approval flow behavior without regressing current CLI interaction patterns.

#### 4. Subagent naming and support alignment

- Align Dogent with the current SDK `Agent` tool naming.
- Review whether Dogent should support:
  - project-defined agents in `.claude/agents/`
  - plugin-defined agents
  - built-in Dogent subagents
- At minimum, ensure Dogent does not block or misconfigure the current SDK subagent path.

#### 5. Built-in plugin and SDK-facing asset sync

- Review Dogent's bundled Claude plugin/skills against the updated local SDK examples/tutorials.
- Update Dogent's built-in Claude plugin packaging only where required for SDK compatibility or documented behavior changes.

### Optional Scope

- Add `ToolAnnotations` to Dogent MCP tools.
- Store or display `ResultMessage.usage` metrics.
- Support partial response streaming with `include_partial_messages`.
- Evaluate file checkpointing and rewind workflows for Dogent document editing.

### Out of Scope

- A broad rewrite of Dogent's CLI UX unrelated to the SDK upgrade.
- Replacing outline editing with a purely SDK-native flow if it reduces current UX quality.
- Adding all possible new SDK features in one release.

### Acceptance Criteria

1. Dogent permission prompts and tool approvals work correctly with the upgraded SDK in the main interactive agent flow.
2. Dogent no longer relies on `allowed_tools` as if it were a hard tool whitelist.
3. The `/init` wizard uses a reliable structured-output path and no longer depends on free-text JSON extraction.
4. Dogent's clarification design is explicitly defined:
   - either native `AskUserQuestion`,
   - or custom `ui_request`,
   - or a documented hybrid model.
5. Dogent is aligned with the SDK `Agent` tool naming and does not regress future subagent support.
6. All changed functions have automated tests.

### Expected User Value

- More reliable clarification and wizard flows.
- Safer and more predictable tool access behavior.
- Better alignment with the latest Claude Agent SDK capabilities.
- Clearer path to future Dogent features such as subagents and richer approval workflows.

### Open Questions For Review

1. Should Dogent adopt `AskUserQuestion` for all clarifications or only for simple multiple-choice cases?
   - Reviewed answer: use it only for simple multiple-choice clarifications, while keeping `mcp__dogent__ui_request` for richer flows.
2. Should Dogent keep its current persistent authorization storage model, or partially adopt SDK runtime permission updates?
   - Reviewed answer: keep persistent storage in `.dogent/dogent.json` and partially adopt SDK runtime permission updates.
3. Should the first subagent milestone only support `.claude/agents/` and plugin agents, or also ship Dogent-defined built-in agents?
   - Reviewed answer: support project built-in commands/skills/sub-agents in both `<workspace>/.claude/` and `<workspace>/.dogent/`.
4. Should file checkpointing be deferred to a later release?
   - Reviewed answer: yes, postpone it until a clearer use case and UX exist.
5. Should partial response streaming be included in the same release or postponed?
   - Reviewed answer: start as opt-in and gather feedback first.
