# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 

---

## Release 0.9.29

### Story 1: Built-in MCP Runtime Alignment
- User Value: As a Dogent user, I can rely on built-in Dogent MCP tools such as document reading and web fetching to execute correctly on the latest Claude Agent SDK / MCP stack.
- Acceptance: Dogent's in-process MCP server registration follows the current low-level MCP request/result contract; built-in Dogent MCP tools can be listed and called successfully through the MCP round-trip path; `mcp__dogent__read_document` and other built-in tools no longer fail before their business logic runs; existing tool names, schemas, and annotations remain intact.
- Dev Status: Done
- Acceptance Status: Accepted (2026-04-05)
- Verification: Automated MCP round-trip tests cover document, UI, web, vision, and image tool families; `python -m unittest discover -s tests -v` passes.

### Story 2: Release Hardening For 0.9.29
- User Value: As a Dogent user, I receive a stable release package whose default repo config does not contain accidental credential-like values and whose automated verification is green.
- Acceptance: Repo default global profile templates use placeholders instead of credential-like values; release docs are updated for the MCP runtime fix; the release is built from a passing unit-test baseline.
- Dev Status: Done
- Acceptance Status: Accepted (2026-04-05)
- Verification: Config tests pass after placeholder cleanup; release notes and tracking docs updated for 0.9.29.

### Story 3: Pre-render Mermaid Blocks In Markdown Export
- User Value: As a Dogent user, when I export Markdown documents containing Mermaid diagrams to PDF or DOCX, the final document shows the rendered diagram instead of raw Mermaid code.
- Acceptance: Markdown-source export/conversion paths run a shared pre-render step for Mermaid fenced blocks before PDF/DOCX generation; the final PDF/DOCX shows rendered diagrams instead of Mermaid source; ordinary non-Mermaid code fences remain regular code text; DOCX export/conversion raises a clear error if Mermaid rendering fails instead of silently emitting raw code; dependency prompts cover Playwright/Chromium when Mermaid pre-rendering is required.
- Dev Status: Done
- Acceptance Status: Accepted (2026-04-24)
- Verification: Automated tests cover Mermaid fence detection/rewrite, shared pre-render invocation across PDF/DOCX Markdown export paths, and content-aware dependency checks for Markdown-source DOCX export; `python -m unittest discover -s tests -v` passes.

---

## Release 0.9.28

### Story 1: Skill-Style Template Catalog
- User Value: As a Dogent user, I can store document templates in the same standard directory structure as skills and still select them from `/init` or `@@`.
- Acceptance: Workspace, global, and built-in templates load from `<template_name>/SKILL.md` directories; descriptions come from YAML frontmatter metadata; prompt-injected template content omits the leading title/introduction block from `SKILL.md`; reusable output-structure references can be loaded from `templates/*.md`; `/init` and `@@` continue to list selectable templates; legacy flat `.md` templates are no longer recognized.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Automated tests cover template discovery, description extraction, prompt assembly, and legacy-format rejection.

### Story 2: Native `/template` Command UX
- User Value: As a Dogent user, I can discover templates and start template workflows from a native `/template` command with behavior consistent with `/profile`.
- Acceptance: `/template` shows the available template inventory; `/template list` shows the same inventory explicitly; typing `/template ` offers `create` and `optimize`; `/template create <free text>` accepts natural-language template requirements directly after the command; `/template optimize` without a template key shows available templates and usage guidance instead of guessing.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Automated tests cover command registration, bare `/template` inventory rendering, `/template create` and `/template optimize` missing-argument behavior, workflow wiring, and completion suggestions.

### Story 3: Built-in Template Creator And Migrated Built-ins
- User Value: As a Dogent user, I can create or optimize templates through a built-in skill-backed workflow, and the shipped templates already follow the new standard format.
- Acceptance: Dogent ships a built-in document-template-creator skill under the Dogent built-in plugin namespace and auto-enables that plugin without requiring `dogent.json` configuration; `/template create` forwards the user’s free-text template brief to that skill; `/template optimize` invokes the same skill with the right target context; built-in templates are rewritten into the new `SKILL.md + templates/examples/assets` format; docs/examples point to the new layout.
- Dev Status: Done
- Acceptance Status: Accepted (2026-03-29)
- Verification: Automated tests cover command-to-agent wiring, built-in plugin installation/default loading, and migrated template availability; docs were updated to the new layout and command flow.
