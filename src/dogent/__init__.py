"""Dogent package."""

from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path
import re


def _load_version() -> str:
    try:
        return pkg_version("dogent")
    except PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject.exists():
            match = re.search(
                r'^version\s*=\s*"(?P<version>[^"]+)"',
                pyproject.read_text(),
                re.MULTILINE,
            )
            if match:
                return match.group("version")
        return "0.0.0"


__version__: str = _load_version()
