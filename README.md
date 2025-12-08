# Dogent

CLI-based interactive writing agent built on the Claude Agent SDK. Dogent plans, researches, drafts, validates, and polishes long-form documents from the terminal.

## Features
- Interactive CLI (`dogent`) with `/init`, `/config`, `/todo`, `/exit`
- System prompt + per-turn user prompt templates under `dogent/prompts/`
- Todo panel synced to `TodoWrite` tool calls/results (no seeded todos)
- @file references load workspace files into each turn
- Supports `.dogent/dogent.md` constraints, profiles in `~/.dogent/claude.json`, and env fallbacks
- Ready for packaging via `pyproject.toml` with Rich-based UI

## Quick Start
1. Install: `pip install .` (Python 3.10+)
2. Run: `dogent` (or `dogent -h/-v`) in your project directory
3. Commands:
   - `/init` → scaffold `.dogent/dogent.md`, `.dogent/memory.md`, `./images`
   - `/config` → create `.dogent/dogent.json` (profile reference; actual creds in `~/.dogent/claude.json` or env)
   - `/todo` → show current task list
   - `/exit` → quit
   - Typing `/` shows command suggestions; typing `@` offers file completions
4. Reference files with `@path/to/file` in your message; Dogent injects their contents.

## Configuration
- Project config: `.dogent/dogent.json` (profile reference only)
- Global profiles: `~/.dogent/claude.json` or `~/.dogent/claude.md` with named profiles (see `docs/usage.md` for JSON/Markdown examples)
- Env fallback: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `API_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`

## Writing Expectations
- Defaults to Chinese + Markdown, with citations collected at the end
- Downloads images to `./images` and references them with relative paths
- Uses `.dogent/memory.md` for scratch notes; clear it after use

## Development Notes
- All prompt text lives in `dogent/prompts/` for manual tuning
- Tests: `python -m unittest`
- Stories and acceptance: `docs/stories.md`
- Usage guide: `docs/usage.md`
