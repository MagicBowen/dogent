# Original Requirements

## Release 0.9.31

There is an issue with the current design of Dogent. Once a task is completed, its corresponding task context is cleared. When users submit new requests within the same session, they have to re-enter much related information from previous conversations since the system cannot retain historical task data. Please analyze the existing agent loop workflow of Dogent and provide code modification solutions to keep all historical context persistent throughout the session until the user exits Dogent.

## Pending Requirements

[issues]
- How to deal the human confirmation in subagent?
- Keep context when a iterator finished.
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
