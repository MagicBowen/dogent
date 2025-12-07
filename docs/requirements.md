I need you to help me develop a CLI-based interactive AI Agent using Claude Agent SDK that can perform professional long-form document writing.

## Dogent Requirements

Specific requirements are as follows:

- It should be independently packaged for user installation. After installation, users can use the command `dogent` in any directory to enter an interactive CLI (can use Python's Rich library). The Agent will use the current directory as the working directory (can access and read/write all files in that directory)

- After entering the interactive CLI, the interaction method should be consistent with Claude Code, supporting the following specific Commands:
    - `/init`: Create a `.dogent` directory in the current directory and generate `.dogent/dogent.md` (template containing document type, length, tone, output format, language, other preferences and requirements). The Agent must always follow these constraints when working in this environment;
    - `/config`: Generate `.dogent/dogent.json` in the current directory, add it to .gitignore (create .gitignore if missing), and allow overriding env configs. If the Agent's working directory has this config file, prioritize reading it; otherwise fall back to environment variables;
    - `/exit`: Exit the CLI interaction and return to the main shell;

- In the interactive CLI, the Agent needs to be able to display its todo list to users, and reflect main operations and key processes during execution in the CLI.
- When starting in a directory without `.dogent/` or `dogent.json`, do not fail; allow the user to run `/init` and `/config` later to create them.
- The system prompt stays constant; per-turn user prompts must dynamically include current todo state and `@file` references. Do not seed default todos—todos come from the model via TodoWrite and must be kept in sync with tool results.
- The Tasks panel must update live based on TodoWrite tool results; detect TodoWrite tool outputs in the agent stream and render the changes in CLI UI to user immediately.
- Users can make requests to the Agent through the interactive CLI. Users can use the @ symbol to reference files in the current directory (like Claude Code, with a dropdown selection when users input @)
- Anthropic/Claude credentials and model settings may be managed globally in `~/.dogent/claude.json` as named profiles (e.g., `deepseek`, `glm`). A project’s `.dogent/dogent.json` can reference a profile name to populate `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `API_TIMEOUT_MS`, and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`. If no profile is referenced or found, fall back to environment variables.

    ```
    export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
    export ANTHROPIC_AUTH_TOKEN="xxx"
    export ANTHROPIC_MODEL="deepseek-reasoner"
    export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
    export API_TIMEOUT_MS=600000
    export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
    ```

- Allow users to create agents, commands, skills, including MCP and other tools in the `.claude` directory of the current directory just like Claude Code. The Agent should be able to recognize and use these configurations when entering, just like Claude Code;
- By default, the Agent in the working directory should be able to access shell tools, access the network, read/write files, load and use user-configured Skills, MCP tools, etc. These should be configured for Claude Agent SDK and recognized and loaded when the Agent starts;

- Document writing requirements:
    - The Agent should be able to follow user requirements and `.dogent/dogent.md` for document writing;
    - The Agent should be able to plan document writing tasks, form a todo list, and then execute them step by step;
    - For long professional documents, the Agent should break them into appropriately sized sections and complete them gradually;
    - The Agent should be able to search online for relevant materials and do professional research for article writing;
    - The Agent needs to be able to download corresponding online images as needed (place them in the working directory's `./images` directory) and insert them into articles to enrich content;
    - The Agent needs to be able to validate articles, plan validation tasks into the todo list, and ensure article accuracy without factual errors or inconsistencies;
    - The Agent should be able to polish the entire article at the end, ensuring coherent language usage, consistent tone, and reasonable structure;
    - The Agent should be able to accurately identify and cite online references and information in the article, with all cited online article links placed at the end;
    - Articles should default to Markdown output, using Chinese; when necessary, DSL (mermaid) diagrams, code snippets, and downloaded images can be inserted in Markdown;
    - During document writing and validation, the Agent can record temporary ideas or key points in `.dogent/memory.md` (inside `.dogent/`) and delete them after use;

---
## Development Requirements：

You need to split the development tasks in the form of user stories. Each story should have user value and be a feature that can be accepted end-to-end. They can be arranged according to the dependencies of the stories and from simple to complex. You need to write tests for each story. You need to write the split stories into an md file under docs. Each time the development is completed and the test passes, update it in a timely manner. When the user has new requirements, also update the file in a timely manner.

- Based on the above document writing requirements, you need to write very accurate, professional, and complete system prompts for Claude Agent SDK;
- All prompts configured for the model in the code need to be formed into separate prompt templates and placed in independent files for manual tuning;
- You need to search for Claude Agent SDK development manuals and example codes in `$project_root/claude-agent-sdk` and maximize the capabilities of Claude Agent SDK;
- The entire project should be developed in Python and be able to be independently packaged into an executable program for distribution to others;

Based on the above requirements, please carefully analyze, design, and break down the tasks, then complete them step by step.
Finally, package and deploy the program, complete local testing, and output usage documentation for my testing.

