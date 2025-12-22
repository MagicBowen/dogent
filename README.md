# Dogent

CLI-based interactive writing agent built on the Claude Agent SDK. Dogent plans, researches, drafts, validates, and polishes long-form documents from the terminal.

## Features
- Interactive CLI (`dogent`) with `/init`, `/config`, `/history`, `/clean`, `/help`, `/learn`, `/lessons`, `/exit`
- System prompt + per-turn user prompt templates under `dogent/prompts/`
- Todo panel synced to `TodoWrite` tool calls/results (no seeded todos)
- @file references load workspace files into each turn
- Supports `.dogent/dogent.md` constraints, profiles in `~/.dogent/claude.json`, and env fallbacks
- Project-only lessons in `.dogent/lessons.md` (auto-captured after failures/interrupts; injected into prompt context)
- Ready for packaging via `pyproject.toml` with Rich-based UI

## Quick Start
1. Install: `pip install .` (Python 3.10+)
2. Run: `dogent` (or `dogent -h/-v`) in your project directory — ASCII banner shows model/API.
3. Commands:
   - `/init` → scaffold `.dogent/dogent.md`
   - `/config` → create `.dogent/dogent.json` (`llm_profile` + `web_profile`; actual creds in `~/.dogent/claude.json` or env)
   - `/history` → show recent history entries and the latest todo snapshot
   - `/clean` → clean workspace state (`/clean [history|lesson|memory|all]`; defaults to `all`)
   - `/help` → display current model/API/LLM profile/web profile plus available commands and shortcuts
   - `/learn` → save a lesson (`/learn <text>`) or toggle auto prompt (`/learn on|off`)
   - `/lessons` → show recent lessons and where to edit `.dogent/lessons.md`
   - `/exit` → quit
   - Typing `/` shows command suggestions; typing `@` offers file completions; press Esc during a task to interrupt and save progress
4. Reference files with `@path/to/file` in your message; Dogent injects their contents. Tool results (e.g., WebFetch/WebSearch) show clear success/failure panels with reasons.

## Configuration
- Project config: `.dogent/dogent.json` (`llm_profile`, `web_profile`, and `learn_auto` (toggled by `/learn on|off`))
- Global profiles: `~/.dogent/claude.json` with named profiles (see `docs/usage.md` for JSON examples)
- Env fallback: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `API_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
- History is stored in `.dogent/history.json` (structured JSON, managed automatically); temporary scratch lives in `.dogent/memory.md` when created on demand.

## Web Search Setup (Release 0.6)

Dogent supports custom web search providers (Google CSE / Bing / Brave) via `~/.dogent/web.json` and `.dogent/dogent.json` `web_profile`. See `docs/usage.md` for setup steps and examples.

## Templates & Parameters
- On first run, Dogent copies default prompts/config templates into `~/.dogent/prompts` and `~/.dogent/templates`. Edit these to tune prompts (`system.md`, `user_prompt.md`) or defaults (`dogent_default.md`, `dogent_default.json`, `claude_default.json`).
- `/init` and `/config` generate workspace files from the templates under `~/.dogent/templates`; prompt rendering also reads from `~/.dogent/prompts`.
- Template placeholders you can use (unknown or empty values render as empty strings and emit a warning):
  - `working_dir`, `preferences`
  - `history` (raw `.dogent/history.json`), `history:last`/`history_block` (recent entries)
  - `memory`
  - `lessons` (raw `.dogent/lessons.md`)
  - `todo_block`/`todo_list`
  - `user_message`, `attachments` (rendered @file content)
  - `config:<key>` for any field in `.dogent/dogent.json` (supports dotted paths such as `config:anthropic.base_url`)

## Writing Expectations
- Defaults to Chinese + Markdown, with citations collected at the end
- For image downloads, pass a workspace-relative `output_dir` to `dogent_web_fetch` (e.g., `./images`) and reference the returned Markdown snippet
- Uses `.dogent/memory.md` for scratch notes only when needed; `.dogent/history.json` records progress for continuity

## Development Notes
- All prompt text lives in `dogent/prompts/` for manual tuning
- Tests: `python -m unittest discover -s tests -v`
- Stories and acceptance: `docs/todo.md`
- Usage guide: `docs/usage.md`
