---
name: doc-template-creator
description: Create or optimize Dogent document templates in the standard template-skill directory format. Use whenever the user asks to create a new document template, improve an existing template, restructure template metadata, or rewrite template guidance for Dogent's `.dogent/templates`, `~/.dogent/templates`, or built-in `dogent/templates` locations.
---

# Doc Template Creator

Create or optimize Dogent document templates as skill-style directories.

## Scope Rules

- Default to workspace scope: `.dogent/templates/<name>/`.
- Use global scope only when the user explicitly asks for a reusable global template: `~/.dogent/templates/<name>/`.
- Use the built-in package templates under `dogent/templates/<name>/` only when the task explicitly targets a built-in template.

## Required Output Structure

Every template must use this structure:

```text
<template-root>/
├── SKILL.md
├── templates/         # optional but recommended
├── examples/          # optional
└── assets/            # optional
```

- `SKILL.md` must contain YAML frontmatter.
- Put the human-readable summary in YAML frontmatter, especially `name` and `description`.
- Use `SKILL.md` as the human-facing entry point that explains the template's purpose, background, key precautions, and the meaning of the companion files.
- Put reusable output-structure references in `templates/*.md`.
- Put sample outputs in `examples/`.
- Put required multimedia assets in `assets/`, and reference them clearly from `SKILL.md`.
- If the user supplies `@file` references or `@@template` references in the brief, treat them as important source context for designing the new template.

## SKILL.md Rules

- Frontmatter must include:
  - `name`
  - `description`
- Keep the YAML description concise because Dogent uses it for template selection summaries.
- Write `description` as a single-line scalar on the same line as `description:`. Do not place the value on the next line and do not use block-scalar YAML for this field.
- Keep a title and `## Introduction` section for human readers so the entry point clearly communicates purpose, background, and precautions.
- The body after that should contain the real operational guidance because Dogent strips the leading title/introduction block before injecting the template into prompts.
- Add a short section that lists the key files under `templates/`, `examples/`, and `assets/` so readers know how to use them.

## Output Format Example

Use this pattern unless the user has a better reason to vary it:

```markdown
---
name: consultant_proposal
description: Consultant proposal template for project scoping and commercial terms.
---

# Consultant Proposal

## Introduction
- Purpose:
- Background:
- Precautions:

## Writing Requirements
- ...

## Companion Files
- `templates/proposal_structure.md`: ...
- `examples/sample_proposal.md`: ...
```

And the reusable structure file should usually live in:

```text
templates/proposal_structure.md
```

## Create Workflow

1. Infer a stable template key from the user's request.
2. Create the target template directory if missing.
3. Write `SKILL.md` with YAML frontmatter plus the main writing guidance and companion-file references.
4. Add `templates/*.md` for reusable output structures.
5. Add `examples/` and `assets/` only when they add concrete value.
6. Keep the result focused on document-writing behavior rather than generic prompt boilerplate.

## Optimize Workflow

1. Read the existing template files first.
2. Preserve the template key and existing useful structure unless the user asks for a rename or restructure.
3. Improve YAML summary metadata when the current description is weak or missing.
4. Refine the actionable writing guidance in the body and any `templates/`, `examples/`, or `assets/` references.
5. Do not convert the template back into the legacy flat `.md` format.

## Quality Bar

- Keep the YAML summary short and selection-friendly.
- Keep the body operational: audience, usage scenarios, writing rules, output structure, and constraints.
- Avoid duplicating the same guidance in both `SKILL.md` and `templates/`.
- Prefer clear document structure examples when the template has a strong expected output shape.
- When the user gives source files or template references, incorporate them explicitly instead of ignoring them.
