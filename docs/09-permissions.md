# 权限管理与授权记忆

Dogent 在涉及敏感操作时会主动弹窗询问权限，以保护你的文件安全与工作区边界。

## 1. 触发权限确认的场景

### 1.1 访问工作区外文件

当 Agent 尝试读取或写入 **工作区之外** 的路径时，会要求授权。

例外：`~/.dogent/plugins` 视为内置插件目录，不会触发授权弹窗。

### 1.2 删除类命令

当 Agent 通过 shell 调用删除命令时会触发权限确认，例如：

- `rm` / `rmdir` / `del` / `mv`

### 1.3 修改受保护文件

`.dogent/dogent.md` 被视为受保护文件：

- 直接写入/编辑需要授权
- 通过重定向写入（`>` / `>>`）也会触发授权

---

## 2. 授权选项

当权限弹窗出现时，你可以选择：

- **Allow**：本次允许
- **Allow and remember**：允许并记忆规则
- **Deny**：拒绝

---

## 3. 授权记忆（authorizations）

“Allow and remember” 会写入 `.dogent/dogent.json`：

```json
{
  "authorizations": {
    "Read": ["/absolute/path/**"],
    "Write": ["/absolute/path/**"],
    "Bash": ["/absolute/path/**"]
  }
}
```

下次遇到相同路径或匹配规则时将自动放行。

---

## 4. 与运行模式的关系

- **交互模式**：每次敏感操作都会提示你确认
- **one-shot 模式**：
  - 默认 `-p` 会在需要权限时直接退出（退出码 10）
  - `--auto` 会自动批准权限

---

## 5. 建议实践

- 对可信目录使用“允许并记忆”
- 对高风险操作（删除、覆盖）坚持手动确认
- 定期检查 `.dogent/dogent.json` 的 `authorizations`

---

下一章将介绍 Dogent 与 Claude 的 commands/plugins 兼容方式。
