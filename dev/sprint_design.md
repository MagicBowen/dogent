# Design

---

## Release 0.9.23

### Goal
- Add @ file and @@ doc template dropdown completion in the multiline markdown editor.
- Keep completion behavior aligned with single-line input.
- Preserve literal @/@@ when nothing is selected.

### Current Baseline
- Single-line prompt uses `DogentCompleter` for `@` file and `@@` template suggestions.
- Multiline editor uses `TextArea` without a completer.
- File references are resolved on submission via `FileReferenceResolver` and template override parsing.

### UX + Behavior
- Typing `@` in the editor shows file/path suggestions relative to the workspace root.
- Typing `@@` shows template suggestions, including `general`, workspace, global, and built-in templates.
- Directory entries appear with a trailing `/` and can be completed to navigate deeper (same as single-line).
- If a completion menu is open, pressing Enter accepts the current suggestion.
- If no completion is selected, Enter inserts a newline and the literal `@`/`@@` stays in the text.
- Completions are enabled in all editor contexts: prompt, clarification, and file edit.

### Implementation Plan
- Reuse `DogentCompleter` for the editor `TextArea`:
  - `root=self.root`
  - `template_provider=self.doc_templates.list_display_names`
  - `commands` can be the existing registry list (safe) or an empty list (to avoid `/` suggestions).
  - `complete_while_typing=True`
- Add an editor key binding for Enter in `_open_multiline_editor`:
  - If `buffer.complete_state.current_completion` exists, apply it and return.
  - Otherwise insert a newline (`buffer.insert_text("\n")`) and keep existing editor behavior.
  - Scope the binding to `edit_active & editor_focus` so overlays and preview mode are unaffected.
- Do not change file/template resolution logic; completion only affects text insertion.

### Edge Cases + Notes
- `@@` completions should not fall through to file completion when template completions are available.
- Completion acceptance should not submit the editor (submission remains Ctrl+Enter or vi :wq).
- Text is only modified on explicit completion acceptance, satisfying the "treat @/@@ as normal characters" rule.

### Tests
- Add a unit test that simulates a buffer with completion state and verifies Enter applies the completion.
- Add a unit test that verifies Enter inserts a newline when no completion is active.
- Skip tests if prompt_toolkit is unavailable (consistent with existing optional dependency handling).
