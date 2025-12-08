# Repository Guidelines

## Project Structure & Modules
- `dogent/`: Core CLI/agent code. Key modules: `cli.py` (interactive loop + command registry), `agent.py` (Claude SDK streaming/interrupts), `config.py` (profiles/env merge), `prompts/` (system/user prompt templates), `todo.py` (TodoWrite sync), `file_refs.py` (@file resolution). Role-specific prompts/templates live under `prompts/` and `templates/` so the core stays reusable.
- `docs/`: Requirements, stories, usage, todo tracking.
- `tests/`: `unittest` suites covering config, prompts, todo syncing.
- `uats/`: user acceptance tests folder for user testing dogent manually.
- `pyproject.toml`: Packaging and entrypoint (`dogent`).

## Build, Test, and Development Commands
- Install editable: `pip install -e .`
- Run CLI locally: `dogent` (from any project directory after install).
- Tests: `python -m unittest discover -s tests -v`
- Package (sdist/wheel): `python -m build` (requires `build` package if not present).

## Coding Style & Naming
- Language: Python 3.10+; 4-space indentation; keep code ASCII unless file already uses Unicode.
- Module naming: snake_case; classes in PascalCase; functions/vars in snake_case.
- Prompts live in `dogent/prompts/*.md`; keep them declarative, and versionable.
- Minimal inline comments; prefer clear function names and small functions.
- Keep CLI-facing strings (panels, errors, banners) in English; let LLM outputs stay in the user’s language.

## Testing Guidelines
- Framework: `unittest`.
- Place new tests in `tests/` with `test_*.py`; mirror module names where possible.
- Aim to cover config merging, prompt rendering, todo synchronization, and CLI behaviors that can be unit-tested.
- Run `python -m unittest discover -s tests -v` before submitting.

## Commit & Pull Request Guidelines
- Commits: concise imperative subject (e.g., “Add todo sync rendering”, “Fix profile merge”). Group related changes; avoid noisy commits.
- PRs: include summary of behavior change, testing performed, and any new config/env needs. Add screenshots or terminal snippets for CLI UX changes when helpful.

## Security & Configuration Tips
- Credentials loaded from `~/.dogent/claude.json`, `.dogent/dogent.json` (profile reference), or env vars (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, etc.). Do not commit secrets.
- Keep network/tool permissions aligned with Claude Agent SDK defaults; review any additions to allowed tools.
- Claude Agent SDK usage must follow the docs and samples under `claude-agent-sdk/`; do not guess behaviors.

## Agent-Specific Notes
- Always keep system/user prompts in `dogent/prompts/` to ease tuning.
- Todo list must reflect `TodoWrite` outputs only—do not seed defaults.
- @file references resolve within the current workspace; avoid reading outside project boundaries.

## Process & Quality Requirements
- All functions must have automated tests; extend `tests/` alongside new code.
- Keep `docs/todo.md` updated with development and acceptance status; work stories sequentially and fix per user acceptance feedback.
- After finishing each story, append/update `uats/uat_guild.md` with step-by-step install/run instructions using a sample directory to guide user acceptance.
- `.dogent/dogent.json` should reference a profile only; real credentials belong in `~/.dogent/claude.json` (or env vars).
- Release 0.3 principles: use a command registry (no hardcoded command lists), externalize templates, keep system/user prompts clean (no hardcoded paths), separate core CLI/agent logic from role-specific configs/templates for extensibility, support multi-line input (Alt/Option+Enter), handle Esc interrupts and Ctrl+C gracefully, keep sections/titles emoji-labeled for clarity, and keep CLI UI language in English while preserving the model’s response language.
