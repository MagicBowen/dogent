# Design

---

## Release 0.9.12

### Goals
- Require permission for any tool access outside the workspace root, including `~/.dogent`.
- Require permission for any deletion inside the workspace except explicit whitelist entries.
- Require permission for modifying an existing `.dogent/dogent.md` across all write paths.
- Keep the agent session alive while awaiting permission; deny -> abort current task.

### Current Behavior (Summary)
- `should_confirm_tool_use` only guards `Read/Write/Edit` and `Bash/BashOutput`.
- `allowed_roots` includes workspace root and `~/.dogent`, so global access is treated as allowed.
- Delete confirmation uses `rm/rmdir/del` parsing; whitelist supports `.dogent/memory.md`.
- `permission_mode` defaults to `"default"` when a permission callback is supplied.

### Proposed Changes
1) Permission rules
   - Outside workspace:
     - Prompt for any tool that targets paths outside the workspace root.
     - This includes `~/.dogent` (treated as outside), and any absolute/relative path not under root.
     - Applies to file tools (`Read/Write/Edit/NotebookEdit`) and list/read tools (`Ls/ListFiles/Glob/Grep`).
     - Applies to MCP tools with file paths, including `mcp__dogent__read_document`.
   - Deletions inside workspace:
     - Continue prompting for delete commands (`rm/rmdir/del`) inside the workspace,
       except whitelisted paths (e.g. `.dogent/memory.md`).
   - `.dogent/dogent.md` protection:
     - If the file already exists, any modification (Write/Edit/NotebookEdit or Bash redirection)
       must prompt before proceeding.
     - If the file does not exist, creation does not require the special prompt.

2) Tool coverage updates
   - Extend `should_confirm_tool_use` to cover:
     - `Ls`, `ListFiles`, `Glob`, `Grep`
     - `NotebookEdit`
     - MCP document tool `mcp__dogent__read_document`
   - Adjust allowed roots to include only the workspace root for tool checks.

3) Path detection
   - Reuse `_extract_file_path` where possible, and add MCP-specific extraction
     (e.g. `path` for `mcp__dogent__read_document`).
   - For list tools, read `path`/`file_path` inputs if provided; if empty, treat as
     workspace root (no prompt).
   - For Bash commands, keep `rm/rmdir/del` detection and path extraction; extend
     detection to notice redirections to `.dogent/dogent.md` for modification prompts.

4) Permission flow
   - Keep the existing permission prompt mechanism and abort-on-deny logic.
   - Ensure the wait indicator stops during prompt and resumes after; do not disconnect
     the client while awaiting a response.

### Tests to Add/Update
- `tests/test_tool_permissions.py`:
  - Outside access with `Ls/ListFiles/Glob/Grep` requires confirmation.
  - `mcp__dogent__read_document` outside workspace requires confirmation.
  - `~/.dogent` treated as outside (prompt required).
  - Existing `.dogent/dogent.md` write via `Write/Edit/NotebookEdit` requires confirmation.
  - Bash redirection to existing `.dogent/dogent.md` requires confirmation.
  - Creation of `.dogent/dogent.md` when missing does not trigger the special prompt.
