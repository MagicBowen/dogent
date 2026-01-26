# Dogent

Dogent 是基于 Claude Agent SDK 开发的专注于**本地文档写作**的 CLI 智能代理。与 Claude Code 聚焦代码任务不同，Dogent 提供针对写作任务的定制的系统提示词与文档模板体系、支持多格式文档处理与导出、具备持续学习与状态管理能力，并支持灵活配置与Claude生态兼容，满足本地文档写作的多样化需求，让 AI 辅助本地文档撰写变得更加轻松和高效。

## Install

> 需要 Python 3.10+，建议使用 venv。

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

```text
$ dogent
> 写一篇关于 dogent 用法的技术博客，参考 https://github.com/MagicBowen/dogent/blob/main/README.md
> /exit
```

如需多行输入，可按 `Ctrl+E` 打开编辑器；

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
