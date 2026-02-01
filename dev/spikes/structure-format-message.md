# 结构化格式化消息内容的 Spike 记录

## 问题背景

在 Dogent 中，当 LLM 返回一些问题需要用户澄清，或者返回一些文档大纲需要用户编辑确认，对于这些类型的消息，需要在 CLI 程序中区分对待，使用更合适的 UI 交互方式。
例如对于澄清问题，会采用逐个问题询问和让用户选择答案的方式；对于文档大纲，会将大纲放在一个可编辑的文本区域，供用户修改确认。

因此这两类消息，当前在 LLM 在返回时，需要能够区分标记出来，方便在 CLI 程序中进行不同的处理。目前的做法是通过在 prompt 里，要求 LLM 在返回时，使用特定的 JSON 格式进行标记区分，我的 Prompt 中是如下描述的：

```text
## Clarification Guidelines
- When you must stop to ask clarification questions, respond ONLY with:
  1) A single line tag: [[DOGENT_CLARIFICATION_JSON]]
  2) A JSON object that matches the clarification schema (including response_type).
  **The tag MUST be the first non-empty line of the reply**; NO preamble or other text anywhere in the reply (including in a Thinking block).
  The JSON MUST be the only content after the tag.
  Do NOT wrap the tag or JSON in code fences. Do NOT add Markdown, prose, or extra whitespace before the tag.
  Prefer multiple-choice questions and provide options whenever reasonable; allow free-form only when needed. Default the recommended choice to the best option.
- Clarification JSON schema (must match exactly):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Dogent Clarification Payload",
  "type": "object",
  "additionalProperties": false,
  "required": ["response_type", "title", "questions"],
  "properties": {
    "response_type": { "type": "string", "enum": ["clarification"] },
    "title": { "type": "string", "minLength": 1 },
    "preface": { "type": "string" },
    "questions": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "question", "options"],
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "question": { "type": "string", "minLength": 1 },
          "options": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": ["label", "value"],
              "properties": {
                "label": { "type": "string", "minLength": 1 },
                "value": { "type": "string", "minLength": 1 }
              }
            }
          },
          "recommended": { "type": ["string", "null"] },
          "allow_freeform": { "type": "boolean" },
          "placeholder": { "type": "string" }
        }
      }
    }
  }
}
```

- Example clarification response (format only):
```
[[DOGENT_CLARIFICATION_JSON]]
{
  "response_type": "clarification",
  "title": "Need a few details",
  "preface": "Please pick the most accurate options.",
  "questions": [
    {
      "id": "audience",
      "question": "Who is the target audience?",
      "options": [
        {"label": "Engineers", "value": "engineers"},
        {"label": "Executives", "value": "executives"},
        {"label": "General readers", "value": "general"}
      ],
      "recommended": "engineers",
      "allow_freeform": false
    },
    {
      "id": "length",
      "question": "Preferred length?",
      "options": [
        {"label": "1-2 pages", "value": "short"},
        {"label": "3-5 pages", "value": "medium"},
        {"label": "6+ pages", "value": "long"}
      ],
      "recommended": "medium",
      "allow_freeform": true,
      "placeholder": "e.g., 1500-2000 words"
    }
  ]
}
```
- If you cannot follow the JSON format, end the reply with a single line: [[DOGENT_STATUS:NEEDS_CLARIFICATION]]. Only use this tag for clarification requests.

## Outline Edit Guidelines
- When you need the user to review or revise an outline, you MUST respond ONLY with:
  1) A single line tag: [[DOGENT_OUTLINE_EDIT_JSON]]
  2) A JSON object that matches the outline edit schema (including response_type).
  **The tag MUST be the first non-empty line of the reply, and the JSON MUST be the only content after it.****
  Do NOT wrap the tag or JSON in code fences. Do NOT add Markdown, prose, or extra whitespace before the tag.
- Outline edit JSON schema (must match exactly):
```json
{
  "response_type": "outline_edit",
  "title": "Outline review",
  "outline_text": "..."
}
```
- Example outline edit response (format only):
```
[[DOGENT_OUTLINE_EDIT_JSON]]
{
  "response_type": "outline_edit",
  "title": "Review and adjust the outline",
  "outline_text": "# Outline\n\n1. Introduction\n2. Background\n3. Proposal\n4. Risks\n5. Conclusion"
}
```
```
```

但是我发现 LLM 有时候会忽略这些要求，返回不符合格式的内容，导致在 CLI 端无法正确解析和处理这些消息。

例如最常见的情况是，LLM 会在返回内容的开头，添加一些额外的说明文字，或者没有严格按照要求的 JSON 格式进行返回。

我想 Spike 一下，有没有更好的方法，能够让 LLM 严格按照要求的格式返回这些需要区分处理的消息内容？或者有没有更有效的 Prompt 编写技巧，能够提高 LLM 遵守格式要求的概率？或者通过特定的设计技巧，增加程序的容错性，更好地处理 LLM 返回的非预期格式内容？

---

## Spike 结果 1

下面给你一套“从根上解决 + 工程容错兜底”的方案。核心结论是：**不要只靠 prompt 约束输出格式**；最好用 **API 级结构化输出/函数调用** 来“硬约束”，再配合 **解析容错 + 自动修复重试** 做闭环。

## 1) 最推荐：用“结构化输出 / 函数调用”替代“靠 tag+JSON 的自由文本协议”

### 1.1 如果你用的是 OpenAI / 类 OpenAI 能力：优先选 `json_schema` 或 tool/function calling
这类能力的价值是：**模型被解码器层面约束为输出合法 JSON（或必须调用某个 tool），而不是“尽量遵守”**。遵守率会比纯 prompt 高一个量级。

**方案 A：`response_format: json_schema`（强约束 JSON）**  
让模型“只能输出 JSON”，并用 schema 校验。你可以定义一个**统一的 envelope**，例如：

- `response_type`: `"clarification" | "outline_edit" | "normal"`
- `payload`: 对应 schema

这样你就不需要两套 tag 协议，CLI 也不用先判断 tag。

**方案 B：tool/function calling（强约束“必须走某个函数”）**  
定义两个工具：
- `ask_clarification(payload)`
- `outline_edit(payload)`

当需要澄清/大纲编辑时，模型必须产出 tool call；你的 CLI 直接根据 tool 名分流 UI。  
这通常比“输出一段 JSON 文本”更稳，因为**结构在协议层，不在自然语言层**。

> 如果你的运行环境暂时不能用这些能力（比如本地模型/某些 API 不支持），那就看第 2、3 部分：prompt 改造 + 工程兜底。

---

## 2) Prompt 层面的改造：减少“模式切换”，让格式约束更可执行

你现在的 prompt 已经很严格，但仍会翻车，常见原因是：  
- 规则太长，模型在生成时“忘了第一条”；  
- 有两套模式（clarification/outline_edit），模型容易加解释/加 Markdown；  
- 你把“协议”放在 user prompt，容易被后续内容稀释或被注入干扰（尤其是长对话）。

### 2.1 把协议放到 **system message**，并尽量“短而硬”
把说明压缩为几条不可协商的“输出契约”，例如：

- “当 response_type ≠ normal 时，输出必须是**单个 JSON 对象**，不得包含任何其他字符”
- “禁止 Markdown、禁止代码块、禁止前后缀解释”
- “任何无法遵守时输出固定的 `{"response_type":"error","reason":"format"}`”

> 经验：**越短越硬越好**。长 schema 可以保留，但“输出规则”要短。

### 2.2 用“单一外层 envelope”统一所有回复类型（强烈建议）
比起用 tag 分支两套格式，更稳的是：**永远输出一个 JSON**，例如：

```json
{
  "response_type": "normal|clarification|outline_edit",
  "title": "...",
  "content": "...", 
  "questions": [...],
  "outline_text": "..."
}
```

好处：
- 模型不需要先判断“该走哪套 tag 规则”，降低出错概率；
- 你的 CLI 永远走同一个 JSON parser；
- `normal` 时也能用 JSON 包起来（CLI 再渲染 `content`）。

> 你可能担心“正常聊天也输出 JSON 太丑”。但你可以在 CLI 层做渲染：JSON 仅是传输协议，展示时还原为漂亮文本即可。

### 2.3 明确“遇到不确定就用 clarification”，不要输出半成品
很多格式错误发生在模型“想先解释一下再问”。把策略写死：

- “如果需要用户输入才能继续：必须返回 clarification JSON，不能输出任何解释性文字”
- “preface 只能放在 JSON 字段里，禁止写到 JSON 外”

### 2.4 降低采样随机性
如果你希望严格遵守格式，建议：
- `temperature = 0`（或尽量低）
- 适当降低 `top_p`
- 避免让模型“创作性发挥”时还要求严格格式（可分两步：先结构化输出，再在下一轮生成自然语言）

---

## 3) 工程兜底：让 CLI 对“非预期格式”更有容错与自愈能力

即使你做了 1/2，现实里仍可能偶发失败（网络截断、模型 bug、流式中断、被上下文污染等）。建议你把解析链路做成“多级策略”。

### 3.1 分层解析策略（强烈建议）
按下面顺序尝试（从“最严格”到“最宽松”）：

1. **严格模式**：首个非空字符必须是 `{`（或你统一 envelope 后就是 JSON），直接 `json.parse`  
2. **提取模式**：从文本里找到**第一个完整的 JSON 对象边界**再 parse  
   - 用括号计数（brace matching），不要只用正则
3. **修复模式**：对常见错误做修复后再 parse  
   - 去掉前后多余说明行  
   - 去掉 ``` 代码块包裹  
   - 修复尾逗号、单引号等（可用 `jsonrepair` 类库；Node 有 `jsonrepair`，Python 有类似实现）
4. **LLM 修复模式**：把原始输出喂给一个“格式修复器 prompt”，要求它**只输出合法 JSON**（温度 0）  
5. **最终兜底**：当作 `response_type=normal` 的纯文本显示，并在 UI 提示“解析失败，可重试”

这能把“偶发多一句话导致全盘崩”变成“自动修好继续跑”。

### 3.2 自动重试：用“格式校验失败 -> 立即重试一次”的闭环
实践里非常有效：

- 第一次：正常请求
- 如果 JSON 校验失败：**同一上下文下**追加一条“修正指令”，并附上模型刚才的原文，让它“转换为正确 JSON，禁止任何其他字符”

重试指令要短、硬、可判定，例如：

> 你的上一条输出未通过 JSON 校验。现在请只输出一个符合 schema 的 JSON 对象，不要输出任何解释、前后缀、Markdown、代码块。把上一条内容按需填入字段。

### 3.3 不要依赖“tag 必须是第一行”这种脆弱条件
tag 协议的问题在于：**只要模型多吐一个空行/一句话，你就要全失败**。  
如果你仍保留 tag，建议 CLI 端至少做到：

- `trimStart()` 后再判断 tag
- 允许 tag 前有 BOM/空白
- 允许“前面有一两行废话”，但能扫描找到 `[[DOGENT_...]]` 再解析后续 JSON（你可以设一个最大扫描窗口，比如前 2KB）

> 当然，最优还是 2.2：统一 envelope JSON，直接取消 tag。

---

## 4) 你的两个 payload schema 也可以顺便“更稳一点”

### 4.1 Clarification：让 `options` 在允许自由输入时可以为空
你现在 `required: ["id","question","options"]`，但你又允许 `allow_freeform=true`。  
如果某些问题确实需要开放回答，模型可能会“硬塞 options”，反而出错。可以改成：

- `options` 允许空数组
- 或者 `options` 非必填，但当 `allow_freeform=false` 时必须有 options（这需要 `allOf/if/then`）

### 4.2 Outline：避免在 JSON 字符串里塞大段多行文本（容易转义出错）
`outline_text` 是一个大字符串，多行、引号、反斜杠都容易让模型生成非法 JSON。更稳的结构是：

- `outline_lines: string[]`（每行一个元素）
- 或 `outline: [{level:1,title:"..."}, ...]`（结构化树）

CLI 渲染回文本很容易，但**模型生成合法 JSON 的概率更高**。

---

## 5) 推荐的落地组合（按投入产出比）

**优先级 1（最有效）**  
- 能用结构化输出/函数调用就用  
- 统一 envelope：永远 JSON

**优先级 2（高性价比）**  
- 解析多级容错（brace matching + jsonrepair）  
- 校验失败自动重试一次（温度 0）

**优先级 3（锦上添花）**  
- schema 调整（outline 用数组/树；clarification 的 options/自由输入逻辑更一致）  
- prompt 放 system，规则变短变硬

---

## Spike 结果 2

你用 **Claude Agent SDK（Claude Code runtime）** 的话，最佳实践基本不是“让模型在文本里乖乖吐某种 JSON”，而是把“需要特殊 UI 的输出”升级成 **工具调用（tool use）**：让模型在需要澄清/需要大纲编辑时 **调用一个你提供的工具**，把结构化 payload 作为 tool 参数传给你的 CLI。这样分流就发生在**协议层**（tool call），而不是在**自然语言层**（tag+JSON 文本）。

> 说明：我无法真实联网打开你给的 URL，但你在消息里已经贴了 *Agent SDK overview* 的主要内容（内置工具、Hooks、Subagents、MCP、Plugins、Sessions、filesystem-based config 等）。下面的建议严格基于这些能力来落地。


## 0) 你现在的方案为什么会“不稳定”
你用 tag+JSON 作为“输出协议”，常见失败模式是：

- 模型会先寒暄/解释两句，导致 tag 不在第一行；
- 模型把多行大纲放进 JSON 字符串时，容易出现转义错误（非法 JSON）；
- 对话变长后，早期规则被稀释；
- 流式输出被截断，导致 JSON 不完整。

这类问题本质上是：**你把“机器可解析协议”放在“自由文本输出通道”里**，只能靠概率。

## 1) Agent SDK 下最稳方案：用 MCP/Plugin 自定义“UI 工具”，让模型用工具来请求交互

Agent SDK overview 明确提到你可以用 **MCP** 与 **Plugins** 扩展工具，并且 SDK 有“agent loop + context management”。因此你可以：

1. 提供两个工具（或一个带 `response_type` 的工具）  
   - `dogent.request_clarification(payload)`  
   - `dogent.request_outline_edit(payload)`
2. 在系统指令/Skill 中规定：  
   - **只要需要用户澄清或需要用户编辑大纲，必须调用相应工具**  
   - 普通回复才允许输出自然语言
3. CLI 端根本不解析模型文本：  
   - 一旦收到 tool call，就进入你的交互 UI（多选/文本编辑），然后把用户结果作为 tool result 返回给 agent loop。

这样做的好处是：  
- 结构化参数由 **tool schema** 约束，比“tag+JSON 文本”稳得多；  
- 你的 UI 分流依据是 **tool name**，不会被模型多输出一句话破坏；  
- tool handler 可以做 **schema 校验 + 自动重试**（见第 3 节）。

### 1.1 推荐：合并成一个工具（更简单）
工具名：`dogent.ui_request`

参数 schema（示意）：

- `type`: `"clarification" | "outline_edit"`
- `title`: string
- `preface?`: string
- `questions?`: array（clarification 用）
- `outline?`:（outline_edit 用，强烈建议用数组/树结构，避免多行字符串转义）

CLI 逻辑就变成：

- `type=clarification` → 逐题渲染选择/输入
- `type=outline_edit` → 打开可编辑文本区域（你也可以在 CLI 把结构渲染成文本再编辑）


## 2) 把规则“固化”在 Claude Code 的工程配置里（减少对话漂移）

Agent SDK overview 提到 Claude Code 的 filesystem-based configuration：  
- Skills：`.claude/skills/SKILL.md`  
- Memory：`CLAUDE.md` 或 `.claude/CLAUDE.md`  
并且 SDK 需要你设置 `setting_sources=["project"]`（Python）或 `settingSources: ['project']`（TS）来启用。

### 2.1 你应该这样组织工程
```text
your_project/
  CLAUDE.md
  .claude/
    skills/
      ui_protocol.md
```

在 `ClaudeAgentOptions` 里启用 project settings：

- Python：`ClaudeAgentOptions(setting_sources=["project"], ...)`
- TypeScript：`settingSources: ['project']`

### 2.2 在 `CLAUDE.md` 写“不可协商”的输出契约（短、硬）
示例（关键是短）：

- 当需要用户参与决策（澄清问题）时：**必须调用 `dogent.ui_request`，type=clarification**
- 当需要用户审阅/编辑大纲时：**必须调用 `dogent.ui_request`，type=outline_edit**
- 禁止在自然语言回复里“顺便问问题/顺便给大纲让用户改”；要么正常输出，要么工具调用

然后在 `.claude/skills/ui_protocol.md` 里放更细的 schema 说明和 examples（skills 适合放长内容）。

> 这比把大段规则塞在每次 prompt 里更稳：规则会作为项目记忆长期存在，且不容易被后续对话冲掉。


## 3) 用 Hooks / 工具返回错误来做“强制校验 + 自动重试”（闭环保证）

Agent SDK overview 列出了 **Hooks**。即使你具体 hook API 叫法不同（各版本可能有差异），设计思路是通用的：

### 3.1 在工具执行层做 schema 校验
当模型调用 `dogent.ui_request(payload)` 时：

1. 你的工具 handler 用 JSON Schema 严格校验 payload
2. 若通过 → 正常打开 UI 并返回用户结果
3. 若不通过 → **不要“尽量修”**，而是返回一个明确的 tool error，让 agent 重新发起正确的 tool call

建议错误返回包含：
- 哪些字段缺失/类型不对
- 期望的 enum 值
- 示例最小合法 payload

这样模型下一次更容易修正。

### 3.2 这一步非常关键：把“格式纠错”变成 agent loop 的一部分
也就是说，你不再指望一次成功；你允许模型犯错，但你用**程序化校验**逼它重来，直到 schema 过关。  
这比“CLI 解析失败就崩”强太多。


## 4) “大纲编辑”payload 建议改成结构化，别用 `outline_text` 大字符串（强烈建议）
你现在的 `outline_text` 是多行字符串，模型极容易输出非法 JSON（引号、换行、反斜杠）。

在工具 schema 里，建议用下面之一：

### 4.1 最简单：`outline_lines: string[]`
```json
{
  "type": "outline_edit",
  "title": "Review outline",
  "outline_lines": [
    "# Outline",
    "1. Introduction",
    "2. Background",
    "3. Proposal"
  ]
}
```

CLI 要给用户编辑时：
- 你可以把 `outline_lines.join("\n")` 放进编辑区
- 用户编辑完再 `split("\n")` 回传（或者直接回传文本，但那是“用户输入”，风险更小）

### 4.2 更高级：树结构（便于你做交互编辑）
```json
{
  "type": "outline_edit",
  "title": "Review outline",
  "outline": [
    {"id":"1", "title":"Introduction", "children":[]},
    {"id":"2", "title":"Background", "children":[
      {"id":"2.1","title":"What problem","children":[]}
    ]}
  ]
}
```


## 5) 如果你暂时不想做 MCP/Plugin：次优但可用的“文本输出容错 + 修复重试”
如果你短期仍要维持 tag+JSON（或统一 JSON）文本协议，建议至少做这套容错链：

1. **严格 parse**（trim BOM/空白后直接判定 JSON）
2. **提取第一个完整 JSON 对象**（括号计数，不要纯正则）
3. **json repair**（去代码块、去前后解释、修尾逗号/单引号等）
4. **失败则二次调用：让 Claude 把上一条“转换为合法 JSON”，温度 0**
5. 最终兜底：当普通文本展示，并提示用户“解析失败可重试”

但我仍建议你尽快迁到第 1 节：**工具调用分流**。


## 6) 在 Agent SDK 的 `allowed_tools` 上做“行为收敛”
overview 的示例里你会传 `allowed_tools=["Read","Edit","Bash"]`。你可以：

- 在需要交互的场景，确保 `allowed_tools` 里包含你的 `dogent.ui_request`
- 并在 rules 中明确：**交互只能通过该工具发生**（不要在自然语言里问）

这会显著降低模型“顺嘴问一句”的概率。


## 7) 我建议你采用的最终架构（最稳、CLI 体验最好）

- **普通回复**：自然语言直接输出（你 CLI 正常打印）
- **需要澄清**：模型调用 `dogent.ui_request(type=clarification, ...)`  
  - CLI 渲染表单/多选  
  - 将答案作为 tool result 返回（结构化）
- **需要大纲编辑**：模型调用 `dogent.ui_request(type=outline_edit, outline_lines=[...])`  
  - CLI 打开编辑区  
  - 用户保存后回传结构化结果
- 工具层做 schema 校验；不合法就返回错误让 agent 重试
