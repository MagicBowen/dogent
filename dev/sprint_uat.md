# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

---

## Release 0.9.16

### Story 1 – Load Claude Commands into CLI
1) In `sample/`, create `.claude/commands/refactor.md` with a short description.
2) Run `dogent` in `sample/` and execute `/help`.
3) Expect `/claude:refactor` listed under Commands and tab completion to suggest it when typing `/claude:r`.
4) Run an unknown slash command (e.g., `/nope`) and confirm the Unknown Command panel shows.

User Test Results: PASS

### Story 2 – Resolve Slash Command Conflicts
1) In `sample/`, create `.claude/commands/help.md`.
2) Run `dogent` and check `/help` output for `/claude:help` (not `/help`).
3) Run `/claude:help` (with valid credentials). Expect it to run without Unknown Command errors.

User Test Results: PASS

### Story 3 – Load Claude Plugins from Workspace Config
1) Create a plugin directory `sample/plugins/demo` with:
   - `.claude-plugin/plugin.json` containing `{ "name": "demo-plugin" }`
   - `commands/greet.md` with a short prompt
2) Add `"claude_plugins": ["plugins/demo"]` to `sample/.dogent/dogent.json`.
3) Run `dogent` in `sample/` and check `/help` for `/claude:demo-plugin:greet`.
4) Add an invalid path to `claude_plugins` and run a command; expect a warning and the plugin command missing.

User Test Results: PASS

### Story 4 – SDK Settings for Claude Assets
1) Create `sample/.claude/skills/example-skill/SKILL.md` with a simple description and instruction.
2) Create `sample/.claude/agents/reviewer.md` with a basic subagent prompt.
3) Run `dogent` in `sample/` and ask for a task that should trigger the skill/subagent.
4) Expect the agent to invoke the skill/subagent when appropriate.

User Test Results: PASS
