# Repository Guidelines

## Project Structure & Modules
- `dogent/`: Core CLI/agent code. Key modules: `cli.py` (interactive loop + command registry), `agent.py` (Claude SDK streaming/interrupts), `config.py` (profiles/env merge), `prompts/` (system/user prompt templates), `todo.py` (TodoWrite sync), `file_refs.py` (@file resolution). Role-specific prompts/templates live under `prompts/` and `templates/` so the core stays reusable.
- `docs/`: usage.
- `dev/`: requirements, user stories tracking, user acceptance test plans...
- `tests/`: `unittest` suites covering config, prompts, todo syncing.
- `uats/`: user acceptance tests folder for user testing dogent manually.
- `claude-agent-sdk`: claude agent sdk usage examples and skills for reference.
- `pyproject.toml`: Packaging and entrypoint (`dogent`).

## Build, Test, and Development Commands
- Install editable: `pip install -e .`
- Run CLI locally: `dogent` (from any project directory after install).
- Tests: `python -m unittest discover -s tests -v`
- Package (sdist/wheel): `python -m build` (requires `build` package if not present).

## Coding Style & Naming
- Language: Python 3.10+; 4-space indentation; keep code ASCII unless file already uses Unicode.
- Module naming: snake_case; classes in PascalCase; functions/vars in snake_case.
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
- Todo list must reflect `TodoWrite` outputs only—do not seed defaults.
- @file references resolve within the current workspace; avoid reading outside project boundaries.
- When using prompt_toolkit, avoid raw stdin/termios reads in parallel; if an Esc listener is needed, ensure it drains escape sequences and exits cleanly before the next prompt to prevent IME/arrow-key echo issues.

## Process & Quality Requirements
- All functions must have automated tests; extend `tests/` alongside new code.
- After receiving the user's update to dev/requirements.md requesting the implementation of specified release requirements, first analyze and conduct preliminary design of the requirements. 
- The design results can be append to `dev/sprint_design.md` by release. If there are contradictions or unclear points, it is necessary to clarify with the user before continuing to revise the design. 
- Once the design is confirmed to be problem-free, split the requirements into user stories with end-to-end value that can be independently accepted, sort them according to dependency order, and append them to `dev/sprint_plan.md`  by release. 
- After finishing each story, design user acceptance test cases for each user story (guiding users to conduct manual step-by-step testing and acceptance in the sample directory, as well as updating acceptance results and identified issues in uat_plan.md), and append them to `dev/uat_plan.md` by release.
- Keep `dev/sprint_plan.md` updated with development and acceptance status; work stories sequentially and fix per user acceptance feedback.