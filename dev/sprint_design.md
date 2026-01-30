# Design

---

## Release 0.9.21
### Overview
- Auto-create `.dogent/dogent.json` and `.dogent/history.json` on the very first CLI launch in a workspace (no init prompt).
- Add a `poe-claude` LLM profile to the global config template (`~/.dogent/dogent.json` seed).
- Update docs/sample configs to mention the new `poe-claude` profile.

### Behavior Changes
- First CLI launch in a workspace:
  - Ensure `.dogent/` exists.
  - Create `.dogent/dogent.json` if missing using existing template merge rules (no prompt).
  - Create `.dogent/history.json` if missing (empty list).
  - Continue normal flow (do not require `/init`).
- The existing `/init` command continues to create `.dogent/dogent.md` and respects user overrides.

### Design / Implementation Notes
- **Config bootstrap on first launch**
  - Current behavior prompts to initialize when `.dogent/dogent.json` is missing; change to auto-create during CLI startup.
  - Preferred hook: call `ConfigManager.create_config_template()` and `HistoryManager._ensure_history_file()` (via a small public helper) early in CLI startup path (interactive and non-interactive).
  - Keep `.dogent/dogent.md` creation tied to `/init` (no change) unless we explicitly decide to auto-create it later.

- **Global template update**
  - Add `poe-claude` under `llm_profiles` in `dogent/resources/dogent_global_default.json`.
  - Ensure template is merged on first-run bootstrap and during global config upgrades.

- **Docs/sample configs**
  - Update configuration docs to include the `poe-claude` profile snippet and brief usage note.
  - Update any sample configs that show `llm_profiles` to include `poe-claude`.

### Tests
- Add/extend unit tests to assert:
  - On first CLI launch in a workspace with no `.dogent/dogent.json`, it is created automatically.
  - `.dogent/history.json` is created on first launch (empty list).
  - `poe-claude` exists in the global default template used to seed `~/.dogent/dogent.json`.

### Risks / Edge Cases
- Ensure auto-creation does not overwrite existing `.dogent/dogent.json`.
- Avoid triggering interactive prompts on first launch.
- Keep global config upgrade logic idempotent if user already added a `poe-claude` profile.
