import unittest
from pathlib import Path

from dogent.tool_permissions import extract_delete_targets, should_confirm_tool_use


class ToolPermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cwd = Path("/workspace").resolve()
        self.allowed = [self.cwd, Path("/home/user/.dogent").resolve()]

    def test_outside_read_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "Read",
            {"file_path": "/etc/hosts"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("outside", reason)

    def test_inside_read_no_confirmation(self) -> None:
        needs, _ = should_confirm_tool_use(
            "Read",
            {"file_path": "docs/plan.md"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertFalse(needs)

    def test_delete_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "Bash",
            {"command": "rm -rf temp.txt"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("Delete command", reason)

    def test_bash_outside_path_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "Bash",
            {"command": "cat /etc/hosts"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("outside", reason)

    def test_bash_inside_path_no_confirmation(self) -> None:
        needs, _ = should_confirm_tool_use(
            "Bash",
            {"command": "cat ./docs/plan.md"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertFalse(needs)

    def test_non_delete_bash_no_confirmation(self) -> None:
        needs, _ = should_confirm_tool_use(
            "Bash",
            {"command": "ls -la"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertFalse(needs)

    def test_bash_output_delete_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "BashOutput",
            {"command": "rm -f temp.txt"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("Delete command", reason)

    def test_extract_delete_targets_handles_flags(self) -> None:
        targets = extract_delete_targets("rm -rf -- temp.txt other.txt", cwd=self.cwd)
        self.assertEqual(len(targets), 2)
        self.assertTrue(str(targets[0]).endswith("temp.txt"))
        self.assertTrue(str(targets[1]).endswith("other.txt"))


if __name__ == "__main__":
    unittest.main()
