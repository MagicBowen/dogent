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

## Pending Requirements

[support builtin commands/skills/sub-agents]

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual

[support mutiple language]
- support multiple languages: en & zh;
