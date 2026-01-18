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

---

## Release 0.9.20

### Story 1: Dependency Precheck + Manual Install Guidance for Document Tools
- User Value: Users immediately see missing dependencies for document tools and clear OS-specific manual install steps instead of waiting.
- Acceptance:
  - Before `mcp__dogent__export_document`, `mcp__dogent__read_document`, and `mcp__dogent__convert_document` run, Dogent checks required dependencies for the target format(s).
  - If dependencies are missing in interactive mode, Dogent prompts with Install now / Install manually / Cancel.
  - Choosing Install manually aborts the task and shows OS-specific install commands for each missing dependency.
  - Document IO no longer auto-downloads dependencies without user confirmation.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: UAT in dev/sprint_uat.md.

### Story 2: Auto-Install with Progress + Continue Execution
- User Value: Users can let Dogent install missing dependencies with visible progress and continue the tool automatically.
- Acceptance:
  - Choosing Install now runs installers with real percent progress for each step.
  - In noninteractive mode, Dogent auto-installs missing dependencies; on failure, it exits with manual install instructions.
  - After successful install, the tool proceeds without requiring re-run.
- Dev Status: Done
- Acceptance Status: Pending
- Verification: UAT in dev/sprint_uat.md.
