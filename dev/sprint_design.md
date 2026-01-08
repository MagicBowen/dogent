# Design

---

## Release 0.9.12

### Goals
- Require permission for tool access outside the workspace root (including `~/.dogent`) for `Read/Write/Edit`.
- Require permission for any deletion inside the workspace except explicit whitelist entries.
- Require permission for modifying existing `.dogent/dogent.md` and `.dogent/dogent.json` across all write paths (tool and CLI).
- Keep the agent session alive while awaiting permission; deny -> abort current task.

### Current Behavior (Summary)
- `should_confirm_tool_use` only guards `Read/Write/Edit` and `Bash/BashOutput`.
- `allowed_roots` includes workspace root and `~/.dogent`, so global access is treated as allowed.
- Delete confirmation uses `rm/rmdir/del` parsing; whitelist supports `.dogent/memory.md`.
- `permission_mode` defaults to `"default"` when a permission callback is supplied.
- CLI writes to `.dogent/dogent.md` and `.dogent/dogent.json` happen without a permission prompt.

### Proposed Changes
1) Permission rules (tool-driven)
   - Outside workspace:
     - Prompt for `Read/Write/Edit` when target path is outside workspace root.
     - This includes `~/.dogent` (treated as outside), and any absolute/relative path not under root.
   - Deletions inside workspace:
     - Continue prompting for delete commands (`rm/rmdir/del/mv`) inside the workspace,
       except whitelisted paths (e.g. `.dogent/memory.md`).
   - `.dogent/dogent.md` / `.dogent/dogent.json` protection:
     - If the file already exists, any modification (Write/Edit or Bash redirection)
       must prompt before proceeding.
     - First creation does not require the special prompt.

2) Tool coverage updates
   - Keep `should_confirm_tool_use` scoped to `Read/Write/Edit` and `Bash/BashOutput`.
   - Treat `~/.dogent` as outside by limiting allowed roots to workspace only.

3) Path detection
   - Reuse `_extract_file_path` for `Read/Write/Edit` tool inputs.
   - For Bash commands, keep `rm/rmdir/del` parsing and add `mv`.
   - Extend detection to notice redirections to existing `.dogent/dogent.md` /
     `.dogent/dogent.json` for modification prompts.

4) Permission flow
   - Keep the existing permission prompt mechanism and abort-on-deny logic.
   - Ensure the wait indicator stops during prompt and resumes after; do not disconnect
     the client while awaiting a response.
   - When `can_use_tool` is set, do not set `allowed_tools`. Allowlist decisions live
     inside `can_use_tool` (return `PermissionResultAllow` for always-allowed tools).
   - Keep the text prompt fallback for non-TTY/non-prompt_toolkit environments.
   - Use the existing "Aborted" panel/status on denial.

5) CLI-initiated file updates
   - Before overwriting existing `.dogent/dogent.md` or `.dogent/dogent.json`,
     prompt for authorization using the same yes/no UI.
   - First-time creation does not require authorization.

### Tests to Add/Update
- `tests/test_tool_permissions.py`:
  - `~/.dogent` treated as outside (prompt required).
  - Existing `.dogent/dogent.md` / `.dogent/dogent.json` write via `Write/Edit` requires confirmation.
  - Bash redirection to existing `.dogent/dogent.md` requires confirmation.
  - Bash `mv` delete-like operations prompt for confirmation when inside workspace.
  - Creation of `.dogent/dogent.md` / `.dogent/dogent.json` when missing does not trigger the special prompt.

- `tests/test_cli_permissions.py` (new):
  - Overwriting existing `.dogent/dogent.md` via `/init` or editor path prompts for approval.
  - Updating `.dogent/dogent.json` via CLI toggles prompts for approval.
  - First-time creation of `.dogent/dogent.md` / `.dogent/dogent.json` does not prompt.
