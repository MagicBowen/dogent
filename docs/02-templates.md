# 模板体系与使用方式

Dogent 的文档模板决定输出文档的结构、写作规则与约束。本章说明模板来源、标准格式、使用方式，以及如何通过新的 `/template` 工作流创建或优化模板。

## 1. 模板的三层来源

Dogent 支持三种层级的模板：

1) **内置模板（built-in）**  
   随软件包发布，适合作为默认模板或参考模板。当前内置模板包括：
   - `general`：通用写作模板；未配置模板时默认使用它
   - `built-in:resume`：简历模板
   - `built-in:research-report`：研究报告模板
   - `built-in:technical-blog`：技术博客模板

2) **全局模板（global）**  
   用户自定义，放在 `~/.dogent/templates/`，适合跨项目复用。

3) **工作区模板（workspace）**  
   用户自定义，放在当前项目的 `.dogent/templates/`，适合当前工作区使用。

使用规则：

- 工作区模板直接使用 `<name>`
- 全局模板使用 `global:<name>`
- 内置模板使用 `built-in:<name>`
- `general` 是默认模板名，通常可直接写 `general`

---

## 2. 新模板标准格式

从 `0.9.28` 开始，Dogent 只支持新的目录式模板格式，不再支持旧的单文件 `<name>.md` 模板。

标准结构如下：

```text
<template-root>/
├── SKILL.md
├── templates/   # 可选，放可复用的输出结构参考
├── examples/    # 可选，放示例输出
└── assets/      # 可选，放图片或其它素材
```

对应路径：

- 工作区模板：`.dogent/templates/<name>/SKILL.md`
- 全局模板：`~/.dogent/templates/<name>/SKILL.md`
- 内置模板：`dogent/templates/<name>/SKILL.md`

### 2.1 `SKILL.md` 的职责

`SKILL.md` 是模板入口文件，应该清楚说明：

- 模板用途
- 背景与适用场景
- 写作注意事项
- 如何使用 `templates/`、`examples/`、`assets/` 中的文件

同时，`SKILL.md` 顶部必须带 YAML 头部，至少包含：

```markdown
---
name: proposal
description: 商务提案模板，用于项目范围、方案与报价说明。
---
```

注意：

- `description` 必须写在同一行，不能写成多行 YAML block scalar。
- Dogent 会用 `description` 作为 `/init`、`@@`、`/template` 列表中的摘要说明。

### 2.2 Dogent 如何读取模板

Dogent 读取模板时遵循以下规则：

- 模板摘要来自 `SKILL.md` 头部 YAML 的 `description`
- 注入提示词时，会去掉 `SKILL.md` 开头的标题和 `## Introduction` 部分
- `templates/*.md` 会按稳定顺序追加到模板内容中，作为输出结构参考
- `examples/` 与 `assets/` 不会自动注入提示词，但应该在 `SKILL.md` 中明确说明其用途
- 旧格式如 `.dogent/templates/proposal.md` 不会被加载，也不会出现在补全列表中

如果模板很简单，也可以只有一个 `SKILL.md`，不必强行拆出 `templates/`、`examples/`、`assets/`。

---

## 3. 使用模板的几种方式

### 方式 A：通过 `/init` 指定模板

```text
/init resume
/init built-in:research-report
/init global:proposal
```

- 工作区模板不需要前缀
- 全局模板使用 `global:`
- 内置模板使用 `built-in:`
- 输入 `/init ` 后会弹出可选模板列表

### 方式 B：在 `.dogent/dogent.json` 中设置默认模板

```json
{
  "doc_template": "built-in:research-report"
}
```

### 方式 C：在当前请求中临时覆盖

在 prompt 中使用 `@@<template>`：

```text
请根据我的工作经历生成一份简历初稿，使用 @@built-in:resume 模板，突出技术能力。
```

这只对当前请求生效，不会修改配置文件。

---

## 4. `/template` 命令

Dogent 提供原生 `/template` 命令来查看模板库存，或启动模板创建/优化工作流：

```text
/template
/template list
/template create <自然语言需求>
/template optimize <template> [自然语言补充要求]
```

行为说明：

- `/template` 与 `/template list` 等价，都会显示可用模板清单
- 输入 `/template ` 时，会弹出 `list`、`create`、`optimize`
- `/template create` 后面可以直接跟自然语言需求
- `/template optimize` 不带模板名时，会显示可用模板与用法提示

---

## 5. 使用 `/template create` 创建模板

这是推荐的模板创建方式。

示例：

```text
/template create 创建一个软件设计文档模板，用于后端服务 RFC，要求包含背景、目标、非目标、架构方案、风险、发布计划
```

`/template create` 的特点：

- 默认在当前工作区下创建模板：`.dogent/templates/<name>/`
- 如果你明确要求全局模板，Dogent 才会创建到 `~/.dogent/templates/<name>/`
- Dogent 会调用内置的 `doc-template-creator` 技能来生成或修改模板文件
- 生成结果遵循新的 `SKILL.md + 可选 templates/examples/assets` 结构

### 5.1 在创建需求中引用文件和已有模板

`/template create` 的自由文本需求中，仍然可以继续使用：

- `@file`：引用工作区文件
- `@@template`：引用已有模板

例如：

```text
/template create 参考 @docs/rfc_guidelines.md 和 @@built-in:research-report，创建一个适合技术方案评审的 RFC 模板
```

在交互输入中：

- 输入 `@` 可以弹出文件补全
- 输入 `@@` 可以弹出模板补全

这对创建复杂模板很有用，因为你可以把已有规范文档、样例文档、已有模板一起作为设计上下文。

---

## 6. 手动创建模板

如果你不想通过 `/template create` 自动生成，也可以手动创建。

### 6.1 创建工作区模板

```bash
mkdir -p .dogent/templates/proposal/templates
mkdir -p .dogent/templates/proposal/examples
```

编辑 `.dogent/templates/proposal/SKILL.md`：

```markdown
---
name: proposal
description: 商务提案模板，用于项目范围、方案与报价说明。
---

# Proposal

## Introduction
- Purpose: 用于商务提案、方案说明与报价沟通。
- Background: 面向客户沟通场景。
- Precautions: 需要兼顾商业可读性与交付边界。

## Writing Requirements
- 明确项目背景、目标、方案、范围、时间与报价。
- 使用专业但不夸张的表达。
- 对假设、风险、依赖项做显式说明。

## Companion Files
- `templates/proposal_structure.md`: 提案标准结构
- `examples/sample_proposal.md`: 示例片段
```

再创建可复用结构文件：

```markdown
## Proposal Structure

1. Executive Summary
2. Background and Goals
3. Proposed Solution
4. Scope and Deliverables
5. Timeline
6. Pricing and Terms
7. Risks and Assumptions
```

参考目录结构：

```text
.dogent/templates/proposal/
├── SKILL.md
├── templates/
│   └── proposal_structure.md
├── examples/
│   └── sample_proposal.md
└── assets/
```

说明：

- `SKILL.md`：入口文件，说明模板用途、背景、注意事项与文件引用
- `templates/*.md`：放可复用的输出结构参考
- `examples/`：放样例输出
- `assets/`：放图片或多媒体素材，并在 `SKILL.md` 中明确说明

创建完成后，可以这样使用：

```text
/init proposal
```

或：

```text
请按 @@proposal 模板输出一份提案初稿。
```

### 6.2 创建全局模板

```bash
mkdir -p ~/.dogent/templates
cp -R .dogent/templates/proposal ~/.dogent/templates/proposal
```

使用时：

```text
/init global:proposal
```

---

## 7. 使用 `/template optimize` 优化模板

`/template optimize` 用于在已有模板基础上继续优化：

```text
/template optimize proposal 增强风险说明和交付边界约束
/template optimize built-in:resume make the template more concise for senior backend engineers
```

行为说明：

- 会先读取现有模板文件，再进行优化
- 会保留当前模板 key，除非你明确要求重命名
- 会继续保持新的目录式模板格式，不会退回旧 `.md` 单文件格式

---

## 8. 模板与文件引用的配合

- `@@<template>`：临时指定模板，仅当前请求有效
- `@<file>`：引用本地文件作为上下文

示例：

```text
使用模板 @@built-in:research-report，参考 @docs/market_notes.md 中的背景信息，输出研究报告提纲。
```

对于 Excel 文件，可以在文件名后追加 `#SheetName`：

```text
@data/sales.xlsx#Q4
```

---

## 9. 模板选择优先级

常见优先级从高到低为：

1) `@@<template>` 临时覆盖
2) `.dogent/dogent.json` 中的 `doc_template`
3) 默认模板 `general`

此外，`.dogent/dogent.md` 中的 **Template Overrides / Template Supplements** 会作为模板之外的额外写作约束，一并注入提示词。

---

下一章将介绍 Dogent 的 CLI 编辑器，帮助你高效进行多行输入和预览。
