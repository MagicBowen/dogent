# Original Requirements

## Release 0.9.32

- The current claude-agent-sdk version in `pyproject.toml` is 0.1.72, I want to update it to the newest version v0.2.115 (https://github.com/anthropics/claude-agent-sdk-python);
- review all the changelog of claude-agent-sdk from 0.1.72 to v0.2.115 and the tutorials and examples in `https://github.com/anthropics/claude-agent-sdk-python/tree/main/examples`, based on SDK updates, identify which usages of SDK features within Dogent require modification, and formulate corresponding design and implementation plans for these updates.
- There is a bug in the current Dogent: when the Claude Agent SDK launched multiple agents, if a user confirmation prompt appears within a  sub-agent, Dogent will not actively display the confirmation options for the user to select or respond to — it only renders confirmation prompts from the main agent. Please investigate and analyze this issue, and design a sound solution for it (including a TUI display scheme).

## Pending Requirements

[issues]
- How to deal the human confirmation in subagent?
- Question/Answer mode should follow the newest claude mode.
- User can choose improving dogent.md or recording lessons when a iterator finished (session stop).

[support more document template]
- resume
- tech report
- blog
- software design document
- software usage manual
- consultant proposal

[support mutiple languages]
- support multiple languages: en & zh;

[support textual & web]

- https://github.com/Textualize/textual
