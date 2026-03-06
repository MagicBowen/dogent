# Repo Acceptance Checklist

## Inputs

- Read the current release section in `dev/sprint_design.md`, `dev/sprint_plan.md`, and `dev/sprint_uat.md`.
- Treat the user's latest edits in `dev/sprint_uat.md` as the current UAT record.

## When UAT Reported Bugs

- Implement only the fixes needed for the reported issue set.
- Add or update automated tests for every changed function.
- Run targeted tests for the changed area.
- Run `python -m unittest discover -s tests -v` before finishing when feasible.
- Update `dev/sprint_uat.md` with the issue disposition and explicit retest guidance.
- Keep `Acceptance Status` pending until the user confirms the retest passed.

## When UAT Passed

- Update `dev/sprint_uat.md` to reflect the accepted result using the actual current date.
- Update the related story entries in `dev/sprint_plan.md` to `Accepted (YYYY-MM-DD)`.
- If all stories in the current release are accepted, update any release-level status lines in the related sprint docs to reflect that completion.

## Boundaries

- Do not close out a release that still has pending or failed story UAT.
- Do not publish or tag a release from this skill; hand that off to the publish skill.
