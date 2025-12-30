# Dogent

CLI-based interactive writing agent built on the Claude Agent SDK. Dogent plans, researches, drafts, validates, and polishes long-form documents from the terminal.

## Features
- Interactive CLI (`dogent`) with `/init`, `/show`, `/clean`, `/archive`, `/help`, `/learn`, `/exit` (plus `!` for shell commands)
- System prompt + per-turn user prompt templates under `dogent/prompts/`
- Todo panel synced to `TodoWrite` tool calls/results (no seeded todos)
- @file references list core file metadata; the agent calls MCP tools to read content or analyze media on demand
- Supports `.dogent/dogent.md` constraints, profiles in `~/.dogent/claude.json`, and env fallbacks
- Project-only lessons in `.dogent/lessons.md` (auto-captured after failures/interrupts; injected into prompt context)
- Ready for packaging via `pyproject.toml` with Rich-based UI

## Quick Start
1. Install: `pip install .` (Python 3.10+)
2. Run: `dogent` (or `dogent -h/-v`) in your project directory — ASCII banner shows model/API.
3. Commands:
   - `/init` → create/update `.dogent/dogent.md` and `.dogent/dogent.json` (template picker or wizard)
   - `/show history` → show recent history entries and the latest todo snapshot
   - `/clean` → clean workspace state (`/clean [history|lesson|memory|all]`; defaults to `all`)
   - `/archive` → archive history/lessons to `.dogent/archives` (`/archive [history|lessons|all]`; defaults to `all`)
   - `/help` → display current model/API/LLM profile/web profile plus available commands and shortcuts
   - `/learn` → save a lesson (`/learn <text>`) or toggle auto prompt (`/learn on|off`)
   - `/show lessons` → show recent lessons and where to edit `.dogent/lessons.md`
   - `/exit` → quit
   - Typing `/` shows command suggestions; typing `@` offers file completions; `!<command>` runs a shell command; press Esc during a task to interrupt and save progress
4. Reference files with `@path/to/file` in your message; Dogent injects file metadata and uses MCP tools on demand to read/understand content. Tool results (e.g., WebFetch/WebSearch) show clear success/failure panels with reasons.

## Configuration
- Project config: `.dogent/dogent.json` (`llm_profile`, `web_profile`, `vision_profile`, `doc_template`, `learn_auto`)
- Global profiles: `~/.dogent/claude.json` with named profiles (see `docs/usage.md` for JSON examples)
- Vision profiles: `~/.dogent/vision.json` with named vision providers (GLM-4.6V supported initially)
- Env fallback: `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `API_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
- History is stored in `.dogent/history.json` (structured JSON, managed automatically); temporary scratch lives in `.dogent/memory.md` when created on demand.

## Web Search Setup (Release 0.6)

Dogent supports custom web search providers (Google CSE / Bing / Brave) via `~/.dogent/web.json` and `.dogent/dogent.json` `web_profile`. See `docs/usage.md` for setup steps and examples.

## Vision Setup (Release 0.9.6)

Dogent can analyze images and videos via `mcp__dogent__analyze_media` when the agent needs it.

`~/.dogent/vision.json` is created on first run. Edit the `api_key` and select the profile in `.dogent/dogent.json`:

```json
{
  "vision_profile": "glm-4.6v"
}
```

Example `~/.dogent/vision.json`:

```json
{
  "profiles": {
    "glm-4.6v": {
      "provider": "glm-4.6v",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      "api_key": "replace-me",
      "model": "glm-4.6v"
    }
  }
}
```

## Templates & Parameters
- Prompt and default config templates are shipped inside the package.
- Document templates live in `.dogent/templates` (workspace), `~/.dogent/templates` (global), and `dogent/templates/doc_templates` (built-in fallback).
  - Workspace templates use the plain name (e.g., `resume`).
  - Global templates require the `global:` prefix (e.g., `global:resume`).
  - Built-in templates require the `built-in:` prefix (e.g., `built-in:resume`).
  - `general` means no template is selected and uses the built-in `doc_template_general.md`.
  - Unprefixed names resolve only in the workspace (except `general`).
- Template placeholders you can use (unknown or empty values render as empty strings and emit a warning):
  - `working_dir`, `preferences`
  - `doc_template` (resolved content from the configured document template)
  - `history` (raw `.dogent/history.json`), `history:last`/`history_block` (recent entries)
  - `memory`
  - `lessons` (raw `.dogent/lessons.md`)
  - `todo_block`/`todo_list`
  - `user_message`, `attachments` (JSON metadata for @file references)
  - `config:<key>` for any field in `.dogent/dogent.json` (supports dotted paths such as `config:anthropic.base_url`)

## Writing Expectations
- Defaults to Chinese + Markdown, with citations collected at the end
- For image downloads, pass a workspace-relative `output_dir` to `dogent_web_fetch` (e.g., `./images`) and reference the returned Markdown snippet
- Uses `.dogent/memory.md` for scratch notes only when needed; `.dogent/history.json` records progress for continuity

Default doc template: when `doc_template=general`, Dogent injects `dogent/templates/doc_templates/doc_template_general.md` into the system prompt.

## Development Notes
- All prompt text lives in `dogent/prompts/` for manual tuning
- Tests: `python -m unittest discover -s tests -v`
- Stories and acceptance: `docs/todo.md`
- Usage guide: `docs/usage.md`
