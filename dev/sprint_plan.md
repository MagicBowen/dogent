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

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted
 
## Release 0.9.5

### Story 0: Document MCP tools registered
- User Value: Document read/export capabilities are exposed as MCP tools for Claude Agent SDK.
- Acceptance: `mcp__dogent__read_document` and `mcp__dogent__export_document` are registered and visible; tools operate within workspace boundaries.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual prompt "list your tools" and unit tests for tool handlers.

### Story 1: Read PDF/DOCX/XLSX @file attachments
- User Value: User can reference .pdf/.docx/.xlsx and the agent reads usable text.
- Acceptance: @file references are listed without content; the agent calls `mcp__dogent__read_document` to read PDFs/DOCX/XLSX (first sheet by default, named sheet supported). Scanned PDFs return a clear tool error.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Unit tests for readers + manual check in `sample/`.

### Story 2: Output format resolution
- User Value: User can request output format in prompt or in `.dogent/dogent.md`.
- Acceptance: Prompt or `.dogent/dogent.md` informs the LLM to write Markdown and call `mcp__dogent__export_document` for pdf/docx output.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual prompt/dogent.md checks with tool calls.

### Story 3: Export to PDF/DOCX with runtime setup
- User Value: Generated Markdown is exported to PDF or DOCX with minimal setup.
- Acceptance: Pandoc/Chromium auto-download on first use via MCP tool; conversion errors are surfaced with actionable messages; output file is created at the requested path or derived from the Markdown file name.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Unit tests with mocks + manual export in `sample/`.
