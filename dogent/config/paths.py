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
    def doc_templates_dir(self) -> Path:
        return self.dogent_dir / "templates"

    @property
    def memory_file(self) -> Path:
        return self.dogent_dir / "memory.md"

    @property
    def history_file(self) -> Path:
        return self.dogent_dir / "history.json"

    @property
    def lessons_file(self) -> Path:
        return self.dogent_dir / "lessons.md"

    @property
    def archives_dir(self) -> Path:
        return self.dogent_dir / "archives"

    @property
    def global_dir(self) -> Path:
        return Path.home() / ".dogent"

    @property
    def global_config_file(self) -> Path:
        return self.global_dir / "dogent.json"

    @property
    def global_schema_file(self) -> Path:
        return self.global_dir / "dogent.schema.json"

    @property
    def global_templates_dir(self) -> Path:
        return self.global_dir / "templates"

    @property
    def global_pdf_style_file(self) -> Path:
        return self.global_dir / "pdf_style.css"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def claude_dir(self) -> Path:
        return self.root / ".claude"
