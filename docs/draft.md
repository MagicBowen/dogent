- 把失败记录存到 history 中，重复的失败不要再犯。
- 更多的写作技巧模板，可以加载？（例如对于长文的更专业的写作技巧，可以独立出去？）
- 将不同类型文章的技巧，从 system prompt 和 dogent md 文件中移动出去，变成动态加载？
- 指定加载模板？？？
- 测试 dogent 加载正常的 claude 的 commands 和 skill 等配置？
- 修改配置系统，引导进行 profiles 的配置？
- 权限控制?



---

  ## Option A — Manual /learn command (low risk, high control)

  - Add /learn (and /lessons) commands.
  - /learn asks you to enter:
      - mistake (what went wrong)
      - correct approach (what to do instead)
      - optional tags/scope (project vs global)
  - Persist to .dogent/lessons.jsonl (or .dogent/lessons.md), show IDs, allow /unlearn <id>.
  - Prompt injection: include “Relevant Lessons” block (top N by keyword match on your current request + last failure
    context).

  Pros: explicit, minimal false positives. Cons: you must remember to run /learn.

  ## Option B — Post-failure “save lesson?” prompt (best UX for your workflow)

  - When a task ends with error or you interrupt with Esc, Dogent shows the summary and then asks:
      - “Save a lesson from this? (y/N)”
      - If yes, it opens a short guided input (mistake + fix).
  - Optionally pre-fill with last error text + last user correction message (you can edit before saving).
  - Same storage + injection as Option A.

  Pros: captures lessons at the moment you notice them. Cons: slightly more CLI prompts.