# Original Requirements

---

## Release 0.9.12

- Bugfix: The current permission management is ineffective. When the agent accesses files outside the workspace and deletes files within the workspace (those not in the whitelist), there is no option to prompt the user for confirmation; instead, the operations are performed directly. The reason is when you set `can_use_tool` in `ClaudeAgentOptions` then should not set the `allowed_tools`. 
- If the agent needs to update the existing `.dogent/dogent.md` and `.dogent/dogent.json` during the execution of a task, it must request user authorization each time and can only proceed with the update after obtaining the user's consent; otherwise, it must not update the file.
- To reiterate the permission management requirements: 1) Accessing any files outside the workspace (reading/writing) requires user authorization; 2) Deleting files within the workspace requires user authorization (except for files on the whitelist, such as `.dogent/memory.md`); 3) Modifying or overwriting an existing `.dogent/dogent.md` requires user authorization; During the process of waiting for user authorization, the agent client's loop must not exit. If the user authorizes the file operation, continue to complete subsequent tasks; if the user does not agree, the current task is considered abandoned (Abort).

---

## Pending Requirements

- Dogent supports more excellent file templates (technical blog);
- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Provide a good solution for model context overflow;
- Dogent supports the ability to generate images;
