# User Stories Backlog

Example:

```
### Story 1: Package & Entrypoint
- User Value: Installable CLI command `dogent` exists.
- Acceptance: `pip install .` exposes `dogent`; running shows welcome prompt; `dogent -h/-v` work.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: Manual install/run check.
```

Status legend — Dev: Todo / In Progress / Done; Acceptance: Pending / Accepted / Rejected
 
---

## Release 0.9.19

### Story 1: Image Generation Profiles + CLI Selection
- User Value: Users can configure image generation providers and select them via `/profile` without editing JSON manually.
- Acceptance:
  - Global config supports `image_profiles` in `~/.dogent/dogent.json`; workspace config supports `image_profile`.
  - `/profile image` lists available image profiles; `/profile image <name>` updates `.dogent/dogent.json`.
  - `/profile show` includes Image profile, and the banner shows the current image profile.
  - If no image profiles exist, `none` sets `image_profile` to `null`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT passed in dev/sprint_uat.md.

### Story 2: Image Generation Tool
- User Value: The agent can generate images via a tool and save them in the workspace.
- Acceptance:
  - New tool `mcp__dogent__generate_image` with params `prompt`, `size` (default `1280x1280`), `watermark_enabled` (default true), `output_path` (optional).
  - Validates `size` as `WxH` within 512-2048 and multiples of 32.
  - Missing `output_path` saves to `./assets/images/dogent_image_<timestamp>.<ext>`; extension derived from response content type, fallback `.png`.
  - Downloads the returned URL and writes to the workspace; returns the URL and saved path in tool output.
  - Missing or placeholder API key returns a clear config error referencing `image_profiles`.
- Dev Status: Done
- Acceptance Status: Accepted
- Verification: UAT passed in dev/sprint_uat.md.
