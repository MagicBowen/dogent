## Package and Publish to Github

1. Start clean in a new venv

  python3 -m venv .venv
  source .venv/bin/activate          # .venv\Scripts\activate on Windows
  python -m pip install --upgrade pip build twine

  2. Set the version (if needed)

  - Ensure pyproject.toml (and any init.py with version) reads 0.1.0.
  - Commit that version bump before tagging.

  3. Build the artifacts

  python -m build    # outputs dist/dogent-0.1.0-py3-none-any.whl and dist/dogent-0.1.0.tar.gz

  4. Smoke-test the wheel in a fresh venv (optional but recommended)

  deactivate
  python3 -m venv .venv-test
  source .venv-test/bin/activate
  python -m pip install dist/dogent-0.1.0-py3-none-any.whl
  dogent --version      # or run a tiny plan to confirm it works
  deactivate

  5. Tag the release in git

  git tag v0.1.0
  git push origin v0.1.0

  6. Create the GitHub release and upload artifacts

  - Go to GitHub → Releases → “Draft a new release”.
  - Choose tag v0.1.0, add a title/notes.
  - Upload both files from dist/:
      - dogent-0.1.0-py3-none-any.whl
      - dogent-0.1.0.tar.gz
  - Publish the release.

  7. How users install from the GitHub release

  pip install https://github.com/<org>/<repo>/releases/download/v0.1.0/dogent-0.1.0-py3-none-any.whl
  # or the sdist:
  pip install https://github.com/<org>/<repo>/releases/download/v0.1.0/dogent-0.1.0.tar.gz

