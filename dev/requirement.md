# Original Requirements

---

## Release 0.9.17

- The various profiles currently supported by Dogent: llm_profile, web_profile..., users need to manually configure them in the configuration file `.dogent/dogent.json`, and often do not know the names of the profiles that can be filled in when configuring; I need a command-based way to change profiles, allowing users to choose from the available range; I hope that the configuration method and UI behavior of this dogent's commands are consistent with other commands, with easy-to-understand names and a user-friendly and beautiful UI;

- To make it easier to locate code problems with Dogent, I hope that Dogent's code supports logging capabilities, which can be used to record code actions or exceptions. The `debug` configuration in the current configuration file `.dogent/dogent.json` can be reused. If it is not configured (or is `null`), it means logging is turned off; otherwise, it indicates the enabled log types. For example, the currently supported type that records the interaction process between users and agents in the session can be called `info`(or other suitable name you recommended) level. Other log types can be classified according to log levels; after adding this logging function, it is necessary to insert logging in all places where exceptions and errors occur in the current dogent code. When the log configuration is turned on, these should be recorded. Logs are uniformly saved in `.dogent/logs` in the current working directory;

- The mcp__dogent__read_document tool currently does not support offsets. When it is necessary to read long documents, it is impossible to read them in multiple segments by the specified offset and length. Please help me modify the implementation of mcp__dogent__read_document and re-register its usage with the agent.

---

## Pending Requirements

[support mutiple language]
- support multiple languages: en & zh;

[support more generation mode]
- Dogent supports the ability to generate images;
- Dogent supports the ability to generate PPTX;
