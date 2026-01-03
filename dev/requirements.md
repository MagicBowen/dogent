# Original Requirements

---

## Release 0.9.10

- Improve CLI prompt and free-form clarification UX: keep single-line input by default, but provide a dedicated multiline Markdown editor when the user presses Ctrl+E (for main prompt input and free-form answers). Selecting "Other (free-form answer)" in clarification should open the editor directly. The editor must support multiline editing with Enter inserting new lines, common shortcuts, and Markdown-friendly writing. Provide a Markdown preview toggle inside the editor, and allow Ctrl+Enter to submit and Esc to cancel and return to single-line input. Pause the Esc listener while the editor is open.

- The markdown editor must combine editing with lightweight real-time rendering in a single view. It should also offer a full preview toggle (Ctrl+P) that is read-only and returns to editing. The UI must be beautiful with a dark theme. Use Ctrl+Enter to submit (fallback like Ctrl+J shown in the footer), and Ctrl+Q to return (Esc should no longer exit the editor). The editor should provide common GUI-like shortcuts (select word/line, skip words, jump to line start/end) and list fallback shortcuts in the footer when terminal limitations apply. Provide prominent labeled actions in the footer. On return, if the buffer is dirty, prompt to discard, submit, or save to file; saving prompts for a file path (relative or absolute) and confirms overwrite if the file exists. Only save-on-return (no explicit save key).

## Release 0.9.11

- The setting of debug mode should not appear in dogent.json default (It is a background function)
- After the debug mode is turned on, the output log will no longer use the jsonl format, but will become a structured md file. The structure and content organization should be easy for humans to read. In addition, the log should be comprehensive. All kinds of exceptions should also be recorded, including the original exception content and the location where the code occurred. The entire log is organized in the form of an event stream.
- When users enter prompts and answer free-form questions, they enter the editor mode, which supports configuration by users in dogent.json. The current editor mode is considered as dogent editor mode (default mode)，should also supports user config the editor to `vi`; for implementation details, refer to some research schemes in dev/spikes/cli-markdown-vi.md (you need to conduct an overall design based on other requirements of dogent)

---

## Pending Requirements

- Dogent supports more excellent file templates (technical blog);
- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Provide a good solution for model context overflow;
- Dogent supports the ability to generate images;
