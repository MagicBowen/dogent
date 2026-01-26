# 故障排查与调试

本章整理 Dogent 常见问题与处理方式，帮助你快速定位原因。

## 1. 打开调试日志

```text
/debug
```

常用模式：

```text
/debug session
/debug error
/debug all
```

日志路径：

```
.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md
```

日志中包含：prompt、tool 调用、响应摘要等信息，适合定位失败原因。

---

## 2. 常见问题与解决办法

### 2.1 LLM 无法连接或鉴权失败

症状：启动即报错，或请求失败。  
处理：确认以下任一方式配置正确：

- `~/.dogent/dogent.json` 中 `llm_profiles`
- 环境变量 `ANTHROPIC_*`

### 2.2 Web / Vision / Image Profile 不生效

症状：提示 profile 缺失或工具不可用。  
处理：检查：

- `~/.dogent/dogent.json` 中是否存在对应 profile
- `.dogent/dogent.json` 是否正确设置 `web_profile` / `vision_profile` / `image_profile`

### 2.3 模板找不到

症状：`/init` 提示模板不存在。  
处理：

- Workspace 模板不需要 `workspace:` 前缀
- 全局模板必须用 `global:`
- 内置模板必须用 `built-in:`

### 2.4 导出 PDF/DOCX 失败

症状：导出异常或格式不完整。  
处理：

- 确保 Pandoc 可用
- 输出路径在工作区内且扩展名匹配

### 2.5 非 TTY 环境下交互异常

症状：编辑器或选择器无法渲染。  
处理：Dogent 会自动退回为文本输入模式，建议在支持 TTY 的终端使用。

### 2.6 权限被拒绝

症状：提示需要授权或直接中断。  
处理：

- 交互模式下选择 Allow / Allow and remember
- one-shot 模式使用 `--auto`

---

## 3. 提交问题时应包含的信息

建议附带：

- Dogent 版本（`dogent -v`）
- 当前工作目录结构（可简化）
- `.dogent/dogent.json` 关键字段（不要泄露密钥）
- 相关日志片段（可裁剪）

---

下一章为附录，包含环境变量与第三方 API 配置说明。
