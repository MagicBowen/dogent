# Repo Planning Checklist

## Files to Update

- `dev/requirement.md`: source of truth for requested release behavior.
- `dev/sprint_design.md`: release design, assumptions, baseline, implementation plan, edge cases, tests.
- `dev/sprint_plan.md`: dependency-ordered user stories with `Dev Status` and `Acceptance Status`.
- `dev/sprint_uat.md`: manual acceptance steps per story.

## Stop and Clarify

Clarify with the user before editing planning docs when any of these are true:

- The requirement conflicts with existing behavior or another requirement.
- A behavior choice would materially change UX, data shape, or compatibility.
- The acceptance condition is too vague to design defensibly.
- The release asks for implementation details that cannot be inferred from local context safely.

## Design Expectations

- State the goal first.
- Summarize the current baseline only when it affects the design.
- Describe behavior, implementation direction, edge cases, and tests.
- Keep the design scoped to the release instead of mixing unrelated cleanup.

## Story Expectations

- Slice by end-to-end value, not by internal layer.
- Order stories by dependency.
- Keep each story independently testable and manually acceptable.
- Use the repo status words exactly: `Todo`, `In Progress`, `Done`, `Pending`, `Accepted`, `Rejected`.

## UAT Expectations

- Write numbered steps.
- Use real file paths, commands, and expected outcomes.
- Keep each story's acceptance steps focused on observable behavior.
- Leave `User Test Results` as pending until the user confirms the outcome.
