# Requirements

## Release 0.1

I need you to help me develop a CLI-based interactive AI Agent using Claude Agent SDK that can perform professional long-form document writing.

### Dogent Requirements

Specific requirements are as follows:

- It should be independently packaged for user installation. After installation, users can use the command `dogent` in any directory to enter an interactive CLI (can use Python's Rich library). The Agent will use the current directory as the working directory (can access and read/write all files in that directory)

- After entering the interactive CLI, the interaction method should be consistent with Claude Code, supporting the following specific Commands:
    - `/init`: Create a `.dogent` directory in the current directory and generate `.dogent/dogent.md` (template containing document type, length, tone, output format, language, other preferences and requirements). The Agent must always follow these constraints when working in this environment;
    - `/init`: Generate `.dogent/dogent.json` in the current directory (with `llm_profile`), `.dogent/dogent.json` refers to the anthropic config in `~/.dogent/claude.json`;
    - `/exit`: Exit the CLI interaction and return to the main shell;

- In the interactive CLI, the Agent needs to be able to display its todo list to users, and reflect main operations and key processes during execution in the CLI.
- When starting in a directory without `.dogent/` or `dogent.json`, do not fail; allow the user to run `/init` later to create them.
- The system prompt stays constant; per-turn user prompts must dynamically include current todo state and `@file` references. Do not seed default todos—todos come from the model via TodoWrite and must be kept in sync with tool results.
- The Tasks panel must update live based on TodoWrite tool results; detect TodoWrite tool outputs in the agent stream and render the changes in CLI UI to user immediately.
- Users can make requests to the Agent through the interactive CLI. Users can use the @ symbol to reference files in the current directory (like Claude Code, with a dropdown selection when users input @)
- Anthropic/Claude credentials and model settings may be managed globally in `~/.dogent/claude.json` as named profiles (e.g., `deepseek`, `glm`). A project’s `.dogent/dogent.json` can reference a profile name via `llm_profile` to populate `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `API_TIMEOUT_MS`, and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`. If no profile is referenced or found, fall back to environment variables.

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

### Development Requirements：

You need to split the development tasks in the form of user stories. Each story should have user value and be a feature that can be accepted end-to-end. They can be arranged according to the dependencies of the stories and from simple to complex. You need to write tests for each story. You need to write the split stories into an md file under docs. Each time the development is completed and the test passes, update it in a timely manner. When the user has new requirements, also update the file in a timely manner.

- Based on the above document writing requirements, you need to write very accurate, professional, and complete system prompts for Claude Agent SDK;
- All prompts configured for the model in the code need to be formed into separate prompt templates and placed in independent files for manual tuning;
- You need to search for Claude Agent SDK development manuals and example codes in `$project_root/claude-agent-sdk` and maximize the capabilities of Claude Agent SDK;
- The entire project should be developed in Python and be able to be independently packaged into an executable program for distribution to others;

Based on the above requirements, please carefully analyze, design, and break down the tasks, then complete them step by step.
Finally, package and deploy the program, complete local testing, and output usage documentation for my testing.

## Release 0.2

- Synchronize the version in pyproject.toml with the __version__ variable in dogent/__init__.py, so that the version number only needs to be maintained in one place. This ensures the version number displayed when running dogent -v after installation matches the version of the published package.

- When installing dogent, if the .dogent directory does not exist in the user's home directory, create it automatically, write a default claude.json file into it, and prompt the user to modify this file.

- After entering the dogent interactive command-line interface (CLI), first display a handcrafted character pattern of "dogent" generated with pure ASCII/Unicode art to enhance the visual appeal of the interactive CLI welcome screen.

- Design a structured format that requires dogent to record the key progress of tasks in `.dogent/history.json` each time. This allows dogent to load previous history and progress when launched in the same directory next time, ensuring continuity between subsequent work sessions. Modify the system prompt to inform the dogent agent of this file’s purpose and enable on-demand loading and usage.

- `.dogent/memory.md` is used for temporarily recording information during a single dogent task session. Therefore, the system prompt should instruct the dogent agent to use this file as needed—create it only when required (not every time) and automatically clean it up after use.

- Do not create the images directory by default at startup. This directory serves as the default path for the agent to download images when needed, and users can configure it in .dogent/dogent.json. If no configuration is set, the default path is the images directory in the current working directory. Add a configuration item for the default image download path in the config file created when the user executes the `/init` command.

- When dogent is running in the interactive CLI, allow users to press the Esc key to terminate the current agent task, then input other instructions. (When dogent is interrupted, it must record the progress to `.dogent/history.json` so that previous work progress can be retrieved when resuming.)， How to interrupt claude agent sdk, please refer to the corresponding document and example codes in claude-agent-sdk folder.

- Remove the `/todo` command and its associated code from the interactive CLI.

- When summarizing after a task is completed, place the summary content into the "Session Summary" section, merging it with existing content: display the summary first, followed by task-related metrics such as time elapsed and costs incurred for the current task.
Add an appropriate emoji before the title of each section (e.g., "Session Summary" and "File Reference") to improve visual distinction.

## Release 0.3

The current release focuses on refactoring and fixing minor issues. The overall goal of refactoring is to decouple the core logic of **Agent scheduling** and **interactive CLI** from `dogent`, and separate the configurations dedicated to *document writing*. This will facilitate the reuse of core logic for extending into other proprietary interactive CLI-based Agents in the future. To this end, the following requirements must be met:

- Commands supported by the interactive CLI should **not be hardcoded** to enable easy extension of new commands. This includes:
  1. The command hints displayed in the banner after launching `dogent`;
  2. The prompt messages printed when a command lookup fails.
  A **registration-based extension mechanism** is recommended, where each command is implemented independently and registered separately.
- Templates embedded in the code should be decoupled as standalone modules as much as possible. For example, the template in `ConfigManager._doc_template` should be extracted into an independent, editable template file.
- Optimize the current **system prompt**:
  - Remove hardcoded image paths from the prompt content;
  - Ensure that the role definition and specific requirements in the writing-oriented system prompt align with prompt engineering best practices.
- Optimize the **user prompt** to enable clearer and more explicit instructions for the LLM.
- Improve code readability by adding comprehensive comments and implementing **Clean Code** refactoring, including more logical file and directory restructuring. Specifically:
  - Treat the interactive CLI-based Agent code (unrelated to specific roles) as the core module;
  - Separate role-specific configurations (including extensible CLI commands and various templates) to allow users to extend `dogent`’s core logic into other Agent roles in the future.
- Support multi-line input in prompts using the **Alt/Option + Enter** shortcut for line breaks.
- Ensure graceful exit when users terminate the program with shortcuts like **Ctrl + C**: avoid throwing exceptions, properly clean up resources, display a user-friendly exit message, and terminate normally.
- Ensure interactive CLI system prompts/titles remain in **English UI**, while the LLM output keeps its original language.

The key design principles outlined above shall be added to **AGENTS.md** as binding architectural guidelines for future development iterations.

## Release 0.4

- Extract the configuration file template corresponding to `template` in the `create_config_template` function in `dogent/config.py` into an independent template file, and place it in the `dogent/templates/dogent_default.json` file. This facilitates modifying the default configuration file and decoupling it from the code;

- The files under `dogent/prompts` and `dogent/templates` need to be copied to the corresponding locations under `~/.dogent` during the first installation of dogent (or the first startup). This allows users to adjust and optimize them independently (including optimizing prompts, modifying and adding default configuration items, etc.). After each startup of dogent, the prompts to be loaded or the default configuration files to be created must be based on the corresponding files under `~/.dogent`;

- Since users are allowed to optimize and modify the prompt templates and configuration file templates under `~/.dogent`, the template parameters referenced in the prompt templates (such as `working_dir`, etc.) will be frequently adjusted and changed. Therefore, a set of flexible template injection schemes needs to be designed and implemented. Prompt templates must also be able to reference configuration parameters in the dogent configuration file, ensuring that users do not need to modify the code after changing variable references in the prompt templates. Some template parameters that I currently think need to be injected into prompts include:
  - Current working directory: `{working_dir}`
  - Content in the history file; the full text of the history file can be specified as `{history}`, or only the most recent history records can be referenced as `{history:last}`;
  - All content in the memory file: `{memory}`
  - Latest to-do list: `{todo_list}`
  - Parameters using user prompt: `{user_message}`, `{attachments}`
- Configuration items in the configuration file: such as a specific configuration item in `dogent/dogent.json` (`{config:llm_profile}`), or a custom configuration item added by the user in the configuration file: `{config:user_specified}`
  - You may continue to design other required template parameters for reference in prompt templates. Finally, please structurally organize all these parameters (which users can configure for prompt templates) and their usage into the README file.
  - If a template parameter referenced in a user-modified prompt template does not exist, it defaults to an empty string. However, a warning must be printed to the user when generating the prompt template if any referenced parameter is empty;

Ultimately, users should be able to optimize prompt templates (system prompts or other prompt templates) independently without modifying the code, and reference predefined template parameters in prompt templates—including configuration items configured by the user in `dogent/dogent.json`;

- Modify the relevant code according to the above requirements, including the logic for generating and loading prompt templates, and the processing logic for `/init` endpoint;

## Release 0.5

- Add the `/history` command, allowing users to view the main history in a structured format, as well as the final status of the todo list. It needs to be displayed concisely, structurally, and beautifully.

- Record the latest version of dogent in the `.dogent` directory under the user's home. If, during the first installation or startup after dogent is upgraded, it is found that the configuration in the .dogent directory under home is from a previous version, the latest version of the template and prompt files need to be used to replace the old version.

- When updating the templates and prompts in the .dogent directory under the user's home, the user-configured claude.json should not be replaced. 

- When a user configures a profile in dogent.json in their own working directory, if it references a profile in claude.json under user home `.dognet` folder, but the user has not modified the configuration of the corresponding profile in claude.json (for example, there is a default profile deepseek, but the key is "replace-me"), an alert message also needs to be given to the user, asking them to modify the necessary configuration first.

- The results of Tool using，such as WebFetch or WebSearch tool, need to be displayed clearly (mainly indicating success or failure, and the reason for failure if it's a failure)

- Add the `/help` command to display the usage of dogent, including the basic information and core configuration of dogent including information in first welcome panel (model, api url, commands usage...).

- Add the `/clean` command to clean the history and memory if exist.

## Release 0.6

- Since using the native WebSearch and WebFetch tools always results in failures, I hope to develop two similar tools myself and then register them with Claude Agent ADK. WebSearch needs to be configured with search APIs (such as Google's or Bing's Custom Search API). These configurations are similar to those in claude.json, and I want users to be able to configure them in appropriate configuration files. When dogent is launched for the first time, these files will be generated in the .dogent directory under the user's home directory, allowing users to configure specific API and key information, etc. If users have multiple configurations, they can configure them in the .dogent/dogent.json file of the current project, similar to profile configuration.
- I need to develop a tool similar to WebFetch, register it with the Claude Agent SDK, and use it to download and retrieve content from specified URLs found through WebSearch. It is necessary to filter out meaningless characters and formats from the web pages and return the core content as tool results (for submission to the model). A complete solution design based on this is required to avoid and solve various problems.
- I need WebSearch to be able to search for images, such as searching on Google Image or finding them in web pages. Then WebFetch can download the specified images, place them in a user-specified workspace-relative output directory, and name them. After that, the images can be referenced in the written articles (if it is in markdown format, the normal image reference method should be used). A complete solution design based on this is required to avoid and solve various problems.
- Fallback behavior:
  - If user does not configure `web_profile` (missing/empty) or sets `web_profile` to `"default"`, Dogent should use the default Claude Agent SDK `WebSearch` and `WebFetch`.
  - If user configures a `web_profile` name that does not exist in `~/.dogent/web.json`, Dogent should warn the user at startup and fall back to default `WebSearch` and `WebFetch`.

## Release 0.7.0

- Add a project-only “Lessons” mechanism so Dogent can learn from failures and user corrections over time and avoid repeating the same mistakes.
- Improve `/clean` so users can selectively reset workspace state.

- Storage:
  - Persist lessons in a human-editable file: `.dogent/lessons.md`.
  - Dogent must append new entries safely without corrupting the file; users can edit the file directly at any time.

- Automatic capture with minimal user input:
  - Dogent should mark the Summary/History status clearly when a run fails or is interrupted (so lesson capture can trigger reliably).
  - Failure Summary UX (trigger signal):
    - If the agent run fails and exits the agent loop while there are unfinished todos, the Summary panel must clearly indicate a failed status.
    - Recommended: include status in the panel title (e.g., `❌ Failed` / `⛔ Interrupted` / `✅ Completed`) and include the result/reason in the panel content.
    - When todos exist, the Summary content should also include a concise “Remaining Todos” section listing the unfinished todo items (or a count + top items).
    - This Summary/Status signal is the primary trigger for recording Lessons (more reliable than guessing from free-form text alone).
  - Treat the last run as a capture candidate when the agent finishes with status `error` or `interrupted`:
    - If the user interrupts the task (Esc/Ctrl+C), record history status `interrupted`.
    - Otherwise (agent run fails or ends prematurely), record history status `error`.
  - Do not determine failure by parsing free-form summary text.
  - When a capture candidate is detected, Dogent should “arm” lesson capture for the next user message.
  - On the next user message, Dogent prompts: “Save a lesson from the last failure/interrupt? [Y/n]” and defaults to **Y** (press Enter).
  - If the user accepts, Dogent should use the LLM to draft the lesson (problem → cause → correct approach) using the last failure Summary and the user’s correction message as context, then save it to `.dogent/lessons.md` and proceed with the user’s request (retry).

- Explicit manual recording:
  - Provide `/learn <free text>` to explicitly record a lesson with minimal user input.
  - Dogent should use the LLM to rewrite/structure the user’s free text into a consistent lesson entry and append it to `.dogent/lessons.md`.
  - Provide `/learn on|off` to enable/disable the automatic “Save a lesson?” prompt behavior.
  - Provide `/lessons` to show a concise summary of recent lessons and where to edit them.

- Prompt injection:
  - For each new task, Dogent should include the full content of `.dogent/lessons.md` in the prompt context (no relevance filtering for now).
  - If the file becomes too large, Dogent may truncate with a clear notice to the user (no semantic filtering required).

- `/clean` targets:
  - `/clean` supports cleaning target parameters: `history`, `lesson`, `memory`, or `all`.
  - The CLI provides a dropdown completion list for these target parameters when the user types `/clean `.

## Release 0.8.0

### Document Type Templates (Extensible)

Dogent’s prompt system must support multiple professional document types via an extensible “document template” mechanism.

- Document templates are identified by a **template name** (e.g., `resume`, `research-report`) that encapsulates:
  - A brief introduction to this template, its purposes and scenarios (Used for LLM to match when selecting an appropriate template based on user prompt when initializing a dogent project by `/init` command).
  - Writing requirements (hard constraints)
  - Best practices (process guidance)
  - Output template format (section skeleton the model should fill)
- Dogent ships with a small set of built-in document templates out of the box （`resume`, `research-report`).
- Users can extend document templates without changing Dogent code:
  - Workspace templates: `.dogent/templates/<name>.md`
  - Global templates: `~/.dogent/templates/<name>.md`
  - Built-in templates: packaged under `dogent/templates/doc_templates/<name>.md`
- Template resolution: unprefixed names resolve only in workspace; prefixed names resolve in their specified source.
- `general` is a reserved default value that means no template is selected; it uses `dogent/templates/doc_templates/doc_general.md`.
- Built-in templates remain packaged and are used only as fallback; they are not copied into `~/.dogent`.
  - Workspace templates do not use a prefix; global templates require `global:` and built-in templates require `built-in:` in `/init` and `doc_template`.

### Config and Prompt System Adjustments

- Default templates must be updated:
  - `dogent/templates/dogent_default.md` focuses on project context, writing preferences, and overrides/supplements.
  - Template selection and primary language are configured in `.dogent/dogent.json` and should not be duplicated in `dogent_default.md`.
  - `dogent/templates/dogent_default.md` includes a "Document Context" section to capture the user's prompt details (name, background, audience, goals, scope).
  - `dogent/templates/dogent_default.json` includes default `doc_template` and `primary_language` config keys (default: `general` and `Chinese`).
  - Users can manually modify the dogent.json file in the current project to adjust the document template configuration and primary language.
- Prompts and default templates are loaded directly from the Python package and are no longer copied into `~/.dogent` (no compatibility migration required).
- System prompt (`dogent/prompts/system.md`) must include a dedicated section for:
  - The document template content when a concrete template is selected
  - System prompt always relies on the doc_template configured in dogent.json (If the user has not configured it, or the configuration is "general", then it will use a default document template from an independent template file.)
- Template content is dynamically inserted into the dedicated section of the system prompt (not hardcoded).
- Provide a default document template file (e.g., `dogent/templates/doc_templates/doc_general.md`) to use when `doc_template` is `general` or missing.

### Project Incremental Customization (Overrides/Supplements)

Users must be able to add incremental, project-specific customization and supplementary requirements without forking templates.

- `.dogent/dogent.md` is the canonical place to write:
  - Template overrides (higher-priority constraints)
  - Template supplements (additive requirements/checklists)
  - Other writting requirements
- Prompts must clearly state precedence for writing behavior:
  - Safety/tooling/system rules (system prompt) > user request (current specific requirements) > `.dogent/dogent.md` (project constraints)  > document template (`doc_template` config).

### `/init` Template Picker + LLM Wizard

`/init` must support selecting and generating project writing configuration.

- Merge the functionality of the `/config` command into the init command and remove the `/config` command.
- When the user types `/init ` (space), a dropdown completion list of available document templates must appear.
  - As the user types, the list filters.
  - The list should display workspace templates without a prefix, and global/built-in templates with prefixes (e.g., `resume`, `global:resume`, `built-in:resume`).
- `/init` accepts either:
  - A document template name (exact match), which scaffolds `.dogent/dogent.md` with that template selection and empty override/supplement sections; OR
  - A free-form prompt (non-matching input), which triggers an LLM-powered “init wizard” to generate a complete `.dogent/dogent.md`.
- When a document template name is an exact match, do **not** run the init wizard. Instead, scaffold a minimal `dogent.md` with supplement sections that provide selectable options (e.g., output format, length).
- The init wizard must use a dedicated system prompt (under `dogent/prompts/`) and output a JSON object containing:
  - `doc_template`: the selected template name (or `general`).
  - `dogent_md`: the full Markdown content for `.dogent/dogent.md`.
- The init wizard output must set `doc_template` in JSON; `dogent_md` must not include template selection or primary language fields.
- The init wizard must follow a default dogent.md skeleton stored in an independent template file (e.g., `dogent/templates/dogent_default.md`).
- The init wizard is necessary to generate a suitable dogent.md based on the template selected by the user or the input prompt.
- If the user does not select any template and does not enter any Prompt after `/init`, a default dogent.md will be generated for the user, and the doc_template configuration in the generated dogent.json will be set to general.
- If the user re-executes `/init` to select a template, modify the configuration in `.dogent/dogent.json` accordingly
- The `doc_template` in `.dogent/dogent.json` is the single source of truth for template selection; `.dogent/dogent.md` is user-authored requirements and does not override `doc_template`.
- Safety: `/init` must not silently overwrite an existing `.dogent/dogent.md`; it should ask for confirmation before overwriting.
  - When re-running `/init`, always update `.dogent/dogent.json`, and ask whether to overwrite `.dogent/dogent.md`.

### Optimization of prompt templates

- The system prompt should not contain specific requirements for writing particular articles, but it should include common requirements that are irrelevant to specific article types. For example, available tools, general writing requirements, and requirements for long article writing (such as plan, outline confirm, splitting, writing step by step, indexing, identifying and associating dependent articles as context, maintaining a consistent tone and style throughout the article, recording key information and cross-file coherent content in memory.md, unified polishing, verification of factual information, etc.). Based on the new design, you need to reconstruct the system prompt, ensuring it has a reasonable structure, professional content, and meets the usage scenarios and needs of Dogent.

## Release 0.9.0

- When an Agent exits the loop before completing the todo, there are currently two scenarios observed: one is that the task has an error, and the other is that the Agent has a question to ask for clarification. It is necessary to determine that if it is the second scenario, it should not be considered a task failure. The CLI's Panel should not use `❌ Failed`; instead, it should use a different title to remind the user to answer the question. A solution needs to be researched to determine the reason why the agent exits the loop midway (failure or seeking clarification).
- For some tasks that take too long, most of them are tasks where the agent needs to interact with the LLM and wait for results, such as when the user enters a prompt, executes `/init` and `/learn`, or when lesson generation is in progress in the background, the user usually needs to wait. It is recommended that a progress bar or timer be provided at this time to help remind the user that the current background task is being executed, rather than appearing to be stuck.
- Currently, the subcommands `/history` and `/lessions` are both display-type commands. Can these be merged into a single subcommand, and then use different parameter options (similar to using a drop-down list in the CLI) to indicate what is being displayed? This would reduce the number of subcommands.
- Support the ability to execute ordinary shell commands like in other interactive CLIs. Generally, commands starting with `!` will be interpreted as a shell command, which the interactive CLI will help execute, and then the result will be echoed (a dedicated panel can be used for this).

## Release 0.9.1

- When the user's input prompt contains multiple lines, pressing the up and down keys should first move the cursor between the user's input lines. Only when the user continues to press up from the first line should it jump to the previous historical commands, or when continuing to press down from the last line should it jump to the subsequent historical commands.
- The implementation of the function in the `DocumentTemplateManager` class that reads document templates to generate template summaries: the current logic in `def _extract_intro(self, content: str) -> str` is to obtain the content of the `## Introduction` section. However, some templates may not have a `## Introduction` section. In such cases, it can be modified to read the first 5 lines of the document to enhance robustness;
- When the user is typing, pressing Alt+Backspace clears the user input before the cursor (only the current line before the cursor when multi-line).

## Release 0.9.2

- Add an `/archive` subcommand that accepts a parameter (`history|lessons|all`, default is `all`) to archive relevant record files in the `.dogent` directory of the current working directory. The archived files will be stored in the `.dogent/archives` directory under the current working directory, named in the format `history_YYYYMMDD_HHMMSS.json`. After archiving, the corresponding history or lessons file will be cleared to facilitate new work for the user.
- Bug fix: When the user inputs a long Chinese content that causes line wrapping due to terminal width limitations, pressing the up and down keys for cursor movement results in either the cursor not moving or the cursor position becoming disordered. This issue needs to be fixed to ensure that the cursor moves correctly when inputting long Chinese content.


## Release 0.9.3

- I hope that dogent can handle pdf / docx / xlsx files. This includes correctly reading the content in these types of files if the user references them using `@` (for now, pdf files can only support text-based PDFs; for other unsupported pdf file types, after detection and identification, it is necessary to return a failure to the user and clearly inform them of the reason).
- I hope that if the user specifies the output type of the document as a pdf or docx file, then dogent can correctly generate pdf and docx files.
- The document(PDF/DOCX) reading and generation can be referred to `dev/spikes/doc_convert.md` and examples in `claude-agent/sdk/skills/skills/pdf/*`、`claude-agent/sdk/skills/skills/docx/*` and `claude-agent/sdk/skills/skills/xlsx/*`, You need to synthesize the characteristics of dogent based on these examples and provide me with the best design solution choice.
- when I told agent to "convert a docx file to markdown file and extract all images in specified path", the agent used the `pandoc` app execute the task (`pandoc "src.docx" -t markdown -o "dst.md" --extract-media=./images`)，This depends on the user's machine app install state. I hope to build the file format conversion capability into dogent. Therefore, please check if this can be done using Python itself, such as with the help of pypandoc. Can we create an mcp specifically for converting between docx, pdf, and markdown?

## Release 0.9.4

- I hope that dogent cann handle off images or video files. if the user references images or vidios using `@`, dogent can post the image/video  to a configured vision llm to get the content details and add the content in the user prompt so that the writting LLM can understand the detailed content in the images/videos. 
- You can refer `dogent/dev/spikes/GLM-4V-Vision-Model-Research-Report.md`，user can select different vision model by dogent.json(maybe the vision profiles in ~/.dogent)

## Release 0.9.5

- Monitor the tool usage of the Agent. If it is found that the agent accesses files outside the working path (whether reading or writing) or deletes files within the working path, it is necessary to confirm with the user first (the original task of the claude agent client should not be interrupted). If the user agrees, continue the task; otherwise, exit the task (shows task abort and reason to user).

## Release 0.9.8

- Optimize the interaction experience when the Agent asks users questions and requests clarification: have an independent question-and-answer interface that displays the total number of questions and the progress; ask questions one by one, and after the user answers, proceed to the next question; 
- for each question, provide users with answer options, allowing them to select by moving the cursor or add free answers. The cursor is by default on the most recommended answer. 
- To achieve this goal, it may be necessary to modify the system prompt so that when the LLM needs the user to answer questions, it organizes the required information such as questions and suggested options in a structured format (e.g., json). Then, the codes extracts this structured content, enters the question-and-answer interactive interface, collects the user's answers, splices all the questions and answers together, and returns them to the LLM for subsequent processing.
- You need to consider whether, in the process of the Agent asking follow-up questions and the user answering questions, in principle, the current loop of the agent client should not exit, otherwise the LLM context will be lost?
- In addition, it is necessary to consider that if the user does not answer for a long time (timeout), the task is regarded as aborted, and the current agent loop is ended.
- In the question-and-answer interaction, the user also has the right to exit and interrupt the task (consider the interaction design, whether to use the same way as the esc interrupt, or need to use other ways to avoid conflicts with the normal exit of the agent loop?).
- For this requirement, you need to have an aesthetically pleasing and user-friendly interaction scheme design;

---

## Release 0.9.9

- All scenarios that require user selection and confirmation (overwrite dogent.md after /init, save lesson, authorize file access/deletion, start writing now, initialize now) must use the same CLI UI as clarification: options selected via up/down with Enter to confirm and Esc to cancel. Non-interactive fallback keeps y/n input. When allowing the user to make a selection, if the agent client itself has not ended, the current agent loop should not be interrupted. The Esc listener should be paused/stopped while a selection prompt is open and restarted after it exits.
- Clarification questions: prefer multiple-choice options whenever reasonable (but do not force options if not appropriate). When answering, Esc skips the current question and the answer is recorded as `user chose not to answer this question`; Ctrl+C cancels the entire clarification flow and aborts the current task. For "Other (free-form answer)", immediately prompt the user to enter the free-form answer after selection using `Other (free-form answer): `. If clarification JSON appears in a thinking block, it should still be parsed and used to enter the QA UI, and the thinking panel should be suppressed for that block.
- Add `debug: false` to dogent.json. When enabled, save each finalized prompt and raw streaming content returned by the LLM in chronological order to `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` in JSONL format. Each entry includes a role field (`system`, `user`, `assistant`, `tool`) and the log captures all LLM calls (main agent, init wizard, lesson drafter). If the system prompt has not changed, record it only once per session.
- Update /init prompt flow: no changes to init_wizard system prompt. After initialization finishes (including the overwrite prompt), ask whether to start writing directly. If Yes, construct the prompt: `The user has initialized the current dogent project, and the user's initialization prompt is "<prompt>". Please continue to fulfill the user's needs.` and start the writing agent. If No or Esc, exit the init flow and return to the CLI.
- New requirement: when a user makes a request and `.dogent/dogent.json` does not exist, first ask whether to initialize. If Yes, run the same /init prompt wizard flow using the user's request as the init prompt, then ask whether to start writing (same as above). If No, proceed with the current default processing. If Esc, cancel and return to the CLI. The default selection for this initialize prompt should be Yes.

---

## Release 0.9.10

- Improve CLI prompt and free-form clarification UX: keep single-line input by default, but provide a dedicated multiline Markdown editor when the user presses Ctrl+E (for main prompt input and free-form answers). Selecting "Other (free-form answer)" in clarification should open the editor directly. The editor must support multiline editing with Enter inserting new lines, common shortcuts, and Markdown-friendly writing. Provide a Markdown preview toggle inside the editor, and allow Ctrl+Enter to submit and Esc to cancel and return to single-line input. Pause the Esc listener while the editor is open.

- The markdown editor must combine editing with lightweight real-time rendering in a single view. It should also offer a full preview toggle (Ctrl+P) that is read-only and returns to editing. The UI must be beautiful with a dark theme. Use Ctrl+Enter to submit (fallback like Ctrl+J shown in the footer), and Ctrl+Q to return (Esc should no longer exit the editor). The editor should provide common GUI-like shortcuts (select word/line, skip words, jump to line start/end) and list fallback shortcuts in the footer when terminal limitations apply. Provide prominent labeled actions in the footer. On return, if the buffer is dirty, prompt to discard, submit, or save to file; saving prompts for a file path (relative or absolute) and confirms overwrite if the file exists. Only save-on-return (no explicit save key).

## Release 0.9.11

- The setting of debug mode should not appear in dogent.json default (It is a background function)
- After the debug mode is turned on, the output log will no longer use the jsonl format, but will become a structured md file. The structure and content organization should be easy for humans to read. In addition, the log should be comprehensive. All kinds of exceptions should also be recorded, including the original exception content and the location where the code occurred. The entire log is organized in the form of an event order.
- When an LLM provides an article outline for the user to modify and confirm during the writing process, the content needs to be displayed in the markdown editor view configured by the current dogent, allowing the user to make modifications (without exiting the agent loop at this time to prevent loss of the LLM context). If the user chooses to save to a file or submit, it should be submitted to the LLM to continue completing the task; if the user chooses to abandon, the current task should be interrupted. You may need to modify the system prompt to recognize such scenarios and also modify the corresponding code.
- should support vi editor mode. The current markdown editor mode is considered as dogent editor mode (default setting). User can choose the editor mode (`default|vi`) in dogent.json; For implementation details of the editor `vi`, refer to some research schemes in dev/spikes/cli-markdown-vi.md (you need to conduct an overall design that also satisfy all other requirements of dogent， such as: if the user chooses to save to a file or submit, it should be submitted to the LLM to continue completing the task; if the user chooses to abandon, when user in question answering that represent user omit the question..., all agent behaviors follow the editor should be as same as dogent default markdown editor)
- If the user submits content edited in the editor to the LLM, wrap that content in a Markdown code block (language tag optional) so it does not affect surrounding formatting. In CLI interactive display, the editor-submitted content should also be shown in its own Markdown code block, visually separated from surrounding text.
- Add a subcommand `/edit`. After the user inputs it, the parameter is a file in the current directory; the user can manually enter the relative path of the file, or a drop-down list will pop up for the user to select after the user enters a space. After pressing Enter, the corresponding file will be opened with the currently configured editor, allowing the user to start editing. For the time being, only plain text formats (markdown, txt...) are supported for file types. Unsuppported formats or non-existent paths need to be clearly reported as errors;

---


## Release 0.9.12

- Bugfix: The current permission management is ineffective. When the agent accesses files outside the workspace and deletes files within the workspace (those not in the whitelist), there is no option to prompt the user for confirmation; instead, the operations are performed directly. The reason is when you set `can_use_tool` in `ClaudeAgentOptions` then should not allow the tools in `allowed_tools`. 
- If the agent needs to update the existing `.dogent/dogent.md` and `.dogent/dogent.json` during the execution of a task, it must request user authorization each time and can only proceed with the update after obtaining the user's consent; otherwise, it must not update the file.
- To reiterate the permission management requirements: 1) Accessing any files outside the workspace (reading/writing) requires user authorization; 2) Deleting files within the workspace requires user authorization (except for files on the whitelist, such as `.dogent/memory.md`); 3) Modifying or overwriting an existing `.dogent/dogent.md` or `.dogent/dogent.json` requires user authorization; During the process of waiting for user authorization, the agent client's loop must not exit. If the user authorizes the file operation, continue to complete subsequent tasks; if the user does not agree, the current task is considered abandoned (Abort).
- While waiting for user authorization, the user can switch between yes/no by selecting up and down, with the default option being yes. Note that at this time, monitor the user's keyboard and mouse operations, and do not leak the original characters to the CLI UI. Refer to the information described in the dev/spikes/cli-meaningless-char.md file.
- If the user does not authorize access to the corresponding file, the task will be terminated. A clear `Interrupted` Panel needs to be shown to the user, informing them of the reason and status.

---

## Release 0.9.13

Here are suggestions for refactoring the code of dogent：
- Decouple and reasonably split all oversized files, such as `dogent/cli.py` is too large and needs to be split and decoupled (Perhaps decouple the two types of editor and preview mode from cli...)
- All complex multi-line prompts and templates in the code should be separated into well-named files instead of being hard-coded in the code， such as below：
```py
    async def _run_llm(self, user_prompt: str) -> str:
        system_prompt = (
            "You write concise, reusable engineering lessons in Markdown.\n"
            "Return ONLY Markdown (no code fences). Start with a '## ' heading.\n"
            "Then include sections: ### Problem, ### Cause, ### Correct Approach.\n"
            "The title must be a specific actionable rule derived from the user correction.\n"
            "Be brief: prefer bullets; avoid long prose.\n"
            "The Correct Approach MUST include the user's correction verbatim as a short quote block.\n"
        )
```
- There are quite a lot of files under "dogent" now. According to functional modules and reusability, different code files should be placed in appropriate subdirectories.
- move all json schema files into `dogent/schema`, such as dogent_schema.json
- rename the `dogent/templates` to `dogent/resources`
- move the `dogent/resources/doc_templates` to `dogent/templates` that is under dogent folder directly and rename from doc_templates to templates.
- Write the new software architecture and main design into `docs/dogent_design.md`, and use mermaid to complete the main design diagrams such as logical architecture and physical architecture;


---

## Release 0.9.14

- Issue: when convert markdown file to docx file, all the images referenced in markdown should be shown in docx. The images referenced in markdown use syntax such as : `![](../images/1.png)` or `<div align="center"><img src="../images/2.png" width="70%"></div>`
- Simplify the content in the startup dogent panel, retaining only the necessary introductions and important reminders. Supplement the help panel (Markdown-rendered in the normal CLI panel) with as comprehensive a functional introduction as possible.
- Refactor `docs/usage.md` to introduce all functions of dogent in a complete end-to-end manner, step by step, from install to usage with examples;

---

## Release 0.9.15

- BugFix：I encountered an error when using dogent to convert an xlsx file to markdown. It seems that the mcp tool did not automatically extract the names of the sheets. Please modify the code so that when the user does not specify the sheet names, the code can automatically extract them, and can extract all the sheets from the xlsx file and convert them into a single markdown file. The names of different sheets can be used as H2 Titles in the markdown file; the H1 title of the markdown file should be the prefix of the xlsx file name.
- python lib termios doesn't support windows platform, I  extracted the terminal.py to split the codes to different platform. Please check and implement all necessary codes for support Windows Platform
- There are some PDF file conversion and generation tools in the code. They will check if the user's computer has them when needed, and then download them in real-time. However, to prevent issues with the user's poor network connection, I hope to add a packaging mode, namely the full mode (which internally carries the tools that users need to download and install during runtime). Then, I can specify the packaging and release mode when publishing.

---

## Release 0.9.16

- Dogent should supports loading the user configured Claude's commands, subagents, and skills from `.claude` under the workspace;
    - Claude Skills are supported by dogent (in the `can_use_tool` callback)，Just check the code to confirm.
    - Claude commands and subagents are not supported by dogent, should register the user configured claude's slash command to dogent commands with a `claude:` prefix.
- Dogent supports loading Claude's plugins;
- For how to support claude's plugins and  commands, subagents, and skills, should according the tutorials under `claude-agent-sdk/tutorials`, In particular, the following documents：`slash_commands_in_the_SDK.md`, `subagents_in_the_SDK.md`, `plugins_in_the_SDK.md`, Other tutorial files can also be consulted if needed.

---

## Release 0.9.17

- The various profiles currently supported by Dogent: llm_profile, web_profile..., users need to manually configure them in the configuration file `.dogent/dogent.json`, and often do not know the names of the profiles that can be filled in when configuring; I need a command-based way to change profiles, allowing users to choose from the available range; I hope that the configuration method and UI behavior of this dogent's commands are consistent with other commands, with easy-to-understand names and a user-friendly and beautiful UI;

- To make it easier to locate code problems with Dogent, I hope that Dogent's code supports logging capabilities, which can be used to record code actions or exceptions. The `debug` configuration in the current configuration file `.dogent/dogent.json` can be reused. If it is not configured (or is `null`), it means logging is turned off; otherwise, it indicates the enabled log types. For example, the currently supported type that records the interaction process between users and agents in the session can be called `info`(or other suitable name you recommended) level. Other log types can be classified according to log levels; after adding this logging function, it is necessary to insert logging in all places where exceptions and errors occur in the current dogent code. When the log configuration is turned on, these should be recorded. Logs are uniformly saved in `.dogent/logs` in the current working directory;

- The mcp__dogent__read_document tool currently does not support offsets. When it is necessary to read long documents, it is impossible to read them in multiple segments by the specified offset and length. Please help me modify the implementation of mcp__dogent__read_document and re-register its usage with the agent.

---

## Release 0.9.18

- Supports a fully automatic execution mode that does not require entering the dogent interactive interface; such as `dogent -p "user prompt"`, no authorization required, one-click execution to the end, equivalent to a pure shell command, indicating success or failure to the user through the return value (`0` indicates success)
- It is necessary to support the design of an authorization configuration method in dogent.json, so that when users are in non-interactive and interactive modes, they will no longer be prompted for authorization for operations that have already been authorized in dogent.json. If the user is in the interactive mode, when the agent requests authorization, in addition to the yes/no options, there should also be a "yes (record, authorize for all subsequent times)" option. If the user selects this option, it will be recorded in the configuration.
- Simplify the authorization request for dogent.json. If the user modifies the configuration by executing commands such as init, profile, debug, lesson..., there is no need to ask the user for permission to modify dogent.json, and the modification can be done directly.
- When a user executes via `dogent -p "user prompt"`, if file operation authorization is required, or if the agent needs clarification, resulting in incomplete execution, an error should be returned. The error codes need to be designed to be distinguishable, and the error reason should be output simultaneously. For successful execution, a simple output should also be provided to indicate that the task is completed.
- Support specifying a parameter in the `dogent -p "user prompt"` mode, which can by default agree to all file authorizations, skip all question clarifications (all questions are equivalent to being ignored by the user), and try to make the agent complete the process with one click.

---

## Release 0.9.19

- Add the image generation capability, refer to this document：`dev/spikes/image_generate.md`, implement and register an image generation capability tool for the agent, and note that the requirements for image generation should be made into various parameters of the tool.
- Add a new profile config for image generation (as same as the vision_profile), user should config the api-key;
- User could config the profile of image generation through `/profile` command;

---

## Release 0.9.20

When I use dogent in a new environment, when dogent uses the `mcp__dogent__export_document` tool, the CLI enters a very long waiting state. I guess it might be because the new environment lacks some related dependency libraries and software, and dogent is downloading them? Please help me check the external dependencies here. I hope to optimize the implementation related to this: when dogent executes the `mcp__dogent__export_document` tool (or other mcp tools that have the ENV depencencies), it first checks the relevant dependencies. If they are not installed in the corresponding OS, it needs to ask the user whether to assist in downloading and installing by dogent now or let the user install manually. If the user chooses to install automatically now, a friendly progress bar needs to be displayed for each download and installation process. If the user chooses to install by themselves, prompt the user with the installation method and interrupt the current task.

---

## Release 0.9.21

- When entering dogent for the first time in a folder, in addition to creating `dogent/history.json` by default, `dogent/dogent.json` will also be created;
- add the `poe-claude` below to the `llm_profiles` in the template file for default configuration file `~/.dogent/dogent.json`:

```json
    "poe-claude": {
      "ANTHROPIC_BASE_URL": "https://api.poe.com",
      "ANTHROPIC_AUTH_TOKEN": "replace-me",
      "ANTHROPIC_MODEL": "Opus",
      "ANTHROPIC_SMALL_FAST_MODEL": "Sonnet",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
```
