# Example Usage Walkthrough

1) Environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="xxx"
export ANTHROPIC_MODEL="deepseek-reasoner"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
export API_TIMEOUT_MS=600000
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

2) Start the CLI
```
dogent
```

3) Seed project rules and config
```
/init          # creates .dogent/dogent.md template (edit it to match your tone and structure)
/config        # writes .dogent/dogent.json and updates .gitignore
```

4) Ask for a sample document
```
写一份针对本项目的设计概览，包含目标、架构、关键模块，并引用 @requirements.md
```

5) Inspect tasks and info
```
/todo          # shows current todo list
/info          # shows SDK-reported tools and commands
```

Notes:
- Edit `.dogent/dogent.md` to tighten the writing rules; rerun prompts to apply.
- Use `@` to reference files; the agent will load their content into context.
- Use Ctrl+C to interrupt a long run; `/exit` to quit.
