# Design

---

## Release 0.9.15

### Goals
- XLSX to Markdown: if no sheet is specified, include all sheets in one Markdown output with H1/H2 structure and per-sheet truncation notes.
- Windows terminal parity: ensure non-blocking input, selection prompts, and escape handling work on Windows without termios.
- Packaging modes: support "lite" (download-on-demand) and "full" (bundled pandoc + Playwright/Chromium) builds.

### Current Behavior (Summary)
- `_read_xlsx` reads only one sheet: the requested sheet or the first sheet.
- `dogent/cli/terminal.py` has Windows stubs but does not manage console modes; escape listener expects termios-like behavior.
- PDF/DOCX conversion tooling downloads pandoc/Chromium at runtime if missing.

### Proposed Changes
1) XLSX multi-sheet Markdown rendering
   - Keep current behavior when `sheet` is specified (single-sheet only).
   - When `sheet` is omitted:
     - Use the full filename stem (e.g., `report.v2.xlsx` -> `report.v2`) as the H1 title.
     - Iterate `workbook.sheetnames` in order.
     - For each sheet, emit:
       - `## <sheet name>`
       - The Markdown table (or `(empty sheet)`), followed by a truncation note if that sheet was capped.
     - Insert a blank line between sheet sections.
   - Metadata:
     - For multi-sheet reads, include `sheets` list and per-sheet metadata (rows/cols/truncated).
     - For single-sheet reads, keep current `sheet` + rows/cols metadata.
   - Update `dogent/prompts/system.md`: when no sheet is specified, read all sheets (not just the first).

2) Windows terminal parity
   - Implement Windows console mode handling in `dogent/cli/terminal.py`:
     - Use `ctypes` + `kernel32.GetConsoleMode/SetConsoleMode` to capture and restore console modes.
     - `tcgetattr` returns a settings object containing the original mode.
     - `setcbreak` disables line input/echo/processed input to allow immediate key reads.
     - `tcsetattr` restores the saved mode.
     - `kbhit/getch` remain `msvcrt`-based (prefer `getwch` for Unicode).
   - Ensure all low-level terminal usage remains centralized through `dogent/cli/terminal.py`.
   - Validate selection prompts and escape listener behavior on Windows.

3) Packaging mode: lite vs full
   - Add a build-time packaging mode indicator (e.g., `DOGENT_PACKAGE_MODE=full|lite`).
   - Full mode bundles:
     - Pandoc binaries
     - Playwright Chromium browser assets
     - Under `dogent/resources/tools/<tool>/<platform>/...`
   - Add resolver helpers in `dogent/features/document_io.py`:
     - `_resolve_pandoc_binary()` returns bundled pandoc in full mode, otherwise system/`pypandoc`.
     - `_resolve_playwright_browser_path()` points Playwright to bundled Chromium in full mode.
   - `*_ensure_*` helpers:
     - Full mode uses bundled assets and skips downloads.
     - Lite mode retains current download-on-demand behavior.
   - Update packaging config (`pyproject.toml`) to include `dogent/resources/tools/**`.

### Tests to Add/Update
- `tests/test_document_io.py`:
  - Multi-sheet XLSX produces H1 + H2 structure, blank lines between sheets, and per-sheet truncation notes.
  - When `sheet` is specified, output remains single-sheet.
  - Metadata includes `sheets` + per-sheet rows/cols/truncated for multi-sheet reads.
- Add platform-guarded tests for terminal helpers (mock `msvcrt` and `ctypes` to validate Windows-path code without requiring Windows).
- Add tests for packaging mode resolution helpers (full vs lite) using environment patching and temp bundled paths.
