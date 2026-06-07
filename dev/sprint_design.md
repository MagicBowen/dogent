# Design

## Release 0.9.31

### Goal

Keep the Claude Agent SDK conversation context persistent across all user prompts within a single Dogent interactive session, so users do not need to re-enter information from previous interactions.

### Current Baseline

- After each task completes, `AgentRunner._safe_disconnect()` destroys the `ClaudeSDKClient`, clearing all conversation state.
- The next prompt creates a fresh client with no conversation history.
- Context between tasks is only available through history injection (`{history}` / `{history:last}` template variables in prompts), which provides summaries from `.dogent/history.json`, not the actual conversation messages.
- The client IS kept alive for follow-up states (`needs_clarification`, `needs_outline_edit`, `awaiting_input`), demonstrating the SDK naturally accumulates messages when the same client instance persists across `query()` calls.

### Design Direction

- Keep the `ClaudeSDKClient` connected throughout the interactive session, regardless of task outcome (completed, error, interrupted, aborted).
- Only disconnect on explicit session termination: user exit, profile change, or user-initiated reset.
- The SDK automatically accumulates conversation history when the same client instance receives multiple `query()` calls.

### Changes to AgentRunner

1. **Remove automatic disconnect after task completion.**
   - In `send_message()`, remove the conditional disconnect after streaming completes.
   - The client stays alive regardless of `last_outcome.status`.

2. **Add a `reset()` method.**
   - Disconnects the current client via `_safe_disconnect()`.
   - Clears all internal state (same cleanup as current fresh-start behavior).
   - Called by the CLI on profile changes, explicit reset, and exit.

3. **Keep interrupt handling intact.**
   - The existing interrupt drain logic already handles keeping the client alive for follow-up states; extend this to all states.

4. **Update system prompt between turns.**
   - The existing `self._client.options.system_prompt = system_prompt` update already works for reusing the client.
   - No change needed here; the SDK applies the new system prompt to the next turn while preserving conversation history.

### Changes to DogentCLI

1. **Call `agent.reset()` on `/exit`.** Ensures clean disconnection.
2. **Call `agent.reset()` on profile changes.** When the user changes an LLM, web, vision, or image profile, the underlying model or API endpoint may change, requiring a new client.
3. **Add a `/context` command.** Manages session context with subcommand parameters:
   - `/context reset` — disconnects the agent client and clears internal state, starting a fresh session without exiting Dogent.
   - `/context` without arguments — shows current session context info (e.g., turn count, status).
   - The command is extensible for future subcommands (e.g., `/context compact` for context window summarization).

### History Injection

- Keep existing `{history}` and `{history:last}` template variables unchanged.
- They remain valuable for cross-session context (when Dogent is restarted in the same workspace with existing `.dogent/history.json`).
- Within a session, the SDK's accumulated conversation history provides the primary context.
- Minor token redundancy from history summaries is acceptable for this release.

### Non-Interactive Mode

- `dogent -p "prompt"` continues to create a fresh client and disconnect after the single task.
- Persistent sessions apply only to interactive mode.

### Edge Cases

- **Very long sessions** may approach context window limits. For this release, accept the SDK's natural behavior (the SDK will error if the context window is exceeded). A future release can add automatic summarization or truncation.
- **Client corruption**: if an unrecoverable SDK error occurs mid-session, the CLI should call `agent.reset()` and inform the user that context was cleared.
- **Interrupt during persistent session**: the existing interrupt drain logic should continue to work; the drained partial response does not affect the next turn.
- **Profile change mid-session**: auto-reset ensures the new model/API takes effect immediately without stale session state.

### Tests

- Add a test for session persistence: send two messages through the runner without disconnecting, verify the second response has context from the first.
- Add a test for `reset()` properly disconnecting and clearing state.
- Add a test for the `/context reset` command.
- Add a test that non-interactive mode still disconnects after the run.
- Ensure the full `python -m unittest discover -s tests -v` suite passes.
