# Design


## Release 0.9.28

### Goal

Refactor Dogent document templates from the current single-file Markdown format into a standard skill-style directory format, remove legacy-format compatibility, preserve `/init` and `@@` template selection through dropdown completion, and add a native `/template` command that can list templates and trigger built-in create/optimize flows.

### Current Baseline

- Document templates are currently loaded from flat Markdown files:
  - workspace: `.dogent/templates/<name>.md`
  - global: `~/.dogent/templates/<name>.md`
  - built-in: `dogent/templates/<name>.md`
- `DocumentTemplateManager` only understands single `.md` files and extracts introductions from inline `## Introduction` sections.
- `/init` and `@@` already use template completion, but they depend on the flat-file loader.
- Dogent auto-enables its built-in Dogent plugin under `~/.dogent/plugins/dogent`, and native CLI commands can invoke agent runs directly.
- `/profile` already establishes the desired command UX pattern:
  - `/profile` with no subcommand shows an overview instead of failing.
  - `/profile <target>` with no value shows available options for that target.
  - command completion proposes target values after the user types `/profile `.

### Template Format Design

- The only supported document-template format after this release is a skill-style directory:
  - workspace: `.dogent/templates/<template_name>/SKILL.md`
  - global: `~/.dogent/templates/<template_name>/SKILL.md`
  - built-in: `dogent/templates/<template_name>/SKILL.md`
- Legacy flat files such as `.dogent/templates/resume.md` are not loaded, not listed, and not migrated automatically.
- Each template directory must contain `SKILL.md`. Companion files should follow the new layout:
  - `templates/`: reusable output-structure references
  - `examples/`: sample outputs
  - `assets/`: multimedia assets when needed
- Built-in templates will be rewritten into the same directory-based format so workspace/global/built-in templates follow one consistent mental model.

### Template Content Assembly

- `DocumentTemplateManager` should treat a template as a directory resource rather than a single file.
- The template display name continues to use existing source prefixes:
  - workspace: `resume`
  - global: `global:resume`
  - built-in: `built-in:resume`
- Template introduction/description for lists, `/init`, and `@@` completion should come from the head YAML frontmatter in `SKILL.md`, using `description` as the primary field.
- When Dogent injects template guidance into prompts, it should build a normalized template text block from:
  - `SKILL.md`, with the title/introduction block removed before prompt injection
  - optional Markdown reference files under `templates/`, appended in deterministic sorted order
- `SKILL.md` acts as the human-facing entry point and should describe the template purpose, background, precautions, and companion files.
- If `SKILL.md` contains an explicit `## Introduction` section, Dogent should omit that section from the injected template body because the summary already comes from YAML metadata.
- If no `## Introduction` section exists, Dogent may trim the leading boilerplate lines from the top of `SKILL.md` before injecting the body so the prompt focuses on actionable template rules.
- This keeps the authoring format aligned with skills while still letting document templates split summary metadata, usage scenarios, output format, and other instructions into separate files.

### `/init` and `@@` Selection Behavior

- `/init` template completion must continue to show all available template keys from workspace, global, and built-in sources.
- `@@<template>` completion must continue to work for inline prompt overrides.
- The init wizard template overview should describe templates using the new metadata extraction logic so standard skill-style templates remain selectable without special casing.
- General/default template behavior remains unchanged from a user perspective, but the built-in general template also moves to the new directory format.

### Native `/template` Command Design

- Add a native built-in `/template` command.
- Command intent:
  - `/template` with no subcommand shows the available templates, equivalent to `/template list`.
  - typing `/template ` should offer dropdown completion entries for `create` and `optimize`, matching the discoverability pattern the user requested.
  - `/template list` shows all available templates grouped by source with one-line descriptions.
  - `/template optimize` with no template key should show the available templates and usage guidance, similar to `/profile <target>` showing options when the value is missing.
- Expected subcommands:
  - `list`
  - `create`
  - `optimize`
- `create` and `optimize` are the primary interactive workflows; `list` exists mainly as an explicit equivalent to bare `/template`.

### `/template` Workflow Behavior

- `/template create <brief>` should run an agent task that explicitly asks the model to use the built-in document-template-creator skill and create a new template in workspace scope unless the user says otherwise.
- The free text after `/template create` is the authoritative creation brief and may contain template purpose, audience, structure, language, style, and other related requirements in one natural-language string.
- `/template create` with no brief should show usage guidance or prompt for the missing request in interactive mode rather than silently doing nothing.
- `/template optimize <template-key> <brief>` should run an agent task that explicitly asks the model to use the built-in document-template-creator skill to refine the named template.
- `/template optimize <template-key>` should still be valid and ask the skill to improve the template using the template’s existing content as the baseline.
- `/template optimize` with no template key should show the available templates and usage guidance instead of guessing a target.
- The command should reuse existing confirmation/update patterns when the agent proposes edits under `.dogent/templates/`.

### Built-in Skill Design

- Add a built-in Claude skill dedicated to document-template authoring and optimization.
- Suggested packaged location:
  - `dogent/plugins/dogent/skills/doc-template-creator/`
- The skill should:
  - generate templates in the new skill-style directory layout
  - explain where to place introduction, usage scenarios, output format, and supporting material
  - support both create and optimize requests
  - prefer workspace templates by default unless the user requests global scope
- The native `/template` command should be a thin UX wrapper around this skill rather than reimplementing template-authoring logic inside the CLI.

### Implementation Direction

- Update template discovery and resolution code to scan template directories with `SKILL.md` instead of flat `.md` files.
- Update built-in resource loading helpers to support directory-based template resources.
- Rewrite shipped templates (`general`, `resume`, `research_report`, `technical_blog`) into directory-based resources.
- Add `/template` command registration, handler logic, help text, and command completion support.
- Reuse the existing command/completion style used by `/profile` so blank-command and missing-argument behaviors stay predictable.
- Ensure docs and examples are updated from `<name>.md` paths to `<name>/SKILL.md` paths wherever they describe template authoring.

### Edge Cases

- If a template directory exists without `SKILL.md`, it should be ignored and should not appear in completion.
- If multiple reference files exist, ordering must be deterministic so generated prompts are stable for tests.
- If `SKILL.md` frontmatter is malformed, Dogent should skip description extraction gracefully instead of trying to recover summary text from the body.
- If a user keeps old `<name>.md` files after upgrading, Dogent should not silently load them, because this release explicitly drops compatibility.
- `/template optimize` must reject unknown template keys with an option list instead of starting a vague agent task.

### Tests

- Add unit tests for directory-based template listing, YAML description extraction, prompt-content assembly, introduction stripping, and prefix resolution across workspace/global/built-in sources.
- Add tests that legacy flat `.md` templates are ignored.
- Add CLI completion tests for `/template ` and any subsequent argument completion rules.
- Add CLI command tests for:
  - `/template`
  - `/template list`
  - `/template optimize` with missing template key
  - `/template create ...`
- Add CLI command tests confirming `/template create <free text>` preserves the full free-text brief when building the agent request.
- Update existing `/init` and template-override tests to use the new directory-based fixtures.
