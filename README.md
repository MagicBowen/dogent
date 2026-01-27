# Dogent

![](./docs/assets/images/dogent-logo.png)

Dogent 是基于 Claude Agent SDK 开发的专注于**本地文档写作**的 CLI 智能代理。与 Claude Code 聚焦代码任务不同，dogent 提供针对写作任务定制的系统提示词与文档模板体系、支持多格式文档处理与导出、支持面向文档协作而优化的 CLI 交互体验，支持状态管理与持续改进的能力，同时保持与 Claude 生态的兼容，满足本地文档写作的多样化需求，让 AI 辅助本地文档撰写变得更加轻松和高效。

## Install

> 需要 Python 3.10+，建议使用 venv.

### 方式 A：Clone 源码安装

```bash
# 获取源码
git clone https://github.com/MagicBowen/dogent
cd dogent

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装（可编辑模式）
pip install -e .

# 验证
dogent -v
dogent -h
```

### 方式 B：下载 wheel 包安装

在 https://github.com/MagicBowen/dogent/releases 下载 dogent 最新版本的 wheel 包。

```bash
# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装 wheel
pip install /path/to/dogent-0.9.20-py3-none-any.whl

# 验证
dogent -v
dogent -h
```

## Quick Start

通过 CLI 进入某工作目录，然后进入 dogent 交互模式：

```bash
> cd /path/to/your/workspace
> dogent
```

进入 dogent 交互模式后，可以使用 `/init` 命令初始化工作区，也可以直接开始写作：

```bash
dogent>  按照 @@built-in:technical_blog，写一篇关于 github/MagicBowen/dogent 工具用法的技术博客
```

在 dogent 交互模式下，输入 `@` 可以引用工作空间下的文件， 输入 `@@` 可以引用可用的文档模板；输入完成后按回车提交，dogent 会进行任务规划并生成内容返回；
在 dogent 执行过程中，可以使用 `ESC` 中断当前任务进行信息补充或者需求更改。

在 dogent 交互模式下，如需多行输入，可按 `Ctrl+E` 打开基于 CLI 的 markdown 编辑器，编辑完成后使用 `Ctrl+J` 提交发送内容。

使用 `/help` 可以查看帮助，使用 `/exit` 退出 dogent。

## Docs

下面是完整文档目录（位于 `docs/`），建议按顺序阅读：

1. [docs/01-quickstart.md](docs/01-quickstart.md) — 快速开始：安装、配置、/init 与第一次写作
2. [docs/02-templates.md](docs/02-templates.md) — 文档模板体系：内置/全局/工作区模板、@@ 覆盖
3. [docs/03-editor.md](docs/03-editor.md) — CLI 编辑器：多行输入、预览、保存、vi 模式
4. [docs/04-document-export.md](docs/04-document-export.md) — 文档导出与格式转换
5. [docs/05-lessons.md](docs/05-lessons.md) — Lessons：经验沉淀与自动提醒机制
6. [docs/06-history-and-state.md](docs/06-history-and-state.md) — history/memory/lessons 与 show/archive/clean
7. [docs/07-commands.md](docs/07-commands.md) — 命令参考：完整命令与快捷键清单
8. [docs/08-configuration.md](docs/08-configuration.md) — 配置详解：全局与工作区、Profile、模板设置
9. [docs/09-permissions.md](docs/09-permissions.md) — 权限管理：授权触发与记忆规则
10. [docs/10-claude-compatibility.md](docs/10-claude-compatibility.md) — Claude 兼容：commands/plugins 等资产复用
11. [docs/11-troubleshooting.md](docs/11-troubleshooting.md) — 异常处理与调试
12. [docs/12-appendix.md](docs/12-appendix.md) — 附录：环境变量与第三方 API 配置
