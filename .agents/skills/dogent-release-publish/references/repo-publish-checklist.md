# Repo Publish Checklist

## Preconditions

- Read `dev/package.md` before running release commands.
- Read the current release section in `dev/sprint_plan.md` and `dev/sprint_uat.md`.
- Publish only after the current release stories are accepted.

## Release Preparation

- Update `CHANGELOG.md` with the accepted user-facing behavior.
- Update `pyproject.toml` to the target version.
- Check for any other repo version locations referenced by `dev/package.md` and keep them aligned.

## Build and Verification

- Create a clean virtual environment when the package workflow requires it.
- Run `python -m build`.
- Verify the expected wheel and sdist exist under `dist/`.
- Smoke-test the built package when requested or when the workflow says it is recommended.

## Git and GitHub Release

- Create a release commit for the version bump and changelog update when needed.
- Create the git tag that matches the version.
- Push the tag and publish the GitHub release with the built artifacts when the user asked for the full release flow.
- Report any skipped remote steps and why.
