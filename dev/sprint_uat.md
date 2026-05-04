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

## Release 0.9.30

### Story 1 – Upstream Skills Submodule
1. From the repo root, inspect `.gitmodules`.
2. Confirm it contains a submodule entry for `claude/skills` with URL `https://github.com/anthropics/skills`.
3. Run `git submodule update --init --recursive`.
4. Confirm `claude/skills/README.md` and `claude/skills/skills/pptx/SKILL.md` exist after initialization.
5. Run `git submodule status claude/skills` and confirm Git reports a submodule commit for `claude/skills`.

User Test Results: Accepted (2026-05-04)

### Story 2 – Manifest-Driven Claude Plugin Skill Selection
1. Open `dogent/plugins/claude/skills_manifest.json`.
2. Confirm the manifest points from `claude/skills/skills` to `dogent/plugins/claude/skills`.
3. Confirm the default `skills` list includes `pptx` and does not include `skill-creator`.
4. Remove any existing generated `dogent/plugins/claude/skills` directory if it exists, then run `python scripts/prepare_claude_plugin_skills.py`.
5. Confirm the command attempts to update `claude/skills` before copying and reports the submodule commit used.
6. Confirm `dogent/plugins/claude/skills/pptx/SKILL.md` exists.
7. Confirm `dogent/plugins/claude/skills/skill-creator` does not exist.
8. Temporarily make the submodule update fail in a controlled way, such as by disconnecting network access or using the implementation's test hook if one exists, while leaving the current `claude/skills` checkout present.
9. Rerun `python scripts/prepare_claude_plugin_skills.py` and expect it to warn about the failed update, continue with the current checkout, and still copy `pptx`.
10. Temporarily add an invalid skill name to the manifest and rerun the preparation command.
11. Expect the command to fail with a clear missing-skill error, then restore the manifest.

User Test Results: Accepted (2026-05-04)

### Story 3 – Release Packaging Uses Prepared Claude Skills
1. Run `python scripts/prepare_claude_plugin_skills.py` from the repo root.
2. Confirm the command reports the `claude/skills` submodule commit used after update-or-fallback.
3. Run `python -m unittest discover -s tests -v`.
4. Build the package with `python -m build`.
5. Install the built artifact into a clean virtual environment or smoke-test environment.
6. Start Dogent once with a clean `HOME`.
7. Confirm `~/.dogent/plugins/claude/.claude-plugin/plugin.json` exists.
8. Confirm `~/.dogent/plugins/claude/skills/pptx/SKILL.md` exists.
9. Confirm `~/.dogent/plugins/claude/skills/skill-creator` does not exist.

User Test Results: Accepted (2026-05-04)
