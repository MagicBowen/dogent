# Design

---

## Release 0.9.9

### UX consistency for confirmations
- Replace inline left/right yes-no prompt with the same up/down list UI used by clarification questions.
- Apply to all yes-no confirmations: overwrite dogent.md, save lesson, tool permission, start writing now, and initialize now.
- Esc cancels the entire flow (treat as hard cancel). Non-interactive fallback keeps y/n input.

### Esc listener and agent loop safety
- Pause or stop the Esc listener entirely while any selection UI is active, then restart after the prompt exits.
- Do not interrupt an active agent loop while waiting for a selection choice (tool permission or other in-flight prompts).

### Debug logging configuration
- Add `debug: false` to `.dogent/dogent.json` defaults and schema.
- Debug disabled when the key is missing.

### Session log format and scope
- When debug is enabled, create `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` in JSONL format.
- Each line is a JSON object with at least: `timestamp`, `role` (system|user|assistant|tool), `source`, `event`, `content`.
- Log all LLM calls: main agent, init wizard, and lesson drafter.
- Log system prompts once per source when changed (including template injection).
- Log every user prompt.
- Log assistant streaming blocks as they arrive (text, thinking, tool_use, tool_result), using role `assistant` for text/thinking/tool_use and role `tool` for tool_result.

### Init wizard flow change
- Only for `/init prompt` (wizard path): after config creation and overwrite decision, show a selection to start writing.
- If user selects Yes, construct a prompt:
  `The user has initialized the current dogent project, and the user's initialization prompt is "<prompt>". Please continue to fulfill the user's needs.`
  and start the writing agent immediately.
- If user selects No or presses Esc, finish init and return to the CLI prompt.

### Auto-init on first request without dogent.json
- On user request, if `.dogent/dogent.json` and `.dogent/dogent.md` are missing, ask whether to initialize.
- If Yes, run the wizard using the user request as the init prompt, then ask to start writing (same as above).
- If No, proceed with current default processing (send the request to the agent without init).
- If Esc, cancel the flow and return to the CLI prompt.
