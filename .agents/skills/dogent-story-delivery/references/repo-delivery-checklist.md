# Repo Delivery Checklist

## Before Coding

- Read `AGENTS.md` and follow the repo process requirements.
- Read the target release section in `dev/sprint_design.md`, `dev/sprint_plan.md`, and `dev/sprint_uat.md`.
- Confirm whether the user asked for story implementation or only a doc/test refresh.

## Implementation Rules

- Default to the next sequential approved story unless the user points to a specific one.
- Add automated tests alongside code changes.
- Prefer focused changes over opportunistic refactors.
- Respect existing file formats and status wording in the sprint docs.
- If the design is contradictory, unclear, or overtaken by unexpected local edits, stop and clarify with the user.

## Test Expectations

- Run targeted tests for the changed area.
- Run `python -m unittest discover -s tests -v` before finishing when feasible.
- Report when tests were not run or when coverage remains indirect.

## Sprint Doc Updates After Implementation

- `dev/sprint_plan.md`: set the story `Dev Status` to `Done`; keep `Acceptance Status` as `Pending` until the user confirms UAT.
- `dev/sprint_uat.md`: add or update manual steps that match the delivered behavior.
