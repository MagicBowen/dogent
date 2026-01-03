import json
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
            files = list(logs_dir.glob("dogent_session_*.json"))
            self.assertEqual(len(files), 1)
            lines = files[0].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload["role"], "system")
            self.assertEqual(payload["event"], "prompt.system")
            self.assertEqual(payload["content"], "system text")

    def test_log_user_prompt_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = DogentPaths(Path(tmp))
            logger = SessionLogger(paths, enabled=True)
            logger.log_user_prompt("agent", "hello")
            logger.close()
            logs_dir = paths.dogent_dir / "logs"
            files = list(logs_dir.glob("dogent_session_*.json"))
            self.assertEqual(len(files), 1)
            payload = json.loads(files[0].read_text(encoding="utf-8").strip())
            self.assertEqual(payload["role"], "user")
            self.assertEqual(payload["event"], "prompt.user")
            self.assertEqual(payload["content"], "hello")

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
            files = list(logs_dir.glob("dogent_session_*.json"))
            self.assertEqual(len(files), 1)
            lines = files[0].read_text(encoding="utf-8").splitlines()
            events = [json.loads(line)["event"] for line in lines]
            self.assertIn("assistant.text", events)
            self.assertIn("assistant.thinking", events)
            self.assertIn("assistant.tool_use", events)
            self.assertIn("assistant.tool_result", events)
            self.assertIn("assistant.result", events)


if __name__ == "__main__":
    unittest.main()
