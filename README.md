# Dogent (Claude Agent SDK)

Interactive CLI (`dogent`) for professional long-form document creation using the Claude Agent SDK.

## Quick Start (with venv)
1) Create venv and install:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
2) Export model settings (or run `/config` inside the REPL):
```
export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="xxx"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```
3) Run: `dogent`
4) In the REPL:
- `/init` seeds `.claude.md` doc rules (edit to your preferences).
- `/config` writes `.doc-config.yaml` and updates `.gitignore`.
- `/todo` shows tasks; `/info` shows available tools/commands; `/exit` quits.

## Features
- Claude Code-like REPL with Rich UI, todo panel, and streaming responses.
- Uses `.claude.md` for project writing rules; loads `.claude/` skills/agents/plugins.
- Supports `@file` references with completions and inline resolution.
- Document workflow: planning, research, drafting, validation, polishing; Chinese Markdown by default.
- Image downloads to `./images`, citations aggregation, and optional `.memory.md` scratchpad.

See `docs/design.md` and `docs/implementation_plan.md` for full details.

## Example session
```
# in project root
source .venv/bin/activate
dogent

# inside REPL
/init          # create .claude.md template
/config        # save local model/token config (overrides env)
写一份关于本项目目标和架构的简要说明，引用 @requirements.md
```
You should see streaming output and a todo panel. Edit `.claude.md` to tighten style/tone, then re-run prompts. Use Ctrl+C to interrupt long runs; `/todo` to review tasks.

## Testing
- Install dev deps and run: `python -m pytest`
- Smoke test manually: `dogent` then `/info` to confirm Claude Agent SDK connectivity and tools.
