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

## 2026-7-13 PDF Export Rendering Fixes

### Story 1: Render Mermaid SVGs in Exported PDFs
- User Value: Mermaid diagrams exported through `dogent_export_document` appear as
  sharp vector graphics instead of broken-image placeholders.
- Acceptance: Exporting `samples/markdown_with_large_mermaid.md` to PDF shows the
  complete diagram without a broken-image icon or `Mermaid diagram 1` alt text.
- Dev Status: Done
- Acceptance Status: Accepted (2026-07-13)
- Verification: Unit coverage for XML SVG serialization and a real Playwright PDF
  export of the reported sample.

### Story 2: Render Inline and Display Math in Exported PDFs
- User Value: LaTeX formulas wrapped in `$` or `$$` are typeset in PDF output across
  common inline, single-line display, and multiline display layouts.
- Acceptance: Exporting a Markdown sample renders `$...$` inline formulas and
  standard and multiline `$$` formulas as math, while currency and code examples
  remain literal.
- Dev Status: Done
- Acceptance Status: Accepted (2026-07-13)
- Verification: Unit coverage for inline, standard display, single-line display,
  multiline display, escaped-dollar, currency, inline-code, and fenced-code cases
  plus real Playwright PDF exports.
