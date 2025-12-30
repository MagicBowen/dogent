# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

User Test Results Status: Pending | Accepted | Rejected

## Release 0.9.5

### Story 0 - Document MCP tools registered
1) Run `dogent` from any workspace.
2) Prompt: `List your tools.`
3) Expect: tools include `mcp__dogent__read_document` and `mcp__dogent__export_document`.

User Test Results: PASS

### Story 1 - Read PDF/DOCX/XLSX @file attachments
1) In `sample/`, place a text-based PDF (`text.pdf`), a DOCX (`sample.docx`), and an XLSX (`sample.xlsx`) with two sheets (Sheet1, Sheet2).
2) Run `dogent` from `sample/`.
3) Prompt: `Please summarize @text.pdf and @sample.docx. Also show the first sheet of @sample.xlsx and Sheet2 via @sample.xlsx#Sheet2.`
4) Expect: CLI shows referenced @file paths only; the agent calls `mcp__dogent__read_document` for each file/sheet.
5) Replace `text.pdf` with a scanned/no-text PDF and prompt again.
6) Expect: CLI warns "Unsupported PDF: no extractable text" and the attachment is marked as failed.

User Test Results: PASS

### Story 2 - Output format resolution
1) In `sample/.dogent/dogent.md`, add a line: `Output Format: docx`.
2) Run `dogent` from `sample/` and ask for a short report with no explicit file name.
3) Expect: model writes Markdown, then calls `mcp__dogent__export_document` to produce DOCX (same stem as the Markdown file).
4) Prompt again with an explicit path, e.g., `Please output as report.pdf`.
5) Expect: prompt overrides dogent.md and `report.pdf` is created.

User Test Results: PASS

### Story 3 - Export to PDF/DOCX with runtime setup
1) From `sample/`, request a PDF output (e.g., `Create a one-page summary and output as summary.pdf`).
2) Expect: if pandoc/chromium are missing, tool call bootstraps them or shows a clear, actionable error.
3) Re-run the same request.
4) Expect: output file is generated without re-downloading dependencies.

User Test Results: PASS

## Release 0.9.6

### Story 0 - Vision profile configuration
1) If `~/.dogent/vision.json` exists, move it aside.
2) Run `dogent` from any workspace.
3) Expect: `~/.dogent/vision.json` is created with a `glm-4.6v` profile stub.
4) In `sample/.dogent/dogent.json`, confirm `vision_profile` exists and can be set to `glm-4.6v`.

User Test Results: PASS

### Story 1 - On-demand vision analysis for @image/@video
1) In `sample/`, add an image file (e.g. `photo.png`) and a short video file (e.g. `clip.mp4`).
2) Update `~/.dogent/vision.json` with a valid GLM-4.6V API key and ensure `sample/.dogent/dogent.json` sets `vision_profile` to `glm-4.6v`.
3) Run `dogent` from `sample/` and prompt: `Summarize @photo.png and @clip.mp4 in a few sentences.`
4) Expect: agent calls `mcp__dogent__analyze_media` for each file and the response includes details that reference the image/video content.
5) Set `vision_profile` to a missing profile name or set `api_key` to `replace-me`.
6) Prompt again with `@photo.png`.
7) Expect: request fails fast with a clear, user-friendly message indicating the vision profile/config is invalid.

User Test Results: PASS
