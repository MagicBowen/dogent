import tempfile
import unittest
from pathlib import Path

from dogent.agent.permissions import extract_delete_targets, should_confirm_tool_use


class ToolPermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cwd = Path(self.temp_dir.name).resolve()
        self.allowed = [self.cwd]

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

    def test_outside_home_dogent_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "Read",
            {"file_path": "/home/user/.dogent/dogent.json"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("outside", reason)

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

    def test_delete_whitelist_skips_confirmation(self) -> None:
        memory_path = self.cwd / ".dogent" / "memory.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text("note", encoding="utf-8")
        needs, _ = should_confirm_tool_use(
            "Bash",
            {"command": f"rm -f {memory_path}"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
            delete_whitelist=[memory_path],
        )
        self.assertFalse(needs)

    def test_mv_requires_confirmation(self) -> None:
        needs, reason = should_confirm_tool_use(
            "Bash",
            {"command": "mv a.txt b.txt"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("Delete command", reason)

    def test_protected_dogent_md_requires_confirmation(self) -> None:
        protected = self.cwd / ".dogent" / "dogent.md"
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_text("x", encoding="utf-8")
        needs, reason = should_confirm_tool_use(
            "Write",
            {"file_path": str(protected)},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("protected", reason)

    def test_protected_dogent_json_requires_confirmation(self) -> None:
        protected = self.cwd / ".dogent" / "dogent.json"
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_text("{}", encoding="utf-8")
        needs, reason = should_confirm_tool_use(
            "Edit",
            {"file_path": str(protected)},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertFalse(needs)
        self.assertEqual(reason, "")

    def test_protected_dogent_creation_no_confirmation(self) -> None:
        protected = self.cwd / ".dogent" / "dogent.md"
        needs, _ = should_confirm_tool_use(
            "Write",
            {"file_path": str(protected)},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertFalse(needs)

    def test_bash_redirection_to_protected_file_requires_confirmation(self) -> None:
        protected = self.cwd / ".dogent" / "dogent.md"
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_text("x", encoding="utf-8")
        needs, reason = should_confirm_tool_use(
            "Bash",
            {"command": "echo hi > .dogent/dogent.md"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
        )
        self.assertTrue(needs)
        self.assertIn("protected", reason)

    def test_authorizations_skip_outside_read(self) -> None:
        resolved_hosts = Path("/etc/hosts").resolve()
        pattern = str(resolved_hosts.parent / "*")
        needs, reason = should_confirm_tool_use(
            "Read",
            {"file_path": "/etc/hosts"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
            authorizations={"Read": [pattern]},
        )
        self.assertFalse(needs)
        self.assertEqual(reason, "")

    def test_authorizations_skip_protected_file(self) -> None:
        protected = self.cwd / ".dogent" / "dogent.md"
        protected.parent.mkdir(parents=True, exist_ok=True)
        protected.write_text("x", encoding="utf-8")
        needs, _ = should_confirm_tool_use(
            "Write",
            {"file_path": str(protected)},
            cwd=self.cwd,
            allowed_roots=self.allowed,
            authorizations={"Write": [str(protected)]},
        )
        self.assertFalse(needs)

    def test_authorizations_require_all_targets(self) -> None:
        first = self.cwd / "a.txt"
        second = self.cwd / "b.txt"
        needs, _ = should_confirm_tool_use(
            "Bash",
            {"command": f"rm -f {first} {second}"},
            cwd=self.cwd,
            allowed_roots=self.allowed,
            authorizations={"Bash": [str(first)]},
        )
        self.assertTrue(needs)


if __name__ == "__main__":
    unittest.main()
