import importlib.metadata
import unittest

import dogent


class VersionTests(unittest.TestCase):
    def test_version_matches_metadata(self) -> None:
        meta_version = importlib.metadata.version("dogent")
        self.assertEqual(dogent.__version__, meta_version)


if __name__ == "__main__":
    unittest.main()
