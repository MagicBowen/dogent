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

## Release 0.9.30

### Story 1: Upstream Skills Submodule
- User Value: As a Dogent maintainer, I can sync Anthropic's official skills from the upstream repository without manually copying a stale tree into Dogent.
- Acceptance: `claude/skills` is configured as a Git submodule pointing to `https://github.com/anthropics/skills`; the repo documents or preserves the command needed to initialize and update the submodule; the old normal checked-in directory content is no longer duplicated outside the submodule.
- Dev Status: Done
- Acceptance Status: Accepted (2026-05-04)
- Verification: `.gitmodules` contains the `claude/skills` submodule entry; `git submodule update --init --recursive` checks out the upstream skills tree.

### Story 2: Manifest-Driven Claude Plugin Skill Selection
- User Value: As a Dogent maintainer, I can decide which upstream Claude skills Dogent bundles by editing one manifest instead of manually vendoring skill folders.
- Acceptance: `dogent/plugins/claude/skills_manifest.json` defines the source, target, and ordered skill list; default bundled skills include `pptx` and exclude `skill-creator`; direct checked-in copies of `dogent/plugins/claude/skills/pptx` and `dogent/plugins/claude/skills/skill-creator` are removed; a deterministic preparation script attempts to update `claude/skills` to the newest upstream submodule version before copying, falls back to the current checkout with a warning if that update fails, and copies only manifest-selected skills from `claude/skills/skills` into `dogent/plugins/claude/skills`; missing submodule/source/skill entries fail with clear errors.
- Dev Status: Done
- Acceptance Status: Accepted (2026-05-04)
- Verification: Automated tests cover manifest parsing, submodule update fallback, selected-skill copy, stale target cleanup, and missing source failure.

### Story 3: Release Packaging Uses Prepared Claude Skills
- User Value: As a Dogent user, I receive a packaged built-in Claude plugin containing exactly the maintainer-selected skills and no stale bundled skill directories.
- Acceptance: The release/package workflow runs the manifest preparation step before `python -m build`; that step reports the submodule commit used after update-or-fallback; package data still includes `dogent/plugins/**`; `ConfigManager._install_builtin_plugins` continues installing the Claude plugin from packaged resources; the installed `~/.dogent/plugins/claude` plugin contains only manifest-selected skills after bootstrap.
- Dev Status: Done
- Acceptance Status: Accepted (2026-05-04)
- Verification: Automated bootstrap/package-preparation tests confirm the installed Claude plugin manifest exists and selected skill directories match `skills_manifest.json`; `python -m unittest discover -s tests -v` passes.
