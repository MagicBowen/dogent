# 附录：第三方 API 配置详细指南

本附录面向初学者，详细介绍如何申请和配置 Dogent 支持的各类第三方 API。每个章节包含平台地址、注册流程、API Key 申请步骤，以及如何在 Dogent 中配置。

> **提示**：本文档基于 2026 年 1 月的各平台界面编写，实际操作时界面可能略有变化，请以平台最新说明为准。

---

## A. Claude Code 风格环境变量（兜底配置）

当 `llm_profile` 未设置或为 `default` 时，Dogent 会读取以下环境变量作为兜底配置。这种方式适合已在 Claude Code 中配置好环境的用户快速上手。

### 环境变量清单

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `ANTHROPIC_BASE_URL` | API 基础地址 | `https://api.deepseek.com/anthropic` |
| `ANTHROPIC_AUTH_TOKEN` | API 鉴权令牌 | `<your-token>` |
| `ANTHROPIC_MODEL` | 主模型名称 | `deepseek-reasoner` |
| `ANTHROPIC_SMALL_FAST_MODEL` | 小模型名称 | `deepseek-chat` |
| `API_TIMEOUT_MS` | 请求超时（毫秒） | `600000` |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 禁用非必要流量 | `1` |

### 配置示例

```bash
# 在终端中设置环境变量（临时生效）
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="<your-token>"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

> **注意**：环境变量只在当前终端会话有效。若需永久生效，请将上述行添加到 shell 配置文件（如 `~/.bashrc`、`~/.zshrc`）中。

---

## B. DeepSeek（Anthropic API 兼容）

DeepSeek 提供了与 Anthropic API 兼容的接口，是目前性价比很高的选择。

### 1. 平台地址
- **开放平台**：https://platform.deepseek.com/api_keys
- **API 文档**：https://api-docs.deepseek.com/

### 2. 注册与申请步骤（详细图文指引）

#### 步骤一：注册/登录账号
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys)。
2. 点击右上角「注册」按钮（若已有账号则直接登录）。
3. 按照提示完成邮箱验证、手机绑定等注册流程。

#### 步骤二：创建 API Key
1. 登录后，在左侧导航栏点击 **「API keys」**。
2. 点击右侧的 **「创建 API key」** 按钮。
3. 输入一个便于记忆的名称（例如 "dogent-dev"）。
4. 点击 **「创建」**。
5. **重要**：创建成功后，页面会显示生成的 API Key（形如 `sk-xxxxxxxxxxxx`）。**请立即复制并妥善保存**，因为关闭页面后无法再次查看完整 Key。

#### 步骤三：查看可用模型与计费
- 在控制台可以查看当前支持的模型列表（如 `deepseek-chat`、`deepseek-reasoner`）。
- 新用户通常有一定免费额度，具体请参考平台的「余额」或「用量」页面。

### 3. Dogent 配置示例

将以下配置添加到 `~/.dogent/dogent.json` 的 `llm_profiles` 部分：

```json
{
  "llm_profiles": {
    "deepseek": {
      "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
      "ANTHROPIC_AUTH_TOKEN": "sk-xxxxxxxxxxxx", // 替换为你的实际 Key
      "ANTHROPIC_MODEL": "deepseek-reasoner",
      "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-chat",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
  }
}
```

### 4. 使用说明
1. 在项目目录中运行 `dogent`。
2. 输入 `/profile`，按空格，选择 `llm`，再选择 `deepseek`。
3. 确认后，当前项目的 `.dogent/dogent.json` 中的 `llm_profile` 会被设置为 `deepseek`。

---

## C. GLM 4.7（智谱AI · Anthropic API 兼容）

智谱AI的 GLM-4.7 是国内领先的大模型，同样提供 Anthropic 兼容接口。

### 1. 平台地址
- **开放平台**：https://open.bigmodel.cn
- **API 文档**：https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7

### 2. 注册与申请步骤

#### 步骤一：注册/登录账号
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn)。
2. 点击右上角「注册」按钮。
3. 填写邮箱、手机号等信息完成注册。

#### 步骤二：实名认证（必需）
1. 登录后，系统会提示进行实名认证。
2. 按照指引完成个人身份证认证或企业营业执照认证。
3. 认证通过后，会获得免费 token 额度（新用户通常赠送数百万 token）。

#### 步骤三：创建 API Key
1. 在控制台左侧导航栏找到 **「API Keys」**（或「密钥管理」）。
2. 点击 **「创建 API Key」**。
3. 填写应用名称（例如 "dogent-project"）。
4. 点击确认，复制生成的 Key（形如 `abcdef1234567890`）。

### 3. Dogent 配置示例

```json
{
  "llm_profiles": {
    "glm4.7": {
      "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
      "ANTHROPIC_AUTH_TOKEN": "abcdef1234567890", // 替换为你的实际 Key
      "ANTHROPIC_MODEL": "glm-4.7",
      "ANTHROPIC_SMALL_FAST_MODEL": "glm-4.7",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
  }
}
```

### 4. 注意事项
- GLM-4.7 支持思考模式（thinking），可在请求中通过参数开启。
- 免费额度有效期为 30 天，请及时关注控制台的「资源包」页面。

---

## D. GLM 图像生成（Image API）

智谱AI也提供了独立的图像生成 API，可用于 Dogent 的 `image_profile` 配置。

### 1. 平台地址
- **同一平台**：https://open.bigmodel.cn（与文本模型同一账号）
- **图像生成文档**：在平台文档中查找「图像生成」章节。

### 2. 申请步骤
1. **已有账号**：如果你已按照 C 章节注册了智谱AI账号，可直接使用同一账号。
2. **开通服务**：在控制台找到「图像生成」或「CogView」服务，确认已开通（通常默认开通）。
3. **获取 API Key**：使用与文本模型相同的 API Key（即 C 章节中创建的 Key）。

### 3. Dogent 配置示例

在 `~/.dogent/dogent.json` 中添加 `image_profiles`：

```json
{
  "image_profiles": {
    "glm-image": {
      "provider": "glm-image",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/images/generations",
      "api_key": "abcdef1234567890", // 与文本模型相同的 Key
      "model": "glm-image"
    }
  }
}
```

### 4. 在工作区启用图像生成
在项目的 `.dogent/dogent.json` 中设置：
```json
{
  "image_profile": "glm-image"
}
```

---

## E. Brave Search（Web Search API）

Brave Search 提供了高质量的网页搜索 API，可用于 Dogent 的 `web_profile` 配置。

### 1. 平台地址
- **API 首页**：https://brave.com/search/api/
- **控制台注册**：https://api-dashboard.search.brave.com/register

### 2. 注册与申请步骤

#### 步骤一：注册账号
1. 访问 [Brave Search API 注册页面](https://api-dashboard.search.brave.com/register)。
2. 填写邮箱、密码等信息完成注册。
3. 登录邮箱完成验证。

#### 步骤二：创建 API Key
1. 登录后，进入控制台仪表板。
2. 找到 **「API Keys」** 或 **「Subscription」** 选项卡。
3. 点击 **「Create new key」** 或类似按钮。
4. 为 Key 命名（例如 "dogent-search"）。
5. 复制生成的 **「X-Subscription-Token」**（形如 `BSA-xxxxxxxxxxxx`）。

#### 步骤三：选择套餐
- **免费套餐**：每月 2,000 次查询，适合个人试用。
- **付费套餐**：根据需求选择 Base AI（$5/千次）或 Pro AI（$9/千次）等套餐。

### 3. Dogent 配置示例

在 `~/.dogent/dogent.json` 中添加 `web_profiles`：

```json
{
  "web_profiles": {
    "brave": {
      "provider": "brave",
      "api_key": "BSA-xxxxxxxxxxxx", // 替换为你的实际 Token
      "endpoint": "https://api.search.brave.com/res/v1",
      "timeout_s": 20
    }
  }
}
```

### 4. 在工作区启用 Brave Search
在项目的 `.dogent/dogent.json` 中设置：
```json
{
  "web_profile": "brave"
}
```

> **注意**：如果 `web_profile` 设置为 `default`，Dogent 将使用内置的 WebSearch/WebFetch 工具（功能有限）。

---

## F. 其他配置建议

### 1. 多 Profile 管理
你可以在 `~/.dogent/dogent.json` 中定义多个 profile，例如：

```json
{
  "llm_profiles": {
    "deepseek": { ... },
    "glm4.7": { ... },
    "claude-default": { ... }
  },
  "web_profiles": {
    "brave": { ... },
    "google": { ... }
  },
  "image_profiles": {
    "glm-image": { ... }
  }
}
```

在不同项目中通过 `/profile` 命令切换使用。

### 2. 安全提醒
- **永远不要**将 API Key 提交到公开的代码仓库。
- 使用 `~/.dogent/dogent.json` 存储 Key，并确保该文件权限为 `600`（仅用户可读）。
- 定期在平台控制台轮换（Rotate）API Key，特别是发现泄露风险时。

### 3. 故障排查
若配置后无法使用，请检查：
1. API Key 是否复制完整（注意首尾空格）。
2. 网络能否访问对应 API 端点（可尝试 `curl` 测试）。
3. 账号余额或免费额度是否耗尽。
4. Dogent 版本是否为最新（`dogent -v`）。

---

## 总结

通过本指南，你应该已经掌握了：
1. DeepSeek、GLM 4.7、GLM 图像生成、Brave Search 的账号注册与 API Key 申请流程。
2. 如何将各个服务的配置填入 `~/.dogent/dogent.json`。
3. 如何在具体项目中选择和切换不同的 profile。

如需补充其他模型或搜索提供商，可参考上述模板结构自行扩展。更多配置细节请参阅 [08-configuration.md](./08-configuration.md)。