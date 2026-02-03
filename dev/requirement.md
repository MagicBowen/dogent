# Original Requirements

---

## Release 0.9.23

- In CLI default editor, user could use @ to mention a file in the current directory, a drop list will show up for user to select, as same as in the single line input mode;
- In CLI default editor, user could use @@ to mention a doc template, a drop list will show up for user to select, as same as in the single line input mode;
- The current code replaces @ and @@ with a prefix in the format `[...]` followed by a colon before sending the user's Prompt to the LLM. I want to unify the cases where users use @ and @@ in the editor for file and template references with the replace strategy in single-line prompts. In the end, both @ and @@ should be replaced with a format similar to markdown links. For example, `@path/file.md` is replaced with `[file.md](path/file.md)`. Similarly, could you help me design a unified replacement scheme for `@@global:resume`?


---

## Pending Requirements

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual

[support more generation mode]
- Dogent supports the ability to generate PPT;

[support mutiple language]
- support multiple languages: en & zh;
