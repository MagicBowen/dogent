# Release 0.6 — Dogent Web Tools Design

This document describes the design for Dogent’s custom web tools that replace the unreliable native `WebSearch`/`WebFetch` tools.

## Goals

- Provide reliable web search and URL fetching as Claude Agent SDK tools.
- Support image discovery + image download into the configured `images_path`.
- Keep configuration user-editable under `~/.dogent`, with per-project selection in `.dogent/dogent.json`.
- Return tool results that are short, readable, and model-friendly (with truncation limits).

## Configuration

### Home config: `~/.dogent/web.json`

- Created automatically on first run (never overwritten on upgrade).
- Stores named provider profiles (similar to `~/.dogent/claude.json`).

Example shape:

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
    }
  }
}
```

### Workspace config: `.dogent/dogent.json`

- Selects a provider profile via `web_profile`.
- If unset/empty or set to `default`, Dogent falls back to the native `WebSearch`/`WebFetch` tools.
- If set to a name not found in `~/.dogent/web.json`, Dogent warns at startup and falls back to native tools.

```json
{
  "profile": "deepseek",
  "images_path": "./images",
  "web_profile": "google"
}
```

## Tools

Dogent registers an in-process SDK MCP server named `dogent`, exposing:

- `mcp__dogent__web_search`
- `mcp__dogent__web_fetch`

Native `WebSearch`/`WebFetch` are used when `web_profile` is empty or `default`.

### `mcp__dogent__web_search`

Inputs:

- `query` (required)
- `mode`: `web` or `image` (default `web`)
- `num_results`: `1..10` (default `5`)

Outputs:

- A JSON blob containing provider + profile metadata and normalized result objects.

Provider behavior:

- `google_cse`: uses Google Custom Search JSON API (`/customsearch/v1`), supports image search via `searchType=image`.
- `bing`: uses Bing Search v7 (`/search` and `/images/search`).

Error handling:

- Missing `web_profile`, missing provider config, placeholder credentials, or HTTP errors return `is_error=true` and an actionable message.

### `mcp__dogent__web_fetch`

Inputs:

- `url` (required)
- `mode`: `auto`, `text`, or `image` (default `auto`)
- `max_chars`: text truncation limit (default `12000`)
- `filename`: optional for image downloads

Behavior:

- Fetches the URL via HTTP GET with a configurable timeout and user agent.
- If the content is HTML, extracts readable text by stripping scripts/styles/navigation and normalizing whitespace.
- If the content is an image (or `mode=image`), saves it to `images_path` (creating the directory on demand) using a safe filename and returns a Markdown snippet.

Safety considerations:

- Only `http`/`https` URLs are allowed.
- Filenames are sanitized to avoid path traversal.
- Returned text is truncated to avoid excessive tool payload size.

## Known Limitations (Intentional for 0.6)

- “Core content” extraction is heuristic (HTML cleanup + whitespace normalization) and does not implement a full readability algorithm.
- No caching/rate-limit backoff logic beyond respecting configured timeouts.
- Image discovery relies on provider image search; parsing images from arbitrary pages is not implemented.
