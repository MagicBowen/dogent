# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Pending
```

---

## Release 0.9.21
### Story 1 – Auto-create workspace config/history on first launch
1) Create a fresh workspace: `mkdir -p sample/uat_0921_auto_init` and ensure `sample/uat_0921_auto_init/.dogent` does not exist.
2) Run `dogent` from `sample/uat_0921_auto_init`.
3) Expect: no init prompt; you see the normal Dogent prompt.
4) In another terminal, confirm `sample/uat_0921_auto_init/.dogent/dogent.json` exists.
5) Confirm `sample/uat_0921_auto_init/.dogent/history.json` exists and contains an empty JSON list (`[]`).

User Test Results: Accepted (2026-01-30)

### Story 2 – Add poe-claude profile to global template + docs
1) Open `dogent/resources/dogent_global_default.json` and verify `llm_profiles.poe-claude` exists with the Poe base URL and model fields.
2) (Optional) Move `~/.dogent/dogent.json` aside, then run `dogent` once from `sample/uat_0921_poe` to regenerate; verify the new `~/.dogent/dogent.json` includes `poe-claude`.
3) Confirm `docs/08-configuration.md` and `docs/12-appendix.md` mention `poe-claude`.

User Test Results: Accepted (2026-01-30)
