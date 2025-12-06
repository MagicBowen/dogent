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
