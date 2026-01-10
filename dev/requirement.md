# Original Requirements

---

## Release 0.9.16

- Dogent should supports loading the user configured Claude's commands, subagents, and skills from `.claude` under the workspace;
    - Claude Skills are supported by dogent (in the `can_use_tool` callback)，Just check the code to confirm.
    - Claude commands and subagents are not supported by dogent, should register the user configured claude's slash command to dogent commands with a `claude:` prefix.
- Dogent supports loading Claude's plugins;
- For how to support claude's plugins and  commands, subagents, and skills, should according the tutorials under `claude-agent-sdk/tutorials`, In particular, the following documents：`slash_commands_in_the_SDK.md`, `subagents_in_the_SDK.md`, `plugins_in_the_SDK.md`, Other tutorial files can also be consulted if needed.

---

## Pending Requirements

[Configuration mode optimization]
- Dogent supports subcommands for re-config profiles;
- log mechanism should be improved, adding the exception log and log level.
- Dogent supports more excellent file templates (technical blog);

[support mutiple language]
- support multiple languages: en & zh;

[support more generation mode]
- Dogent supports the ability to generate images;
- Dogent supports the ability to generate PPT;

[test the new claude code and claude agent sdk]
- Provide a good solution for model context overflow;
- A comprehensive solution to address context overflow needs to investigate the causes and mechanisms of context overflow in Claude Agent Client and LLM, and construct a multiple-cycle scheme based on these mechanisms.
