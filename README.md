# Dogent

![](./docs/assets/images/dogent-logo.png)

Dogent is a CLI agent focused on **local document writing**, built on the Claude Agent SDK. 

Unlike Claude Code, which targets coding tasks, Dogent provides writing-specific system prompts and document templates, supports multi-format document processing and export, offers a CLI experience optimized for document workflows, and includes state management plus continuous improvement features. It remains compatible with the Claude ecosystem to cover a wide range of local writing scenarios, making AI-assisted document authoring simpler and more efficient.

## Install

> Requires Python 3.10+. A virtual environment is recommended.

### Option A: Install from source

```bash
# Get the source
git clone https://github.com/MagicBowen/dogent
cd dogent

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install (editable)
pip install -e .

# Verify
dogent -v
```

### Option B: Install from a wheel

Download the latest wheel from https://github.com/MagicBowen/dogent/releases.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the wheel
pip install /path/to/dogent-0.9.20-py3-none-any.whl

# Verify
dogent -v
```

## Quick Start

Enter a workspace directory and start Dogent:

```bash
> cd /path/to/your/workspace
> dogent
```

Inside the interactive session, you can initialize the workspace with `/init` or start writing immediately:

```bash
dogent>  Use template @@built-in:technical_blog to write a technical blog about github/MagicBowen/dogent
```

In interactive mode:
- Type `@` to reference files in the workspace.
- Type `@@` to reference available document templates.
- Press Enter to submit; Dogent will plan the task and generate content.
- Press `Esc` to interrupt and provide more info or adjust requirements.

For multi-line input, press `Ctrl+E` to open the CLI markdown editor, then press `Ctrl+J` to submit.

Use `/help` for help and `/exit` to quit.

## Docs

Complete documentation lives in `docs/` (recommended reading order):

1. [docs/01-quickstart.md](docs/01-quickstart.md) - Quick start: install, configure, /init, first run
2. [docs/02-templates.md](docs/02-templates.md) - Templates: built-in/global/workspace templates and @@ overrides
3. [docs/03-editor.md](docs/03-editor.md) - CLI editor: multi-line input, preview, save, vi mode
4. [docs/04-document-export.md](docs/04-document-export.md) - Document export and format conversion
5. [docs/05-lessons.md](docs/05-lessons.md) - Lessons: knowledge capture and reminders
6. [docs/06-history-and-state.md](docs/06-history-and-state.md) - history/memory/lessons and show/archive/clean
7. [docs/07-commands.md](docs/07-commands.md) - Command reference: all commands and shortcuts
8. [docs/08-configuration.md](docs/08-configuration.md) - Configuration: global/workspace, profiles, templates
9. [docs/09-permissions.md](docs/09-permissions.md) - Permissions: prompts and remembered rules
10. [docs/10-claude-compatibility.md](docs/10-claude-compatibility.md) - Claude compatibility: commands/plugins reuse
11. [docs/11-troubleshooting.md](docs/11-troubleshooting.md) - Troubleshooting and debugging
12. [docs/12-appendix.md](docs/12-appendix.md) - Appendix: env vars and third-party API setup
