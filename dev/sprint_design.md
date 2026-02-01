# Design

---

## Release 0.9.22

### Goals
- Persist input recall across restarts for user prompts (from `.dogent/history.json`) and `/` commands.
- Replace tag+JSON clarification/outline edit outputs with MCP tool-based UI calls.

### Design Overview
#### 1) Input recall across restarts (prompts + `/` commands)
- **Source of prompts + commands:** use existing `.dogent/history.json` entries (`HistoryManager.append(..., prompt=...)`) for both user prompts and `/` commands.
- **Lifecycle:** `/clean history` clears both prompts and `/` command recall.
- **Limit:** seed prompt history with the **latest 30** combined items (prompts + commands).
- **Exclude:** clarification answers are stored in history but not used for recall.

**Seeding strategy**
- Load prompts from `history.json` (filter non-empty `prompt`).
- Sort by timestamp, take last 30, preserve chronological order.
- Preload `prompt_toolkit` history using `InMemoryHistory`.

**Write path**
- When `_handle_command(...)` receives a valid `/` command, append a history entry with `prompt` set to the raw command (e.g. `/show history`) and a distinct status (e.g. `status="command"`), so it is eligible for recall.

#### 2) Tool-based UI requests for clarification/outline edit
- **New MCP tool:** `mcp__dogent__ui_request` via SDK MCP server.
- **Schema (input):**
  - `type`: `"clarification" | "outline_edit"`
  - `title`: string
  - `preface?`: string (clarification only)
  - `questions?`: clarification schema (same as current JSON schema)
  - `outline_text?`: string (outline_edit only)
- **Tool-only:** remove tag+JSON parsing paths; only tool calls trigger clarification/outline edit UI.

**Runtime flow**
1. Model calls `mcp__dogent__ui_request`.
2. `AgentRunner` intercepts `ToolUseBlock`:
   - Validate payload based on `type`.
   - Set `_needs_clarification` / `_needs_outline_edit` and store payload.
   - Interrupt streaming to avoid further assistant output.
3. CLI renders the appropriate UI:
   - Clarification → existing Q&A prompts.
   - Outline edit → existing multiline editor (using `outline_text`).
4. CLI sends user answers back as a normal user message (same as current flow).

**Tool execution**
- The MCP tool implementation can return a minimal placeholder response (e.g. “UI request received”) if executed; `AgentRunner` should still interrupt on `ToolUseBlock` and ignore any subsequent tool result blocks.

**Prompt updates**
- Update `dogent/prompts/system.md` to require tool calls for clarification/outline edit.
- Remove or de-emphasize tag+JSON instructions; keep fallback sentinel guidance only for non-tool-capable runtimes.

### Affected Modules
- `dogent/cli/app.py`: preload history; record `/` commands into history; intercept UI tool use.
- `dogent/core/history.py`: reuse for prompt sources.
- `dogent/features/ui_tools.py` (new): define `ui_request` tool + schema.
- `dogent/config/manager.py`: register UI tool in MCP server + allowed tools.
- `dogent/agent/runner.py`: handle `ToolUseBlock` for UI tool; remove tag parsing logic.
- `dogent/features/clarification.py` and `dogent/outline_edit.py`: remove tag parsing helpers.
- `dogent/prompts/system.md`: update clarification/outline rules (tool-only).

### Testing Notes
- Add unit tests for:
  - merging prompt+command history (limit 30, ordering).
  - command history persistence in `.dogent/history.json`.
  - tool-use interception sets `needs_clarification/needs_outline_edit`.
