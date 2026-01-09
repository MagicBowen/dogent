# Original Requirements

---

## Release 0.9.15

- BugFix：I encountered an error when using dogent to convert an xlsx file to markdown. It seems that the mcp tool did not automatically extract the names of the sheets. Please modify the code so that when the user does not specify the sheet names, the code can automatically extract them, and can extract all the sheets from the xlsx file and convert them into a single markdown file. The names of different sheets can be used as H2 Titles in the markdown file; the H1 title of the markdown file should be the prefix of the xlsx file name.
- python lib termios doesn't support windows platform, I  extracted the terminal.py to split the codes to different platform. Please check and implement all necessary codes for support Windows Platform
- There are some PDF file conversion and generation tools in the code. They will check if the user's computer has them when needed, and then download them in real-time. However, to prevent issues with the user's poor network connection, I hope to add a packaging mode, namely the full mode (which internally carries the tools that users need to download and install during runtime). Then, I can specify the packaging and release mode when publishing.

---

## Pending Requirements

[support claude]
- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;

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
