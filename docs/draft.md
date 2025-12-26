## Release 1.0.0

- 监控 Agent 的工具使用，发现 agent 访问工作路径之外的文件（无论读写），或者删除工作路径之内的文件，需要先与用户确认，用户同意了才能访问
- `DocumentTemplateManager` 类中读取文档模板生成模板概要的函数实现： `def _extract_intro(self, content: str) -> str` 中目前的逻辑是获取 `## Introduction` 的段落内容，但是可能有的模板没有 `## Introduction` 段落，这时可以变为读取其文档前 5 行，以增加鲁棒性；
- 测试 dogent 加载正常的 claude 的 commands 和 skill 等配置？
- 解决上下文溢出问题

