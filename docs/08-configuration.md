# 配置详解（全局与工作区）

Dogent 的配置分为「全局配置」与「工作区配置」，两者协作决定当前项目的模型、模板、工具与交互行为。

## 1. 配置文件清单

### 1.1 全局配置（用户级）

- 路径：`~/.dogent/dogent.json`
- 作用：存放 profile 与默认工作区配置

### 1.2 工作区配置（项目级）

- 路径：`.dogent/dogent.json`
- 作用：覆盖全局默认值，决定当前项目的行为

### 1.3 写作约束文件

- 路径：`.dogent/dogent.md`
- 作用：记录写作目标、风格、禁止项等

### 1.4 JSON Schema（可选）

- 路径：`~/.dogent/dogent.schema.json`
- 作用：用于编辑器校验与自动补全

---

## 2. 配置优先级

1) 工作区 `.dogent/dogent.json`
2) 全局 `~/.dogent/dogent.json` 的 `workspace_defaults`
3) 环境变量（仅在 llm_profile 未配置或为 default 时兜底）

写作时，`.dogent/dogent.md` 作为额外约束注入提示词。

---

## 3. 工作区配置字段说明

以下字段位于 `.dogent/dogent.json`：

- `llm_profile`：使用的 LLM profile 名称（在全局 `llm_profiles` 中定义）
- `web_profile`：Web 搜索配置；`default` 表示使用内置 WebSearch/WebFetch
- `vision_profile`：视觉模型配置；`null` 表示禁用
- `image_profile`：图像生成配置；`null` 表示禁用
- `doc_template`：默认文档模板（如 `general`、`built-in:resume`）
- `primary_language`：CLI 回复语言（默认 Chinese）
- `learn_auto`：是否启用 Lesson 自动记录
- `editor_mode`：`default` 或 `vi`
- `debug`：调试日志开关与级别
- `authorizations`：权限记忆（详见权限章节）
- `claude_plugins`：Claude 插件根目录列表

示例：

```json
{
  "llm_profile": "deepseek",
  "web_profile": "default",
  "vision_profile": null,
  "image_profile": null,
  "doc_template": "general",
  "primary_language": "Chinese",
  "learn_auto": true,
  "editor_mode": "default",
  "debug": false,
  "authorizations": {},
  "claude_plugins": []
}
```

---

## 4. 全局配置字段说明

全局配置主要包含：

- `workspace_defaults`：新项目初始化时使用的默认值
- `llm_profiles`：模型与鉴权配置
- `web_profiles`：自定义 Web Search 配置
- `vision_profiles`：视觉模型配置
- `image_profiles`：图像生成配置

示例结构：

```json
{
  "workspace_defaults": {
    "llm_profile": "default",
    "web_profile": "default",
    "vision_profile": null,
    "image_profile": null,
    "doc_template": "general",
    "primary_language": "Chinese",
    "learn_auto": true,
    "editor_mode": "default"
  },
  "llm_profiles": { "deepseek": { ... } },
  "web_profiles": { "brave": { ... } },
  "vision_profiles": { "glm-4.6v": { ... } },
  "image_profiles": { "glm-image": { ... } }
}
```

---

## 5. LLM Profile 配置

> **提示**：如何申请 DeepSeek、GLM 4.7 等 API Key？请参阅 [附录：第三方 API 配置详细指南](./12-appendix.md)。

`llm_profiles` 中可定义多个模型配置，每个 profile 支持：

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL`
- `API_TIMEOUT_MS`
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`

示例（v0.9.20 默认模板）：

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

---

## 6. Web Profile（自定义搜索）

> **提示**：如何申请 Brave Search 等 Web API Key？请参阅 [附录：第三方 API 配置详细指南](./12-appendix.md)。

当 `web_profile` 设置为某个 profile 名称时，Dogent 会改用自定义 Web Search 工具。支持的 `provider`：

- `google_cse`
- `bing`
- `brave`

字段：

- `api_key`
- `cse_id`（仅 Google CSE 需要）
- `endpoint`
- `timeout_s`

示例：

```json
{
  "web_profiles": {
    "brave": {
      "provider": "brave",
      "api_key": "replace-me",
      "endpoint": "https://api.search.brave.com/res/v1",
      "timeout_s": 20
    }
  }
}
```

如果指定的 profile 不存在，Dogent 会警告并回退到内置 WebSearch/WebFetch。

---

## 7. Vision Profile（视觉能力）

视觉能力默认关闭，设置 `vision_profile` 后启用：

```json
{
  "vision_profile": "glm-4.6v"
}
```

全局 profile 示例：

```json
{
  "vision_profiles": {
    "glm-4.6v": {
      "provider": "glm-4.6v",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      "api_key": "replace-me",
      "model": "glm-4.6v"
    }
  }
}
```

---

## 8. Image Profile（图像生成）

> **提示**：如何申请 GLM 图像生成 API Key？请参阅 [附录：第三方 API 配置详细指南](./12-appendix.md)。

图像生成默认关闭，设置 `image_profile` 后启用：

```json
{
  "image_profile": "glm-image"
}
```

全局 profile 示例：

```json
{
  "image_profiles": {
    "glm-image": {
      "provider": "glm-image",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/images/generations",
      "api_key": "replace-me",
      "model": "glm-image"
    }
  }
}
```

---

## 9. Debug 配置

`debug` 支持以下值：

- `false` / `true`
- 字符串：`"session"`、`"error"`、`"warn"`、`"info"`、`"debug"`、`"all"`
- 数组：如 `["session", "error"]`

日志位置：`.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.md`

---

## 10. 环境变量兜底

当 `llm_profile` 未设置或为 `default` 时，Dogent 会读取环境变量。详见附录。

---

下一章将介绍权限管理与授权记忆机制。
