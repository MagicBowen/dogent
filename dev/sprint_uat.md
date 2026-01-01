# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

User Test Results Status: Pending | Accepted | Rejected

---

## Release 0.9.8
### Story 1 – Layered Config Defaults
1) Ensure `~/.dogent/dogent.json` exists; set `"web_profile": "default"` and `"doc_template": "general"`; leave out `llm_profile`.
2) In `sample/`, delete any existing `sample/.dogent/dogent.json`.
3) Run `dogent` in `sample/` and execute `/init`.
4) Verify `sample/.dogent/dogent.json` includes global defaults and does not add `llm_profile`.
5) Edit `sample/.dogent/dogent.json` and override `doc_template` or `primary_language`; restart `dogent` and confirm the override applies.

User Test Results: PASS

### Story 2 – Vision Disabled by Default
1) In `sample/.dogent/dogent.json`, set `"vision_profile": null`.
2) Start `dogent` and reference an image with `@images/sample.png` (or any existing image).
3) Confirm Dogent shows a fail-fast error and does not proceed to the LLM.
4) Set `vision_profile` to a valid profile and retry; confirm the request proceeds and vision tool is available.

User Test Results: PASS

### Story 3 – Prompt-Level Doc Template Override
1) In `sample/.dogent/templates/`, add a template `demo.md` with a recognizable intro line.
2) Start `dogent` and type `@@` to confirm the template list appears; choose `demo`.
3) Submit a prompt with `@@demo` and verify the template applies only to that request.
4) Send another prompt without `@@`; confirm it uses the configured `doc_template` in `sample/.dogent/dogent.json`.

User Test Results: PASS

### Story 4 – Unified Global Config File
1) Delete any existing `~/.dogent/claude.json`, `~/.dogent/web.json`, and `~/.dogent/vision.json`.
2) Start `dogent` once; confirm only `~/.dogent/dogent.json` is created.
3) Edit `~/.dogent/dogent.json` to add a `llm_profiles` entry and set `.dogent/dogent.json` `llm_profile` to it; confirm Dogent loads the profile.
4) Add a `web_profiles` entry and set `.dogent/dogent.json` `web_profile` to it; confirm custom web tools register.
5) Add a `vision_profiles` entry and set `.dogent/dogent.json` `vision_profile` to it; confirm vision tool is available.

User Test Results: PASS

### Story 5 – Versioned Global Config Upgrade
1) In `~/.dogent/dogent.json`, set `"version"` to `"0.0.1"` and remove a known top-level key (e.g., delete `vision_profiles`).
2) Start `dogent`; confirm a warning or upgrade message appears.
3) Re-open `~/.dogent/dogent.json`; confirm the missing key was added and `"version"` updated to the current Dogent version.
4) Set `"version"` to a higher value (e.g., `"99.0.0"`) and restart `dogent`; confirm a warning about newer config version appears.

User Test Results: PASS

---

## Release 0.9.9
### Story 1 – Configurable PDF Style
1) Start `dogent` once to ensure `~/.dogent/pdf_style.css` is created.
2) Edit `~/.dogent/pdf_style.css` to apply a visible change (e.g., `body { font-size: 18pt; }`).
3) In `sample/`, create a simple markdown file and request a PDF export (via prompt or tool). Confirm the PDF reflects the global style.
4) Create `sample/.dogent/pdf_style.css` with a different visible style (e.g., `body { font-size: 10pt; }`).
5) Export to PDF again; confirm the workspace style overrides the global style.
6) Optional: make `sample/.dogent/pdf_style.css` unreadable and export again; confirm Dogent warns and falls back to the global style.

User Test Results: PASS

### Story 2 – Template Override in User Prompt
1) In `sample/.dogent/templates/`, add a template `override.md` with a recognizable line (e.g., `## Introduction` content).
2) Start `dogent` and submit a prompt like `@@override Draft a short report`.
3) Confirm the system prompt does not include the override template content (optional: enable debug/logging if available).
4) Confirm the user prompt includes a "Template Remark" section containing the override template content.
5) Verify the response follows the override template even if `.dogent/dogent.json` or `.dogent/dogent.md` specify a different template.

User Test Results: PASS

### Story 3 – Graceful Exit Without Pipe Errors
1) Start `dogent` and run `/exit`.
2) Confirm the CLI exits without any `EPIPE` or write errors.
3) Optional: run `dogent` in a piped environment (e.g., inside a wrapper/PTY) and repeat `/exit`.

User Test Results: PASS
