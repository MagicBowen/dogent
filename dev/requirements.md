# Original Requirements

---

## Release 0.9.9

- All scenarios that require user selection and confirmation (overwrite dogent.md after /init, save lesson, authorize file access/deletion, start writing now, initialize now) must use the same CLI UI as clarification: options selected via up/down with Enter to confirm and Esc to cancel. Non-interactive fallback keeps y/n input. When allowing the user to make a selection, if the agent client itself has not ended, the current agent loop should not be interrupted. The Esc listener should be paused/stopped while a selection prompt is open and restarted after it exits.
- Clarification questions: prefer multiple-choice options whenever reasonable (but do not force options if not appropriate). When answering, Esc skips the current question and the answer is recorded as `user chose not to answer this question`; Ctrl+C cancels the entire clarification flow and aborts the current task. For "Other (free-form answer)", immediately prompt the user to enter the free-form answer after selection using `Other (free-form answer): `. If clarification JSON appears in a thinking block, it should still be parsed and used to enter the QA UI, and the thinking panel should be suppressed for that block.
- Add `debug: false` to dogent.json. When enabled, save each finalized prompt and raw streaming content returned by the LLM in chronological order to `.dogent/logs/dogent_session_YYYYmmdd_HHMMSS.json` in JSONL format. Each entry includes a role field (`system`, `user`, `assistant`, `tool`) and the log captures all LLM calls (main agent, init wizard, lesson drafter). If the system prompt has not changed, record it only once per session.
- Update /init prompt flow: no changes to init_wizard system prompt. After initialization finishes (including the overwrite prompt), ask whether to start writing directly. If Yes, construct the prompt: `The user has initialized the current dogent project, and the user's initialization prompt is "<prompt>". Please continue to fulfill the user's needs.` and start the writing agent. If No or Esc, exit the init flow and return to the CLI.
- New requirement: when a user makes a request and `.dogent/dogent.json` does not exist, first ask whether to initialize. If Yes, run the same /init prompt wizard flow using the user's request as the init prompt, then ask whether to start writing (same as above). If No, proceed with the current default processing. If Esc, cancel and return to the CLI. The default selection for this initialize prompt should be Yes.

---

## Pending Requirements

- Dogent supports more excellent file templates;
- Dogent supports configuring Claude's commands, subagents, and skills;
- Dogent supports loading Claude's plugins;
- Dogent supports mdbook's skill (using the capability of external skill configuration);
- Provide a good solution for model context overflow;
- Dogent supports the ability to generate images;
