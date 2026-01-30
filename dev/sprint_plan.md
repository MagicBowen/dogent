# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.21
### Story 1: Auto-create workspace config/history on first launch
- User Value: Entering Dogent in a new workspace auto-creates `.dogent/dogent.json` and `.dogent/history.json` without manual init.
- Acceptance: On first CLI launch in a workspace with no `.dogent/dogent.json`, the file is created with defaults; `.dogent/history.json` exists as an empty list; no init prompt appears; `/init` still controls `.dogent/dogent.md`.
- Dev Status: Done
- Acceptance Status: Accepted (2026-01-30)
- Verification: Unit tests + manual smoke run in a fresh workspace.

### Story 2: Add poe-claude profile to global template + docs
- User Value: Users can configure Poe’s Claude endpoint via a ready-made `poe-claude` profile and see it documented.
- Acceptance: `dogent/resources/dogent_global_default.json` includes `poe-claude` under `llm_profiles`; docs that show `llm_profiles` include the new profile snippet; new global config bootstrap contains `poe-claude`.
- Dev Status: Done
- Acceptance Status: Accepted (2026-01-30)
- Verification: Unit test for template content + doc review.
