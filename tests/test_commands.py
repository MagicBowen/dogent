import unittest

from dogent.cli.commands import CommandRegistry


class CommandRegistryTests(unittest.TestCase):
    def test_register_and_lookup(self) -> None:
        registry = CommandRegistry()

        async def dummy_handler(cmd: str) -> bool:  # noqa: ARG001
            return True

        registry.register("init", dummy_handler, "create init")

        self.assertIn("/init", registry.names())
        command = registry.get("/init")
        self.assertIsNotNone(command)
        assert command  # for mypy/pylint
        self.assertEqual(command.handler, dummy_handler)
        descriptions = registry.descriptions()
        self.assertTrue(any("create init" in desc for desc in descriptions))


if __name__ == "__main__":
    unittest.main()
