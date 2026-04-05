# Original Requirements

---

## Release 0.9.29

- The built-in Dogent MCP tools currently fail under the latest installed Claude Agent SDK and MCP package combination. For example, `mcp__dogent__read_document` and `mcp__dogent__web_fetch` are listed but always return an MCP tool error before their business logic runs. Fix this against the latest SDK and interface behavior instead of adding backward-compatibility code for older interfaces.
- Align Dogent's in-process MCP server registration with the latest Claude Agent SDK / MCP low-level server contract so all built-in Dogent MCP tools can be listed and called successfully.
- Verify all built-in Dogent MCP tools provided by Dogent itself, including document, UI, web, vision, and image tools, can be invoked correctly through the MCP round-trip path.
- Add automated tests that exercise the real `tools/list` and `tools/call` flow for Dogent's MCP tools, not only direct Python-level tool objects.
- Ensure the full `python -m unittest discover -s tests -v` suite passes after the fix.
- Clean up any credential-like values accidentally left in repo default config templates and replace them with placeholders before release.

---

## Release 0.9.28

- Refactor the current document template format into a standard format consistent with the standard Agent Skill (refer to the directory and file format introduction for skills in `claude/skills/skills/skill-creator`). Rewrite the existing document templates into the new format. The code will only support the new standard format; no compatibility with the old format is required. From now on, in Dogent, the only difference between document templates and skills is their location (document templates are specific skills placed in the corresponding directory under `.dogent`).
- The new document template structure should be able to separate the template introduction, usage scenarios, output format, and other information by referring to the skill specifications, and place them into different files and directories. Meanwhile, it should also support users during the `init` or `@@` reference process to specify the required template through a dropdown list.
- Refer to `claude/skills/skills/skill-creator` to write a built-in skill for Dogent that can specifically generate document templates. At the same time, implement a built-in command for Dogent that allows users to trigger the corresponding skill with one click to assist in generating or optimizing the relevant document templates.
- Users should be able to enter free text directly after `/template create` to describe the template requirements and related information that should be used for generation.

---

## Pending Requirements

[support more document template]
- resume
- research report
- blog
- software design document
- software usage manual
- consultant proposal

[support mutiple language]
- support multiple languages: en & zh;
