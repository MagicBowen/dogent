import unittest

from dogent.commands import CommandRegistry


class CommandRegistryTests(unittest.TestCase):
    def test_register_and_lookup(self) -> None:
        registry = CommandRegistry()

        async def dummy_handler(cmd: str) -> bool:  # noqa: ARG001
            return True

        registry.register("config", dummy_handler, "create config")

        self.assertIn("/config", registry.names())
        command = registry.get("/config")
        self.assertIsNotNone(command)
        assert command  # for mypy/pylint
        self.assertEqual(command.handler, dummy_handler)
        descriptions = registry.descriptions()
        self.assertTrue(any("create config" in desc for desc in descriptions))


if __name__ == "__main__":
    unittest.main()
