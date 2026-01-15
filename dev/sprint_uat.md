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

## Release 0.9.19

### Story 1 – Image Generation Profiles + CLI Selection
1) Add an `image_profiles` entry in `~/.dogent/dogent.json` with a valid API key.
2) Run `dogent` in a workspace and execute `/profile image <name>`; verify `.dogent/dogent.json` stores `"image_profile": "<name>"`.
3) Run `/profile show`; verify the Image row shows the selected profile.
4) Restart `dogent`; verify the banner includes the Image profile.

User Test Results: PASS

### Story 2 – Image Generation Tool
1) Ensure `.dogent/dogent.json` has `image_profile` set to a valid profile.
2) In `dogent`, ask the agent to generate an image with size `1280x1280` and save to `assets/images/test.png`; verify the file exists and the tool output shows the saved path.
3) Ask the agent to generate another image without specifying `output_path`; verify a file appears under `assets/images/dogent_image_<timestamp>.<ext>`.

User Test Results: PASS
