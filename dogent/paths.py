from dataclasses import dataclass
from pathlib import Path


@dataclass
class DogentPaths:
    """Centralizes filesystem paths for a Dogent workspace."""

    root: Path

    @property
    def dogent_dir(self) -> Path:
        return self.root / ".dogent"

    @property
    def doc_preferences(self) -> Path:
        return self.dogent_dir / "dogent.md"

    @property
    def config_file(self) -> Path:
        return self.dogent_dir / "dogent.json"

    @property
    def memory_file(self) -> Path:
        return self.dogent_dir / "memory.md"

    @property
    def global_profile_file(self) -> Path:
        return Path.home() / ".dogent" / "claude.json"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def claude_dir(self) -> Path:
        return self.root / ".claude"
