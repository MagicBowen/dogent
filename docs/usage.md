# Dogent Usage Guide

## Install
- Ensure Python 3.10+ is available.
- From the project root: `pip install .`
- The CLI will be available as `dogent`.

## First Run
1. Navigate to your project directory.
2. Run `dogent` (or `dogent -h` for help) to enter the interactive shell; an ASCII banner and model/API info are shown.
3. If `.dogent/dogent.json` is missing, Dogent will prompt to initialize the workspace before handling requests.
4. Use `/init` to generate `.dogent/dogent.md` and `.dogent/dogent.json` (template picker or wizard).

## Credentials & Profiles
- Global config: `~/.dogent/dogent.json` (workspace defaults + profiles; auto-created on first run).
- Local config: `.dogent/dogent.json` (overrides global workspace defaults for the current workspace).
- JSON schema: `~/.dogent/dogent.schema.json` (for editor validation).
- Example `~/.dogent/dogent.json`:
  ```json
  {
    "$schema": "./dogent.schema.json",
    "version": "0.9.8",
    "workspace_defaults": {
      "web_profile": "default",
      "vision_profile": null,
      "doc_template": "general",
      "primary_language": "Chinese",
      "learn_auto": true
    },
    "llm_profiles": {
      "deepseek": {
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_AUTH_TOKEN": "replace-me",
        "ANTHROPIC_MODEL": "deepseek-reasoner",
        "ANTHROPIC_SMALL_FAST_MODEL": "deepseek-chat",
        "API_TIMEOUT_MS": 600000,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
      }
    },
    "web_profiles": {
      "google": {
        "provider": "google_cse",
        "api_key": "replace-me",
        "cse_id": "replace-me",
        "timeout_s": 20
      }
    },
    "vision_profiles": {
      "glm-4.6v": {
        "provider": "glm-4.6v",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "api_key": "replace-me",
        "model": "glm-4.6v"
      }
    }
  }
  ```

- `llm_profile` can be set in `.dogent/dogent.json`; if missing, Dogent falls back to environment variables.
- Debug logs are written when `.dogent/dogent.json` sets `"debug": true` (see Debug Logging below).

## Debug Logging (Release 0.9.9)
- Set `"debug": true` in `.dogent/dogent.json` to capture JSONL logs for every LLM call.
- Log files are written to `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json`.
- Each entry includes `role`, `source`, `event`, and `content`. System prompts are logged once per source unless they change.

## Document Templates (Release 0.8.0)

- Workspace templates: `.dogent/templates/<name>.md` (use `<name>` in `doc_template`)
- Global templates: `~/.dogent/templates/<name>.md` (use `global:<name>` in `doc_template`)
- Built-in templates: `dogent/templates/doc_templates/<name>.md` (use `built-in:<name>` in `doc_template`)
- General template: `dogent/templates/doc_templates/doc_general.md` (use `general` when no template is selected)
- Unprefixed names resolve only in the workspace.
When `doc_template=general`, Dogent uses `dogent/templates/doc_templates/doc_general.md` as the default template content in prompts.
- For a one-off template override in the prompt, use `@@<template>` (e.g., `@@global:resume`). This does not update config files.

## Web Search Setup (Release 0.6)

Dogent supports two modes:

- Native mode (default): if `.dogent/dogent.json` has no `web_profile` (or it is empty/`"default"`), Dogent uses Claude Agent SDK’s built-in `WebSearch` / `WebFetch`.
- Custom mode: if `.dogent/dogent.json` sets `web_profile` to a real profile name that exists in `~/.dogent/dogent.json` under `web_profiles`, Dogent uses the custom tools `dogent_web_search` / `dogent_web_fetch` (tool IDs: `mcp__dogent__web_search` / `mcp__dogent__web_fetch`) with your configured provider.

If you set `web_profile` to a name that does not exist in `~/.dogent/dogent.json`, Dogent warns at startup and falls back to native mode.

### Configure `~/.dogent/dogent.json` (web_profiles)

Dogent creates `~/.dogent/dogent.json` on first run. It stores named search provider profiles under `web_profiles`:

```json
{
  "web_profiles": {
    "google": {
      "provider": "google_cse",
      "api_key": "replace-me",
      "cse_id": "replace-me",
      "timeout_s": 20
    },
    "bing": {
      "provider": "bing",
      "api_key": "replace-me",
      "endpoint": "https://api.bing.microsoft.com/v7.0",
      "timeout_s": 20
    },
    "brave": {
      "provider": "brave",
      "api_key": "replace-me",
      "endpoint": "https://api.search.brave.com/res/v1",
      "timeout_s": 20
    }
  }
}
```

Dogent sends `User-Agent: dogent/<version>` automatically; you typically don't need to configure a user agent.

Then select one profile per workspace in `.dogent/dogent.json`:

```json
{
  "web_profile": "brave"
}
```

### Google Custom Search (google_cse) — Apply & Configure

1. Create a Google Cloud project.
2. Enable the **Custom Search API** (JSON API).
3. Create an API key.
4. Create a **Programmable Search Engine** (Custom Search Engine) and get its **Search engine ID** (also called `cx`).
5. Put the values into `~/.dogent/dogent.json` under `web_profiles` (e.g., `google`) and set `.dogent/dogent.json` `web_profile` to `"google"`.

Notes:
- For image search, ensure your Programmable Search Engine is configured to search the web (or the sites you need).
- Treat API keys as secrets; do not commit them into your repo.

### Brave Search API (brave) — Apply & Configure

1. Sign up for Brave Search API access (Brave developer/portal) and create a subscription.
2. Create an API key (token).
3. Put the token into `~/.dogent/dogent.json` under `web_profiles` (e.g., `brave`):

```json
{
  "web_profiles": {
    "brave": {
      "provider": "brave",
      "api_key": "YOUR_BRAVE_API_KEY",
      "endpoint": "https://api.search.brave.com/res/v1",
      "timeout_s": 20
    }
  }
}
```

4. Set `.dogent/dogent.json` `web_profile` to `"brave"` and restart `dogent`.

Notes:
- Dogent sends the token using the `X-Subscription-Token` request header.
- Web and image searches return structured results; image downloads return a Markdown snippet using the path you provided.

## Vision Setup (Release 0.9.6)

Dogent can analyze images and videos on demand via `mcp__dogent__analyze_media`.

`~/.dogent/dogent.json` is created on first run. Vision is disabled by default (`vision_profile: null`). To enable it, edit the `api_key` under `vision_profiles` and select the profile in `.dogent/dogent.json`:

```json
{
  "vision_profile": "glm-4.6v"
}
```

Example `~/.dogent/dogent.json` snippet:

```json
{
  "vision_profiles": {
    "glm-4.6v": {
      "provider": "glm-4.6v",
      "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      "api_key": "replace-me",
      "model": "glm-4.6v"
    }
  }
}
```

## Commands Inside the CLI
- `/init` – generate `.dogent/dogent.md` and `.dogent/dogent.json` (template picker or wizard).
- `/learn` – save a lesson (`/learn <text>`) or toggle the automatic prompt (`/learn on|off`).
- `/show history` – show recent history entries and the latest todo snapshot.
- `/show lessons` – show recent lessons and where to edit `.dogent/lessons.md`.
- `/clean` – clean workspace state (`/clean [history|lesson|memory|all]`; defaults to `all`).
- `/archive` – archive history/lessons to `.dogent/archives` (`/archive [history|lessons|all]`; defaults to `all`).
- `/exit` – leave the CLI.
- Typing `/` shows live command suggestions; typing `@` offers file completions; typing `@@` offers template completions; `!<command>` runs a shell command.
- Press `Esc` during an in-progress task to interrupt; progress is saved to `.dogent/history.json`.

## Markdown Editor (Release 0.9.10)
- Default input stays single-line for the main prompt and free-form clarification answers.
- Press Ctrl+E to open the multiline Markdown editor (also opens automatically for "Other (free-form answer)").
- In the editor: Enter inserts new lines; Ctrl+Enter submits (fallback Ctrl+J shown in the footer); Ctrl+Q returns.
- Ctrl+P toggles a read-only full preview; press Esc to return to edit mode.
- If you return with dirty content, Dogent prompts to Discard/Submit/Save/Cancel; Save accepts relative or absolute paths and confirms overwrite.

## Safety & Permissions (Release 0.9.7)
- Dogent prompts for confirmation before any built-in `Read`/`Write`/`Edit` tool accesses paths outside the workspace.
- Delete commands (`rm`, `rmdir`, `del`) require confirmation before execution.
- Denied permissions abort the current task with an `aborted` status.
- Prompts show inline `yes   no` choices; use left/right (or up/down) to switch and Enter to accept the default.

## Referencing Files
- Inline `@` references attach file metadata to the prompt (path/name/type), e.g. `Review @docs/plan.md`.
- The agent calls `mcp__dogent__read_document` for text/doc files or `mcp__dogent__analyze_media` for images/videos when it needs content.
- If `vision_profile` is `null` (or missing), image/video references fail fast and you must enable vision first.

## Working With Todos
- The agent uses the `TodoWrite` tool; Dogent mirrors its outputs with emoji statuses and concise logs.
- No default todos are created; the list always reflects the latest TodoWrite result.

## Lessons (Release 0.7.0)
- Lessons live in `.dogent/lessons.md` (project-only, user-editable) and are injected into prompt context on every new task.
- When a run ends with `❌ Failed` or `⛔ Interrupted`, Dogent prompts on your next message with an inline yes/no selector (default **yes**).
- Use `/learn off` to disable the automatic prompt (saved to `.dogent/dogent.json`; you can still use `/learn <text>` any time).

## Document Writing Expectations
- Defaults: Chinese, Markdown, citations at the end.
- For image downloads, choose an output directory per call (e.g., `./images`) and pass it to `dogent_web_fetch`.
- The system prompt enforces planning, research (including online search), sectioned drafting, validation, and final polishing; history in `.dogent/history.json` provides continuity.
- Temporary notes go to `.dogent/memory.md` only when needed—create on demand and clean after use.

## Running Tests
- From the project root: `python -m unittest discover -s tests -v`
- Tests cover config/profile merge, prompt assembly, and todo syncing behavior.
