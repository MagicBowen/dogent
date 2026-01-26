# Claude 资产兼容：Commands / Plugins / Skills

Dogent 基于 Claude Agent SDK，能够复用 Claude Code 生态中的资产（commands、skills、plugins 等），降低迁移成本。

## 1. Claude Commands（命令复用）

Dogent 会加载以下位置的 Claude commands：

- 项目级：`.claude/commands/*.md`
- 用户级：`~/.claude/commands/*.md`

这些命令在 Dogent 中会以 **`/claude:<name>`** 的形式出现，以避免与 Dogent 内置命令冲突。

示例：

```text
# 原 Claude 命令文件：.claude/commands/outline.md
# 在 Dogent 中使用：
/claude:outline
```

---

## 2. Claude Plugins（插件复用）

如果你有 Claude 插件，可在 `.dogent/dogent.json` 中配置：

```json
{
  "claude_plugins": ["./plugins/demo", "~/.claude/plugins/shared"]
}
```

要求：插件根目录必须包含 `.claude-plugin/plugin.json`。

插件命令在 Dogent 中的形式：

```text
/claude:<plugin>:<command>
```

---

## 3. 其它 Claude 资产（skills / agents）

Dogent 会将项目内 `.claude/` 目录传递给 Claude Agent SDK，方便复用已有的 Claude 资产结构。  
（若你在 Claude Code 中已有 skills/agents 配置，可直接迁移到同名目录。）

> 注意：Dogent 只在 CLI 中显式注册 **commands**；其他资产由 SDK 在后台使用。

---

## 4. 实战建议

- 若你已有 Claude Code 项目，可直接拷贝 `.claude/commands` 到当前项目
- 将共享命令放在 `~/.claude/commands` 便于跨项目复用
- 插件建议集中配置在 `~/.claude/plugins`，然后通过 `claude_plugins` 引用

---

下一章将介绍故障排查与调试方式。
