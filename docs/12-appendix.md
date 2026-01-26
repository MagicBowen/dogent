# 附录：环境变量与第三方 API 配置

本附录汇总常用的环境变量与第三方 API 配置方式（以 v0.9.20 默认模板为例）。

---

## A. Claude Code 风格环境变量

Dogent 在 `llm_profile` 未设置或为 `default` 时，会读取环境变量：

- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- `ANTHROPIC_SMALL_FAST_MODEL`
- `API_TIMEOUT_MS`
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`

示例：

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-token>"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

---

## B. DeepSeek（Anthropic API 兼容）

### 申请步骤（概述）

1) 在 DeepSeek 控制台注册账号
2) 创建 API Key
3) 将 Key 配置到 `~/.dogent/dogent.json` 的 `llm_profiles`

### 配置示例

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

## C. GLM 4.7（Anthropic API 兼容）

### 申请步骤（概述）

1) 在智谱 AI 控制台注册账号
2) 创建 API Key
3) 将 Key 配置到 `llm_profiles`

### 配置示例

```json
{
  "llm_profiles": {
    "glm4.7": {
      "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
      "ANTHROPIC_AUTH_TOKEN": "replace-me",
      "ANTHROPIC_MODEL": "glm-4.7",
      "ANTHROPIC_SMALL_FAST_MODEL": "glm-4.7",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
  }
}
```

---

## D. GLM 图像生成（Image API）

### 申请步骤（概述）

1) 在智谱 AI 控制台创建图像生成 API Key
2) 配置到 `image_profiles`
3) 在 `.dogent/dogent.json` 中选择 `image_profile`

### 配置示例

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

## E. Brave Search（Web Search API）

### 申请步骤（概述）

1) 在 Brave Search 控制台注册账号
2) 创建 Search API Key
3) 配置到 `web_profiles`
4) 在 `.dogent/dogent.json` 中设置 `web_profile: "brave"`

### 配置示例

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

---

如需补充其它模型或搜索提供商，可参考 `~/.dogent/dogent.json` 的模板结构自行扩展。
