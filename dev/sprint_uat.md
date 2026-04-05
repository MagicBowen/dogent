# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Accepted (2026-02-03)
```

---

## Release 0.9.29

### Story 1 – Built-in MCP Runtime Alignment
1. Start `dogent` in a sample workspace that contains a Markdown file such as `sample.md`.
2. Ask Dogent to summarize `@sample.md`.
3. Expect Dogent to call `mcp__dogent__read_document` successfully instead of failing immediately with an MCP tool error before file reading happens.
4. With a configured Dogent web profile, ask Dogent to fetch or summarize a simple web page.
5. Expect Dogent to use the built-in Dogent web MCP path successfully instead of failing immediately with an MCP tool error before the fetch logic runs.
6. Optionally trigger another built-in Dogent MCP tool that is available in the current workspace configuration, such as the UI, vision, or image tool path, and confirm the tool either succeeds or returns a normal tool-level validation/business error rather than a broken MCP transport/runtime error.

User Test Results: Accepted (2026-04-05)

### Story 2 – Release Hardening For 0.9.29
1. Review the repo default global config template under `dogent/resources/dogent_global_default.json`.
2. Confirm shipped profile tokens are placeholders such as `replace-me`, not credential-like values.
3. Run `python -m unittest discover -s tests -v`.
4. Expect the full unit-test suite to pass before packaging the release.

User Test Results: Accepted (2026-04-05)

---

## Release 0.9.28

### Story 1 – Skill-Style Template Catalog
1. In a sample workspace, create `.dogent/templates/product_brief/SKILL.md` with frontmatter `name` and `description`, plus a small body. Also create `.dogent/templates/product_brief/templates/sections.md` with extra output-structure guidance.
2. Start `dogent` in that workspace and type `/init `.
3. Expect the completion list to include `product_brief`.
4. In the prompt area, type `hello @@` and expect the completion list to include `product_brief`.
5. Configure the workspace to use `product_brief`, then start a writing task and confirm Dogent applies the actionable template rules plus the extra `templates/` guidance successfully, while not injecting the title/`Introduction` block from `SKILL.md`.
6. Add a legacy flat file `.dogent/templates/legacy.md`.
7. Repeat `/init ` and `@@` completion checks. Expect `legacy` not to appear anywhere.

User Test Results: Accepted (2026-03-29)

### Story 2 – Native `/template` Command UX
1. Start `dogent` in a workspace that has at least one workspace template and the shipped built-in templates available.
2. Run `/template`.
3. Expect a visible template inventory that matches `/template list`.
4. Type `/template ` and confirm the dropdown offers `create` and `optimize`.
5. Run `/template create write a bilingual software usage manual template for internal tools, with sections for prerequisites, step-by-step usage, troubleshooting, and FAQ`.
6. Expect Dogent to accept the full free-text request after `/template create` as the template-generation brief instead of asking for a fixed structured argument format.
7. Run `/template optimize`.
8. Expect Dogent to show available templates and usage guidance, including the optional free-text optimize brief, instead of starting an agent run with an unknown target.
9. Run `/template list` and confirm the displayed templates and descriptions match the bare `/template` output.

User Test Results: Accepted (2026-03-29)

### Story 3 – Built-in Template Creator And Migrated Built-ins
1. In a sample workspace, run `/template create create a software design document template for backend service RFCs`.
2. Expect Dogent to trigger the built-in template-creator workflow and use the free-text request as the template brief, then create or propose a new template under `.dogent/templates/`.
3. Inspect the generated template. Expect a skill-style directory containing `SKILL.md`, reusable structure files under `templates/`, optional examples under `examples/`, and optional assets under `assets/`, instead of a single `.md` file.
4. Run `/template optimize built-in:resume make the template more concise for senior backend engineers in English`.
5. Expect Dogent to trigger the built-in optimization workflow using the selected template as the baseline.
6. Confirm the built-in template-creator skill is packaged under the Dogent built-in plugin namespace at `~/.dogent/plugins/dogent/skills/doc-template-creator/` instead of the Claude built-in plugin namespace.
7. Run `/init built-in:resume` and confirm the migrated built-in template is still selectable and usable after the format change.

User Test Results: Partially Failed (2026-03-29)
- I used `/template create` to create a new consultant-proposal template in samples folder, then I use `/template` to list all the templates, but the new template shows: "consult-proposal: >" which do not show the description. I checked the generated `SKILL.md` and found the description is in the next line of `description:` , please fix the template creator to make the description show in the same line of `description:` in the YAML frontmatter.
- according the `claude/skills/skills/skill-creator` to prompt the built-in template creator skill, to give format of the doc template skills format and enhance other useful information in it.
- when I input `/template` and blank, there are only create and optimize options, but there is no `list` option;
- when I input `/template create` and followed by the template brief demand, I can not use `@` to refer files in the template brief, also can not use `@@` to refer the other template in the template brief, please support the `@` and `@@` in the template brief for the template creator skill, which can make the template creator more powerful and flexible.

Fix Status (2026-03-29): Implemented for retest
Retest Notes:
1. Re-run `/template ` and confirm the dropdown now includes `list` in addition to `create` and `optimize`.
2. Re-run `/template create` with a brief that includes `@file` and `@@template` references; confirm the creator workflow receives both as usable context.
3. Re-create the consultant-proposal template and confirm the generated `SKILL.md` keeps `description: ...` on a single YAML line and the `/template` inventory shows the description correctly.
4. Re-check the generated template guidance and confirm the built-in template creator now follows the strengthened format instructions based on the skill-creator reference.

User Test Results: Accepted (2026-03-29)

Post-Acceptance Follow-up (2026-03-29)
- Interactive completion after `/template create ` still did not offer `@file` or `@@template` references, even though the command handler already supported them at execution time.

Fix Status (2026-03-29): Implemented for retest
Retest Notes:
1. Type `/template create use @` and confirm workspace file completions appear.
2. Type `/template create use @@` and confirm template completions appear.
3. Select a file or template from the dropdown, submit `/template create ...`, and confirm the creator workflow still receives the selected reference as usable context.

User Test Results: Accepted (2026-03-29)
