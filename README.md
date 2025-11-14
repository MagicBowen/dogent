# Document Writing Agent

一个基于 Claude Agent SDK 的专业文档撰写 AI 代理，支持交互式 CLI 界面，可以生成长篇专业文档。

## 功能特性

### 🤖 核心功能
- **交互式 CLI**: 类似 Claude Code 的交互体验
- **智能文档撰写**: 支持多种文档类型和格式
- **研究集成**: 自动进行网络研究和资料收集
- **图像管理**: 下载和管理文档相关图片
- **引用管理**: 自动生成和格式化引用
- **质量验证**: 事实核查和文档质量检查
- **记忆系统**: 临时笔记和思考记录

### 📁 Claude Code 风格支持
- **@ 文件引用**: 使用 @ 符号引用本地文件，支持自动补全
- **.claude 目录**: 支持 agents、commands、skills、mcp 工具配置
- **命令系统**: `/init`、`/config`、`/exit` 等命令
- **Todo 显示**: 实时显示代理的工作计划和进度

### 🌐 多 AI 供应商支持
- **Anthropic Claude**: 官方 Claude API
- **DeepSeek**: 支持推理模型和快速模型
- **GLM (智谱清言)**: 国产大模型支持
- **KIMI (月之暗面)**: 月之暗面模型支持
- **本地 API**: 支持本地部署的模型

## 安装

### 环境要求
- Node.js 18.0.0 或更高版本
- npm 或 yarn

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd doc_agent
```

2. **安装依赖**
```bash
npm install
```

3. **全局安装（可选）**
```bash
npm install -g .
```

### 🔧 代码更新后手动重新部署

如果您修改了代码库中的文件，需要手动重新部署最新的版本：

```bash
# 1. 进入项目目录
cd /path/to/doc-agent

# 2. 卸载旧版本
npm uninstall -g doc-agent

# 3. 安装最新版本
npm install -g .

# 4. 验证安装
doc --version
doc --help
```

**注意**:
- 每次修改 `src/` 目录下的代码后都需要重新安装
- 修改配置文件或文档不需要重新安装
- 确保使用 Node.js 18+ 版本

## 配置

### 环境变量配置
设置以下环境变量：

```bash
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="your-api-key-here"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

### 本地配置文件
在项目目录中运行 `/config` 命令创建本地配置文件：

```bash
doc
# 进入交互模式后输入
/config
```

这将创建 `.doc-agent.json` 配置文件。配置文件中的敏感信息（如 API 密钥）默认使用环境变量引用，因此是安全的。

## 使用方法

### 启动交互模式
```bash
doc
```

### 基本命令

#### `/init` - 创建文档指南
创建 `.doc-guild.md` 模板文件，定义文档类型、长度、语气等：

```
/init
```

#### `/config` - 创建本地配置
生成本地配置文件：

```
/config
```

#### `/help` - 显示帮助
显示所有可用命令和功能：

```
/help
```

#### `/exit` - 退出程序
退出交互模式：

```
/exit
```

### 文件引用
使用 `@` 符号引用本地文件，支持 Tab 自动补全：

```
编写一个基于 @requirements.md 的实现计划文档
```

### 自然语言请求
直接使用自然语言描述你的文档需求：

```
写一篇关于机器学习的技术博客，包含代码示例和最佳实践
```

## 文档撰写工作流程

### 1. 初始化项目
```bash
doc
/init  # 创建文档指南
```

### 2. 配置文档参数
编辑 `.doc-guild.md` 文件，设置：
- 文档类型 (blog_post, technical_article, research_paper 等)
- 目标长度 (short, medium, long)
- 语气风格 (professional, casual, academic 等)
- 输出格式 (markdown, html, pdf)
- 语言 (zh-CN, en 等)

### 3. 撰写文档
```
写一篇关于云计算架构的技术文章，包含实际案例和性能对比
```

### 4. 监控进度
系统会自动显示 Todo 列表，显示当前进度：
- ✅ 分析文档需求和指南
- ⏳ 研究主题和收集信息
- ⏳ 创建文档大纲和结构
- ⏳ 逐节撰写文档内容
- ⏳ 下载和插入相关图片
- ⏳ 添加引用和参考资料
- ⏳ 验证事实和检查一致性
- ⏳ 润色和完善语言
- ⏳ 最终审查和格式化

## 项目结构

```
doc_agent/
├── bin/
│   └── doc                    # CLI 入口点
├── src/
│   ├── interactive/
│   │   └── session.js         # 交互会话管理器
│   ├── agent/
│   │   └── document-agent.js  # 文档撰写代理
│   ├── config/
│   │   └── config-manager.js  # 配置管理器
│   ├── research/
│   │   └── web-researcher.js   # 网络研究模块
│   ├── media/
│   │   └── image-manager.js   # 图像管理模块
│   ├── citation/
│   │   └── citation-manager.js # 引用管理模块
│   ├── validation/
│   │   └── document-validator.js # 文档验证模块
│   ├── memory/
│   │   └── memory-manager.js  # 记忆管理模块
│   └── utils/
│       └── file-utils.js      # 文件工具模块
├── test/
│   └── test-system.js         # 系统测试脚本
├── images/                    # 生成的图片存储目录
├── .memory.md                 # 临时笔记和思考
├── .doc-guild.md              # 文档撰写指南
├── .doc-agent.json           # 本地配置文件
└── README.md                  # 本文档
```

## 高级功能

### .claude 目录支持
支持 Claude Code 风格的自定义配置：

```
.claude/
├── agents/     # 自定义代理
├── commands/   # 自定义命令
├── skills/     # 自定义技能
└── mcp/        # MCP 工具配置
```

### 记忆系统
- **自动记录**: 代理会自动将临时想法和关键要点记录到 `.memory.md`
- **分类管理**: 支持研究笔记、想法、任务等分类
- **搜索功能**: 可以搜索和检索历史记录

### 引用管理
- **多种格式**: 支持 APA、MLA、Chicago、IEEE、Harvard 等引用格式
- **自动提取**: 从 URL 和文本自动提取引用信息
- **验证功能**: 验证引用的准确性和完整性

### 图像管理
- **自动下载**: 根据描述自动下载相关图片
- **格式支持**: 支持多种图片格式
- **优化处理**: 自动优化图片大小和质量

## 测试

运行系统测试：

```bash
npm test
```

或直接运行测试脚本：

```bash
node test/test-system.js
```

## 故障排除

### 常见问题

1. **配置错误**
   - 确保环境变量设置正确
   - 检查 `.doc-agent.json` 配置文件格式

2. **API 连接失败**
   - 验证 API 密钥是否正确
   - 检查网络连接和 API 端点

3. **文件权限问题**
   - 确保有读写当前目录的权限
   - 检查环境变量配置

### 调试模式

设置详细日志输出：

```bash
export DEBUG=doc-agent:*
doc
```

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

### 开发环境设置

1. Fork 项目
2. 创建功能分支
3. 安装依赖：`npm install`
4. 运行测试：`npm test`
5. 提交更改

## 许可证

MIT License

## 更新日志

### v1.0.0
- 初始版本发布
- 支持交互式文档撰写
- 集成多种 AI 供应商
- 完整的引用和图像管理系统
- 质量验证和事实核查功能

---

**Document Writing Agent** - 让专业文档撰写变得简单高效！