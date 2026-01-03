# Design

---

## Release 0.9.10

### Multiline Markdown editor for prompts and free-form answers
- Default input stays single-line for the main CLI prompt and free-form clarification answers.
- Add Ctrl+E to open a dedicated multiline editor (prompt_toolkit TextArea) for:
  - Main CLI prompt input (pre-filled with current buffer text).
  - Free-form clarification answers (including "Other (free-form answer)" and freeform-only questions).
- Selecting "Other (free-form answer)" in the clarification choice list opens the editor immediately.
- Editor UX:
  - Single editor view with lightweight, real-time Markdown rendering (syntax highlighting only; no layout changes).
  - Full preview toggle with Ctrl+P (read-only; toggle back to edit).
  - Multiline editing with standard prompt_toolkit shortcuts plus GUI-like bindings:
    - Word skip (Alt+Left/Right, Alt+B/F), line start/end (Ctrl+A/E), undo/redo (Ctrl+Z/Y).
    - Select word/line with Ctrl+W/Ctrl+L (footer lists fallback shortcuts).
  - Enter inserts new lines; Ctrl+Enter submits the editor content (fallback Ctrl+J shown in footer).
  - Ctrl+Q returns from the editor (Esc does not exit the editor).
  - Return behavior (dirty only): prompt to Discard / Submit / Save to file / Cancel.
    - Save prompts for a path (relative or absolute) and confirms overwrite when the file exists.
  - Footer shows prominent action labels and shortcut hints.
  - Dark theme with styled headings, code blocks, inline code, math spans, tasks, quotes, and table pipes.
  - Only save-on-return; no explicit save keybinding.
- While the editor is open, pause the Esc interrupt listener (reuse the same guard as selection prompts).
- Non-interactive fallback remains single-line text input with no editor.
