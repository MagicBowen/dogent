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
    def history_file(self) -> Path:
        return self.dogent_dir / "history.json"

    @property
    def global_dir(self) -> Path:
        return Path.home() / ".dogent"

    @property
    def global_profile_file(self) -> Path:
        return self.global_dir / "claude.json"

    @property
    def global_prompts_dir(self) -> Path:
        return self.global_dir / "prompts"

    @property
    def global_templates_dir(self) -> Path:
        return self.global_dir / "templates"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def claude_dir(self) -> Path:
        return self.root / ".claude"
