# Design

## Release 0.9.30

### Goal

Make Dogent's reference copy of Anthropic skills syncable from the upstream `https://github.com/anthropics/skills` repository, and replace the currently hardcoded bundled Claude plugin skills with a manifest-driven packaging selection.

### Current Baseline

- `claude/skills` is currently a normal checked-in directory containing the upstream skills repository content.
- `dogent/plugins/claude/skills` currently vendors two skills directly:
  - `pptx`
  - `skill-creator`
- Dogent package data includes `dogent/plugins/**`, and `ConfigManager._install_builtin_plugins` copies packaged plugin directories into `~/.dogent/plugins` at startup.
- The built-in Claude plugin manifest already lives at `dogent/plugins/claude/.claude-plugin/plugin.json`.

### Design Direction

- Convert `claude/skills` into a Git submodule that points to `https://github.com/anthropics/skills`.
- Remove the checked-in bundled copies of `dogent/plugins/claude/skills/pptx` and `dogent/plugins/claude/skills/skill-creator`.
- Add a Dogent-owned manifest file at `dogent/plugins/claude/skills_manifest.json`.
- The manifest is the source of truth for which upstream skills Dogent bundles into the packaged Claude plugin.
- Add a deterministic packaging preparation step that first attempts to update the `claude/skills` submodule to the newest upstream version, then reads `skills_manifest.json`, copies selected skills from `claude/skills/skills/<name>` into `dogent/plugins/claude/skills/<name>`, and fails clearly when a manifest entry does not exist in the available submodule checkout.

### Manifest Format

Use a small JSON file so it can be edited without code changes:

```json
{
  "source": "claude/skills/skills",
  "target": "dogent/plugins/claude/skills",
  "skills": [
    "pptx"
  ]
}
```

- `source` is repo-root relative and should point inside the `claude/skills` submodule.
- `target` is repo-root relative and should point to the package plugin skill directory.
- `skills` is an ordered list of skill directory names to copy.
- The initial default should include only `pptx`, preserving the previously shipped PPTX capability while no longer bundling `skill-creator` by default.
- Empty `skills` is valid and produces a Claude plugin with no bundled skills.

### Packaging Preparation Behavior

- Add a script such as `scripts/prepare_claude_plugin_skills.py`.
- The script should:
  - load `dogent/plugins/claude/skills_manifest.json`;
  - resolve source and target paths relative to repo root;
  - attempt to update `claude/skills` to the newest upstream submodule version before copying;
  - continue with the currently checked-out `claude/skills` version if the update command fails, while printing a warning that names the failed update step;
  - remove and recreate only the target `skills` directory;
  - copy each selected skill directory from the submodule into the target directory;
  - preserve nested files, scripts, references, assets, and license files;
  - print the submodule commit used and copied skill names for release verification;
  - return a non-zero exit code with a clear error when the submodule is missing, the manifest is invalid, or a requested skill does not exist.
- The packaging/release workflow should run this script before `python -m build` so packaged artifacts contain exactly the manifest-selected skills.

### Git Submodule Behavior

- `.gitmodules` should contain a `claude/skills` submodule entry with URL `https://github.com/anthropics/skills`.
- Existing local `claude/skills` content should be replaced by the submodule checkout, not duplicated elsewhere.
- Release/update documentation should tell maintainers to initialize and update the submodule before preparing packages:
  - `git submodule update --init --recursive`
  - `git submodule update --remote claude/skills` when intentionally syncing upstream.
- The preparation script should automate the remote update attempt during packaging, but network or upstream failures must not block packaging when a usable current submodule checkout already exists.

### Compatibility And Install Behavior

- Keep the built-in Claude plugin root and plugin manifest path unchanged so `ConfigManager._install_builtin_plugins` can continue installing `~/.dogent/plugins/claude`.
- Keep package data inclusion for `dogent/plugins/**`.
- Do not add `~/.dogent/plugins/claude` back to default workspace `plugins`; current built-in plugin loading behavior should remain unchanged unless a separate requirement changes it.
- Runtime startup should not require network access or a checked-out submodule. The package must already contain the manifest-selected skills after the packaging preparation step.

### Edge Cases

- If the submodule is not initialized, the preparation script should fail with guidance instead of producing an empty plugin accidentally.
- If the submodule remote update fails but the existing checkout is usable, the preparation script should warn and continue from that checkout.
- If `skills_manifest.json` names `skill-creator`, the script may copy it, but the default manifest should not include it.
- If `dogent/plugins/claude/skills` contains stale files from an earlier build, the preparation script should remove them before copying selected skills.
- If upstream changes a selected skill layout, Dogent should copy the directory as-is and rely on package/build tests to verify expected `SKILL.md` files exist.

### Tests

- Add tests for manifest parsing and copying selected skills into a temporary plugin target.
- Add tests that submodule update failure falls back to the current checkout and emits a warning.
- Add tests that stale target skills are removed before copy.
- Add tests that missing source skills and missing submodule/source directory produce clear failures.
- Update config/bootstrap tests to expect the installed Claude plugin to contain only manifest-selected bundled skills after the packaging preparation step.
- Keep the full `python -m unittest discover -s tests -v` suite green.
