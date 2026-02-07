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

---

## Release 0.9.24

### Goal
- Ship a built-in Claude plugin that wraps the PPTX skill under `dogent/plugins/claude`.
- Auto-install all built-in plugins to `~/.dogent/plugins` on startup (overwrite/update).
- New workspace configs include the built-in Claude plugin path by default; existing projects remain unchanged unless edited.

### Current Baseline
- Claude plugins are loaded from `.dogent/dogent.json` via `claude_plugins`; defaults are empty.
- Plugin roots must contain `.claude-plugin/plugin.json`.
- Startup bootstrap creates `~/.dogent` config/schema files but does not install plugins.

### Plugin Layout (Package)
- Plugin root: `dogent/plugins/claude`.
- Manifest: `dogent/plugins/claude/.claude-plugin/plugin.json` (name `claude`, version, description).
- Skills: `dogent/plugins/claude/skills/pptx` (copied from `claude/skills/skills/pptx`, including SKILL.md, scripts, ooxml, and LICENSE.txt).
- Follow Claude plugin structure (see `claude/examples/plugins`) so SDK loads skills correctly.

### Install Flow (Startup)
- Add `DogentPaths.global_plugins_dir` -> `~/.dogent/plugins`.
- Implement `ConfigManager._install_builtin_plugins()` and call it from `_ensure_home_bootstrap()` after `~/.dogent` exists.
- Source: `importlib.resources.files("dogent") / "plugins"` (skip if missing).
- For each directory under source, copy to `~/.dogent/plugins/<name>` with `shutil.copytree(..., dirs_exist_ok=True)` to overwrite/update.
- On permission errors, warn and continue (do not block CLI startup).

### Default Config Behavior
- Update `dogent/resources/dogent_global_default.json`:
  - `workspace_defaults.claude_plugins = ["~/.dogent/plugins/claude"]`.
- Ensure existing projects are not auto-updated:
  - If `.dogent/dogent.json` exists and lacks `claude_plugins`, treat it as an explicit empty list so global defaults do not inject the built-in plugin.
  - New workspaces created via `create_config_template()` inherit the default plugin path.

### Packaging
- Add `plugins/**` to `tool.setuptools.package-data` for the `dogent` package so built-in plugins ship with the distribution.

### Docs
- Update `docs/07-commands.md` and `docs/10-claude-compatibility.md`:
  - Mention built-in plugins are installed to `~/.dogent/plugins`.
  - Note only the built-in Claude plugin is included in default `claude_plugins`; others require manual addition.

### Tests
- Add a unit test for config behavior:
  - New workspace config includes `~/.dogent/plugins/claude`.
  - Existing workspace config without `claude_plugins` yields an empty list.
- Add a unit test for builtin plugin install (helper takes a source dir in tests, copies into a temp `~/.dogent/plugins`).
