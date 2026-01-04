import tempfile
import unittest
from pathlib import Path

from dogent.paths import DogentPaths
from dogent.session_log import SessionLogger


class SessionLoggerTests(unittest.TestCase):
    def test_logger_disabled_creates_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=False)
            logger.log_user_prompt("agent", "hello")
            logs_dir = paths.dogent_dir / "logs"
            self.assertFalse(logs_dir.exists())

    def test_log_system_prompt_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=True)
            logger.log_system_prompt("agent", "system text")
            logger.log_system_prompt("agent", "system text")
            logger.close()
            logs_dir = paths.dogent_dir / "logs"
            files = list(logs_dir.glob("dogent_session_*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("# Dogent Session Log", text)
            self.assertEqual(text.count("prompt.system"), 1)
            self.assertIn("system text", text)

    def test_log_user_prompt_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=True)
            logger.log_user_prompt("agent", "hello")
            logger.close()
            logs_dir = paths.dogent_dir / "logs"
            files = list(logs_dir.glob("dogent_session_*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("prompt.user", text)
            self.assertIn("hello", text)

    def test_log_block_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=True)
            logger.log_assistant_text("agent", "text")
            logger.log_assistant_thinking("agent", "thinking")
            logger.log_tool_use("agent", name="Read", tool_id="1", input_data={"path": "a"})
            logger.log_tool_result(
                "agent", name="Read", tool_id="1", content="ok", is_error=False
            )
            logger.log_result("agent", result="done", is_error=False)
            logger.close()
            logs_dir = paths.dogent_dir / "logs"
            files = list(logs_dir.glob("dogent_session_*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("assistant.text", text)
            self.assertIn("assistant.thinking", text)
            self.assertIn("assistant.tool_use", text)
            self.assertIn("assistant.tool_result", text)
            self.assertIn("assistant.result", text)

    def test_log_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=True)
            try:
                raise ValueError("boom")
            except Exception as exc:  # noqa: BLE001
                logger.log_exception("agent", exc)
            logger.close()
            logs_dir = paths.dogent_dir / "logs"
            files = list(logs_dir.glob("dogent_session_*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn("exception", text)
            self.assertIn("ValueError", text)


if __name__ == "__main__":
    unittest.main()
