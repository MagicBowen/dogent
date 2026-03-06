---
name: dogent-story-delivery
description: Implement approved Dogent release stories under the repo workflow. Use when the user asks to code according to `dev/sprint_design.md` or `dev/sprint_plan.md`, add automated tests for changed functions, run the unittest suite, or update `dev/sprint_uat.md` and `dev/sprint_plan.md` to reflect delivered work that is still pending acceptance.
---

# Dogent Story Delivery

Implement one approved Dogent story at a time, verify it with automated tests, and keep the repo tracking docs in sync up to the point where the work is ready for manual UAT.

## Workflow

1. Read the target story in `dev/sprint_plan.md` and the corresponding release design and UAT sections.
2. Default to the next sequential story unless the user points to a specific one.
3. Implement the story with minimal scoped code changes.
4. Add or update automated tests for every changed function.
5. Run targeted tests first, then run `python -m unittest discover -s tests -v` when feasible.
6. Update sprint tracking after implementation: mark `Dev Status: Done`, keep `Acceptance Status: Pending`, and ensure `dev/sprint_uat.md` covers the delivered behavior.

## Delivery Rules

- Work sequentially unless the user explicitly overrides the order.
- Do not revert unrelated dirty worktree changes.
- Stop and ask before continuing if the design is unclear, contradictory, or overtaken by unexpected local edits.
- Leave post-UAT bugfix handling, acceptance closeout, and release publishing to the dedicated follow-up skills.
- If the user asks only for post-UAT closeout, do not redo implementation work.

## Resources

- Read [references/repo-delivery-checklist.md](references/repo-delivery-checklist.md) for the repo-specific implementation, testing, and pre-UAT tracking checklist.
