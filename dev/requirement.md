# Original Requirements

---

## Release 0.9.21

- When entering dogent for the first time in a folder, in addition to creating `dogent/history.json` by default, `dogent/dogent.json` will also be created;
- add the `poe-claude` below to the `llm_profiles` in the template file for default configuration file `~/.dogent/dogent.json`:

```json
    "poe-claude": {
      "ANTHROPIC_BASE_URL": "https://api.poe.com",
      "ANTHROPIC_AUTH_TOKEN": "replace-me",
      "ANTHROPIC_MODEL": "Opus",
      "ANTHROPIC_SMALL_FAST_MODEL": "Sonnet",
      "API_TIMEOUT_MS": 600000,
      "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": true
    }
```

---

## Pending Requirements

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual

[support more generation mode]
- Dogent supports the ability to generate PPT;

[support mutiple language]
- support multiple languages: en & zh;
