
---

- 命令消减，展示的命令进行合并，- lessions history 折叠
- 用户确认不是失败！！！
- 权限控制?
- 耗时过长的都需要给个进度条提醒 （一旦开始与 LLM 进行交互，让用户在等待，给一个计时器读秒？以及一个活动的提示设计？）

- 如果发现 dogent.md 中的 和 dogent.json 中的不一致，给出提醒？

- def _extract_intro(self, content: str) -> str: 只取前十行？

---

- 测试 dogent 加载正常的 claude 的 commands 和 skill 等配置？
- 修改配置系统，引导进行 profiles 的配置？
- 支持像 claude code 一样，感叹号开头的方式执行本地shell命令
- 解决上下文溢出问题
