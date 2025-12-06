import tempfile
from pathlib import Path

from dogent.context import resolve_references


def test_resolve_references_reads_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = Path(tmpdir)
        target = cwd / "note.md"
        target.write_text("hello", encoding="utf-8")
        refs = resolve_references("请阅读 @note.md", cwd)
        assert len(refs) == 1
        assert refs[0].path == "note.md"
        assert "hello" in refs[0].content
