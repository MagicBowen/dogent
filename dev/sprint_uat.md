# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

---

## Release 0.9.15

### Story 1 – XLSX Multi-Sheet Markdown Export
1) `cd sample`
2) Create a workbook with multiple sheets (example using openpyxl):
   - Run:
     ```
     python - <<'PY'
     from pathlib import Path
     import openpyxl

     root = Path(".")
     docs = root / "docs"
     docs.mkdir(parents=True, exist_ok=True)
     path = docs / "sample.xlsx"

     wb = openpyxl.Workbook()
     ws1 = wb.active
     ws1.title = "SheetOne"
     ws1.append(["ColA", "ColB"])
     for i in range(1, 65):
         ws1.append([f"Row {i}", i])

     ws2 = wb.create_sheet("SheetTwo")
     ws2.append(["Note"])
     for i in range(1, 65):
         ws2.append([f"Note {i}"])

     wb.save(path)
     PY
     ```
3) Run `dogent` and ask: “Read docs/sample.xlsx”.
4) Confirm the output uses `# sample` as the H1 title and includes `## <sheet name>` for each sheet.
5) Confirm there is a blank line between each sheet section.
6) Confirm each sheet section ends with its own truncation note (because of the 50-row cap).
7) Ask: “Convert docs/sample.xlsx to docs/sample.md”. Confirm the output file exists and contains the same H1/H2 structure.

User Test Results: PASS

### Story 2 – Windows Terminal Parity
1) On Windows, `cd sample`.
2) Run `dogent` and trigger a permission prompt (for example, ask it to read a file outside the workspace).
3) Confirm arrow-key selection works and no raw escape sequences appear.
4) Start a long task and press `Esc` to interrupt; confirm it stops cleanly.

User Test Results: Pending

### Story 3 – Full/Lite Packaging for Pandoc + Playwright
1) Set `DOGENT_PACKAGE_MODE=full` and ensure bundled tools exist under `dogent/resources/tools/` for your platform.
2) Run `dogent` and export a Markdown file to DOCX and PDF; confirm no runtime downloads occur.
3) Set `DOGENT_PACKAGE_MODE=lite` and repeat; confirm it uses system/downloaded tools when needed.

User Test Results: Pending
