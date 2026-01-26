# Quick Start：从安装到第一次写作

## 1. Dogent 是什么？

Dogent 是基于 Claude Agent SDK 的 CLI 写作 Agent，强调「文档写作」场景的结构化产出：

- 更适合写作的系统提示词与模板体系（区别于 Claude Code 的通用代码开发）
- 面向文档的流程：规划 → 研究 → 初稿 → 校验 → 打磨
- 内置工具：文档读取、导出/转换、模板渲染、Lesson 记录等
- 交互方式：终端中的交互式写作、可中断与可编辑的多轮协作

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

# 3) 安装（可编辑模式）
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

1) 进入任意项目目录，运行一次 `dogent`，它会创建 `~/.dogent/dogent.json` 的模板文件。  
2) 打开 `~/.dogent/dogent.json`，在 `llm_profiles` 中填入你的配置。  
3) 在项目中选择 `llm_profile`（见下一节）。

---

## 4. 选择 Profile（`/profile` command）

进入某个项目目录后：

```text
$ dogent
> /profile
```

你将看到当前项目已选择 profile 配置。

当输入 `/profile` 命令后输入空格，下拉列表中会给出可以配置的profile，选择 llm 继续空格，会看到可选的 llm-profile（只显示已经在`~/.dogent/dogent.json`配置好的）
选择好后回车，当前工程下配置的 profile 会保存在当前工程目录下的 `./dogent/dogent.json`  的 `llm_profile` 中。

`~/.dogent/dogent.json` 中配置的全局可以选择的 llm_profile 及其属性，每个工作目录下根据任务适配度选择不同的 llm_profile 名称。

---

## 5. 初始化项目（/init）

第一次使用某个工作目录时，可以通过执行 `/init` 命令来初始化该工作目录的项目配置：

```text
> /init
```

会生成两个关键文件：

- `.dogent/dogent.json`：工作区配置（profile、模板、语言、权限记忆等）
- `.dogent/dogent.md`：项目写作约束（写作目标、语气、受众、风格要求等）

输入命令 `/init` 后输入空格，可以看到可以使用的文档模板，可以直接指定模板：

```text
> /init resume
> /init built-in:research_report
> /init global:proposal
```

若输入的是普通文字而不是模板名，`/init` 会进入「智能向导」模式，并根据你的描述自动生成写作约束与自动选择合适的模板。

---

## 6. 完成一次最小写作任务

示例流程：

```text
> 我们需要一份 1-2 页的产品周报，包含本周工作、问题与下周计划。先给出提纲。
```

如果你有本地资料，可以直接引用：

```text
> @docs/notes.md 请根据以上内容完善周报初稿。
```

中途需要多行输入时，按 `Ctrl+E` 进入编辑器；需要中断任务时按 `Esc`。

---

## 7. 退出

```text
> /exit
```

或者在终端中使用 `Ctrl+C`。

---

下一章将介绍模板体系与模板优先级，帮助你稳定地产出结构一致的文档。
