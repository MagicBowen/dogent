import importlib.metadata
import unittest

import dogent


class VersionTests(unittest.TestCase):
    def test_version_matches_metadata(self) -> None:
        meta_version = importlib.metadata.version("dogent")
        self.assertEqual(dogent.__version__, meta_version)

    def test_claude_agent_sdk_meets_release_baseline(self) -> None:
        sdk_version = importlib.metadata.version("claude-agent-sdk")
        numeric = tuple(int(part) for part in sdk_version.split(".")[:3])
        self.assertGreaterEqual(numeric, (0, 2, 115))


if __name__ == "__main__":
    unittest.main()
