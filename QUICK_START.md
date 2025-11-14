# 快速开始指南

## 1. 环境准备

### 安装依赖
```bash
npm install
```

### 设置环境变量
```bash
export ANTHROPIC_AUTH_TOKEN="your-api-key-here"
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_MODEL="deepseek-reasoner"
```

## 2. 首次使用

### 启动交互模式
```bash
node bin/doc
```

### 创建文档指南
在交互界面中输入：
```
/init
```

这将创建 `.doc-guild.md` 文件，编辑该文件以设置文档参数。

## 3. 撰写第一篇文档

### 简单示例
```
写一篇关于人工智能发展趋势的技术文章
```

### 带文件引用的示例
```
基于 @requirements.md 的要求，设计一个完整的系统架构方案
```

### 复杂文档示例
```
撰写一份关于微服务架构的白皮书，包含：
1. 架构设计原则
2. 技术选型分析
3. 实施案例研究
4. 性能优化策略
```

## 4. 查看进度

系统会自动显示 Todo 列表，实时显示文档撰写进度。

## 5. 查看结果

生成的文档会保存为 Markdown 文件，图片保存在 `./images/` 目录。

## 6. 其他有用命令

- `/config` - 创建本地配置文件
- `/help` - 显示帮助信息
- `/exit` - 退出程序

## 7. 故障排除

如果遇到问题，请检查：
1. 环境变量是否正确设置
2. API 密钥是否有效
3. 网络连接是否正常

更多详细信息请参考 [README.md](./README.md)。