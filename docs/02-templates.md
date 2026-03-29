# 模板体系与使用方式

Dogent 的模板体系决定了不同文档类型的输出结构与写作规则，保证专业文档的内容风格与结构的一致性。本章聚焦模板来源、优先级与使用方式。

## 1. 模板的三层来源

Dogent 支持三种层级的模板：

1) **内置模板（built-in）**  
   随包发布，适合作为默认模板或示例。目前随包发布的模板只有如下几个（更多模板可以通过后文介绍的自定义方式进行创建）：
   - `built-in:general`：通用写作模板，如果没有配置，默认使用该模板
   - `built-in:technical_blog`：技术博客模板
   - `built-in:research_report`：研究报告模板
   - `built-in:resume`：个人简历模板

2) **全局模板（global）**  
   用户自定义，放在 `~/.dogent/templates/`，适合团队或个人跨项目复用。

3) **工作区模板（workspace）**  
   用户自定义，放在项目工作区内 `.dogent/templates/` 目录下，适合当前工作区内使用。

**模板目录命名规则**：`<name>/SKILL.md`，使用时直接写 `<name>`。

---

## 2. 使用模板的几种方式

### 方式 A：通过 `/init` 指定模板

```text
> /init resume
> /init built-in:research_report
> /init global:proposal
```

- **工作区模板**不需要前缀，放在当前工作目录的 `.dogent/templates/<name>/SKILL.md` 下；使用 `/init` 命令加空格后，会自动出现在可选模板列表中。
- **全局模板**使用 `global:` 前缀，放在用户目录的 `~/.dogent/templates/<name>/SKILL.md` 下；使用 `/init` 命令加空格后，会自动出现在可选模板列表中。
- **内置模板**使用 `built-in:` 前缀，软件包自带。

### 方式 B：在 `.dogent/dogent.json` 中设置

```json
{
  "doc_template": "built-in:research_report"
}
```

### 方式 C：临时覆盖（只对当前请求生效）

在用户输入前加上 `@@`：

```text
请根据我的工作经历生成一份简历初稿，使用 @@global:resume 模板，突出技术能力。
```

这不会修改任何配置文件，仅对本轮有效。

---

## 3. 让 `/init` “自动智能选择”模板

当 `/init` 的参数不是一个已知模板时，Dogent 会进入 **Init Wizard** 模式：

```text
> /init 我需要写一份 B2B 产品的市场分析报告
```

向导会：

- 尝试匹配一个合适的模板（如 `research_report`）
- 生成 `.dogent/dogent.md` 的初稿
- 将配置自动写入 `.dogent/dogent.json`

这是一种“让 `/init` 自动理解需求并给出模板建议”的方式。

---

## 4. 创建自定义模板

### 创建工作区模板

```bash
mkdir -p .dogent/templates/proposal/templates
mkdir -p .dogent/templates/proposal/examples
```

编辑 `.dogent/templates/proposal/SKILL.md`。模板需要使用 skill 风格目录结构，推荐把简短摘要写在 YAML 头部，把模板用途、背景、注意事项写在 `SKILL.md`，再把可复用的输出结构放进 `templates/`：

```markdown
---
name: proposal
description: 商务提案模板
---

# Proposal Template

## Writing Principles
本模板的写作原则和要求。

## Document Structure
本文档类型的输出结构说明。
```

可参考的目录结构：

```text
.dogent/templates/proposal/
├── SKILL.md
├── templates/
│   └── proposal_structure.md
├── examples/
│   └── sample_proposal.md
└── assets/            # 仅在需要多媒体素材时使用
```

- `SKILL.md`：入口文件，说明模板的用途、背景、注意事项，以及如何使用其他文件。
- `templates/*.md`：放可复用的输出结构参考。
- `examples/`：放样例输出。
- `assets/`：放多媒体素材，并在 `SKILL.md` 中明确引用。

配置好的模板，可以在交互中使用 `@@proposal` 进行引用，或者在初始化工作区时使用：

```text
> /init proposal
```

### 创建全局模板

```bash
mkdir -p ~/.dogent/templates
cp -R .dogent/templates/proposal ~/.dogent/templates/proposal
```

使用时：

```text
> /init global:proposal
```

---

## 5. 模板与文件引用的配合（`@@` 与 `@`）

- `@@<template>`：临时指定模板，仅对当前请求生效。
- `@<file>`：引用本地文件作为上下文。

示例：

```text
使用模板 @@built-in:research_report，参考 @docs/market_notes.md 中的背景信息，输出研究报告提纲。
```

对于 Excel，可用在文件名后面使用 `#SheetName` 指定具体的 Excel 文件中的工作表：

```text
@data/sales.xlsx#Q4
```

---

## 6. 模板选择与优先级

常见使用优先级（从高到低）：

1) **临时覆盖：`@@<template>`**（用户在 Dogent 的 CLI 中输入 prompt 的时候，可以使用 `@@` 引用可用的文档模板，指示 agent 按照指定模板要求进行撰写）
2) **工作区配置：`.dogent/dogent.json` 的 `doc_template`**（本工作目录下文档写作的默认模板，可以手动修改该配置更换模板，也可以使用 `/init <template>` 命令更换模板配置）
3) **默认模板：`general` -> 内置 `dogent/templates/general/SKILL.md`**（当没有指定和配置任何文档模板，该工作目录下的文档写作默认采用该内置模板）

此外，`.dogent/dogent.md` 中的 **Template Overrides / Template Supplements** 会作为模板的“额外约束”，可以手动修改该 markdown 文件，在其中增加更多模板之外的要求和约束。

---

## 7. `/template` 命令

Dogent 还提供原生 `/template` 命令来查看模板库存或启动模板工作流：

```text
/template
/template list
/template create <自然语言需求>
/template optimize <template> [自然语言补充要求]
```

- 直接回车执行 `/template` 时，会显示当前可用模板清单。
- 输入 `/template ` 时会弹出 `list`、`create` 与 `optimize` 选项。
- `/template create` 后面可以直接跟自然语言描述，也可以在需求中继续使用 `@file` 引用工作区文件、使用 `@@template` 引用已有模板作为参考上下文。
- `/template optimize` 不带模板名时，会显示可用模板和用法提示。

---

下一章将介绍 Dogent 的 CLI 编辑器，帮助你高效进行多行输入和预览。
