---
name: dogent-story-acceptance
description: Process Dogent manual UAT feedback after the user updates `dev/sprint_uat.md`. Use when the user asks to fix bugs found in UAT, update `dev/sprint_uat.md` for retest, or mark current-release stories accepted in `dev/sprint_uat.md` and `dev/sprint_plan.md` after all UATs pass.
---

# Dogent Story Acceptance

Handle post-UAT delivery work for the current Dogent release: fix bugs reported by the user in `dev/sprint_uat.md`, refresh the manual test records, and close out acceptance statuses only after the release stories pass.

## Workflow

1. Read the current release sections in `dev/sprint_design.md`, `dev/sprint_plan.md`, and `dev/sprint_uat.md`.
2. Treat the user's latest edits in `dev/sprint_uat.md` as the source of truth for current UAT results and bug reports.
3. If the user reported bugs, implement the fixes with minimal scoped code changes.
4. Add or update automated tests for every changed function.
5. Run targeted tests first, then run `python -m unittest discover -s tests -v` when feasible.
6. Update `dev/sprint_uat.md` with the fix status and the next retest instructions, then stop so the user can test again.
7. When all stories in the current release have passing UAT results, update the related release status fields in `dev/sprint_uat.md`, `dev/sprint_plan.md`, and any matching acceptance trackers.

## Acceptance Rules

- Do not mark a story or release accepted until the user indicates the current UAT passed.
- Use the actual current date for acceptance records.
- Keep the wording and structure of the sprint docs consistent with the existing format.
- If the user asks only for a bugfix round, do not close out acceptance or changelog work yet.

## Resources

- Read [references/repo-acceptance-checklist.md](references/repo-acceptance-checklist.md) for the repo-specific bugfix, retest, and acceptance-closeout checklist.
