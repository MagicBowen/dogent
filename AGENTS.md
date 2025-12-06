# Repository Guidelines

Contributor quick-start for the Dogent (Claude Agent SDK) CLI. Keep edits lean, typed, and test-backed.

## Project Structure & Module Organization
- `src/dogent/`: main package. `cli.py` runs the Typer REPL and slash commands, `runtime.py` streams to the Claude Agent SDK, `config.py` loads env + `.dogent/dogent.json`, `guidelines.py` manages `.dogent/dogent.md`, `context.py` resolves `@file` references, `todo.py` renders tasks, and `prompts/*.md` hold role/system templates.
- `docs/`: design, requirements, usage notes; update when behavior changes.
- `examples/`: reference setups (e.g., `examples/claude-agent-tutorial`).
- `tests/`: `pytest` suites for config, context, runtime, and guidelines.
- Runtime scratch files: `.doc_history` (REPL history) and `images/` for downloaded assets.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate`: start a local dev shell.
- `pip install -e .`: editable install of the CLI and dependencies.
- `dogent` (or `python -m dogent.cli`): launch REPL; use `/init`, `/config`, `/todo`, `/info`, `/exit`.
- `python -m pytest`: run all tests; `python -m pytest tests/test_config.py -k model` to focus locally.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indent, type hints everywhere; prefer `pathlib.Path` and small async helpers for I/O.
- Modules/files stay `snake_case`; prompt templates live in `src/dogent/prompts/` with matching names.
- Keep user-facing strings concise; existing CLI copy is Simplified Chinese—follow that tone unless documenting for developers.
- Avoid hidden globals; surface options through `Settings` (`config.py`) and pass state explicitly.

## Testing Guidelines
- Framework: `pytest`; name tests `test_*.py` under `tests/`.
- Keep tests hermetic: use `TemporaryDirectory`, set env vars per-case, and avoid real Anthropic calls by mocking SDK interactions.
- When checking UI output, assert stable substrings rather than full panels to reduce churn.

## Commit & Pull Request Guidelines
- Commits: short, imperative summaries with optional scope prefix (e.g., `cli: add /help prompt`); include rationale in the body when behavior shifts.
- PRs: describe intent, user impact, and verification steps; attach terminal captures for notable UI changes.
- Link related issues/tasks; call out config/env changes (`.dogent/dogent.json`, `.dogent/dogent.md`) and update docs accordingly.

## Configuration & Security
- Secrets stay in env vars; never commit tokens or local configs. `.dogent/dogent.json` should remain ignored.
- Defaults favor DeepSeek (`deepseek-reasoner`, fallback `deepseek-chat`); override via env or `/config`.
- Agent write access is constrained to the project root; keep new file operations inside `cwd` and defend against destructive commands.
