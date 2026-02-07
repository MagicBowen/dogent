import os
import tempfile
import unittest
from pathlib import Path

from rich.console import Console

from dogent.agent.runner import AgentRunner
from dogent.config import ConfigManager
from dogent.config.paths import DogentPaths
from dogent.core.history import HistoryManager
from dogent.core.todo import TodoManager
from dogent.prompts import PromptBuilder


class TempFileTrackingTests(unittest.TestCase):
    def _make_runner(self, root: Path, home: str) -> AgentRunner:
        os.environ["HOME"] = home
        paths = DogentPaths(root)
        config = ConfigManager(paths)
        history = HistoryManager(paths)
        console = Console(record=True, force_terminal=False, color_system=None)
        todo_manager = TodoManager(console=console)
        prompt_builder = PromptBuilder(paths, todo_manager, history, console=console)
        return AgentRunner(
            config=config,
            prompt_builder=prompt_builder,
            todo_manager=todo_manager,
            history=history,
            console=console,
        )

    def test_track_temp_file_write_registers_new_path(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            runner = self._make_runner(Path(tmp), tmp_home)
            temp_root = Path(tempfile.gettempdir()).resolve()
            path = temp_root / "dogent-temp-write.txt"
            if path.exists():
                path.unlink()
            runner._track_temp_files("Write", {"file_path": str(path)})
            self.assertIn(path.resolve(), runner._task_temp_files)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_track_temp_file_write_skips_existing(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            runner = self._make_runner(Path(tmp), tmp_home)
            temp_root = Path(tempfile.gettempdir()).resolve()
            path = temp_root / "dogent-temp-existing.txt"
            path.write_text("x", encoding="utf-8")
            runner._track_temp_files("Write", {"file_path": str(path)})
            self.assertNotIn(path.resolve(), runner._task_temp_files)
            path.unlink()
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)

    def test_track_temp_file_bash_redirection(self) -> None:
        original_home = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            runner = self._make_runner(Path(tmp), tmp_home)
            temp_root = Path(tempfile.gettempdir()).resolve()
            path = temp_root / "dogent-temp-redirect.txt"
            if path.exists():
                path.unlink()
            runner._track_temp_files("Bash", {"command": f"echo hi > {path}"})
            self.assertIn(path.resolve(), runner._task_temp_files)
        if original_home is not None:
            os.environ["HOME"] = original_home
        else:
            os.environ.pop("HOME", None)


if __name__ == "__main__":
    unittest.main()
