## issues

claude code 比 n8n 等流编排的好处？

让 code review agent 等都好做了...

claude code 不如 agent sdk的不足：
- system prompt 不能定制
- Agent loop 不能定制：例如 打断，打断的处理...
- 交互方式不能定制：如 写作体验，问题追问，快捷键...
- 与其它能力的内置集成：image，pdf
- 国内限制：web search...
- 国内模型调优：deepseek，glm...

---

每次都要拷贝
prompt 要重写，没有积累
模板不能共享
在线搜索，图片理解，PDF（模板配置）和docx阅读与生成

claude code 的写作风格（system prompt）

更易用编辑和输入的 CLI 交互体验

调试 deepseek 和 glm

## Dogent purpose

## vibe writing

## Procedure

1 ~ 2000:
2000 ~ 10000: 
- process

> 10000: design

当规模变大，很多不一致性就会出现，人需要决策。而决策是复杂的，需要考虑未来的可能，LLM可以提示，合作，但是LLM对未来的真实演变没有人耦敏感度和话语权的。所以还是得人来决策。这时人的决策质量就很重要，当决策在未来证明是失败的，影响范围也很重要；

当规模变大，故障也越来越难解决，可观测性设计很重要（设计了日志和异常处理应对，让模型分析）

将软件解耦为 《 10000 行的小模块，独立 vibe 完成! 减少 IDE，完全 vibe

