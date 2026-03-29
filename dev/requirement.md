# Original Requirements

---

## Release 0.9.23

- In CLI default markdown editor, user could use @ to mention a file in the current directory, a drop list will show up for user to select, as same as the action in the single line input mode;
- In CLI default markdown editor, user could use @@ to mention a doc template, a drop list will show up for user to select, as same as the action in the single line input mode;
- If user input @ or @@ but select nothing from the drop list, the @ or @@ will be treated as normal characters and remain in the content;

---

## Release 0.9.24

- Encapsulate the skill located at `claude/skills/skills/pptx` as a Claude Plugin. Place the Plugin, along with its corresponding skill configuration and source code, into the `dogent/plugins/claude` directory for distribution with the package. Install this Claude Plugin to the corresponding directory under `~/.dogent/plugins`, then add the Plugin to the configuration file (in `claude_plugins` of `.dogent.json`) by default, so that Dogent can natively use the official Claude PPTX skill out of the box.
- all builtin plugins under the `dogent/plugins` directory need to be automatically packaged and installed to the plugin directory under `~/.dogent/plugins` by default. Users can manually add all existing plugins in the plugin directory under `~/.dogent/plugins` to `claude_plugins` of `.dogent.json` file.

---

## Release 0.9.25

- rename `claude_plugins` to `plugins` in `.dogent.json` and `~/.dogent/dogent.json` , and modify all related codes and docs;
- Add instructions in `docs/04-document-export.md` stating that PDF generation and conversion depend on pandoc and Chrome. If Dogent detects that they are not installed locally, it will prompt the user whether to download them first.
- Add a note in `docs/04-document-export.md` that there is currently no perfect solution for PPTX generation. For the time being, the official Claude PPTX skill is used by default. For details about this skill, please refer to: https://github.com/anthropics/skills/tree/main/skills/pptx
- When dogent read files or execute script in `~/.dogent/plugins/` or `~/.claude`, do not need to request permission allowance from user.
- If dogent generates any temporary files during the execution of this task (the temporary files could to be saved in a python list and clear when task exist), subsequent deletion of these files within the same task execution does not require user authorization.

---

## Release 0.9.26

- When the user invokes the editor with `CTRL+E`, edits the prompt, and sends it using `CTRL+J`. The prompt edited via CTRL+E does not appear later when the user uses the Up Arrow to recall historical commands and prompts. This issue needs to be fixed.

- When the user recall the historical prompt edited by `CTRL+E` with Up Arrow, the content of the prompt should be exactly the same as the content edited by `CTRL+E`, user could edit the prompt directly or edit the prompt by invoking `CTRL+E` again;

---

## Release 0.9.27

- Upgrade `claude-agent-sdk` to `0.1.51` and align Dogent's Claude SDK integration with the latest official tutorials and examples under the `claude` directory.
- Fix Dogent's tool approval integration to match the latest SDK streaming pattern, including the documented hook handling required by `can_use_tool`, and start using SDK permission `suggestions` / `updated_permissions` where useful while still keeping Dogent's persistent authorizations in `.dogent/dogent.json`.
- Stop using `allowed_tools` as if it were a strict whitelist, and update the related configuration, helper flows, and tests so restricted flows only expose the intended tools under the latest SDK semantics.
- Replace Dogent's default subagent tool naming from `Task` to `Agent` in configuration and docs, and support project builtin commands/skills/sub-agents under `<workspace>/.claude/` and `<workspace>/.dogent/` according to the latest SDK plugin / filesystem-agent structure.
- For simple clarification flows, use the SDK built-in `AskUserQuestion`; for complex outline editing or richer custom input flows, keep using Dogent's existing `mcp__dogent__ui_request`.
- Start using the SDK structured output capability in suitable one-shot flows, especially flows that currently depend on strict JSON text parsing, and add automated tests for the upgraded parsing path.
- Add `ToolAnnotations` to Dogent custom MCP tools where appropriate, so read-only and open-world tools provide better behavior hints to the SDK.
- Add richer SDK runtime feedback in Dogent, including cumulative `ResultMessage.usage`, cache-token fields, rate-limit / task progress notifications, and optional partial response streaming in the CLI for long-running outputs.

---

## Pending Requirements

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual
- consultant proposal

[support mutiple language]
- support multiple languages: en & zh;
