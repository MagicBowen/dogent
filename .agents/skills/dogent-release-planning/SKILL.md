---
name: dogent-release-planning
description: Analyze and plan Dogent release requirements into the repo tracking docs. Use when the user says `dev/requirement.md` was updated, asks to read a release requirement, design it, identify contradictions or missing decisions, append release design to `dev/sprint_design.md`, split approved work into dependency-ordered user stories in `dev/sprint_plan.md`, or append manual UAT cases to `dev/sprint_uat.md` before implementation.
---

# Dogent Release Planning

Plan release requirements before implementation. Keep the work inside the repo planning documents and stop for clarification when the requirement is contradictory or materially underspecified.

## Workflow

1. Read the target release section in `dev/requirement.md` and the matching sections in `dev/sprint_design.md`, `dev/sprint_plan.md`, and `dev/sprint_uat.md`.
2. Identify contradictions, missing decisions, or acceptance ambiguity.
3. Ask the user to clarify before editing if the requirement is unclear enough to risk designing the wrong behavior.
4. Append or update the release design in `dev/sprint_design.md` using the existing file format.
5. After the design is problem-free, split the release into dependency-ordered user stories in `dev/sprint_plan.md`.
6. Append manual user acceptance steps for each story in `dev/sprint_uat.md`.
7. Match the user's scope. If the user asked only for design, stop after `dev/sprint_design.md`.

## Planning Rules

- Write stories with end-to-end user value that can be accepted independently.
- Keep plan statuses consistent with the repo legend: new implementation stories start as `Dev Status: Todo` and `Acceptance Status: Pending` unless work is already complete.
- Keep UAT steps manual, concrete, and runnable in a sample workspace.
- Preserve existing release history and append by release instead of rewriting unrelated sections.
- Do not implement code in this skill unless the user explicitly pivots from planning to delivery.

## Resources

- Read [references/repo-planning-checklist.md](references/repo-planning-checklist.md) for the repo-specific file responsibilities, stop conditions, and formatting checklist.
