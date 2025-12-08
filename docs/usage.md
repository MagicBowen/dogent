# Dogent Usage Guide

## Install
- Ensure Python 3.10+ is available.
- From the project root: `pip install .`
- The CLI will be available as `dogent`.

## First Run
1. Navigate to your project directory.
2. Run `dogent` (or `dogent -h` for help) to enter the interactive shell; an ASCII banner and model/API info are shown.
3. Use `/init` to generate `.dogent/dogent.md`.
4. Use `/config` to scaffold `.dogent/dogent.json` (profile-only, includes `images_path` default); edit the profile name or supply env vars for credentials.

## Credentials & Profiles
- Local config: `.dogent/dogent.json` (profile reference only) plus `images_path` for downloads (defaults to `./images` when not set).
- Global profiles: `~/.dogent/claude.json`, e.g.:
  ```json
  {
    "profiles": {
      "deepseek": {
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "xxx",
        "ANTHROPIC_MODEL": "deepseek-reasoner",
        "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-chat",
        "API_TIMEOUT_MS": 600000,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
      }
    }
  }
  ```

- Environment fallback if no profile/config is provided.

## Commands Inside the CLI
- `/init` – create writing constraint template and scratch memory.
- `/config` – generate config JSON (profile-only, includes `images_path`).
- `/exit` – leave the CLI.
- Typing `/` shows live command suggestions; typing `@` offers file completions.
- Press `Esc` during an in-progress task to interrupt; progress is saved to `.dogent/history.md`.

## Referencing Files
- Inline `@` references pull file contents into the prompt, e.g. `Review @docs/plan.md`.
- CLI prints which files were loaded; contents are injected into the user prompt; completions appear as soon as you type `@`.

## Working With Todos
- The agent uses the `TodoWrite` tool; Dogent mirrors its outputs with emoji statuses and concise logs.
- No default todos are created; the list always reflects the latest TodoWrite result.

## Document Writing Expectations
- Defaults: Chinese, Markdown, citations at the end; images saved under configured `images_path` (default `./images`) and referenced with relative paths.
- The system prompt enforces planning, research (including online search), sectioned drafting, validation, and final polishing; history in `.dogent/history.md` provides continuity.
- Temporary notes go to `.dogent/memory.md` only when needed—create on demand and clean after use.

## Running Tests
- From the project root: `python -m unittest`
- Tests cover config/profile merge, prompt assembly, and todo syncing behavior.
