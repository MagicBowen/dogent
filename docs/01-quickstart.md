# Quick Start：从安装到第一次写作

## 1. Dogent 是什么？

Dogent 是基于 Claude Agent SDK 开发的专注于**本地文档写作**的 CLI 智能代理。与 Claude Code 聚焦代码任务不同，Dogent 为报告、博客、技术文档、运营内容等写作场景提供优化的交互体验、文档模板与内置工具链，让 AI 辅助本地文档撰写变得更加高效和轻松。

Dogent 的主要功能如下：

**1. 专注写作任务**
- **定制的系统提示词与写作最佳实践**：针对长文档撰写任务优化，避免 AI 长文写作常见的风格与逻辑结构"碎片化"问题
- **文档模板体系**：可以配置工作区的默认文档模板类型（内置/全局/工作区三层模板结构），也支持通过 `@@template` 制定临时模板，指导 agent 按照特定模板要求输出
- **终端写作体验**：CLI 交互中集成即时 Markdown 编辑器（预览/保存/提交、vi 模式），支持 `Esc` 中断、快捷键与命令补全，让交互过程中编辑更流畅

**2. 智能文档处理**
- **多格式上下文输入**：`@file` 引用本地文件，支持 PDF、DOCX、XLSX、文本等格式，Excel 可通过 `#Sheet` 指定工作表，轻松整合现有资料
- **多格式导出与转换**：Markdown ↔ DOCX、Markdown → PDF，支持图片抽取、PDF 样式定制（CSS/分页），满足不同输出格式要求
- **视觉内容理解与生成**：通过配置特定的模型 profile，支持图片/视频分析，并可基于文本提示生成配图，让文档更生动

**3. 持续学习与状态管理**
- **Lessons 经验沉淀**：当 Agent 执行失败或用户主动中断时自动记录教训，也可通过 `/learn` 手动添加，持续注入上下文提示，避免重复错误
- **项目状态文件化**：history、memory、lessons 均持久化存储，支持 `/show` 查看、`/archive` 归档、`/clean` 清理，方便回溯与协作

**4. 灵活配置与生态兼容**
- **可配置的搜索服务**：针对国内 Claude Code 的 Web Search 不可用的问题，支持用户配置第三方搜索服务，保持联网研究能力
- **分层配置体系**：支持全局/工作区 profiles 配置，可分别为不同工作空间设置独立的模型服务与搜索服务
- **丰富运行模式**：交互式对话与 one-shot（`-p`）模式，支持 `--auto` 自动批准权限，适应不同使用习惯
- **Claude 生态兼容**：可复用 Claude Code 的 commands、plugins、skills，降低学习与迁移成本

如果你需要长期写报告、方案、技术文档或运营内容，Dogent 的设计会更贴近你的习惯。

---

## 2. 安装（两种方式）

> 下面默认使用 Python 3.10+，建议新建 venv。

### 方式 A：Clone 源码安装（开发/调试友好）

```bash
# 1) 获取源码
git clone https://github.com/MagicBowen/dogent
cd dogent

# 2) 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3) 安装（基于源码安装）
pip install -e .

# 4) 验证
dogent -v
dogent -h
```

### 方式 B：下载 wheel 包安装（稳定使用）

在 https://github.com/MagicBowen/dogent/releases 下载 dogent 最新版本的 wheel 包。

```bash
# 1) 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 2) 安装 wheel
pip install /path/to/dogent-0.9.20-py3-none-any.whl

# 3) 验证
dogent -v
dogent -h
```

---

## 3. 最小配置：LLM Profile

> **提示**：如何申请 DeepSeek、GLM 4.7 等 API Key？详细步骤请参阅 [附录：第三方 API 配置详细指南](./12-appendix.md)。

Dogent 至少需要一个可用的 LLM 配置。推荐两种方式：

### 方式 A：直接使用环境变量（继承 Claude Code 的环境变量配置）

Dogent 会读取以下环境变量：

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL`
- `API_TIMEOUT_MS`
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`

在终端中配置（示例）：

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-token>"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### 方式 B：配置全局 profile（更推荐）

优点：无需设置环境变量，只需在 dogent 全局配置中设置可用的 LLM 配置；之后每个工作区只用按需选择对应的需要的 LLM profile 即可。

1) 第一次执行 `dogent` 命令（无论在哪个目录）都会自动在用户的 HOME 目录下创建 `~/.dogent/dogent.json` 全局配置文件，里面已经包含常用 `llm_profiles` 模板，你只需要补全对应的 API TOKEN。

2) 打开 `~/.dogent/dogent.json`，以配置 **DeepSeek** 为例，在 `llm_profiles.deepseek` 中把 "replace-me" 替换为你自己的 DeepSeek Anthropic API Token：

```json
{
  "llm_profiles": {
    "deepseek": {
      "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
      "ANTHROPIC_AUTH_TOKEN": "replace-me",
      "ANTHROPIC_MODEL": "deepseek-reasoner",
      "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-chat",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
  }
}
```

> DeepSeek Anthropic API Token 的申请步骤见 [附录：第三方 API 配置详细指南](./12-appendix.md) 的 `DeepSeek（Anthropic API 兼容）` 章节。

3) 回到某个工作目录，在 CLI 中进入 dogent后，使用 `/profile` 子命令为当前工作区选择刚刚配置的 `deepseek`：

```bash
dogent> /profile llm deepseek
``` 

在 dogent 下，输入子命令 `/profile` 后输出空格，可以配置的 profile 类型会自动出现在下拉类表中，然后选择 llm 后再输入空格，可以看到可用的 llm profile 列表，选择 `deepseek` 后回车即可。

此时项目的 `./.dogent/dogent.json` 会自动写入：

```json
{ "llm_profile": "deepseek" }
```

你也可以通过直接修改当前工作区下的 `./.dogent/dogent.json` 来指定不同的 `llm_profile`。

4) 完成。你已经具备一个可用的 LLM Profile，可以开始写作了。每个工作区都可以根据任务的差异单独配置不同的 LLM Profile。

> 更多 LLM profile 示例与其它平台的 API 申请方式，请参考 [附录：第三方 API 配置详细指南](./12-appendix.md) 与 [配置说明](./08-configuration.md)。

---

## 4. 初始化项目（/init）

第一次使用某个工作目录时，可以通过执行 `/init` 命令来初始化该工作目录的项目配置：

```bash
> /init
```

会生成如下关键文件:

- `.dogent/dogent.md`：项目写作约束（写作目标、语气、受众、风格要求等）

你可以修改该文件，为该工作区指定更具体的写作约束。

更常用的初始化方式是，在输入命令 `/init` 后输入空格，可以看到可以使用的文档模板，然后直接选择该工作区的默认写作模板：

```bash
> /init built-in:research_report
```

此外，也可以不指定模板，而是输入自由的提示词，这时`/init` 会进入「智能向导」模式，并根据你的描述自动选择合适的模板并自动生成写作约束，例如：

```bash
> /init 我需要写一个个人简历，要求突出技术能力，适合申请软件工程师岗位。
```

对于上面的初始化，dogent会自动匹配到 `@@built-in:resume` 模板，并生成相应的 `.dogent/dogent.md` 写作约束文件。

---

## 5. 完成一次最小写作任务

示例流程：

```bash
dogent>  按照模板 @@built-in:technical_blog，写一篇关于 github/MagicBowen/dogent 工具用法的技术博客
```

如果你有本地资料，可以直接引用：

```bash
> @docs/notes.md 请根据以上内容技术博客。
```

在 dogent 交互模式下，输入 `@` 可以引用工作空间下的文件， 输入 `@@` 可以引用可用的文档模板；输入完成后按回车提交，dogent 会进行任务规划并生成内容返回；
在 dogent 执行过程中，可以使用 `ESC` 中断当前任务进行信息补充或者需求更改。

在 dogent 交互模式下，如需多行输入，可按 `Ctrl+E` 打开基于 CLI 的 markdown 编辑器，编辑完成后使用 `Ctrl+J` 提交发送内容。

使用 `/help` 可以查看帮助，使用 `/exit` 退出 dogent。

---

## 6. 退出

```bash
> /exit
```

或者在终端中使用 `Ctrl+C`。

---

下一章将介绍模板体系与模板优先级，帮助你稳定地产出结构一致的文档。
