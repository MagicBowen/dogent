#!/usr/bin/env python3
"""Prepare packaged Claude plugin skills from the upstream skills checkout."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


DEFAULT_MANIFEST = Path("dogent/plugins/claude/skills_manifest.json")


class PrepareError(RuntimeError):
    """Raised when Claude plugin skill preparation cannot continue."""


@dataclass(frozen=True)
class SkillsManifest:
    source: Path
    target: Path
    skills: tuple[str, ...]


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def default_runner(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise PrepareError(f"Cannot locate repository root from {start}")


def load_manifest(path: Path, repo_root: Path) -> SkillsManifest:
    repo_root = repo_root.resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PrepareError(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PrepareError(f"Manifest is not valid JSON: {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise PrepareError("Manifest root must be a JSON object")

    source = _manifest_path(raw.get("source"), repo_root, "source")
    target = _manifest_path(raw.get("target"), repo_root, "target")
    raw_skills = raw.get("skills")
    if not isinstance(raw_skills, list):
        raise PrepareError("Manifest field 'skills' must be a list")

    skills: list[str] = []
    for value in raw_skills:
        if not isinstance(value, str) or not value.strip():
            raise PrepareError("Manifest field 'skills' must contain non-empty strings")
        cleaned = value.strip()
        if "/" in cleaned or "\\" in cleaned or cleaned in {".", ".."}:
            raise PrepareError(f"Invalid skill name in manifest: {cleaned!r}")
        skills.append(cleaned)

    return SkillsManifest(source=source, target=target, skills=tuple(skills))


def _manifest_path(value: object, repo_root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PrepareError(f"Manifest field {field!r} must be a non-empty string")
    path = Path(value.strip())
    if path.is_absolute():
        raise PrepareError(f"Manifest field {field!r} must be repo-relative")
    return (repo_root / path).resolve()


def update_submodule(
    repo_root: Path,
    submodule_path: Path,
    runner: CommandRunner = default_runner,
) -> tuple[bool, str]:
    rel_path = _relative_to_repo(submodule_path, repo_root)
    result = runner(
        ["git", "submodule", "update", "--init", "--remote", str(rel_path)],
        repo_root,
    )
    output = _combined_output(result)
    return result.returncode == 0, output


def submodule_commit(
    repo_root: Path,
    submodule_path: Path,
    runner: CommandRunner = default_runner,
) -> str:
    rel_path = _relative_to_repo(submodule_path, repo_root)
    result = runner(["git", "-C", str(rel_path), "rev-parse", "HEAD"], repo_root)
    if result.returncode != 0:
        raise PrepareError(
            f"Cannot determine submodule commit for {rel_path}: {_combined_output(result)}"
        )
    return result.stdout.strip()


def prepare_skills(
    manifest_path: Path,
    repo_root: Path,
    *,
    runner: CommandRunner = default_runner,
    out: Callable[[str], None] = print,
) -> list[str]:
    repo_root = repo_root.resolve()
    manifest = load_manifest(manifest_path, repo_root)
    submodule_path = _resolve_submodule_root(manifest.source, repo_root)

    update_ok, update_output = update_submodule(repo_root, submodule_path, runner)
    if not update_ok:
        out(
            "Warning: failed to update claude/skills submodule; "
            "continuing with current checkout."
        )
        if update_output:
            out(update_output)

    _validate_source(manifest.source)
    commit = submodule_commit(repo_root, submodule_path, runner)

    if manifest.target.exists():
        shutil.rmtree(manifest.target)
    manifest.target.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for skill in manifest.skills:
        source_dir = manifest.source / skill
        if not source_dir.is_dir():
            raise PrepareError(f"Requested skill not found in source: {skill}")
        if not (source_dir / "SKILL.md").is_file():
            raise PrepareError(f"Requested skill is missing SKILL.md: {skill}")
        shutil.copytree(source_dir, manifest.target / skill)
        copied.append(skill)

    out(f"Claude skills source commit: {commit}")
    if copied:
        out("Copied Claude plugin skills: " + ", ".join(copied))
    else:
        out("Copied Claude plugin skills: none")
    return copied


def _resolve_submodule_root(source: Path, repo_root: Path) -> Path:
    try:
        source.relative_to(repo_root)
    except ValueError as exc:
        raise PrepareError("Manifest source must resolve inside the repository") from exc

    parts = source.relative_to(repo_root).parts
    if len(parts) < 2 or parts[:2] != ("claude", "skills"):
        raise PrepareError("Manifest source must be inside claude/skills")
    return repo_root / "claude" / "skills"


def _validate_source(source: Path) -> None:
    if not source.is_dir():
        raise PrepareError(
            f"Skill source directory not found: {source}. "
            "Run git submodule update --init --recursive."
        )


def _relative_to_repo(path: Path, repo_root: Path) -> Path:
    try:
        return path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PrepareError(f"Path is outside repository: {path}") from exc


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Dogent's packaged Claude plugin skills."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Repo-relative or absolute path to the skills manifest.",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo_root = find_repo_root(Path.cwd())
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path
        prepare_skills(manifest_path.resolve(), repo_root)
    except PrepareError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
