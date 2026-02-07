# Commands 参考手册

本章是“查阅式”手册，列出 Dogent 的全部命令、参数与快捷键。若需要教程，请先阅读前面章节。

## 1. CLI 启动与模式

### 交互式模式

```bash
dogent
```

### 单次模式（One-shot）

```bash
dogent -p "写一份 README 提纲"
```

- `--auto`：自动批准权限并跳过澄清
- 未初始化时会自动创建默认 `.dogent` 配置

#### One-shot 退出码

- `0`：完成（会输出 `Completed.`）
- `1`：错误
- `2`：用法错误
- `10`：需要权限（默认 `-p` 会直接退出）
- `11`：需要澄清
- `12`：需要大纲编辑
- `13`：等待输入
- `14`：被中断
- `15`：被取消

---

## 2. 内置命令列表

### /init

初始化工作区 `.dogent` 目录。

用法：

```text
/init
/init <template>
/init <自然语言描述>
```

说明：

- 模板名支持 `built-in:` / `global:` 前缀
- 参数不是模板时进入 Init Wizard（智能生成）

---

### /edit

打开编辑器编辑工作区文件。

```text
/edit <path>
```

支持 `.md/.markdown/.mdown/.mkd/.txt` 文件。

---

### /profile

查看或切换 profile。

```text
/profile
/profile show
/profile llm <name>
/profile web <name>
/profile vision <name|none>
/profile image <name|none>
```

---

### /debug

配置调试日志。

```text
/debug
/debug off|session|error|session-errors|warn|info|debug|all|custom
```

---

### /learn

记录 Lesson 或控制自动记录。

```text
/learn <text>
/learn on
/learn off
```

---

### /show

展示历史或 lessons。

```text
/show history
/show lessons
```

---

### /clean

清理工作区状态。

```text
/clean [history|lesson|memory|all]
```

---

### /archive

归档历史/lesson。

```text
/archive [history|lessons|all]
```

---

### /help

显示当前模型、profile、命令与快捷键提示。

---

### /exit

退出 Dogent CLI。

---

## 3. Claude Commands / Plugins

### Claude Commands

- 放置在 `.claude/commands/*.md`（项目）或 `~/.claude/commands/*.md`（用户）
- 会在 Dogent 中以 `/claude:<name>` 形式出现

### Claude Plugins

- 在 `.dogent/dogent.json` 中配置 `claude_plugins`
- 插件路径中需要包含 `.claude-plugin/plugin.json`
- 命令会以 `/claude:<plugin>:<name>` 形式出现
- Dogent 会在启动时把内置插件安装到 `~/.dogent/plugins`，并在新工作区默认加入 `~/.dogent/plugins/claude`

---

## 4. 快捷键与输入特性

### 全局快捷键

- `Esc`：中断当前任务
- `Ctrl+C`：退出（或终止当前任务）
- `Ctrl+E`：打开多行 Markdown 编辑器
- `Alt/Option+Enter`：插入换行

### 其他输入特性

- 输入 `/`：显示命令提示
- 输入 `@`：提示文件补全
- 输入 `@@`：提示模板补全
- `!<command>`：执行工作区内 shell 命令

---

如果需要了解配置结构、模板系统或权限机制，请继续阅读后续章节。
