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

## Release 0.9.15

### Story 1: XLSX Multi-Sheet Markdown Export
- User Value: Users can convert entire XLSX files into a single Markdown output without manually listing sheets.
- Acceptance: When `sheet` is omitted, output uses the full filename stem as H1 and includes all sheets in order with H2 sheet titles, blank lines between sheets, and per-sheet truncation notes; when `sheet` is specified, behavior remains single-sheet; `convert_document` supports XLSX -> Markdown.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: `python -m unittest discover -s tests -v`

### Story 2: Windows Terminal Parity
- User Value: Windows users get the same non-blocking input, selection prompts, and escape handling as Unix users.
- Acceptance: Terminal functions use Windows console modes with proper get/set/restore; escape listener works; selection prompts and key handling are stable on Windows.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual Windows CLI run + unit tests (mocked).

### Story 3: Full/Lite Packaging for Pandoc + Playwright
- User Value: Users on poor networks can run conversions without runtime downloads by installing a full package build.
- Acceptance: `DOGENT_PACKAGE_MODE=full` uses bundled pandoc and Playwright Chromium under `dogent/resources/tools/...` without downloading; `lite` retains download-on-demand; missing bundled tools raise clear errors.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Unit tests for path resolution + manual packaging smoke.
