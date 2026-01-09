# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.12

### Story 1: Permission Pipeline Uses `can_use_tool` Only
- User Value: Users get consistent permission gating because tool allow/deny flows run through the permission callback rather than a static allowlist.
- Acceptance: When `can_use_tool` is set, `allowed_tools` is not set in `ClaudeAgentOptions`; the permission callback decides which tools proceed.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Tool Permissions for Outside Access and Deletes
- User Value: Users are prompted before the agent reads/writes outside the workspace or deletes workspace files.
- Acceptance: `Read/Write/Edit` require permission for paths outside workspace (including `~/.dogent`); `rm/rmdir/del/mv` inside workspace always prompt unless the target is whitelisted (e.g. `.dogent/memory.md`).
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: Protect Existing `.dogent` Files
- User Value: Users must approve any modification to existing `.dogent/dogent.md` or `.dogent/dogent.json`.
- Acceptance: If these files exist, tool-based `Write/Edit` and Bash redirections prompt for permission; first-time creation does not prompt.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: CLI Authorization for `.dogent` Updates
- User Value: CLI actions cannot overwrite `.dogent/dogent.md` or `.dogent/dogent.json` without explicit approval.
- Acceptance: CLI writes to existing `.dogent/dogent.md` or `.dogent/dogent.json` prompt for authorization each time and skip updates on denial; first-time creation proceeds without prompts.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 5: Permission Prompt UX Defaults to Yes
- User Value: Permission prompts are fast to approve and do not leak raw escape sequences while selecting.
- Acceptance: Permission prompts default to yes and allow up/down selection when prompt_toolkit is available; text fallback remains when it is not.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual interactive test (CLI).

---

## Release 0.9.13

### Story 1: Resource Layout & Loader Consolidation
- User Value: Configs, templates, and schemas live in predictable locations with a single loader, reducing confusion and duplicate logic.
- Acceptance: `dogent/templates` is renamed to `dogent/resources`; `dogent/resources/doc_templates` content moves to `dogent/templates`; schemas live under `dogent/schema/workspace` and `dogent/schema/global` (same content); `dogent/schemas/clarification.schema.json` moves under `dogent/schema/`; all loads go through one resource loader.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Complex Multi-line Prompts Externalized
- User Value: Prompts are easier to audit and update without touching code.
- Acceptance: Only complex multi-line prompts are moved into `dogent/prompts/` files with content unchanged; short prompts stay inline; runtime loads via the centralized loader.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 3: CLI Module Split
- User Value: The CLI codebase is easier to maintain and extend without cross-cutting edits.
- Acceptance: `dogent/cli.py` and related CLI helpers are split into the `dogent/cli/` package per the design; CLI behavior remains unchanged; imports/tests updated.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 4: Agent/Config/Core/Feature Modules Split
- User Value: Core services and feature modules are clearly separated, reducing coupling and duplication.
- Acceptance: `dogent/agent`, `dogent/config`, `dogent/core`, and `dogent/features` packages are created per the design; public entrypoints remain stable; tests updated.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 5: Panels + English Documentation Refresh
- User Value: Users see a concise startup panel, an expanded help panel, and complete English documentation.
- Acceptance: Startup panel is minimal; help panel documents end-to-end usage; `docs/dogent_design.md` added with mermaid diagrams; `docs/usage.md` rewritten in English with step-by-step examples.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual review of panels/docs.

---

## Release 0.9.14

### Story 1: DOCX Export Embeds Markdown Images
- User Value: Users get DOCX exports that include all local images referenced in Markdown or HTML.
- Acceptance: Markdown and HTML image references (relative or absolute local paths) appear in the DOCX output; width/height/style attributes are preserved where possible; code blocks and tables render correctly with a syntax-highlighted theme; conversion uses a normalized Markdown copy and proper resource paths.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Startup Panel Simplified + Markdown Help Panel
- User Value: Startup UI is concise while help remains comprehensive and readable.
- Acceptance: Startup panel shows name/version, model/profile info, and 1-2 key reminders only; `/help` renders Markdown directly in the normal CLI panel.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual CLI review.

### Story 3: English End-to-End Usage Guide
- User Value: New users can install, configure, and use Dogent with step-by-step examples.
- Acceptance: `docs/usage.md` is fully rewritten in English with end-to-end flow (install -> configure -> run -> tools/templates -> permissions -> troubleshooting) and includes examples.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Doc review.
