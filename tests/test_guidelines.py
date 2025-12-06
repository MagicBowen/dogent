import tempfile
from pathlib import Path

from dogent import guidelines


def test_ensure_guidelines_creates_file_with_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        path = guidelines.ensure_guidelines(cwd)
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "文档编写规范" in text
        # calling again should not overwrite
        text_before = text
        path2 = guidelines.ensure_guidelines(cwd)
        assert path2 == path
        assert path.read_text(encoding="utf-8") == text_before


def test_ensure_guidelines_migrates_legacy_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        legacy = cwd / ".claude.md"
        legacy.write_text("legacy rules", encoding="utf-8")
        path = guidelines.ensure_guidelines(cwd)
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "legacy rules"
        assert not legacy.exists()
