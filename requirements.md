我需要你帮我使用 Claude Agent SDK 开发一个可以进行专业长文撰写的基于 CLI 可交互的 AI Agent。
具体要求如下：

- 可以独立打包，让用户安装，用户安装后可以使用命令行命令 `doc` 在对应的目录下进入可交互式 CLI，Agent 会将当前目录作为工作目录（可以访问该目录下所有文件，进行读写）
- Claude Agent SDK 可以从一下环境变量中读取配置，用于进行模型 API 访问以及参数配置：

```
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="xxx"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

- 进入交互式 CLI 之后的交互方式和 Claude Code 保持一直，支持如下具体的 Command：
    - `/init`: 在本目录下创建 `.doc_guild.md` 文件，默认生成一个模版，包含文档的类型、长度、语气、输出格式、语言、其它倾向和要求等全局配置。需要 Agent 在本工作环境中工作的时候一直遵从该约束；
    - `/config`: 帮助用户在当前目录下生成一个配置文件，加入到 .gitignore 中，其中用户可以自定义上面从环境变量中读取的配置。如果 Agent 当前的工作目录下有配置文件，则优先读取该配置文件中的配置，否则再读环境变量；
    - `/exit`: 退出该 CLI 交互，返回主 shell；

- 在交互式 CLI 中，Agent 需要能够把自己的 todo list 显示给用户，主要的工具操作和关键过程要能回显在 CLI 中。
- 用户基于交互式 CLI 可以给 Agent 提出要求，用户可以使用 @ 符号引用本目录下的文件（和 claude code 一样，需要当用户输入 @ 的时候通过下拉让用户选择）
- 允许用户像 Claude Code 一样在当前目录的 .claude 目录下创建 agents、commands 、skills，包括mcp 等工具，Agent进入的时候要能和 Claude Code 一样识别和使用这些配置；
- Agent 在工作目录下默认可以访问 shell 工具，访问网络，读写文件，加载和使用用户配置 Skills、MCP 工具等，这样要配置给 Claude Agent SDK;

- 文档撰写的要求：
    - Agent 要能够遵循用户的要求以及 `.doc_guild.md` 进行文档撰写；
    - Agent 要能对文档撰写工作进行规划，形成 todo list，然后逐步执行；
    - 对于长的专业文档的撰写，Agent 可以将其拆分成小节，逐步完成；
    - Agent 要能上网搜索相关资料，做专业的研究，用于文章撰写；
    - Agent 需要能够根据需要下载对应的在线图片（放到工作目录下的 `./images`目录下），插入文章，用于丰富内容；
    - Agent 需要能够对文章进行校验，要把校验任务规划到 todo list 中，保证文章的准确性，不要有事实错误或者前后不一致的地方；
    - Agent 要能最后统一对文章进行润色，保证全文用语逻辑连贯，语气统一，结构合理
    - Agent 要能从文章中引用在线资料和信息的地方进行准确标识引用，所有引用的在线文章链接放到文章最后；
    - 文章默认以 Markdown 输出，使用中文；必要的时候可以在 Markdown 中进行 DSL（mermaid）绘图，插入代码片段，插入下载的图片；
    - 文档撰写和校验的过程中，Agent 可以把一些临时想法或者关键要点记录到 `.memory.md`  中，用完后可以删掉；

- 基于上面的文档撰写要求，你要写出非常准确、专业和完整的系统提示词给到 Claude Agent SDK；


---
基于上面的要求，请你仔细分析、设计、并拆分任务，然后逐步的完成。过程中可以查询 Claude Agent SDK 的在线文档。
最后将程序打包部署后再本地完成测试，并输出使用文档，供我进行测试。