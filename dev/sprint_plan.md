# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.8
### Story 1: Layered Config Defaults
- User Value: Global config in `~/.dogent/dogent.json` provides defaults for new workspaces; local overrides remain scoped to the workspace.
- Acceptance: `load_project_config()` merges defaults -> global -> local; if no local config, global values are used; if global lacks `llm_profile`, env fallback remains; `/init` creates `.dogent/dogent.json` using global defaults without overwriting existing keys.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for merge behavior and config template creation.

### Story 2: Vision Disabled by Default
- User Value: Vision tools are opt-in; image references fail fast when `vision_profile` is `null` or missing.
- Acceptance: Default `vision_profile` is `null`; vision MCP tools are not registered when disabled; CLI blocks image/video attachments with a clear error when vision is disabled.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for tool registration and CLI attachment blocking.

### Story 3: Prompt-Level Doc Template Override
- User Value: Users can temporarily select a doc template per request using a selector token without editing config files.
- Acceptance: Typing `@@` triggers template completion; `@@<template>` overrides `doc_template` only for that request and is stripped from the outgoing user message.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for token parsing and prompt rendering with overrides.

### Story 4: Unified Global Config File
- User Value: All global profiles and defaults live in a single `~/.dogent/dogent.json`.
- Acceptance: LLM/web/vision profiles are read from `llm_profiles`/`web_profiles`/`vision_profiles` in the global config; legacy separate files are no longer referenced; warnings and docs point to `~/.dogent/dogent.json`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for profile loading and web/vision tool behavior.

### Story 5: Versioned Global Config Upgrade
- User Value: Dogent upgrades the global config when new keys are added, without overwriting user settings.
- Acceptance: `~/.dogent/dogent.json` includes `version`; on startup, if config version < Dogent version, merge in missing keys only and update `version`; if config version > Dogent version, warn.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Unit tests for upgrade behavior and warnings.
