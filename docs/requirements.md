I need you to help me develop a CLI-based interactive AI Agent using Claude Agent SDK that can perform professional long-form document writing.

Specific requirements are as follows:

- It should be independently packaged for user installation. After installation, users can use the command `doc` in any directory to enter an interactive CLI (can use Python's Rich library). The Agent will use the current directory as the working directory (can access and read/write all files in that directory)
- Claude Agent SDK should be able to read configurations from the following environment variables for model API access and parameter configuration:

```
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="xxx"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

- After entering the interactive CLI, the interaction method should be consistent with Claude Code, supporting the following specific Commands:
    - `/init`: Create a `.doc-guild.md` file in the current directory, generating a template by default containing global configurations such as document type, length, tone, output format, language, other preferences and requirements. The Agent must always follow these constraints when working in this environment;
    - `/config`: Help users generate a configuration file in the current directory, add it to .gitignore, where users can reconfigure those configurations read from environment variables. If the Agent's current working directory has a configuration file, prioritize reading the configuration from that file, otherwise read from environment variables;
    - `/exit`: Exit the CLI interaction and return to the main shell;

- In the interactive CLI, the Agent needs to be able to display its todo list to users, and reflect main operations and key processes during execution in the CLI.
- Users can make requests to the Agent through the interactive CLI. Users can use the @ symbol to reference files in the current directory (like Claude Code, with a dropdown selection when users input @)
- Allow users to create agents, commands, skills, including MCP and other tools in the `.claude` directory of the current directory just like Claude Code. The Agent should be able to recognize and use these configurations when entering, just like Claude Code;
- By default, the Agent in the working directory should be able to access shell tools, access the network, read/write files, load and use user-configured Skills, MCP tools, etc. These should be configured for Claude Agent SDK and recognized and loaded when the Agent starts;

- Document writing requirements:
    - The Agent should be able to follow user requirements and `.doc-guild.md` for document writing;
    - The Agent should be able to plan document writing tasks, form a todo list, and then execute them step by step;
    - For long professional documents, the Agent should break them into appropriately sized sections and complete them gradually;
    - The Agent should be able to search online for relevant materials and do professional research for article writing;
    - The Agent needs to be able to download corresponding online images as needed (place them in the working directory's `./images` directory) and insert them into articles to enrich content;
    - The Agent needs to be able to validate articles, plan validation tasks into the todo list, and ensure article accuracy without factual errors or inconsistencies;
    - The Agent should be able to polish the entire article at the end, ensuring coherent language usage, consistent tone, and reasonable structure;
    - The Agent should be able to accurately identify and cite online references and information in the article, with all cited online article links placed at the end;
    - Articles should default to Markdown output, using Chinese; when necessary, DSL (mermaid) diagrams, code snippets, and downloaded images can be inserted in Markdown;
    - During document writing and validation, the Agent can record temporary ideas or key points in `.memory.md` and delete them after use;

- Based on the above document writing requirements, you need to write very accurate, professional, and complete system prompts for Claude Agent SDK;
- All prompts configured for the model in the code need to be formed into separate prompt templates and placed in independent files for manual tuning;
- You need to search for Claude Agent SDK development manuals (https://platform.claude.com/docs/en/agent-sdk/python) and maximize the capabilities of Claude Agent SDK;
- The entire project should be developed in Python and be able to be independently packaged into an executable program for distribution to others;

---
Based on the above requirements, please carefully analyze, design, and break down the tasks, then complete them step by step.
Finally, package and deploy the program, complete local testing, and output usage documentation for my testing.