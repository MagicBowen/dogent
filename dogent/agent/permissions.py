from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
import fnmatch
import os
from typing import Iterable

from ..core.session_log import log_exception

BASH_TOOLS = {"Bash", "BashOutput"}
DELETE_COMMANDS = {"rm", "rmdir", "del", "mv"}
FILE_TOOLS = {"Read", "Write", "Edit"}
PROTECTED_DOGENT_FILES = {Path(".dogent/dogent.md")}


@dataclass(frozen=True)
class PermissionCheck:
    needs_confirm: bool
    reason: str
    targets: list[Path]


def should_confirm_tool_use(
    tool_name: str,
    input_data: dict,
    *,
    cwd: Path,
    allowed_roots: Iterable[Path],
    delete_whitelist: Iterable[Path] | None = None,
    authorizations: dict[str, list[str]] | None = None,
) -> tuple[bool, str]:
    check = evaluate_tool_permission(
        tool_name,
        input_data,
        cwd=cwd,
        allowed_roots=allowed_roots,
        delete_whitelist=delete_whitelist,
        authorizations=authorizations,
    )
    return check.needs_confirm, check.reason


def evaluate_tool_permission(
    tool_name: str,
    input_data: dict,
    *,
    cwd: Path,
    allowed_roots: Iterable[Path],
    delete_whitelist: Iterable[Path] | None = None,
    authorizations: dict[str, list[str]] | None = None,
) -> PermissionCheck:
    check = _collect_permission_targets(
        tool_name,
        input_data,
        cwd=cwd,
        allowed_roots=allowed_roots,
        delete_whitelist=delete_whitelist,
    )
    if not check.needs_confirm:
        return check
    if not authorizations or not check.targets:
        return check
    if _targets_authorized(tool_name, check.targets, authorizations, cwd):
        return PermissionCheck(False, "", check.targets)
    return check


def _collect_permission_targets(
    tool_name: str,
    input_data: dict,
    *,
    cwd: Path,
    allowed_roots: Iterable[Path],
    delete_whitelist: Iterable[Path] | None = None,
) -> PermissionCheck:
    if tool_name in FILE_TOOLS:
        raw_path = _extract_file_path(input_data)
        if not raw_path:
            return PermissionCheck(False, "", [])
        resolved = _resolve_path(raw_path, cwd)
        if not resolved:
            return PermissionCheck(False, "", [])
        if tool_name in {"Write", "Edit"} and _is_existing_protected_file(
            resolved, cwd
        ):
            return PermissionCheck(True, f"Modify protected file: {resolved}", [resolved])
        if _is_outside_allowed_roots(resolved, allowed_roots):
            return PermissionCheck(
                True,
                f"{tool_name} path outside workspace: {resolved}",
                [resolved],
            )
        return PermissionCheck(False, "", [])

    if tool_name in BASH_TOOLS:
        command = str(input_data.get("command") or "")
        targets = extract_delete_targets(command, cwd=cwd)
        if targets:
            remaining = _exclude_whitelisted_targets(targets, delete_whitelist)
            if not remaining:
                return PermissionCheck(False, "", [])
            joined = ", ".join(str(path) for path in remaining)
            return PermissionCheck(True, f"Delete command targets: {joined}", remaining)
        redirections = extract_redirection_targets(command, cwd=cwd)
        protected_redirections = [
            target for target in redirections if _is_existing_protected_file(target, cwd)
        ]
        if protected_redirections:
            joined = ", ".join(str(path) for path in protected_redirections)
            return PermissionCheck(
                True,
                f"Modify protected file via redirection: {joined}",
                protected_redirections,
            )
        paths = extract_command_paths(command, cwd=cwd)
        outside = [
            path
            for path in paths + redirections
            if _is_outside_allowed_roots(path, allowed_roots)
        ]
        if outside:
            joined = ", ".join(str(path) for path in outside)
            return PermissionCheck(
                True,
                f"Bash command targets outside workspace: {joined}",
                outside,
            )
        return PermissionCheck(False, "", [])

    return PermissionCheck(False, "", [])


def _targets_authorized(
    tool_name: str,
    targets: Iterable[Path],
    authorizations: dict[str, list[str]],
    cwd: Path,
) -> bool:
    patterns = authorizations.get(tool_name)
    if not patterns:
        return False
    normalized_patterns = [
        _normalize_authorization_pattern(pattern, cwd) for pattern in patterns
    ]
    normalized_patterns = [pattern for pattern in normalized_patterns if pattern]
    if not normalized_patterns:
        return False
    for target in targets:
        target_str = target.resolve().as_posix()
        if not any(
            fnmatch.fnmatchcase(target_str, pattern)
            for pattern in normalized_patterns
        ):
            return False
    return True


def _normalize_authorization_pattern(pattern: str, cwd: Path) -> str:
    raw = pattern.strip()
    if not raw:
        return ""
    expanded = os.path.expanduser(raw)
    if os.path.isabs(expanded):
        normalized = os.path.normpath(expanded)
    else:
        normalized = os.path.normpath(str(cwd / expanded))
    return Path(normalized).as_posix()


def extract_delete_targets(command: str, *, cwd: Path) -> list[Path]:
    tokens = _split_command(command)
    if not tokens:
        return []
    cmd = tokens[0]
    if cmd not in DELETE_COMMANDS:
        return []
    if cmd == "mv":
        return _extract_mv_sources(tokens[1:], cwd=cwd)
    return _extract_flagged_paths(tokens[1:], cwd=cwd)


def extract_redirection_targets(command: str, *, cwd: Path) -> list[Path]:
    tokens = _split_command(command)
    if not tokens:
        return []
    targets: list[Path] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if token in {">", ">>", "1>", "2>", "1>>", "2>>"}:
            if idx + 1 < len(tokens):
                resolved = _resolve_path(tokens[idx + 1], cwd)
                if resolved:
                    targets.append(resolved)
            idx += 2
            continue
        if ">" in token:
            candidate = token.split(">")[-1]
            if candidate:
                resolved = _resolve_path(candidate, cwd)
                if resolved:
                    targets.append(resolved)
        idx += 1
    return targets


def extract_command_paths(command: str, *, cwd: Path) -> list[Path]:
    tokens = _split_command(command)
    if not tokens:
        return []
    paths: list[Path] = []
    for token in tokens[1:]:
        path = _token_to_path(token, cwd)
        if path:
            paths.append(path)
    return paths


def _split_command(command: str) -> list[str]:
    command = command.strip()
    if not command:
        return []
    try:
        return shlex.split(command)
    except ValueError as exc:
        log_exception("permissions", exc)
        return command.split()


def _extract_mv_sources(tokens: list[str], *, cwd: Path) -> list[Path]:
    sources: list[Path] = []
    treat_as_paths = False
    target_dir: str | None = None
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        if not treat_as_paths and token == "--":
            treat_as_paths = True
            idx += 1
            continue
        if not treat_as_paths and token in {"-t", "--target-directory"}:
            if idx + 1 < len(tokens):
                target_dir = tokens[idx + 1]
                idx += 2
                continue
        if not treat_as_paths and token.startswith("--target-directory="):
            target_dir = token.split("=", 1)[1]
            idx += 1
            continue
        if not treat_as_paths and token.startswith("-"):
            idx += 1
            continue
        sources.append(token)
        idx += 1
    if target_dir is None and len(sources) > 1:
        sources = sources[:-1]
    resolved_sources: list[Path] = []
    for token in sources:
        resolved = _resolve_path(token, cwd)
        if resolved:
            resolved_sources.append(resolved)
    return resolved_sources


def _extract_flagged_paths(tokens: list[str], *, cwd: Path) -> list[Path]:
    targets: list[Path] = []
    treat_as_paths = False
    for token in tokens:
        if not treat_as_paths and token == "--":
            treat_as_paths = True
            continue
        if not treat_as_paths and token.startswith("-"):
            continue
        resolved = _resolve_path(token, cwd)
        if resolved:
            targets.append(resolved)
    return targets


def _extract_file_path(input_data: dict) -> str:
    for key in ("file_path", "path"):
        value = input_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _resolve_path(raw_path: str, cwd: Path) -> Path | None:
    raw_path = raw_path.strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _token_to_path(token: str, cwd: Path) -> Path | None:
    token = token.strip()
    if not token or token.startswith("-"):
        return None
    if "://" in token:
        return None
    if "=" in token:
        _, value = token.split("=", 1)
        value = value.strip()
        if value.startswith(("/", "~", ".", "..")):
            return _resolve_path(_expand_home(value), cwd)
        return None
    if token.startswith(("/", "~", ".", "..")) or "/" in token:
        return _resolve_path(_expand_home(token), cwd)
    return None


def _expand_home(raw_path: str) -> str:
    if raw_path.startswith("~"):
        return str(Path(raw_path).expanduser())
    return raw_path


def _is_outside_allowed_roots(path: Path, roots: Iterable[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return False
        except Exception as exc:
            log_exception("permissions", exc)
            continue
    return True


def _exclude_whitelisted_targets(
    targets: Iterable[Path], delete_whitelist: Iterable[Path] | None
) -> list[Path]:
    if not delete_whitelist:
        return list(targets)
    whitelist = {path.resolve() for path in delete_whitelist}
    remaining: list[Path] = []
    for target in targets:
        if target.resolve() in whitelist:
            continue
        remaining.append(target)
    return remaining


def _is_existing_protected_file(path: Path, cwd: Path) -> bool:
    resolved = path.resolve()
    for rel in PROTECTED_DOGENT_FILES:
        candidate = (cwd / rel).resolve()
        if resolved == candidate and candidate.exists():
            return True
    return False
