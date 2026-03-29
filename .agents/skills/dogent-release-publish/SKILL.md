---
name: dogent-release-publish
description: Publish an accepted Dogent release according to `dev/package.md`. Use when the user asks to update `CHANGELOG.md`, bump the version in `pyproject.toml`, commit and tag the release, build artifacts, or publish the release to GitHub.
---

# Dogent Release Publish

Prepare and publish an accepted Dogent release using the repo packaging workflow in `dev/package.md`.

## Workflow

1. Read `dev/package.md`, `pyproject.toml`, `CHANGELOG.md`, and the current release status in `dev/sprint_plan.md` and `dev/sprint_uat.md`.
2. Confirm the target release is accepted before publishing. If acceptance is still pending, stop and tell the user what remains open.
3. Update `CHANGELOG.md` with concise user-facing notes for the accepted release.
4. Update the version in `pyproject.toml` and any matching version locations required by the repo if needed.
5. Run the package workflow from `dev/package.md`: build artifacts, smoke-test when requested or when the workflow says it is recommended, and verify the expected files exist in `dist/`.
6. When the user asked for a full release, create the release commit and git tag for the current version, then publish the release to GitHub with the built artifacts.
7. Report the exact version, tag, artifacts, and any steps that were skipped.

## Publish Rules

- Follow `dev/package.md` instead of inventing a release process.
- Keep changelog entries limited to accepted user-visible behavior.
- Use non-interactive git commands.
- If the user asked only to prepare the release, stop before push, tag, or GitHub publishing.
- If packaging or publishing needs network or credentials, request the required approval or surface the blocker clearly.

## Resources

- Read [references/repo-publish-checklist.md](references/repo-publish-checklist.md) for the repo-specific release preparation and publish checklist.
