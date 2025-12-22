# Dogent Usage Guide

## Install
- Ensure Python 3.10+ is available.
- From the project root: `pip install .`
- The CLI will be available as `dogent`.

## First Run
1. Navigate to your project directory.
2. Run `dogent` (or `dogent -h` for help) to enter the interactive shell; an ASCII banner and model/API info are shown.
3. Use `/init` to generate `.dogent/dogent.md`.
4. Use `/config` to scaffold `.dogent/dogent.json` (`llm_profile` and `web_profile`); edit `llm_profile` or `web_profile` (or supply env vars for credentials).

## Credentials & Profiles
- Local config: `.dogent/dogent.json` (`llm_profile` reference only).
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

## Web Search Setup (Release 0.6)

Dogent supports two modes:

- Native mode (default): if `.dogent/dogent.json` has no `web_profile` (or it is empty/`"default"`), Dogent uses Claude Agent SDK’s built-in `WebSearch` / `WebFetch`.
- Custom mode: if `.dogent/dogent.json` sets `web_profile` to a real profile name that exists in `~/.dogent/web.json`, Dogent uses the custom tools `dogent_web_search` / `dogent_web_fetch` (tool IDs: `mcp__dogent__web_search` / `mcp__dogent__web_fetch`) with your configured provider.

If you set `web_profile` to a name that does not exist in `~/.dogent/web.json`, Dogent warns at startup and falls back to native mode.

### Configure `~/.dogent/web.json`

Dogent creates `~/.dogent/web.json` on first run. It stores named search provider profiles:

```json
{
  "profiles": {
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
  "llm_profile": "deepseek",
  "web_profile": "brave"
}
```

### Google Custom Search (google_cse) — Apply & Configure

1. Create a Google Cloud project.
2. Enable the **Custom Search API** (JSON API).
3. Create an API key.
4. Create a **Programmable Search Engine** (Custom Search Engine) and get its **Search engine ID** (also called `cx`).
5. Put the values into `~/.dogent/web.json` under a profile (e.g., `google`) and set `.dogent/dogent.json` `web_profile` to `"google"`.

Notes:
- For image search, ensure your Programmable Search Engine is configured to search the web (or the sites you need).
- Treat API keys as secrets; do not commit them into your repo.

### Brave Search API (brave) — Apply & Configure

1. Sign up for Brave Search API access (Brave developer/portal) and create a subscription.
2. Create an API key (token).
3. Put the token into `~/.dogent/web.json` under a profile (e.g., `brave`):

```json
{
  "profiles": {
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

## Commands Inside the CLI
- `/init` – create writing constraint template and scratch memory.
- `/config` – generate config JSON for `llm_profile` and `web_profile`.
- `/exit` – leave the CLI.
- Typing `/` shows live command suggestions; typing `@` offers file completions.
- Press `Esc` during an in-progress task to interrupt; progress is saved to `.dogent/history.json`.

## Referencing Files
- Inline `@` references pull file contents into the prompt, e.g. `Review @docs/plan.md`.
- CLI prints which files were loaded; contents are injected into the user prompt; completions appear as soon as you type `@`.

## Working With Todos
- The agent uses the `TodoWrite` tool; Dogent mirrors its outputs with emoji statuses and concise logs.
- No default todos are created; the list always reflects the latest TodoWrite result.

## Document Writing Expectations
- Defaults: Chinese, Markdown, citations at the end.
- For image downloads, choose an output directory per call (e.g., `./images`) and pass it to `dogent_web_fetch`.
- The system prompt enforces planning, research (including online search), sectioned drafting, validation, and final polishing; history in `.dogent/history.json` provides continuity.
- Temporary notes go to `.dogent/memory.md` only when needed—create on demand and clean after use.

## Running Tests
- From the project root: `python -m unittest discover -s tests -v`
- Tests cover config/profile merge, prompt assembly, and todo syncing behavior.
