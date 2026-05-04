---
name: dogent-archive-history
description: Archive completed Dogent release history from active planning files into `dev/archives`. Use when the user asks to archive old/history requirements, sprint design, sprint plan, or sprint UAT sections from `dev/requirement.md`, `dev/sprint_design.md`, `dev/sprint_plan.md`, and `dev/sprint_uat.md`.
---

# Dogent Archive History

Move completed release history out of the active development tracking files and into the matching archive files under `dev/archives`.

## File Mapping

- `dev/requirement.md` -> `dev/archives/requirement.md`
- `dev/sprint_design.md` -> `dev/archives/sprint_design.md`
- `dev/sprint_plan.md` -> `dev/archives/sprint_plan.md`
- `dev/sprint_uat.md` -> `dev/archives/uat_plan.md`

## Workflow

1. Read all four active source files and their archive targets before editing.
2. Determine the release sections to archive:
   - If the user names releases, archive only those releases.
   - If the user says to archive history without naming releases, archive completed historical release sections that are already accepted/done, and keep the current active release plus any pending requirements in the active files.
3. For each selected release, move the complete matching section from every active source file where it exists into the mapped archive file.
4. Append archived sections in release order consistent with the archive file. Preserve section content, headings, dates, status notes, and manual UAT results.
5. Remove only the moved release sections from the active files. Keep top-level titles, examples, status legends, separators, pending sections, and active release sections intact.
6. If a selected release exists in some source files but not others, archive the sections that exist and mention the missing sections in the final response.
7. After edits, verify each moved release appears exactly once across active and archive locations.

## Rules

- Do not archive `## Pending Requirements` unless the user explicitly asks.
- Do not archive a release with `Dev Status: Todo` / `In Progress`, `Acceptance Status: Pending` / `Rejected`, or unresolved UAT retest notes unless the user explicitly names it and confirms it should be archived.
- Do not rewrite unrelated archive history or normalize old formatting beyond what is needed to insert the moved sections cleanly.
- Prefer structured Markdown section moves over ad hoc line deletion. Use release headings such as `## Release 0.9.29` as section boundaries.
- Keep archive filenames as they currently exist. The UAT archive target is `dev/archives/uat_plan.md`, not `dev/archives/sprint_uat.md`.
- If duplicate release headings exist in a source file, treat each block independently and archive only the blocks that match the user's requested scope.

## Verification

- Run `rg "^## Release" dev/requirement.md dev/sprint_design.md dev/sprint_plan.md dev/sprint_uat.md dev/archives/requirement.md dev/archives/sprint_design.md dev/archives/sprint_plan.md dev/archives/uat_plan.md` to inspect release placement.
- Use `git diff -- dev/requirement.md dev/sprint_design.md dev/sprint_plan.md dev/sprint_uat.md dev/archives/requirement.md dev/archives/sprint_design.md dev/archives/sprint_plan.md dev/archives/uat_plan.md` to confirm the diff only moves the intended sections.
